"""Evidence-linked software candidates from saved assessments, never from disc rereads.

Directory names, executable filenames and resources support candidates only. This
module does not verify titles, executable targets, redistribution rights or playability.
"""
from contextlib import closing
import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

RULE_VERSION = 1
# Primary launch names are candidates only when present in the recorded directory.
PRIMARY_NAMES = {
    'doom2': ('DOOM II', 'doom2.exe'), 'doom': ('DOOM', 'doom.exe'),
    'duke3d': ('Duke3d', 'duke3d.exe'), 'heretic': ('HERETIC', 'heretic.exe'),
    'quake': ('QUAKE', 'quake.exe'), 'mk4': ('MK4', None),
    'vcop2': ('VCOP2', 'vc2.exe'), 'mickey': ('MICKEY', 'm&fps.exe'),
    'motorace': ('MOTORACE', 'moto.exe'), 'td4': ('TD4', '2.exe'),
    'tt_racing_class': ('TT_RACING_CLASS', 'manxtt.exe'),
}
LAUNCH_EXTENSIONS = {'.exe','.com','.bat'}
ROM_EXTENSIONS = {'.smc','.sfc','.fig'}
SUPPORT_NAMES = {'setup.exe','install.exe','ipxsetup.exe','sersetup.exe','cwsdpmi.exe',
                 'readme.exe','snes9x.exe','class.exe','build.exe','editart.exe',
                 'kextract.exe','kgroup.exe','_isdel.exe'}


def identify(entries):
    groups = defaultdict(list)
    for entry in entries:
        if entry['kind'] != 'file':
            continue
        path = PurePosixPath(entry['path'])
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Saved inventory contains an unsafe relative path')
        if len(path.parts) < 2:
            continue
        package = '/'.join(path.parts[:2]) if path.parts[0].casefold()=='juegos' and len(path.parts)>2 else path.parts[0]
        groups[package].append(entry)
    results = []
    for package, files in sorted(groups.items()):
        executables = [item for item in files if PurePosixPath(item['path']).suffix.casefold() in LAUNCH_EXTENSIONS]
        roms = [item for item in files if PurePosixPath(item['path']).suffix.casefold() in ROM_EXTENSIONS]
        if not executables and not roms:
            continue
        base = PurePosixPath(package).name
        title, main_name = PRIMARY_NAMES.get(base.casefold(),(base,None))
        primary = next((item for item in executables if PurePosixPath(item['path']).parent.as_posix()==package
                        and PurePosixPath(item['path']).name.casefold()==main_name),None)
        emulators = [item for item in executables if PurePosixPath(item['path']).name.casefold()=='snes9x.exe']
        platform = 'unknown; headers not assessed'
        if emulators:
            platform = 'SNES software candidate bundled with a PC emulator; filename evidence only'
        elif primary and primary.get('classification'):
            platform = primary['classification']['platform']+'; observed primary header'
        resource_files = [item for item in files if PurePosixPath(item['path']).suffix.casefold() in {'.wad','.grp','.pak',*ROM_EXTENSIONS}]
        statuses = Counter(item['status'] for item in files)
        recovery = ('read error observed; remaining integrity unknown' if statuses.get('read error') else
                    'not fully assessed' if statuses.get('not assessed') or statuses.get('changed during assessment') else
                    'readable; historical integrity unverified')
        if emulators:
            next_test = 'Validate ROM or split-ROM format, then select an isolated SNES-capable emulator; PC launcher is not the game platform'
        elif primary and (primary.get('classification') or {}).get('format')=='MZ':
            next_test = 'DOS-compatible emulation is an estimate; inspect extended headers, resources and runtime on a verified working copy first'
        else:
            next_test = 'Inspect executable or installer headers on a verified working copy before selecting a DOS/Windows test environment'
        results.append({'candidate_key':package,'title':title,'original_directory':package,
            'identification_status':'candidate; naming and inventory evidence only',
            'identification_confidence':'filename plus resource evidence' if primary and resource_files else 'directory/filename evidence only',
            'executable_path':primary['path'] if primary else None,
            'launcher_candidates':[item['path'] for item in executables
                if PurePosixPath(item['path']).name.casefold() not in SUPPORT_NAMES],
            'support_executables':[item['path'] for item in executables
                if PurePosixPath(item['path']).name.casefold() in SUPPORT_NAMES],
            'bundled_emulators':[item['path'] for item in emulators],
            'resource_paths':[item['path'] for item in resource_files],
            'file_count':len(files),'file_status_counts':dict(statuses),
            'recovery_status':recovery,'payload_preserved':False,
            'platform':platform,'compatibility_status':'untested','playable':False,
            'license_status':'unknown; no redistribution authorization established',
            'recommended_next_test':next_test,
            'limitations':['Candidate count is not a count of confirmed games or playable packages.',
                          'A directory read failure does not establish that every file in the directory is corrupt.',
                          'Extensions and names do not establish format, edition, completeness, or license.']})
    return results


def catalog_candidates(root, disc_id, assessment_dir):
    """Append a versioned candidate inventory; preserve original assessment artifacts."""
    root, assessment_dir = Path(root),Path(assessment_dir).resolve()
    if not assessment_dir.is_relative_to(root/'evidence'/'assessments'):
        raise ValueError('Candidate input must be a saved assessment inside this workspace')
    source = assessment_dir/'files.json'
    data = source.read_bytes()
    checksums = json.loads((assessment_dir/'checksums.json').read_text())
    digest = hashlib.sha256(data).hexdigest()
    if checksums.get('files.json') != digest:
        raise ValueError('Assessment file inventory hash does not match its retained checksum')
    summary = json.loads((assessment_dir/'summary.json').read_text())
    if summary['disc_id'] != disc_id:
        raise ValueError('Disc ID does not match saved assessment')
    candidates = identify(json.loads(data))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = root/'reports'/disc_id/'software-candidates'/stamp
    output.mkdir(parents=True,exist_ok=False)
    provenance = {'assessment_run':summary['run_id'],'source_inventory':str(source.relative_to(root)),
                  'source_inventory_sha256':digest,'rule_version':RULE_VERSION,
                  'generated_utc':datetime.now(timezone.utc).isoformat(),
                  'source_reads':False,'disc_id':disc_id}
    result = {'provenance':provenance,'candidate_count':len(candidates),'candidates':candidates}
    (output/'software_candidates.json').write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\n')
    with (output/'software_inventory.csv').open('w',newline='',encoding='utf-8') as stream:
        fields = ['title','original_directory','identification_status','executable_path','file_count',
                  'platform','recovery_status','compatibility_status','license_status']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(candidates)
    lines=['# Software candidates and emulation readiness','',
           'Source: saved assessment inventory; no physical disc reads. All rows are candidates. No emulator tests have run.', '',
           '| Candidate directory | Primary executable candidate | Recovery assessment | Emulation |',
           '|---|---|---|---|']
    lines += [f"| {item['original_directory']} | {item['executable_path'] or 'Not established'} | {item['recovery_status']} | Untested |" for item in candidates]
    lines += ['', 'SNES9X bundles are grouped by software directory, not counted as independent games per EXE. ROM and split-ROM identification remains unverified. Setup, network, editor and runtime utilities are retained as support evidence.',
              'Unknown license status is independent of technical identification. No payload is copied or exported.', '']
    (output/'compatibility_report.md').write_text('\n'.join(lines))
    with closing(sqlite3.connect(root/'catalog'/'catalog.sqlite')) as db, db:
        db.execute('PRAGMA foreign_keys=ON')
        if not db.execute('SELECT 1 FROM discs WHERE disc_id=?',(disc_id,)).fetchone():
            raise ValueError('Disc does not exist in catalog')
        db.execute('''CREATE TABLE IF NOT EXISTS software_candidate_observations (
            observation_id INTEGER PRIMARY KEY, disc_id TEXT NOT NULL REFERENCES discs(disc_id),
            assessment_run TEXT NOT NULL REFERENCES assessment_runs(run_id),
            generated_utc TEXT NOT NULL, candidate_key TEXT NOT NULL, candidate_json TEXT NOT NULL,
            provenance_json TEXT NOT NULL)''')
        for candidate in candidates:
            db.execute('INSERT INTO software_candidate_observations(disc_id,assessment_run,generated_utc,candidate_key,candidate_json,provenance_json) VALUES(?,?,?,?,?,?)',
                       (disc_id,summary['run_id'],provenance['generated_utc'],candidate['candidate_key'],json.dumps(candidate),json.dumps(provenance)))
        db.execute('INSERT OR IGNORE INTO schema_info VALUES(3)')
        db.execute('INSERT INTO recovery_events(disc_id,timestamp,operation,source,output,result,supporting_log,tool_version) VALUES(?,?,?,?,?,?,?,?)',
                   (disc_id,provenance['generated_utc'],'saved_inventory_candidate_identification',str(source.relative_to(root)),
                    str(output.relative_to(root)),f'{len(candidates)} candidates; untested',str((output/'software_candidates.json').relative_to(root)),f'candidate rules {RULE_VERSION}'))
    return output,result
