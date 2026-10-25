#!/usr/bin/env python3
"""Build an audited source copy; normalize archive owners without touching evidence."""
import argparse
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from audit_public_tree import audit


def sanitize_sdist(path,epoch=0):
    """Preserve member contents; remove local ownership, variable timestamps/headers."""
    path=Path(path)
    with tarfile.open(path,'r:gz') as archive:
        entries=[(member,archive.extractfile(member).read() if member.isfile() else None) for member in archive.getmembers()]
    output=io.BytesIO()
    with gzip.GzipFile(fileobj=output,mode='wb',filename='',mtime=epoch) as compressed:
        with tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as archive:
            for member,data in entries:
                if not (member.isfile() or member.isdir()):raise ValueError('Unexpected archive link/special member')
                member.uid=member.gid=0;member.uname=member.gname='root';member.mtime=epoch
                member.mode=0o755 if member.isdir() else 0o644;member.pax_headers={}
                archive.addfile(member,io.BytesIO(data) if data is not None else None)
    path.write_bytes(output.getvalue())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',type=Path,required=True,help='New external directory with an existing parent')
    parser.add_argument('--epoch',type=int,default=0,help='Reproducible build timestamp; not a forensic observation time')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1];out=args.out_dir.absolute()
    if args.epoch<0 or out.is_relative_to(root):parser.error('Nonnegative epoch and external output directory required')
    if not audit(root)['passed']:parser.error('Public candidate audit failed')
    out.mkdir(exist_ok=False,parents=False)
    files=json.loads((root/'public-release-files.json').read_text())['files']
    with tempfile.TemporaryDirectory(prefix='replay-public-build-') as tmp:
        copy=Path(tmp)/'source';copy.mkdir()
        for name in files:
            target=copy/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
        env=dict(os.environ,SOURCE_DATE_EPOCH=str(args.epoch),PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable,'-m','build','--no-isolation','--outdir',str(out)],cwd=copy,env=env,check=True)
    for path in out.glob('*.tar.gz'):sanitize_sdist(path,args.epoch)
    print('Built audited public artifacts; source ownership normalized. Nothing published.')
    return 0
if __name__=='__main__':raise SystemExit(main())
