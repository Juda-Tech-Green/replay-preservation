#!/usr/bin/env python3
"""RE Preservation Baseline v0.1 offline CLI. Never acquires or executes software."""
import argparse
import json
import sqlite3
import struct
from contextlib import closing
import sys
from pathlib import Path
from replay_preservation import baseline as b
from replay_preservation.iso_coverage import coverage


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version',action='version',version='RE Preservation 0.1.0-alpha (schema baseline '+b.VERSION+')')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('hash');s.add_argument('path');s.add_argument('--expected')
    s=sub.add_parser('map-summary');s.add_argument('--map',required=True);s.add_argument('--expected-size',type=int,required=True)
    def image_args(s):
        for a in ('image','map','image-sha256','map-sha256'):s.add_argument('--'+a,required=True)
    s=sub.add_parser('coverage');image_args(s);s.add_argument('--offset',type=int,required=True);s.add_argument('--length',type=int,required=True)
    s=sub.add_parser('inspect-image');image_args(s);s.add_argument('--namespace',choices=['Joliet','ISO9660'],required=True)
    s=sub.add_parser('extract-package');image_args(s);s.add_argument('--namespace',choices=['Joliet','ISO9660'],required=True);s.add_argument('--package',required=True);s.add_argument('--output-dir',required=True)
    s=sub.add_parser('validate-target')
    for a in ('chunk','map','chunk-sha256','map-sha256'):s.add_argument('--'+a,required=True)
    for a in ('offset','length'):s.add_argument('--'+a,type=int,required=True)
    s=sub.add_parser('merge-target')
    for a in ('base-image','base-map','chunk','target-map','base-sha256','base-map-sha256','chunk-sha256','target-map-sha256','output-dir'):s.add_argument('--'+a,required=True)
    for a in ('offset','length'):s.add_argument('--'+a,type=int,required=True)
    s=sub.add_parser('static-check');s.add_argument('path');s.add_argument('--kind',choices=['mz','wad'],required=True)
    s=sub.add_parser('validate-record');s.add_argument('path')
    s=sub.add_parser('verify-manifest');s.add_argument('--manifest',required=True);s.add_argument('--root',required=True)
    s=sub.add_parser('catalog-check');s.add_argument('--catalog',required=True)
    s=sub.add_parser('session-summary')
    for a in ('viewer','worker-events','controller'):s.add_argument('--'+a,required=True)
    s.add_argument('--human')
    s=sub.add_parser('pilot-plan');s.add_argument('--disc-id',required=True)
    args=p.parse_args(argv);a=vars(args).copy();cmd=a.pop('command');inputs=[]
    try:
        if cmd=='hash':result=b.fingerprint(args.path,args.expected);inputs=[result]
        elif cmd=='map-summary':inputs=[b.fingerprint(args.map)];result=b.map_summary(args.map,args.expected_size)
        elif cmd=='coverage':
            inspector,inputs=b.verified_inspector(args.image,args.map,args.image_sha256,args.map_sha256)
            result=coverage(inspector.ranges,args.offset,args.length,inspector.size,inspector.holes)
        elif cmd in ('inspect-image','extract-package'):
            a['map_path']=a.pop('map');result=(b.inspect_image if cmd=='inspect-image' else b.extract_package)(**a);inputs=result['inputs']
        elif cmd=='validate-target':a['map_path']=a.pop('map');result=b.target_validation(**a);inputs=result['inputs']
        elif cmd=='merge-target':result=b.merge_target(**a);inputs=result['inputs']
        elif cmd=='static-check':inputs=[b.fingerprint(args.path)];result=b.static_check(args.path,args.kind)
        elif cmd=='validate-record':inputs=[b.fingerprint(args.path)];result=b.validate_record(b.read_json(args.path))
        elif cmd=='verify-manifest':
            inputs=[b.fingerprint(args.manifest)];root=Path(args.root).resolve();manifest=b.read_json(args.manifest)
            # Canonical map format; original manifests need explicit adapters, never guesses.
            if manifest.get('schema')!='replay.preservation.manifest.v0.1' or not isinstance(manifest.get('sha256'),dict):raise ValueError('Expected baseline manifest schema and sha256 mapping')
            checks=[]
            for name,h in sorted(manifest['sha256'].items()):
                if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Manifest path must be relative and contained')
                checks.append(b.fingerprint(root/name,h))
            result={'verified':True,'artifacts':checks}
        elif cmd=='catalog-check':
            path=b.regular(args.catalog);inputs=[b.fingerprint(path)]
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
                db.execute('PRAGMA query_only=ON');integrity=[r[0] for r in db.execute('PRAGMA integrity_check')];fk=db.execute('PRAGMA foreign_key_check').fetchall()
                tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                counts={t:db.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
            if integrity!=['ok'] or fk:raise ValueError('Catalog integrity/foreign-key check failed')
            result={'integrity':integrity,'foreign_key_errors':fk,'table_counts':counts}
        elif cmd=='session-summary':
            paths=[args.viewer,args.worker_events,args.controller]+([args.human] if args.human else []);inputs=[b.fingerprint(x) for x in paths]
            events=[json.loads(l) for l in b.bounded_bytes(args.worker_events,16*1024**2).decode().splitlines() if l.strip()]
            result=b.session_summary(b.read_json(args.viewer),events,b.read_json(args.controller),b.read_json(args.human) if args.human else None)
        else:
            if not __import__('re').fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',args.disc_id):raise ValueError('Invalid disc ID')
            result={'disc_id':args.disc_id,'state':'planned_only','reads_authorized':False,'execution_authorized':False,'stages':['assign independent disc identity and operator physical assessment','obtain separate acquisition scope and access authorization','record tools, tracks/session geometry and fresh acquisition artifacts','offline verify hashes and map coordinates','inspect metadata and rank exact missing extents','extract sector-covered known packages and run bounded static checks','prepare harmless isolation probes','request scoped supervised execution authorization','append scoped observations and seal evidence'],'pause_guidance':'Use physical Pause/Break when the game binding supports it; P is not the validated DOOM II pause instruction.'}
        for item in inputs:b.fingerprint(item['path'],item['sha256'])
        print(json.dumps({'schema':'replay.preservation.analysis.v0.1','operation':cmd,'inputs':inputs,'result':result},sort_keys=True,indent=2,ensure_ascii=False))
        return 0
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,struct.error,sqlite3.Error) as exc:
        print(json.dumps({'schema':'replay.preservation.error.v0.1','operation':cmd,'error':str(exc)},sort_keys=True),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
