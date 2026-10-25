"""Single-pass file assessment on an explicitly selected read-only mount.

No extraction, execution, imaging, repairs, application-level retries, or source writes.
The kernel/drive may perform internal retries; userspace cannot promise otherwise.
"""
import csv
import hashlib
import json
import os
import platform
import re
import sqlite3
import stat
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .catalog import initialize
from .signatures import classify

READABLE = 'readable, historical integrity unverified'
READ_ERROR = 'read error'
CHANGED = 'changed during assessment'
NOT_ASSESSED = 'not assessed'
HEADER_LIMIT = 1024 * 1024
CHUNK_SIZE = 1024 * 1024

ASSESSMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS assessment_runs (
 run_id TEXT PRIMARY KEY, disc_id TEXT NOT NULL REFERENCES discs(disc_id),
 started_utc TEXT NOT NULL, ended_utc TEXT, source_path TEXT NOT NULL,
 mount_json TEXT NOT NULL, command_json TEXT NOT NULL,
 status TEXT NOT NULL, summary_json TEXT, supporting_log TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assessment_entries (
 run_id TEXT NOT NULL REFERENCES assessment_runs(run_id), original_path TEXT NOT NULL,
 kind TEXT NOT NULL, metadata_json TEXT, status TEXT NOT NULL,
 bytes_read INTEGER NOT NULL DEFAULT 0, sha256 TEXT, classification_json TEXT,
 error_json TEXT, PRIMARY KEY(run_id, original_path)
);
INSERT OR IGNORE INTO schema_info VALUES(2);
"""


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def error_details(error):
    return {'type':type(error).__name__, 'message':str(error), 'errno':getattr(error,'errno',None)}


def metadata(info):
    # ctime is the observed inode-change timestamp, not a creation date.
    return {'size':info.st_size, 'mtime_ns':info.st_mtime_ns,
            'atime_ns':info.st_atime_ns, 'ctime_ns':info.st_ctime_ns,
            'mode':info.st_mode, 'device':info.st_dev, 'inode':info.st_ino,
            'uid':info.st_uid, 'gid':info.st_gid}


def stable_identity(info):
    return tuple(info[key] for key in ('device','inode','size','mtime_ns','ctime_ns','mode'))


def mount_snapshot(source):
    """Read kernel mount metadata, without touching an optical device node."""
    source = Path(source)
    if source != source.resolve(strict=True):
        raise ValueError('Source must be a canonical path without symlink components')
    def decode(value):
        return re.sub(r'\\([0-7]{3})', lambda match:chr(int(match[1],8)), value)
    matches = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        before, after = line.split(' - ',1)
        fields, extra = before.split(), after.split()
        if decode(fields[4]) == str(source):
            matches.append({'mount_id':fields[0], 'device':fields[2],
                            'root':decode(fields[3]), 'target':decode(fields[4]),
                            'options':fields[5], 'filesystem':extra[0],
                            'source':decode(extra[1]), 'super_options':extra[2]})
    if len(matches) != 1:
        raise ValueError('Source must identify one exact, unambiguous mount point')
    result = matches[0]
    if 'ro' not in result['options'].split(','):
        raise ValueError('Source mount must be read-only')
    result['root_identity'] = metadata(source.lstat())
    if not stat.S_ISDIR(result['root_identity']['mode']):
        raise ValueError('Source must be a mounted directory')
    # Only identity fields: directory size/timestamps may not be stable on all filesystems.
    result['root_identity'] = {key:result['root_identity'][key] for key in ('device','inode','mode')}
    return result


def open_parent(root_fd, relative):
    """Walk each path component without following links or crossing filesystems."""
    fd = os.dup(root_fd)
    device = os.fstat(fd).st_dev
    try:
        for part in Path(relative).parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            if os.fstat(fd).st_dev != device:
                raise ValueError('Nested filesystem is outside the assessment source')
        return fd
    except BaseException:
        os.close(fd)
        raise


def discover(root_fd):
    """Enumerate metadata only; preserve every skipped link and directory error."""
    entries = []
    device = os.fstat(root_fd).st_dev
    def walk(fd, prefix):
        try:
            with os.scandir(fd) as iterator:
                names = sorted(entry.name for entry in iterator)
        except OSError as error:
            existing = next((item for item in entries if item['path'] == (prefix or '.')),None)
            if existing is not None:
                existing.update(kind='enumeration error',error=error_details(error))
            else:
                entries.append({'path':prefix or '.', 'kind':'enumeration error',
                                'metadata':None, 'error':error_details(error)})
            return
        for name in names:
            relative = f'{prefix}/{name}' if prefix else name
            try:
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if info.st_dev != device:
                    kind = 'nested filesystem'
                elif stat.S_ISLNK(info.st_mode):
                    kind = 'symlink'
                elif stat.S_ISDIR(info.st_mode):
                    kind = 'directory'
                elif stat.S_ISREG(info.st_mode):
                    kind = 'file'
                else:
                    kind = 'special file'
                entries.append({'path':relative, 'kind':kind, 'metadata':metadata(info), 'error':None})
                if kind == 'directory':
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        if stable_identity(metadata(os.fstat(child))) != stable_identity(metadata(info)):
                            raise ValueError('Directory changed during enumeration')
                        walk(child,relative)
                    finally:
                        os.close(child)
            except (OSError, ValueError) as error:
                # Retain the failed path even when lstat/open fails.
                entries[:] = [item for item in entries if item['path'] != relative]
                entries.append({'path':relative, 'kind':'enumeration error',
                                'metadata':None, 'error':error_details(error)})
    walk(root_fd,'')
    return entries


def assess_file(root_fd, entry, reader=os.read):
    """One open and forward read, with identity/size checks and a bounded header."""
    result = {'status':NOT_ASSESSED, 'bytes_read':0, 'sha256':None,
              'classification':None, 'error':None}
    digest = hashlib.sha256()
    header = bytearray()
    parent_fd = fd = None
    try:
        parent_fd = open_parent(root_fd,entry['path'])
        fd = os.open(Path(entry['path']).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=parent_fd)
        before = metadata(os.fstat(fd))
        if not stat.S_ISREG(before['mode']) or stable_identity(before) != stable_identity(entry['metadata']):
            result.update(status=CHANGED, error={'message':'File identity or metadata changed before reading'})
            return result
        # Bound reads to the original length plus one byte to detect growth without reading forever.
        while result['bytes_read'] <= before['size']:
            block = reader(fd,min(CHUNK_SIZE,before['size']+1-result['bytes_read']))
            if not block:
                break
            digest.update(block)
            result['bytes_read'] += len(block)
            header.extend(block[:max(0,HEADER_LIMIT-len(header))])
        after = metadata(os.fstat(fd))
        path_after = metadata(os.stat(Path(entry['path']).name,dir_fd=parent_fd,follow_symlinks=False))
        if (result['bytes_read'] != before['size'] or stable_identity(before) != stable_identity(after)
                or stable_identity(after) != stable_identity(path_after)):
            result.update(status=CHANGED, error={'message':'Size, metadata, or path identity changed during assessment',
                                               'expected_bytes':before['size'], 'observed_metadata':after})
        else:
            result.update(status=READABLE,sha256=digest.hexdigest())
    except OSError as error:
        result.update(status=READ_ERROR,error=error_details(error))
    except ValueError as error:
        result.update(status=CHANGED,error=error_details(error))
    finally:
        if fd is not None:
            os.close(fd)
        if parent_fd is not None:
            os.close(parent_fd)
    result['classification'] = classify(bytes(header),entry['path'])
    return result


def write_json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def run_assessment(root, source, disc_id, command, expected_device=None, expected_filesystem=None,
                   mount_probe=mount_snapshot, file_assessor=assess_file, progress=print):
    root, source = Path(root), Path(source).absolute()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',disc_id):
        raise ValueError('Disc ID must be 1-64 ASCII letters, digits, underscores or hyphens')
    initial_mount = mount_probe(source)
    if source == root or source in root.parents or root in source.parents:
        raise ValueError('Source and workspace must be separate directory trees')
    if expected_device and initial_mount['source'] != expected_device:
        raise ValueError('Mounted source device differs from expected device')
    if expected_filesystem and initial_mount['filesystem'] != expected_filesystem:
        raise ValueError('Mounted filesystem differs from expected filesystem')
    initialize(root/'catalog'/'catalog.sqlite')
    db = sqlite3.connect(root/'catalog'/'catalog.sqlite')
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript(ASSESSMENT_SCHEMA)
    existing = db.execute('SELECT source_description FROM discs WHERE disc_id=?',(disc_id,)).fetchone()
    if existing and existing[0] != str(source):
        db.close()
        raise ValueError('Disc ID already belongs to a different source; choose a new ID')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8]
    output = root/'evidence'/'assessments'/disc_id/run_id
    output.mkdir(parents=True,exist_ok=False)
    logpath = output/'events.jsonl'
    started = utcnow()
    summary = {'run_id':run_id, 'disc_id':disc_id, 'source':str(source),
               'started_utc':started, 'mount':initial_mount, 'command':command,
               'python_version':platform.python_version(), 'status':'in progress',
               'actor':{'uid':os.getuid(),'gid':os.getgid(),'pid':os.getpid()},
               'implementation_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in (Path(__file__),Path(__file__).with_name('signatures.py'),
                                Path(__file__).with_name('catalog.py'))},
               'acquisition_status':'not acquired; mounted-file assessment only',
               'stop_reason':None}
    entries = []
    root_fd = None
    abort_error = None
    with logpath.open('x',encoding='utf-8') as log:
        def event(operation, **details):
            record = {'timestamp_utc':utcnow(), 'operation':operation, **details}
            log.write(json.dumps(record,ensure_ascii=True)+'\n')
            log.flush()
            os.fsync(log.fileno())
        db.execute('INSERT OR IGNORE INTO discs(disc_id,label,source_description,filesystem,acquisition_status) VALUES(?,?,?,?,?)',
                   (disc_id,source.name,str(source),initial_mount['filesystem'],'not acquired'))
        db.execute('INSERT INTO assessment_runs VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (run_id,disc_id,started,None,str(source),json.dumps(initial_mount),json.dumps(command),
                    'in progress',None,str(logpath.relative_to(root))))
        db.commit()
        write_json(output/'summary.json',summary)
        event('assessment_started', **summary)
        try:
            root_fd = os.open(source,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            identity = initial_mount['root_identity']
            if any(metadata(os.fstat(root_fd))[key] != identity[key] for key in identity):
                raise ValueError('Source root changed before enumeration')
            entries = discover(root_fd)
            for item in entries:
                item.update(status=NOT_ASSESSED,bytes_read=0,sha256=None,classification=None)
            for item in entries:
                db.execute('INSERT INTO assessment_entries VALUES(?,?,?,?,?,?,?,?,?)',
                           (run_id,item['path'],item['kind'],json.dumps(item['metadata']),NOT_ASSESSED,
                            0,None,None,json.dumps(item['error']) if item['error'] else None))
            db.commit()
            write_json(output/'enumeration.json',entries)
            event('enumeration_finished', entries=len(entries))
            if any(item['kind'] == 'enumeration error' for item in entries):
                summary['stop_reason'] = 'Enumeration failed; file contents not read; coverage is incomplete'
            last_progress = time.monotonic()
            tested = 0
            for item in entries:
                if summary['stop_reason']:
                    break
                if item['kind'] != 'file':
                    continue
                # Revalidate the actual mount ID, read-only state and source before every file.
                if mount_probe(source) != initial_mount:
                    summary['stop_reason'] = 'Mount identity or read-only state changed'
                    break
                item.update(file_assessor(root_fd,item))
                tested += 1
                db.execute('UPDATE assessment_entries SET status=?,bytes_read=?,sha256=?,classification_json=?,error_json=? WHERE run_id=? AND original_path=?',
                           (item['status'],item['bytes_read'],item['sha256'],json.dumps(item['classification']),
                            json.dumps(item['error']) if item['error'] else None,run_id,item['path']))
                db.execute('''INSERT INTO files(disc_id,original_path,file_size,sha256,detected_format,recovery_status,
                              damage_information,mtime_ns,mode,provenance) VALUES(?,?,?,?,?,?,?,?,?,?)
                              ON CONFLICT(disc_id,original_path) DO UPDATE SET file_size=excluded.file_size,
                              sha256=excluded.sha256,detected_format=excluded.detected_format,recovery_status=excluded.recovery_status,
                              damage_information=excluded.damage_information,mtime_ns=excluded.mtime_ns,
                              mode=excluded.mode,provenance=excluded.provenance''',
                           (disc_id,item['path'],item['metadata']['size'],item['sha256'],
                            (item['classification'] or {}).get('format'),item['status'],
                            json.dumps(item['error']) if item['error'] else None,
                            item['metadata']['mtime_ns'],item['metadata']['mode'],
                            json.dumps({'run_id':run_id,'source':'mounted original; no acquisition',
                                        'log':str(logpath.relative_to(root))})))
                db.commit()
                event('file_assessed',path=item['path'],status=item['status'],bytes_read=item['bytes_read'],error=item['error'])
                if item['status'] == READ_ERROR:
                    summary['stop_reason'] = 'Stopped at first file read error; no application-level retries'
                if time.monotonic()-last_progress >= 10:
                    progress(f'Assessed {tested} files; {item["path"]}')
                    last_progress = time.monotonic()
            if not summary['stop_reason'] and mount_probe(source) != initial_mount:
                summary['stop_reason'] = 'Mount changed at end of assessment; coverage cannot be certified'
        except (Exception, KeyboardInterrupt) as error:
            abort_error = error
            summary['stop_reason'] = f'{type(error).__name__}: {error}'
            event('assessment_exception',error=error_details(error))
        finally:
            if root_fd is not None:
                os.close(root_fd)
            counts = Counter(item['status'] for item in entries if item['kind'] == 'file')
            summary.update(ended_utc=utcnow(), status='stopped' if summary['stop_reason'] else 'completed',
                           file_status_counts=dict(counts), discovered_regular_files=sum(counts.values()),
                           enumerated_entries=len(entries),
                           discovered_file_bytes=sum(item['metadata']['size'] for item in entries if item['kind']=='file'),
                           bytes_read=sum(item['bytes_read'] for item in entries),
                           header_warnings=sum(bool((item['classification'] or {}).get('warning')) for item in entries),
                           enumeration_errors=sum(item['kind']=='enumeration error' for item in entries),
                           skipped_entries=sum(item['kind'] not in ('file','directory','enumeration error') for item in entries),
                           coverage_complete=not summary['stop_reason'] and all(item['status']==READABLE for item in entries if item['kind']=='file'),
                           limitations=['Readability and SHA-256 do not prove historical integrity or playability.',
                                        'No sector image, physical condition test, archive decompression, or track/session analysis.',
                                        'No application-level retries; kernel/drive retries are outside this tool control.',
                                        'Names reflect the existing mount view; original on-disc namespaces are not reconstructed.'])
            db.execute('UPDATE assessment_runs SET ended_utc=?,status=?,summary_json=? WHERE run_id=?',
                       (summary['ended_utc'],summary['status'],json.dumps(summary),run_id))
            db.execute('INSERT INTO recovery_events(disc_id,timestamp,operation,source,output,result,supporting_log,command_json,tool_version) VALUES(?,?,?,?,?,?,?,?,?)',
                       (disc_id,summary['ended_utc'],'mounted_file_assessment',str(source),str(output.relative_to(root)),
                        summary['status'],str(logpath.relative_to(root)),json.dumps(command),'Python '+platform.python_version()))
            db.commit()
            db.close()
            write_json(output/'summary.json',summary)
            write_json(output/'files.json',entries)
            with (output/'files.csv').open('w',encoding='utf-8',newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['original_path','kind','file_size','mtime_ns','status','bytes_read','sha256','detected_format','header_warning','error'])
                for item in entries:
                    info,classification = item['metadata'] or {},item['classification'] or {}
                    writer.writerow([item['path'],item['kind'],info.get('size'),info.get('mtime_ns'),item['status'],item['bytes_read'],
                                     item['sha256'],classification.get('format'),classification.get('warning'),json.dumps(item['error']) if item['error'] else ''])
            event('assessment_finished', **summary)
    render_reports(root,output,summary,entries)
    # Hash output artifacts, not the source a second time.
    checksums = {path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(output.iterdir()) if path.is_file()}
    write_json(output/'checksums.json',checksums)
    progress(f'Assessment {summary["status"]}: {output}')
    if abort_error:
        raise abort_error
    return summary, output


def render_reports(root, output, summary, entries):
    counts = summary['file_status_counts']
    lines = ['# Mounted-file condition assessment','',
             f'Disc ID: `{summary["disc_id"]}`',f'Source: `{summary["source"]}`',
             f'Run: `{summary["run_id"]}`',f'Started UTC: {summary["started_utc"]}',
             f'Ended UTC: {summary["ended_utc"]}',f'Status: {summary["status"]}', '',
             '**This is a mounted-file assessment, not forensic acquisition or a physical disc safety test.**','',
             '| File status | Count |','|---|---|']
    lines += [f'| {status} | {counts.get(status,0)} |' for status in (READABLE,READ_ERROR,CHANGED,NOT_ASSESSED)]
    lines += ['',f'- Discovered regular files: {summary["discovered_regular_files"]}.',
              f'- Discovered file bytes: {summary["discovered_file_bytes"]}.',
              f'- Bytes read: {summary["bytes_read"]}.',f'- Enumeration errors: {summary["enumeration_errors"]}.',
              f'- Skipped links/special entries: {summary["skipped_entries"]}.',
              f'- Header warnings (not proof of damage): {summary["header_warnings"]}.',
              f'- All discovered regular files read successfully: {summary["coverage_complete"]}.',
              f'- Stop reason: {summary["stop_reason"] or "None"}.','',
              'Full per-path metadata, errors, untested entries, classifications and SHA-256 are in `files.json` and `files.csv` beside this report.', '',
              '## Limitations',''] + ['- '+value for value in summary['limitations']]
    report = '\n'.join(lines)+'\n'
    (output/'report.md').write_text(report,encoding='utf-8')
    report_dir = root/'reports'/summary['disc_id']
    report_dir.mkdir(exist_ok=True)
    (report_dir/'03_damage_assessment.md').write_text(report,encoding='utf-8')
    (report_dir/'04_filesystem_analysis.md').write_text(
        '# Filesystem observations\n\n'+json.dumps(summary['mount'],indent=2)+'\n\n'
        'Observed mount metadata only. ISO descriptor extensions, alternate namespaces, tracks and sessions have not been independently analyzed.\n',encoding='utf-8')
    # Preserve the global manifest's existing fields and append this run without claiming acquisition.
    manifest_path = root/'reports'/'forensic_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['stage'] = 'mounted-file assessment; acquisition pending'
    manifest['warning'] = 'File readability is not historical integrity, complete disc acquisition, or playability.'
    manifest.setdefault('assessments',[]).append({'disc_id':summary['disc_id'],'run_id':summary['run_id'],
        'source':summary['source'],'status':summary['status'],'evidence':str(output.relative_to(root))})
    write_json(manifest_path,manifest)
