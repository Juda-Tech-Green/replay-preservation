"""Bounded ISO 9660/Joliet metadata inspection gated by ddrescue byte coverage.

Only regular image files are opened. No mounting, extraction, execution or device I/O.
Unsupported/interleaved files and unavailable metadata remain explicitly unknown.
"""
import hashlib
import os
import stat
import struct
from collections import Counter
from pathlib import Path

SECTOR = 2048
FULL = 'fully covered by recovered sectors'
PARTIAL = 'partially covered'
OUTSIDE = 'entirely outside recovered regions'
UNKNOWN = 'coverage unknown; unsupported layout'


def coverage(ranges, offset, length, image_size, holes=()):
    if offset < 0 or length < 0:
        raise ValueError('Negative file extent')
    if length == 0:
        return {'length':0,'recovered_bytes':0,'missing_bytes':0,'status_bytes':{},'missing_ranges':[], 'empty':True}
    end=offset+length
    points={offset,end}
    for item in ranges:
        for value in (item['offset'],item['offset']+item['length']):
            if offset < value < end:points.add(value)
    if offset < image_size < end:points.add(image_size)
    for start,size in holes:
        for value in (start,start+size):
            if offset < value < end:points.add(value)
    totals=Counter(); missing=[]
    points=sorted(points)
    for left,right in zip(points,points[1:]):
        item=next((item for item in ranges if item['offset']<=left<item['offset']+item['length']),None)
        status=item['status'] if item else 'unmapped'
        # Mapfile '+' alone is insufficient when bytes do not exist or are sparse holes.
        if status=='+':
            if left>=image_size:status='image EOF'
            elif any(start<=left<start+size for start,size in holes):status='sparse hole'
        totals[status]+=right-left
        if status!='+':missing.append({'offset':left,'length':right-left,'status':status})
    return {'length':length,'recovered_bytes':totals['+'],'missing_bytes':length-totals['+'],
            'status_bytes':dict(totals),'missing_ranges':missing,'empty':False}


def image_holes(path):
    """Capture host filesystem sparse extents; no inference from zero byte content."""
    holes=[]
    with Path(path).open('rb') as stream:
        size=os.fstat(stream.fileno()).st_size
        position=0
        while position<size:
            try:
                data=os.lseek(stream.fileno(),position,os.SEEK_DATA)
            except OSError as error:
                if error.errno==6: # ENXIO: no more data
                    holes.append((position,size-position));break
                return None
            if data>position:holes.append((position,data-position))
            try:
                position=os.lseek(stream.fileno(),data,os.SEEK_HOLE)
            except OSError:
                return None
    return holes


def both32(data, offset):
    little=struct.unpack_from('<I',data,offset)[0]
    big=struct.unpack_from('>I',data,offset+4)[0]
    if little!=big:raise ValueError('Inconsistent both-endian 32-bit ISO field')
    return little


def both16(data, offset):
    little=struct.unpack_from('<H',data,offset)[0]
    big=struct.unpack_from('>H',data,offset+2)[0]
    if little!=big:raise ValueError('Inconsistent both-endian 16-bit ISO field')
    return little


def directory_record(data, offset, joliet):
    length=data[offset]
    if length<34 or offset+length>len(data):raise ValueError('Truncated ISO directory record')
    record=data[offset:offset+length]
    name_length=record[32]
    if 33+name_length>length:raise ValueError('Invalid ISO directory identifier length')
    identifier=record[33:33+name_length]
    special=identifier in (b'\0',b'\1')
    name=('.' if identifier==b'\0' else '..') if special else identifier.decode('utf-16-be' if joliet else 'ascii',errors='strict')
    if not special and (name in ('','.', '..') or '/' in name or '\x00' in name):
        raise ValueError('Invalid ISO path component')
    return {'record_length':length,'raw_name':name,'name':name.rsplit(';',1)[0] if not special and ';' in name else name,
            'extent_lba':both32(record,2),'length':both32(record,10),'flags':record[25],
            'extended_attribute_blocks':record[1],'file_unit_size':record[26],
            'interleave_gap':record[27],'volume_sequence':both16(record,28),
            'recording_timestamp_hex':record[18:25].hex(),
            'system_use_hex':record[33+name_length+(0 if name_length%2 else 1):].hex()}


class Inspector:
    def __init__(self,path,ranges,holes=None):
        self.path=Path(path)
        if self.path.is_symlink() or not stat.S_ISREG(self.path.stat().st_mode):
            raise ValueError('ISO input must be a regular non-symlink image')
        self.size=self.path.stat().st_size
        self.ranges=ranges
        self.holes=image_holes(path) if holes is None else holes
        if self.holes is None:
            raise ValueError('Host filesystem cannot report sparse extents; refuse unsupported sparse interpretation')
        self.metadata_reads=[]
        self.warnings=[]

    def read(self, offset, size):
        result=coverage(self.ranges,offset,size,self.size,self.holes)
        if result['missing_bytes']:
            raise ValueError(f'Metadata unavailable at {offset}+{size}: {result["missing_ranges"]}')
        with self.path.open('rb') as stream:
            stream.seek(offset);data=stream.read(size)
        if len(data)!=size:raise ValueError('Unexpected EOF in verified recovered metadata')
        self.metadata_reads.append({'offset':offset,'length':size})
        return data

    def descriptors(self):
        results=[]
        for lba in range(16,80):
            data=self.read(lba*SECTOR,SECTOR)
            if data[1:6]!=b'CD001' or data[6]!=1:
                raise ValueError('Not a supported cooked ISO 9660 descriptor at expected image origin')
            kind=data[0]
            if kind==255:return results
            if kind not in (1,2):
                self.warnings.append(f'Descriptor type {kind} retained at LBA {lba}, not interpreted');continue
            joliet=kind==2 and data[88:91] in (b'%/@',b'%/C',b'%/E')
            if kind==2 and not joliet:
                self.warnings.append(f'Non-Joliet supplementary descriptor at LBA {lba} not interpreted');continue
            block_size=both16(data,128)
            if block_size!=SECTOR:raise ValueError('Unsupported ISO logical block size')
            namespace='Joliet' if joliet else 'ISO9660'
            sequence=both16(data,124)
            if sequence==0:
                self.warnings.append(f'{namespace}: nonstandard zero volume sequence retained; directory records must match it')
            results.append({'namespace':namespace,'descriptor_lba':lba,
                'volume_label':data[40:72].decode('utf-16-be' if joliet else 'ascii').strip(' \0'),
                'volume_blocks':both32(data,80),'block_size':block_size,
                'volume_sequence':sequence,'volume_set_size':both16(data,120),
                'path_table_size':both32(data,132),
                'little_endian_path_table_lba':struct.unpack_from('<I',data,140)[0],
                'big_endian_path_table_lba':struct.unpack_from('>I',data,148)[0],
                'escape_sequence_hex':data[88:91].hex(),
                'root':directory_record(data,156,joliet)})
        raise ValueError('No ISO volume descriptor terminator within bounded descriptor scan')

    def tree(self, descriptor):
        joliet=descriptor['namespace']=='Joliet'
        files=[]; directories=[]; errors=[]; seen=set()
        volume_end=descriptor['volume_blocks']*SECTOR
        def visit(record,prefix,depth=0):
            if depth>64:raise ValueError('Directory depth exceeds inspection bound')
            key=(record['extent_lba'],record['length'])
            if key in seen:raise ValueError('Cyclic or aliased directory extent')
            seen.add(key)
            start=(record['extent_lba']+record['extended_attribute_blocks'])*SECTOR
            if record['length']>16*1024**2 or start+record['length']>volume_end:
                raise ValueError('Directory extent outside validated bounds')
            if record['file_unit_size'] or record['interleave_gap']:
                raise ValueError('Interleaved directory not supported')
            directories.append({'path':prefix or '/', 'offset':start,'length':record['length']})
            try:data=self.read(start,record['length'])
            except ValueError as error:
                errors.append({'path':prefix or '/','error':str(error)});return
            position=0; pending=None
            while position<len(data):
                if data[position]==0:
                    position=((position//SECTOR)+1)*SECTOR;continue
                record_offset=position
                if position%SECTOR+data[position]>SECTOR:
                    raise ValueError('Directory record crosses logical sector boundary')
                item=directory_record(data,position,joliet)
                position+=item['record_length']
                if item['name'] in ('.','..'):continue
                path=f'{prefix}/{item["name"]}' if prefix else item['name']
                extent={'offset':(item['extent_lba']+item['extended_attribute_blocks'])*SECTOR,
                        'length':item['length'],'extent_lba':item['extent_lba'],
                        'record_image_offset':start+record_offset}
                extent['beyond_declared_volume']=extent['offset']+extent['length']>volume_end
                if extent['beyond_declared_volume']:
                    self.warnings.append(f'{descriptor["namespace"]}: {path} extends beyond declared ISO volume; retain its recorded extent without repairing metadata')
                if item['volume_sequence']!=descriptor['volume_sequence']:
                    if (item['volume_sequence']==0 and descriptor['root']['volume_sequence']==0
                            and descriptor['volume_sequence']==1 and descriptor['volume_set_size']==1):
                        warning=f'{descriptor["namespace"]}: nonconformant zero directory volume sequence interpreted within declared single volume; corroborate with independent parser'
                        if warning not in self.warnings:self.warnings.append(warning)
                    else:
                        raise ValueError('Directory record references a different volume')
                if item['flags']&2:
                    if pending:raise ValueError('Unterminated multi-extent file')
                    visit(item,path,depth+1);continue
                unsupported=bool(item['file_unit_size'] or item['interleave_gap'])
                if pending:
                    if pending['path']!=path:raise ValueError('Nonconsecutive multi-extent file records')
                    pending['extents'].append(extent)
                    pending['file_size']+=item['length']
                    pending['unsupported_layout'] |= unsupported
                else:
                    pending={'path':path,'raw_name':item['raw_name'],'file_size':item['length'],
                             'extents':[extent],'unsupported_layout':unsupported,
                             'recording_timestamp_hex':item['recording_timestamp_hex'],
                             'flags':item['flags']}
                if not item['flags']&128:
                    files.append(pending);pending=None
                if len(files)>100000:raise ValueError('ISO file count exceeds inspection bound')
            if pending:raise ValueError('Incomplete multi-extent file record chain')
        visit(descriptor['root'],'')
        names=[item['path'] for item in files]
        if len(names)!=len(set(names)):raise ValueError('Duplicate canonical paths in one namespace')
        return {'namespace':descriptor['namespace'],'files':files,'directories':directories,'errors':errors,
                'metadata_complete':not errors}

    def annotate(self, tree):
        for item in tree['files']:
            checks=[coverage(self.ranges,extent['offset'],extent['length'],self.size,self.holes) for extent in item['extents']]
            item['recovered_bytes']=sum(check['recovered_bytes'] for check in checks)
            item['missing_bytes']=sum(check['missing_bytes'] for check in checks)
            item['missing_ranges']=[missing for check in checks for missing in check['missing_ranges']]
            sector_checks=[coverage(self.ranges,extent['offset'],((extent['length']+SECTOR-1)//SECTOR)*SECTOR,
                                    self.size,self.holes) for extent in item['extents']]
            item['sector_coverage_complete']=all(not check['missing_bytes'] for check in sector_checks)
            item['coverage_status']=(UNKNOWN if item['unsupported_layout'] else
                FULL if item['sector_coverage_complete'] else
                PARTIAL if item['recovered_bytes'] else OUTSIDE)
            item['file_sha256']=None
            item['integrity_status']='not independently established'
            if item['coverage_status']==FULL:
                digest=hashlib.sha256()
                with self.path.open('rb') as stream:
                    for extent in item['extents']:
                        stream.seek(extent['offset']);remaining=extent['length']
                        while remaining:
                            block=stream.read(min(1024*1024,remaining))
                            if not block:raise ValueError('Unexpected EOF in covered file')
                            digest.update(block);remaining-=len(block)
                item['file_sha256']=digest.hexdigest()
        return tree
