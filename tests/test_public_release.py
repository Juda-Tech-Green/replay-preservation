"""Public packaging and audit regressions; no private evidence or native display."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from replay_preservation.compat.private_x11 import Display
from replay_preservation.compat.private_display_protocol import Client
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('public_audit',ROOT/'scripts/audit_public_tree.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class PublicReleaseTests(unittest.TestCase):
 def test_wheel_cli_entrypoints_agree(self):
  a=subprocess.check_output([sys.executable,'-m','replay_preservation','pilot-plan','--disc-id','synthetic-disc'],text=True)
  b=subprocess.check_output([sys.executable,str(ROOT/'scripts/replay.py'),'pilot-plan','--disc-id','synthetic-disc'],text=True)
  self.assertEqual(json.loads(a),json.loads(b));self.assertFalse(json.loads(a)['result']['execution_authorized'])
 def test_disallowed_native_key_rejected_before_x11_calls(self):
  d=Display.__new__(Display);d.x=Mock();d.t=Mock()
  with self.assertRaises(ValueError):d.key('XF86AudioMute',True)
  d.x.XKeysymToKeycode.assert_not_called();d.t.XTestFakeKeyEvent.assert_not_called()
 def test_security_checks_survive_optimized_python(self):
  code="from replay_preservation.compat.private_x11 import Display; d=Display.__new__(Display); d.key('not_allowed',True)"
  p=subprocess.run([sys.executable,'-O','-c',code],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('ValueError',p.stderr);self.assertNotIn('AttributeError',p.stderr)
 def test_oversized_request_rejected_before_send(self):
  c=Client.__new__(Client);c.s=Mock()
  with self.assertRaises(ValueError):c.request('x'*300)
  c.s.sendall.assert_not_called()
 def test_source_archive_ownership_is_anonymous_and_reproducible(self):
  import io,tarfile
  sys.path.insert(0,str(ROOT/'scripts'))
  from build_public_release import sanitize_sdist
  with tempfile.TemporaryDirectory() as tmp:
   archive=Path(tmp)/'synthetic.tar.gz'
   with tarfile.open(archive,'w:gz') as out:
    item=tarfile.TarInfo('source/example.txt');item.size=4;item.uid=1234;item.gid=1234;item.uname='private-owner';item.gname='private-group';item.mtime=123456
    out.addfile(item,io.BytesIO(b'test'))
   sanitize_sdist(archive);first=archive.read_bytes();sanitize_sdist(archive);self.assertEqual(archive.read_bytes(),first)
   with tarfile.open(archive) as out:
    item=out.getmembers()[0];self.assertEqual((item.uid,item.gid,item.uname,item.gname,item.mtime),(0,0,'root','root',0));self.assertEqual(out.extractfile(item).read(),b'test')
 def test_scanner_detects_unlisted_binary_secret_and_path(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'public-release-files.json').write_text(json.dumps({'files':['public-release-files.json','readme.md']}));(root/'readme.md').write_text('safe\n')
   self.assertTrue(audit.audit(root)['passed'])
   (root/'unexpected').write_bytes(b'M'+b'Z'+b'\0'+b'fake')
   (root/'readme.md').write_text('gh'+'p_'+'A'*36+'\n'+'/'+'home'+'/example/private\n')
   rules={x['rule'] for x in audit.audit(root)['findings']}
   self.assertTrue({'not_allowlisted','binary_signature_or_nul','github_token','personal_absolute_path'}<=rules)
 def test_reviewed_manifest_rejects_same_name_content_change(self):
  import hashlib
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);names=['public-release-files.json','PUBLIC_FILE_MANIFEST.md','example.md']
   (root/names[0]).write_text(json.dumps({'files':names}));(root/'example.md').write_text('reviewed')
   rows=[f"| `{name}` | {(root/name).stat().st_size} | `{hashlib.sha256((root/name).read_bytes()).hexdigest()}` | reviewed |" for name in names if name!='PUBLIC_FILE_MANIFEST.md']
   (root/'PUBLIC_FILE_MANIFEST.md').write_text('\n'.join(rows));self.assertTrue(audit.audit(root)['passed'])
   (root/'example.md').write_text('changed');self.assertIn('reviewed_manifest_hash_mismatch',{x['rule'] for x in audit.audit(root)['findings']})
 def test_scanner_rejects_escape_allowlist_and_links(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'public-release-files.json';p.write_text(json.dumps({'files':['../outside']}))
   with self.assertRaises(ValueError):audit.audit(root)
   p.write_text(json.dumps({'files':['public-release-files.json','readme.md']}));(root/'readme.md').write_text('[missing](missing.md)')
   self.assertIn('broken_or_external_local_link',{x['rule'] for x in audit.audit(root)['findings']})
