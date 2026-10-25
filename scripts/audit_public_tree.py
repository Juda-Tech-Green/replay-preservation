#!/usr/bin/env python3
"""Audit an explicit public file allowlist without initializing Git or publishing.

Static heuristics supplement human review. They cannot prove every secret or
encoded copyrighted payload absent. Findings contain locations, never secret text.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BANNED_SUFFIXES={'.iso','.bin','.img','.exe','.com','.wad','.dsg','.db','.sqlite','.sqlite3','.chunk','.zip','.7z','.rar','.arj','.lzh','.pem','.key','.whl','.gz','.tar'}
PRIVATE_DIRS={'evidence','images','recovery','extracted','reconstructed','catalog','emulation','.venv','venv','build','dist','__pycache__'}
MAGICS=(b'MZ',b'\x7fELF',b'PK\x03\x04',b'SQLite format 3',b'\x89PNG\r\n\x1a\n',b'%PDF-')
SECRET_RULES={
 'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
 'github_token':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
 'aws_access_key':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'jwt':r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b',
 'credential_assignment':r'''(?i)\b(?:api_key|access_token|secret_key|password)\s*[:=]\s*["'][A-Za-z0-9_+/-]{16,}["']''',
 'credential_url':r'https?://[^\s/:]+:[^\s/@]+@',
}
PERSONAL_RULES={
 'personal_absolute_path':r'/(?:home|Users)/[^\s\x22\x27<>]+|/(?:mnt)/data/[^\s\x22\x27<>]+|[A-Za-z]:\\Users\\[^\s\x22\x27<>]+',
 'email_address':r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
}

def audit(root):
    root=Path(root).resolve();findings=[];files=[]
    allowpath=root/'public-release-files.json'
    if not allowpath.is_file():raise ValueError('Reviewed public-release-files.json allowlist is required')
    data=json.loads(allowpath.read_text());allowed=data.get('files')
    if not isinstance(allowed,list) or len(set(allowed))!=len(allowed):raise ValueError('Invalid/duplicate public allowlist')
    for name in allowed:
        if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Unsafe public allowlist path')
    for path in sorted(root.rglob('*')):
        rel=path.relative_to(root)
        if '.git' in rel.parts:continue
        if path.is_symlink():findings.append({'path':str(rel),'rule':'symlink'});continue
        if not path.is_file():continue
        name=rel.as_posix();files.append(name)
        if path.stat().st_size>1024**2:
            findings.append({'path':name,'rule':'larger_than_1_MiB'});continue
        content=path.read_bytes()
        if name not in allowed:findings.append({'path':name,'rule':'not_allowlisted'})
        if any(x in PRIVATE_DIRS or x.endswith('.egg-info') for x in rel.parts):findings.append({'path':name,'rule':'private_or_generated_directory'})
        if path.suffix.lower() in BANNED_SUFFIXES or '.sqlite' in path.name.lower():findings.append({'path':name,'rule':'forbidden_payload_extension'})
        if content.startswith(MAGICS) or b'\0' in content:findings.append({'path':name,'rule':'binary_signature_or_nul'})
        try:text=content.decode('utf-8')
        except UnicodeDecodeError:findings.append({'path':name,'rule':'non_utf8'});continue
        for rule,pattern in {**SECRET_RULES,**PERSONAL_RULES}.items():
            for match in re.finditer(pattern,text):findings.append({'path':name,'line':text.count('\n',0,match.start())+1,'rule':rule})
        if path.suffix=='.md':
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if '://' in link or link.startswith('#'):continue
                target=(path.parent/link.split('#')[0]).resolve()
                if not target.is_relative_to(root) or not target.exists():findings.append({'path':name,'rule':'broken_or_external_local_link','link':link})
    for name in set(allowed)-set(files):findings.append({'path':name,'rule':'missing_allowlisted_file'})
    manifest=root/'PUBLIC_FILE_MANIFEST.md'
    if manifest.is_file():
        sealed=dict(re.findall(r'^\| `([^`]+)` \| \d+ \| `([0-9a-f]{64})` \|',manifest.read_text(),re.M))
        for name in set(allowed)-{'PUBLIC_FILE_MANIFEST.md'}:
            target=root/name
            if name not in sealed or not target.is_file() or target.is_symlink() or target.stat().st_size>1024**2 or hashlib.sha256(target.read_bytes()).hexdigest()!=sealed[name]:
                findings.append({'path':name,'rule':'reviewed_manifest_hash_mismatch'})
    git={'status':'not_initialized','tracked_files':0,'note':'No real index exists; proposed files audited against explicit allowlist. Repeat after authorized initialization/staging.'}
    if (root/'.git').exists():
        raw=subprocess.check_output(['git','ls-files','--cached','-z'],cwd=root)
        tracked=[x.decode() for x in raw.split(b'\0') if x]
        git={'status':'index_inspected','tracked_files':len(tracked)}
        if sorted(tracked)!=sorted(allowed):findings.append({'rule':'tracked_index_differs_from_allowlist'})
    return {'passed':not findings,'candidate_files':len(files),'bytes':sum((root/f).stat().st_size for f in files),'git':git,'findings':findings,'sha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files if (root/f).stat().st_size<=1024**2},'limits':'Custom static patterns and binary/size checks plus explicit allowlist; not exhaustive secret detection, legal certification or vulnerability analysis.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    try:result=audit(args.root)
    except (OSError,ValueError,TypeError) as exc:print(json.dumps({'passed':False,'error':str(exc)}));return 2
    print(json.dumps(result,indent=2,sort_keys=True));return 0 if result['passed'] else 2
if __name__=='__main__':raise SystemExit(main())
