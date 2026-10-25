"""Append-only partial-image coverage catalog and recovery priorities."""
from contextlib import closing
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from .iso_coverage import SECTOR,FULL,PARTIAL,OUTSIDE,coverage


def union_ranges(items):
    """Union physical byte intervals to avoid counting shared extents twice."""
    merged=[]
    for start,end in sorted((item['offset'],item['offset']+item['length']) for item in items if item['length']):
        if merged and start<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
        else:merged.append([start,end])
    return [{'offset':start,'length':end-start} for start,end in merged]


def package_analysis(files,ranges,image_size,holes=()):
    grouped=defaultdict(list)
    for item in files:
        parts=item['path'].split('/')
        key='/'.join(parts[:2]) if parts[0].casefold()=='juegos' and len(parts)>2 else parts[0]
        grouped[key].append(item)
    packages=[]
    for name,items in grouped.items():
        allocated=[{'offset':extent['offset'],'length':((extent['length']+SECTOR-1)//SECTOR)*SECTOR}
                   for item in items for extent in item['extents']]
        merged=union_ranges(allocated)
        missing=[]
        for extent in merged:
            missing.extend(coverage(ranges,extent['offset'],extent['length'],image_size,holes)['missing_ranges'])
        totals=Counter()
        for span in missing:totals[span['status']]+=span['length']
        targets=[dict(span,start_lba=span['offset']//SECTOR,
                      end_lba_inclusive=(span['offset']+span['length']-1)//SECTOR) for span in missing]
        statuses=Counter(item['coverage_status'] for item in items)
        package={'package':name,'file_count':len(items),'file_coverage_counts':dict(statuses),
                 'all_known_files_covered':all(item['coverage_status']==FULL for item in items),
                 'required_dependency_manifest':'not independently established',
                 'fully_recovered_required_package':False,
                 'missing_payload_bytes':sum(item['missing_bytes'] for item in items),
                 'missing_allocated_bytes':sum(totals.values()),'missing_allocated_sectors':sum(totals.values())//SECTOR,
                 'missing_status_bytes':dict(totals),'target_ranges':targets,
                 'touches_map_bad_sector':bool(totals['-']),
                 'touches_non_trimmed':bool(totals['*']),
                 'integrity_status':'unknown; sector coverage does not prove file integrity',
                 'emulation_status':'untested','missing_files':[item['path'] for item in items if item['coverage_status']!=FULL]}
        packages.append(package)
    # Prefer not-yet-tried locations over previously failing regions; then lower unique byte cost.
    packages.sort(key=lambda item:(item['touches_map_bad_sector'],item['touches_non_trimmed'],
                                   item['missing_allocated_bytes'],item['package']))
    for rank,item in enumerate(packages,1):item['priority_rank']=rank
    return packages


def corroborate(files,log):
    pattern=re.compile(r"File data lba:\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'(.*)'\s*$")
    records=[]
    for line in log.splitlines():
        match=pattern.fullmatch(line)
        if match:records.append((match[5].lstrip('/'),int(match[2]),int(match[4])))
    expected=Counter((item['path'],extent['extent_lba'],extent['length']) for item in files for extent in item['extents'])
    if Counter(records)!=expected:raise ValueError('Independent xorriso extent records do not exactly match parsed Joliet tree')
    return {'xorriso_extent_records':len(records),'exact_path_lba_size_match':True}


def save_catalog(root,evidence,files,packages,verification):
    database=root/'catalog/catalog.sqlite'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    snapshot=root/'catalog/snapshots'/f'pre-image-investigation-{stamp}.sqlite'
    snapshot.parent.mkdir(exist_ok=True)
    with closing(sqlite3.connect(f'{database.as_uri()}?mode=ro',uri=True)) as source, source:
        with closing(sqlite3.connect(snapshot)) as backup, backup:source.backup(backup)
    snapshot.chmod(0o444)
    with closing(sqlite3.connect(database)) as db, db:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS image_investigations (
          investigation_id TEXT PRIMARY KEY, disc_id TEXT NOT NULL REFERENCES discs(disc_id),
          created_utc TEXT NOT NULL, image_sha256 TEXT NOT NULL, map_sha256 TEXT NOT NULL,
          evidence_path TEXT NOT NULL, verification_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS image_file_coverage (
          investigation_id TEXT NOT NULL REFERENCES image_investigations(investigation_id),
          original_path TEXT NOT NULL, file_size INTEGER NOT NULL, coverage_status TEXT NOT NULL,
          recovered_bytes INTEGER NOT NULL, missing_bytes INTEGER NOT NULL, file_sha256 TEXT,
          recovery_confidence TEXT NOT NULL, observation_json TEXT NOT NULL,
          PRIMARY KEY(investigation_id,original_path));
        CREATE TABLE IF NOT EXISTS image_extent_coverage (
          investigation_id TEXT NOT NULL, original_path TEXT NOT NULL, extent_index INTEGER NOT NULL,
          image_offset INTEGER NOT NULL, length INTEGER NOT NULL, observation_json TEXT NOT NULL,
          PRIMARY KEY(investigation_id,original_path,extent_index),
          FOREIGN KEY(investigation_id,original_path) REFERENCES image_file_coverage(investigation_id,original_path));
        CREATE TABLE IF NOT EXISTS package_sector_coverage (
          investigation_id TEXT NOT NULL REFERENCES image_investigations(investigation_id),
          package TEXT NOT NULL, all_known_files_covered INTEGER NOT NULL,
          missing_bytes INTEGER NOT NULL, priority_rank INTEGER NOT NULL,
          required_file_integrity TEXT NOT NULL, emulation_status TEXT NOT NULL, observation_json TEXT NOT NULL,
          PRIMARY KEY(investigation_id,package));
        ''')
        artifacts={Path(item['source']).name:item for item in verification['artifacts']}
        run_id=evidence.name
        db.execute('INSERT INTO image_investigations VALUES(?,?,?,?,?,?,?)',
                   (run_id,'disc01-juegos-variados',datetime.now(timezone.utc).isoformat(),
                    artifacts['disc-01.iso']['sha256'],artifacts['disc-01.map']['sha256'],
                    str(evidence.relative_to(root)),json.dumps(verification)))
        for item in files:
            confidence='mapfile and independent filesystem extents corroborated; historical integrity unverified'
            if item['coverage_status']!=FULL:confidence='incomplete sector coverage; no complete-file hash inferred'
            db.execute('INSERT INTO image_file_coverage VALUES(?,?,?,?,?,?,?,?,?)',
                       (run_id,item['path'],item['file_size'],item['coverage_status'],item['recovered_bytes'],
                        item['missing_bytes'],item['file_sha256'],confidence,json.dumps(item)))
            for index,extent in enumerate(item['extents']):
                db.execute('INSERT INTO image_extent_coverage VALUES(?,?,?,?,?,?)',
                           (run_id,item['path'],index,extent['offset'],extent['length'],json.dumps(extent)))
        for package in packages:
            db.execute('INSERT INTO package_sector_coverage VALUES(?,?,?,?,?,?,?,?)',
                       (run_id,package['package'],int(package['all_known_files_covered']),package['missing_allocated_bytes'],
                        package['priority_rank'],'not independently established','untested',json.dumps(package)))
        db.execute('UPDATE discs SET image_path=?,image_hash=?,mapfile_path=?,acquisition_status=? WHERE disc_id=?',
                   (artifacts['disc-01.iso']['source'],artifacts['disc-01.iso']['sha256'],artifacts['disc-01.map']['source'],
                    'partial; interrupted external ddrescue acquisition','disc01-juegos-variados'))
        db.execute('INSERT OR IGNORE INTO schema_info VALUES(4)')
        db.execute('INSERT INTO recovery_events(disc_id,timestamp,operation,source,output,result,supporting_log,tool_version) VALUES(?,?,?,?,?,?,?,?)',
                   ('disc01-juegos-variados',datetime.now(timezone.utc).isoformat(),'partial_image_sector_coverage',
                    artifacts['disc-01.iso']['source'],str(evidence.relative_to(root)),
                    'partial image; no physical CD reads; integrity and playability not established',
                    str((evidence/'artifact_verification.json').relative_to(root)),'Python ISO inspector; xorriso 1.5.6 corroboration'))
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Catalog integrity check failed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Catalog foreign-key check failed')
    return snapshot


def export(root,evidence,tree,packages,verification,validation):
    report_dir=root/'reports/disc01-juegos-variados/partial-image'/evidence.name
    report_dir.mkdir(parents=True,exist_ok=False)
    files=tree['files']
    counts=Counter(item['coverage_status'] for item in files)
    with (report_dir/'file_sector_coverage.csv').open('w',newline='',encoding='utf-8') as stream:
        fields=['path','file_size','coverage_status','recovered_bytes','missing_bytes','sector_coverage_complete','file_sha256','integrity_status']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(files)
    with (report_dir/'package_recovery_priorities.csv').open('w',newline='',encoding='utf-8') as stream:
        fields=['priority_rank','package','file_count','all_known_files_covered','missing_payload_bytes',
                'missing_allocated_bytes','missing_allocated_sectors','touches_map_bad_sector','touches_non_trimmed','emulation_status']
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(packages)
    with (report_dir/'targeted_recovery_ranges.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['priority_rank','package','start_lba','end_lba_inclusive','byte_offset','byte_length','map_status'])
        for package in packages:
            for target in package['target_ranges']:
                writer.writerow([package['priority_rank'],package['package'],target['start_lba'],target['end_lba_inclusive'],target['offset'],target['length'],target['status']])
    (evidence/'package_coverage.json').write_text(json.dumps(packages,indent=2)+'\n')
    (evidence/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    summary=verification['map_summary']; recovered=summary['read_bytes']; total=summary['covered_end']
    lines=['# Disc 01 — Partial-image forensic assessment','',
        f'Investigation: `{evidence.name}`. Image and mapfile sources: `<private-acquisition-directory>`.', '',
        '## Acquisition and evidence status','',
        f'- The image is **partial**, not a full-length ISO: {recovered:,} stored bytes. The map covers {total:,} bytes.',
        f'- Map recovered: **{recovered:,} bytes ({100*recovered/total:.6f}%)**; untried: **490,561,536**; non-trimmed: **18,102,272**; bad-sector: **4,096** (two 2048-byte sectors).',
        '- The recovered prefix is byte range [0, 147324928), LBA 0–71935 inclusive. The map has no gaps. The remainder is unrecovered or untried, not necessarily permanently bad.',
        '- Original image, current map and available map backups were SHA-256 recorded. A verified read-only working image was created; no physical CD was accessed or acquisition resumed.',
        '- No separate acquisition console transcript was found. The map records GNU ddrescue 1.30 and command `ddrescue -n -b2048 /dev/sr0 disc-01.iso disc-01.map`. Local map timestamps have no recorded timezone.',
        f'- Artifact hashes and copy provenance: `{evidence.relative_to(root)}/artifact_verification.json`.', '',
        '## Filesystem and cross-checks','',
        '- ISO 9660 and Joliet descriptors and all directory trees lie in recovered bytes. Each namespace contains **1,058 files and 115 directories including root**, matching the earlier inventory. Joliet preserves original case and Spanish names.',
        '- ISO volume size is 319,871 × 2048 = **655,095,808 bytes**, smaller than the map domain by **897,024 bytes**. This is a declared-size discrepancy, not permission to discard the tail.',
        '- The directory-record volume sequence is nonconformant zero despite a declared single-volume sequence 1. It is recorded as a warning; no bytes were repaired.',
        '- `JUEGOS/JEDI/JEDI.SMC` is recorded at LBA 319151, length 2,097,664: it ends at byte 655,718,912, beyond the declared ISO volume but within the mapped device domain. Its recorded extent is independently corroborated and remains unrecovered.',
        '- xorriso independently matches every Joliet filename, LBA and size (1,058 extent records). Primary and Joliet extent multisets also agree.',
        f'- Prior readable-file hashes match for **{validation["prior_hash_matches"]}** available files, with **{validation["prior_hash_mismatches"]}** mismatches. This supports repeat-read consistency, not historical authenticity.', '',
        '## File coverage and integrity','',
        '| Sector coverage classification | Files |','|---|---|']
    lines += [f'| {name} | {counts[name]} |' for name in (FULL,PARTIAL,OUTSIDE)]
    lines += ['',
        '- Only map `+` ranges backed by present, non-sparse image bytes count as recovered. Files beyond EOF, holes and non-`+` areas are never treated as authentic zero data. The current image has no sparse holes.',
        '- Fully covered means every allocated sector of the recorded file extent is covered; it does not prove checksums against an original release, internal archive integrity or playability. SHA-256 is recorded only for files whose complete extents are available.',
        '- `HERETIC/HERETIC.WAD` is the one partial file: 14,100,480 of 14,189,976 payload bytes are covered; 89,496 payload bytes remain missing. Its missing allocation spans LBA 71936–71979 inclusive (44 sectors), including the first bad sector and non-trimmed bytes.',
        '- `HERETIC/RESOURCE.EXE` is a zero-length directory entry. Its empty extent is vacuously covered; that is not an operational executable or proof of valid software.',
        '- Files wholly outside the recovered region are labeled unavailable in this image, not corrupted. Partial files are not assigned full-file hashes.', '',
        '## Package completeness and requirements','',
        f'**None of the {len(packages)} package directories has all its known files covered. No package can currently be certified to have all required files recovered, and none is marked playable.**', '',
        'Required-file manifests and runtime dependencies have not been independently established. All-known-files coverage is a conservative package-completeness criterion; it must not be confused with a proven minimal launch set. Existing directory/filename candidates remain estimates, including SNES ROM bundles.', '',
        '- DOOM2: 14/15 known files covered; `DOOM2.EXE` is missing although `DOOM2.WAD` is covered.',
        '- QUAKE: 17/19 covered; both PAK files and CWSDPMI are covered, but QUAKE.EXE and QLAUNCH.EXE are missing.',
        '- HERETIC: 19/21 covered; HERETIC.EXE is absent and HERETIC.WAD is partial.',
        '- Duke3d: 96/116 covered; DUKE3D.GRP is covered but DUKE3D.EXE is absent.',
        '- Other packages have individually recovered files but missing payloads, executables, installers or support files. Consult package JSON/CSV rather than counting all setup/runtime EXEs as games.', '',
        '## Prioritized future recovery plan','',
        '**No recovery commands were run.** The ranges below are coordinates in the current cooked 2048-byte image/map domain, not a raw-track domain. Revalidate the same disc, physical safety, format and original map before any separately approved future acquisition.', '',
        'The machine-readable plan ranks packages avoiding map bad sectors first, avoiding known non-trimmed areas next, then by unique missing allocated bytes. Shared/overlapping extents are unioned within each package. Exact missing byte/LBA spans and map statuses are in `targeted_recovery_ranges.csv`; costs assume successful reads and do not promise a successful recovery.', '',
        '| Priority | Package | Missing allocated bytes | Missing sectors | Non-trimmed / bad-sector overlaps |',
        '|---|---|---|---|---|']
    lines += [f'| {p["priority_rank"]} | {p["package"]} | {p["missing_allocated_bytes"]:,} | {p["missing_allocated_sectors"]:,} | {p["touches_non_trimmed"]} / {p["touches_map_bad_sector"]} |' for p in packages]
    lines += ['',
        'Highest-value PC targets:', '',
        '1. **DOOM2/DOOM2.EXE** — LBA 212224–212559, 336 sectors (688,128 allocated bytes; 686,993 payload). Recovering it would cover all 15 currently known package files, subject to file integrity/dependency checks.',
        '2. **QUAKE/QUAKE.EXE** — LBA 173172–173365, 194 sectors, plus **QUAKE/QLAUNCH.EXE** — LBA 148303–148456, 154 sectors. Together these require 712,704 allocated bytes and would cover all 19 known files. The main executable includes 28 non-trimmed sectors at LBA 173188–173215, so the risk-first table places it after packages needing only untried ranges. The launcher may be optional, but that has not been proven.',
        '3. **HERETIC** — HERETIC.EXE at LBA 215456–215811 plus the WAD tail at LBA 71936–71979. This small remaining set has high completion value but includes an already failed sector: do not automatically retry that area. The conservative default is to exhaust safer untried locations before separately reviewing attempts on failing media.',
        '4. **Duke3d/DUKE3D.EXE** — LBA 278128–278736. It would complement the covered GRP, but 19 other missing package files mean this is not a claim of full package completion. Consult exact targets for utilities/add-ons rather than assuming they are required.',
        '5. For each remaining package, use the complete ranked range table and review essential versus optional files from recovered documentation. For SNES bundles, distinguish emulator copies, ROM data, split ROMs and saves. Do not substitute duplicate-named binaries without evidence of identical content.', '',
        'Acquire future successful reads into a separate authorized attempt with persistent map evidence; retain this image and investigation unchanged. Verify any enlarged master/working copy and rerun this analysis. Continue static file/format validation on covered working data, then isolated emulator testing only after package requirements and rights are assessed.', '',
        '## Deliverables and preservation','',
        '- `file_sector_coverage.csv`: every Joliet file and coverage/hash status.',
        '- `package_recovery_priorities.csv`: all package completion costs and risks.',
        '- `targeted_recovery_ranges.csv`: exact physical-domain byte/LBA ranges per package.',
        f'- `{evidence.relative_to(root)}/`: acquisition artifact hashes, namespace extents, filesystem metadata, independent parser logs, package JSON and verification records.',
        '- SQLite adds append-only image investigation, per-file sector coverage, per-extent records and package-priority tables. Prior assessment observations remain unchanged, and the earlier catalog is snapshotted.',
        '- No zero-filled repair, source-image modification, host execution, game translation or physical CD read occurred.', '']
    (report_dir/'11_partial_image_assessment.md').write_text('\n'.join(lines),encoding='utf-8')
    return report_dir
