"""Prepare bounded optical recovery proposals. This module never opens devices.

Target output is a fresh compact chunk: absolute input/map offsets and zero-based
chunk output are deliberately different and must be translated during validation.
"""
import hashlib
import json
from pathlib import Path
from .iso_coverage import SECTOR,FULL,coverage,image_holes
from .mapfile import parse_mapfile


OPTIONS = ['--ask','--sector-size=2048','--cpass=1','--no-trim','--no-sweep',
           '--no-scrape','--retry-passes=0','--max-read-errors=0','--timeout=20s']


def command_for(offset,length,attempt_dir,device='/dev/sr0'):
    if offset<0 or length<=0 or offset%SECTOR or length%SECTOR:
        raise ValueError('Target must be a nonempty aligned absolute-sector interval')
    directory=Path(attempt_dir)
    if not directory.is_absolute():raise ValueError('Attempt path must be absolute')
    return ['ddrescue',*OPTIONS,f'--input-position={offset}','--output-position=0',
            f'--size={length}',f'--log-events={directory}/events.log',
            f'--log-reads={directory}/reads.log',device,str(directory/'target.chunk'),str(directory/'target.map')]


def file_targets(item,ranges,image_size):
    """Return missing allocated spans split by recorded map status, never a broad envelope."""
    if item.get('unsupported_layout'):raise ValueError('Unsupported extent layout cannot be targeted')
    targets=[]
    for extent in item['extents']:
        size=((extent['length']+SECTOR-1)//SECTOR)*SECTOR
        for span in coverage(ranges,extent['offset'],size,image_size)['missing_ranges']:
            if span['status'] in ('image EOF','sparse hole','unmapped'):
                raise ValueError('Map/image inconsistency needs investigation before recovery planning')
            targets.append({**span,'start_lba':span['offset']//SECTOR,
                'end_lba':(span['offset']+span['length'])//SECTOR-1,
                'sector_count':span['length']//SECTOR,'file_path':item['path']})
    return targets


def validate_chunk(target,chunk_path,map_path):
    """Read-only post-acquisition validator. No device access or image patching."""
    path=Path(chunk_path)
    if path.is_symlink() or not path.is_file():raise ValueError('Chunk must be a regular non-symlink file')
    ranges=parse_mapfile(Path(map_path).read_text())
    holes=image_holes(path)
    if holes is None:raise ValueError('Sparse map unavailable')
    size=path.stat().st_size
    if size>target['length']:raise ValueError('Chunk exceeds authorized domain length')
    original_offset=target['offset']
    # Convert absolute input/map offsets to compact chunk coordinates only for availability checks.
    shifted=[dict(item,offset=item['offset']-original_offset) for item in ranges]
    result=coverage(shifted,0,target['length'],size,holes)
    authorized_end=original_offset+target['length']
    unexpected=[item for item in ranges if item['status']=='+' and
                (item['offset']<original_offset or item['offset']+item['length']>authorized_end)]
    if unexpected:raise ValueError('Target map claims recovered bytes outside authorized range')
    usable=[]
    for item in ranges:
        if item['status']!='+':continue
        left=max(original_offset,item['offset']);right=min(authorized_end,item['offset']+item['length'])
        if left>=right:continue
        actual=coverage(shifted,left-original_offset,right-left,size,holes)
        if actual['missing_bytes']:raise ValueError('Map plus range has no allocated chunk bytes')
        usable.append({'absolute_offset':left,'chunk_offset':left-original_offset,'length':right-left})
    return {'source_device_read':False,'target_input_offset':original_offset,'chunk_output_offset':0,
            'authorized_length':target['length'],'covered_bytes':result['recovered_bytes'],
            'missing_bytes':result['missing_bytes'],'complete':not result['missing_bytes'],
            'usable_ranges':usable,'chunk_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'map_sha256':hashlib.sha256(Path(map_path).read_bytes()).hexdigest(),
            'integrity':'sector reading only; original file integrity and playability not established'}
