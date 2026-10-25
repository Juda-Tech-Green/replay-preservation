"""Preservation Baseline v0.1: offline adapters, provenance, and scoped statuses.

No device acquisition, subprocess execution, package installation or catalog mutation.
Historical modules remain unchanged; their pure parsers are reused here.
"""
import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path, PurePosixPath
from .mapfile import parse_mapfile, summarize
from .iso_coverage import Inspector, coverage, FULL
from .target_strategy import validate_chunk
from .target_merge import apply_target, write_map
from .doom_static import mz_header, wad_directory

VERSION = '0.1'
STATUS_VALUES = {
 'acquisition': ('not_assessed','partial','complete','failed'),
 'sector_coverage': ('not_assessed','full','partial','unavailable','unknown'),
 'file_integrity': ('not_assessed','readable_unverified','structural_checks_passed','check_failed','changed'),
 'package_completeness': ('not_assessed','known_set_complete','known_set_incomplete','unknown'),
 'emulator_compatibility': ('not_tested','prepared','startup_verified','interactive_partial','checks_passed','failed','inconclusive'),
 'actual_playability': ('not_tested','unverified','limited_interactive_verified','defined_scope_verified','failed'),
 'historical_authenticity': ('unverified','reference_match','conflicting_reference'),
}
SHA = re.compile(r'^[0-9a-f]{64}$')

def regular(path):
    """Reject symlink components, devices and optical filesystem files before reading.

    Intended for private inputs without concurrent hostile path replacement.
    """
    path = Path(os.path.abspath(path))
    for component in [*reversed(path.parents), path]:
        if component.is_symlink():
            raise ValueError(f'Symlink input component: {component}')
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Input must be a regular local file')
    # Mounted optical files look regular; forbid iso9660/udf mounts as well.
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        mount = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1],8)), left.split()[4])
        if right.split()[0] in ('iso9660','udf') and path.is_relative_to(mount):
            raise ValueError('Offline CLI refuses files on optical filesystems')
    return path

def identity(path):
    s=path.stat()
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def fingerprint(path, expected=None):
    path=regular(path); before=identity(path)
    with path.open('rb') as f: value=hashlib.file_digest(f,'sha256').hexdigest()
    if identity(path)!=before: raise ValueError('Input changed while hashing')
    if expected is not None and (not SHA.fullmatch(expected) or value!=expected):
        raise ValueError(f'SHA-256 mismatch: {path}')
    return {'path':str(path),'size':before[2],'sha256':value}

def bounded_bytes(path, limit=128*1024**2):
    path=regular(path)
    if path.stat().st_size>limit: raise ValueError('Input exceeds parser byte limit')
    before=identity(path)
    with path.open('rb') as f:data=f.read(limit+1)
    if len(data)>limit or identity(path)!=before: raise ValueError('Input changed or exceeds bound')
    return data

def read_json(path):return json.loads(bounded_bytes(path,16*1024**2))
def ranges(path):return parse_mapfile(bounded_bytes(path,16*1024**2).decode('utf-8'))

def map_summary(path, expected_size):
    if expected_size<=0:raise ValueError('Expected source size must be positive')
    rows=ranges(path); result=summarize(rows)
    if result['covered_end']>expected_size:raise ValueError('Map extends beyond expected source domain')
    result['expected_source_bytes']=expected_size
    result['unmapped_bytes']=expected_size-sum(x['length'] for x in rows)
    result['recovery_percentage']=100*result['read_bytes']/expected_size
    result['completion']='complete' if result['read_bytes']==expected_size and not result['unmapped_bytes'] else 'partial'
    result['bad_sector_bytes']=result['bytes_by_status'].get('-',0)
    result['bad_2048_sector_equivalent']=result['bad_sector_bytes']/2048
    result['unreadable_sector_count_note']='Known bad bytes only; untried/non-trimmed ranges are separate. Cooked 2048-byte geometry assumed only for the equivalent.'
    return result

def verified_inspector(image, map_path, image_sha256, map_sha256):
    inputs=[fingerprint(image,image_sha256),fingerprint(map_path,map_sha256)]
    return Inspector(regular(image),ranges(map_path)),inputs

def inspect_image(image,map_path,image_sha256,map_sha256,namespace='Joliet'):
    inspector,inputs=verified_inspector(image,map_path,image_sha256,map_sha256)
    matches=[d for d in inspector.descriptors() if d['namespace']==namespace]
    if len(matches)!=1:raise ValueError('Requested namespace absent or ambiguous; choose explicitly')
    tree=inspector.annotate(inspector.tree(matches[0]))
    for i in inputs:fingerprint(i['path'],i['sha256'])
    return {'descriptor':matches[0],'tree':tree,'warnings':inspector.warnings,'inputs':inputs}

def target_validation(chunk,map_path,offset,length,chunk_sha256,map_sha256):
    if length>128*1024**2:raise ValueError('Compact target exceeds v0.1 128 MiB validation limit')
    if offset<0 or length<=0 or offset%2048 or length%2048:raise ValueError('Target requires aligned cooked-sector byte coordinates')
    inputs=[fingerprint(chunk,chunk_sha256),fingerprint(map_path,map_sha256)]
    result=validate_chunk({'offset':offset,'length':length},regular(chunk),regular(map_path))
    for i in inputs:fingerprint(i['path'],i['sha256'])
    return {**result,'start_lba':offset//2048,'end_lba':(offset+length)//2048-1,'inputs':inputs}

def fresh_directory(path):
    path=Path(os.path.abspath(path))
    # Existing parent must be private and stable. Do not create through symlinks.
    for p in [path.parent,*path.parents]:
        if p.is_symlink():raise ValueError('Symlink output parent')
    path.mkdir(mode=0o700,parents=False,exist_ok=False)
    return path

def save_new(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,ensure_ascii=False);f.write('\n')

def merge_target(base_image,base_map,chunk,target_map,base_sha256,base_map_sha256,chunk_sha256,target_map_sha256,offset,length,output_dir):
    inputs=[fingerprint(base_image,base_sha256),fingerprint(base_map,base_map_sha256)]
    validation=target_validation(chunk,target_map,offset,length,chunk_sha256,target_map_sha256)
    if not validation['complete']:raise ValueError('Incomplete target; no derivative created')
    inputs+=validation['inputs'];out=fresh_directory(output_dir)
    try:
        merged=apply_target(regular(base_image),ranges(base_map),regular(chunk),validation,out/'image.iso')
        write_map(out/'combined.map',merged,'Baseline v0.1; compact chunk local zero maps to absolute target offset. See provenance.json.')
        for i in inputs:fingerprint(i['path'],i['sha256'])
        # Verify every imported byte in output at its absolute offset.
        with regular(chunk).open('rb') as src,(out/'image.iso').open('rb') as dst:
            for span in validation['usable_ranges']:
                src.seek(span['chunk_offset']);dst.seek(span['absolute_offset']);left=span['length']
                while left:
                    n=min(left,1024**2)
                    if src.read(n)!=dst.read(n):raise ValueError('Derivative imported-byte verification failed')
                    left-=n
        result={'inputs':inputs,'target':validation,'outputs':[fingerprint(out/'image.iso'),fingerprint(out/'combined.map')],'state':'verified_derivative','historical_authenticity':'unverified'}
        save_new(out/'provenance.json',result);return result
    except Exception as exc:
        save_new(out/'FAILED.json',{'state':'failed_do_not_use','error':str(exc)})
        raise

def extract_package(image,map_path,image_sha256,map_sha256,namespace,package,output_dir):
    if not package or any(p in ('','.','..') for p in package.split('/')) or '\\' in package:raise ValueError('Invalid package prefix')
    inspector,inputs=verified_inspector(image,map_path,image_sha256,map_sha256)
    descriptors=[d for d in inspector.descriptors() if d['namespace']==namespace]
    if len(descriptors)!=1:raise ValueError('Requested namespace absent or ambiguous')
    tree=inspector.annotate(inspector.tree(descriptors[0]));files=[f for f in tree['files'] if f['path'].startswith(package+'/')]
    if tree['errors']:raise ValueError('Filesystem enumeration incomplete')
    if not files or any(f['coverage_status']!=FULL for f in files):raise ValueError('Known package not fully sector-covered')
    names=set()
    for item in files:
        parts=PurePosixPath(item['path']).parts
        if any(p in ('.','..') or '\\' in p or ':' in p for p in parts) or item['path'].startswith('/'):raise ValueError('Unsafe extraction path')
        folded=item['path'].casefold()
        if folded in names:raise ValueError('Case-colliding package paths')
        names.add(folded)
    out=fresh_directory(output_dir);manifest=[]
    try:
        for item in files:
            destination=out/'files'/item['path'];destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            h=hashlib.sha256();size=0
            with destination.open('xb') as stream:
                for extent in item['extents']:
                    offset=extent['offset'];left=extent['length']
                    while left:
                        n=min(left,1024**2);block=inspector.read(offset,n);stream.write(block);h.update(block);size+=n;offset+=n;left-=n
            destination.chmod(0o400)
            if size!=item['file_size'] or h.hexdigest()!=item['file_sha256']:raise ValueError('Extraction hash/size mismatch')
            manifest.append({'original_path':item['path'],'size':size,'sha256':h.hexdigest(),'extents':item['extents'],'sector_coverage':'full'})
        for i in inputs:fingerprint(i['path'],i['sha256'])
        result={'state':'verified_extraction','known_file_count':len(files),'inputs':inputs,'files':manifest,'historical_authenticity':'unverified','actual_playability':'not_tested'}
        save_new(out/'manifest.json',result);return result
    except Exception as exc:
        save_new(out/'FAILED.json',{'state':'failed_do_not_use','error':str(exc)});raise

def static_check(path,kind):
    data=bounded_bytes(path)
    return (mz_header if kind=='mz' else wad_directory)(data)

def validate_record(record):
    if not isinstance(record,dict):raise ValueError('Record must be a JSON object')
    if record.get('schema')!='replay.preservation.record.v0.1':raise ValueError('Unsupported record schema')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',record.get('disc_id','')):raise ValueError('Invalid disc ID')
    stamp=datetime.fromisoformat(record['recorded_utc'].replace('Z','+00:00'))
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds()!=0:raise ValueError('UTC timestamp required')
    if not isinstance(record.get('operation'),str) or not record['operation'].strip():raise ValueError('Operation required')
    if not isinstance(record.get('statuses'),dict) or set(record['statuses'])!=set(STATUS_VALUES):raise ValueError('All independent status dimensions required')
    for k,v in record['statuses'].items():
        if v not in STATUS_VALUES[k]:raise ValueError(f'Unsupported {k} status')
    for key in ('inputs','evidence','limitations'):
        if not isinstance(record.get(key),list):raise ValueError(f'{key} list required')
    if any(not isinstance(x,dict) for x in record['evidence']):raise ValueError('Evidence entries must be objects')
    if any(not isinstance(x,str) for x in record['limitations']):raise ValueError('Limitations must be strings')
    if record.get('scope') is not None and not isinstance(record['scope'],str):raise ValueError('Scope must be text or null')
    for item in record['inputs']:
        if not isinstance(item,dict) or not isinstance(item.get('path'),str) or not SHA.fullmatch(item.get('sha256','')):raise ValueError('Input path and SHA-256 required')
    interactive=record['statuses']['actual_playability'] in ('limited_interactive_verified','defined_scope_verified')
    if interactive:
        if not record.get('scope') or not any(isinstance(x,dict) and x.get('source')=='human_confirmation' and x.get('result')=='pass' for x in record['evidence']):
            raise ValueError('Interactive verification needs scope and human evidence')
    return {'valid':True,'statuses':record['statuses']}

def session_summary(viewer,events,controller,human=None):
    if viewer.get('synthetic_test') is not False or viewer.get('accelerated_regression') is not False:raise ValueError('Synthetic viewer cannot establish actual gameplay')
    authorization=controller.get('authorization',{})
    if controller.get('mode')!='authorized_gameplay' or authorization.get('authorized') is not True or authorization.get('sessions')!=1:raise ValueError('Not a single authorized gameplay record')
    finished=[x for x in events if x.get('event')=='session_finished']
    if len(finished)!=1 or finished[0].get('mode')!='gameplay':raise ValueError('Expected exactly one completed gameplay session')
    controls=viewer.get('controls',{})
    def confirmed(x):return x.get('result')=='Pass' and x.get('source')=='human_confirmation'
    checks={k:confirmed(controls.get(k,{})) for k in ('movement','turning','firing','use')}
    map_pass=confirmed(viewer.get('MAP01',{}))
    # Missing markers stay unknown; initial UI failures stay raw, later statements are separate.
    return {'actual_playability':'limited_interactive_verified' if map_pass and all(checks.values()) else 'unverified','scope':'human-confirmed MAP01 and movement/turning/firing/use; sound-disabled session','checks':checks,'MAP01_human_confirmed':map_pass,'raw_controls':controls,'human_followup':human,'first_menu':viewer.get('observations',{}).get('first_visible_game_menu'),'first_level_transition':viewer.get('observations',{}).get('first_level_transition'),'termination':{k:finished[0].get(k) for k in ('utc','termination_reason','emulator_returncode','forced_kill','game_returned_to_autoexec')},'full_functional_validation':False}
