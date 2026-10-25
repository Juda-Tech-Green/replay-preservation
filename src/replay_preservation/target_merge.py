"""Merge validated compact acquisition chunks into fresh sparse derivatives only."""
import hashlib
import os
from pathlib import Path
from .iso_coverage import coverage,image_holes


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while data:=stream.read(1024*1024):result.update(data)
    return result.hexdigest()


def merge_ranges(base,updates):
    if not base:raise ValueError('Empty baseline map')
    for update in updates:
        if update['length']<=0:raise ValueError('Empty update')
        start,end=update['absolute_offset'],update['absolute_offset']+update['length']
        if start<base[0]['offset'] or end>base[-1]['offset']+base[-1]['length']:
            raise ValueError('Update exceeds original acquisition domain')
        covered=sum(max(0,min(end,item['offset']+item['length'])-max(start,item['offset'])) for item in base)
        if covered!=update['length']:raise ValueError('Baseline map has an unmapped gap in update')
    points={value for item in base for value in (item['offset'],item['offset']+item['length'])}
    points.update(value for u in updates for value in (u['absolute_offset'],u['absolute_offset']+u['length']))
    result=[]
    points=sorted(points)
    for start,end in zip(points,points[1:]):
        original=next((item for item in base if item['offset']<=start<item['offset']+item['length']),None)
        if original is None:continue
        status='+' if any(u['absolute_offset']<=start< u['absolute_offset']+u['length'] for u in updates) else original['status']
        if result and result[-1]['status']==status and result[-1]['offset']+result[-1]['length']==start:
            result[-1]['length']+=end-start
        else:result.append({'offset':start,'length':end-start,'status':status})
    return result


def write_map(path,ranges,provenance):
    with Path(path).open('x') as stream:
        stream.write('# Derived forensic recovery map; not an original ddrescue acquisition map.\n')
        for line in provenance.splitlines():stream.write('# '+line+'\n')
        stream.write('0x0 + 1\n')
        for item in ranges:stream.write(f"0x{item['offset']:X} 0x{item['length']:X} {item['status']}\n")


def copy_known_ranges(source,ranges,destination,domain_end):
    """Unrecovered areas remain holes; no filesystem holes are promoted to recovered."""
    source=Path(source);destination=Path(destination)
    if source.is_symlink() or not source.is_file():raise ValueError('Source must be regular')
    holes=image_holes(source)
    if holes is None:raise ValueError('Sparse discovery unavailable')
    with source.open('rb') as reader,destination.open('xb+') as writer:
        writer.truncate(domain_end)
        for item in ranges:
            if item['status']!='+':continue
            verified=coverage(ranges,item['offset'],item['length'],source.stat().st_size,holes)
            if verified['missing_bytes']:raise ValueError('Recovered source span lacks actual bytes')
            reader.seek(item['offset']);writer.seek(item['offset']);left=item['length']
            while left:
                data=reader.read(min(left,1024*1024))
                if not data:raise ValueError('Source truncated during copy')
                writer.write(data);left-=len(data)
        writer.flush();os.fsync(writer.fileno())


def apply_target(base_image,base_map,chunk,validation,output):
    if not validation['complete'] or validation['missing_bytes']:
        raise ValueError('This handoff requires a complete validated target')
    if digest(chunk)!=validation['chunk_sha256']:raise ValueError('Chunk changed since validation')
    merged=merge_ranges(base_map,validation['usable_ranges'])
    domain_end=base_map[-1]['offset']+base_map[-1]['length']
    copy_known_ranges(base_image,base_map,output,domain_end)
    with Path(chunk).open('rb') as reader,Path(output).open('r+b') as writer:
        for span in validation['usable_ranges']:
            # Existing '+' overlaps must agree; never silently replace conflicting good evidence.
            for original in base_map:
                if original['status']!='+':continue
                start=max(span['absolute_offset'],original['offset'])
                end=min(span['absolute_offset']+span['length'],original['offset']+original['length'])
                if start<end:
                    reader.seek(span['chunk_offset']+start-span['absolute_offset']);writer.seek(start)
                    left=end-start
                    while left:
                        size=min(left,1024*1024)
                        if reader.read(size)!=writer.read(size):raise ValueError('Conflicting recovered evidence')
                        left-=size
            reader.seek(span['chunk_offset']);writer.seek(span['absolute_offset']);left=span['length']
            while left:
                data=reader.read(min(left,1024*1024))
                if not data:raise ValueError('Truncated target chunk')
                writer.write(data);left-=len(data)
        writer.flush();os.fsync(writer.fileno())
    return merged
