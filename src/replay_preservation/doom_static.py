"""Bounded static checks for DOS MZ executables and Doom WAD containers. No execution."""
import struct
from collections import Counter


def mz_header(data):
    if len(data)<64 or data[:2]!=b'MZ':raise ValueError('Missing/truncated MZ header')
    fields=struct.unpack_from('<14H',data)
    _,last,pages,relocs,paragraphs,minmem,maxmem,ss,sp,checksum,ip,cs,reloff,overlay=fields
    declared=(pages-1)*512+(last or 512) if pages else 0
    header_size=paragraphs*16
    if not pages or last>511 or header_size<28 or not header_size<=declared<=len(data):
        raise ValueError('Invalid MZ image/header bounds')
    if reloff+relocs*4>header_size:raise ValueError('Relocation table outside MZ header')
    module_size=declared-header_size
    invalid=[]
    for index in range(relocs):
        off,segment=struct.unpack_from('<HH',data,reloff+index*4)
        if segment*16+off+2>module_size:invalid.append(index)
    if invalid:raise ValueError('Relocation target outside declared real-mode module')
    if cs*16+ip>=module_size:raise ValueError('MZ entry point outside declared module')
    le=[]
    start=0
    while True:
        offset=data.find(b'LE\0\0',start)
        if offset<0:break
        if offset+196<=len(data):
            # Signature candidates require plausible little-endian header fields.
            cpu=struct.unpack_from('<H',data,offset+8)[0]
            os_type=struct.unpack_from('<H',data,offset+10)[0]
            page_size=struct.unpack_from('<I',data,offset+40)[0]
            if cpu in (2,3,4,5) and page_size in (512,1024,2048,4096):
                le.append({'file_offset':offset,'cpu_type':cpu,'os_type':os_type,'page_size':page_size})
        start=offset+4
    return {'signature':'MZ','file_size':len(data),'declared_real_mode_bytes':declared,
            'header_bytes':header_size,'relocation_count':relocs,'relocation_table_offset':reloff,
            'entry_cs':cs,'entry_ip':ip,'stack_ss':ss,'stack_sp':sp,
            'minimum_extra_paragraphs':minmem,'maximum_extra_paragraphs':maxmem,
            'overlay_number':overlay,'overlay_bytes':len(data)-declared,
            'optional_e_lfanew':struct.unpack_from('<I',data,60)[0],
            'e_lfanew_interpretation':'not required to be a PE/NE pointer in historical DOS executables',
            'dos4g_marker':b'DOS/4G' in data,'dos4gw_professional_marker':b'DOS/4GW Professional' in data,
            'le_header_candidates':le,'structural_result':'MZ header, entry and relocation bounds passed',
            'limitations':'Does not validate packed/protected-mode payload, publisher authenticity or execution'}


def wad_directory(data):
    if len(data)<12 or data[:4] not in (b'IWAD',b'PWAD'):raise ValueError('Invalid WAD header')
    count,offset=struct.unpack_from('<ii',data,4)
    if not 0<=count<=200000 or offset<12 or offset+count*16>len(data):
        raise ValueError('WAD directory outside file or count exceeds bound')
    lumps=[];warnings=[]
    for index in range(count):
        pos,size,raw=struct.unpack_from('<ii8s',data,offset+index*16)
        if pos<0 or size<0 or pos+size>len(data):raise ValueError(f'Lump {index} outside WAD')
        name=raw.split(b'\0',1)[0].decode('ascii',errors='strict')
        if any(ord(char)<32 or ord(char)>126 for char in name):raise ValueError('Invalid lump name bytes')
        if size and (pos<12 or pos<offset+count*16 and pos+size>offset):
            warnings.append({'lump':index,'name':name,'warning':'payload intersects header/directory'})
        lumps.append({'index':index,'name':name,'offset':pos,'size':size})
    sizes={'THINGS':10,'LINEDEFS':14,'SIDEDEFS':30,'VERTEXES':4,'SEGS':12,'SSECTORS':4,'NODES':28,'SECTORS':26}
    order=['THINGS','LINEDEFS','SIDEDEFS','VERTEXES','SEGS','SSECTORS','NODES','SECTORS','REJECT','BLOCKMAP']
    maps=[]
    for index,lump in enumerate(lumps):
        if len(lump['name'])!=5 or not lump['name'].startswith('MAP') or not lump['name'][3:].isdigit():continue
        section=lumps[index+1:index+11]
        if [entry['name'] for entry in section]!=order:raise ValueError(f'Map {lump["name"]} has incomplete/reordered standard map lumps')
        counts={}
        for entry in section:
            if entry['name'] in sizes:
                if entry['size']%sizes[entry['name']]:raise ValueError('Map lump record size is inconsistent')
                counts[entry['name']]=entry['size']//sizes[entry['name']]
        byname={entry['name']:entry for entry in section}
        def rows(name,format):
            entry=byname[name]
            return struct.iter_unpack(format,data[entry['offset']:entry['offset']+entry['size']])
        for v1,v2,flags,action,tag,right,left in rows('LINEDEFS','<7H'):
            if v1>=counts['VERTEXES'] or v2>=counts['VERTEXES']:raise ValueError('Linedef vertex index invalid')
            if any(side!=65535 and side>=counts['SIDEDEFS'] for side in (right,left)):raise ValueError('Linedef sidedef index invalid')
        for row in rows('SIDEDEFS','<hh8s8s8sH'):
            if row[-1]>=counts['SECTORS']:raise ValueError('Sidedef sector index invalid')
        for v1,v2,angle,line,direction,offset_value in rows('SEGS','<6H'):
            if v1>=counts['VERTEXES'] or v2>=counts['VERTEXES'] or line>=counts['LINEDEFS'] or direction not in (0,1):
                raise ValueError('Seg index/direction invalid')
        for number,first in rows('SSECTORS','<HH'):
            if first+number>counts['SEGS']:raise ValueError('Subsector seg range invalid')
        for node in rows('NODES','<12h2H'):
            for child in node[-2:]:
                if child&0x8000:
                    if child&0x7fff>=counts['SSECTORS']:raise ValueError('BSP child subsector index invalid')
                elif child>=counts['NODES']:raise ValueError('BSP child node index invalid')
        reject=byname['REJECT']
        expected=(counts['SECTORS']**2+7)//8
        if reject['size']<expected:warnings.append({'map':lump['name'],'warning':'REJECT shorter than sector visibility matrix','expected_minimum':expected})
        maps.append({'name':lump['name'],'record_counts':counts,'standard_map_sequence':True})
    duplicate_names={name:n for name,n in Counter(lump['name'] for lump in lumps).items() if n>1}
    return {'magic':data[:4].decode(),'file_size':len(data),'lump_count':count,'directory_offset':offset,
            'directory_end':offset+count*16,'directory_ends_at_eof':offset+count*16==len(data),
            'lumps':lumps,'maps':maps,'duplicate_lump_names':duplicate_names,'warnings':warnings,
            'structural_result':'header, directory, lump bounds and inspected map records passed',
            'limitations':'Not an exhaustive validation of textures, audio, BSP behavior, gameplay or original-release authenticity'}
