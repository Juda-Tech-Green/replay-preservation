"""Offline reusable workflow regressions; synthetic payloads, no recovered execution."""
import copy,hashlib,importlib.util,json,os,struct,sys,tempfile,unittest
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
from replay_preservation import baseline as b
from replay_preservation.iso_coverage import coverage,SECTOR
from replay_preservation.target_merge import merge_ranges
from replay_preservation.bounded_process_capture import Capture
from test_iso_coverage import fixture,record
import replay_preservation.cli as cli
CASE=json.loads((ROOT/'tests/fixtures/disc01_cases.json').read_text())
class BaselineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name)
 def put(self,name,data):
  p=self.r/name;p.write_bytes(data);return p
 def hash(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def invoke(self,*args):
  import subprocess
  completed=subprocess.run([sys.executable,str(ROOT/'scripts/replay.py'),*args],capture_output=True,text=True,timeout=10)
  return completed.returncode,json.loads(completed.stdout or completed.stderr)
 def test_initial_exact_counts_and_unmapped_not_complete(self):
  end=0;lines=['0 ? 1']
  for s,n in CASE['initial_status_bytes'].items():lines.append(f'{end} {n} {s}');end+=n
  p=self.put('a.map','\n'.join(lines).encode());x=b.map_summary(p,CASE['source_bytes'])
  self.assertEqual(x['read_bytes'],147324928);self.assertAlmostEqual(x['recovery_percentage'],22.4583,places=3);self.assertEqual(x['bad_2048_sector_equivalent'],2);self.assertEqual(x['completion'],'partial')
  self.assertEqual(b.map_summary(p,end+2048)['unmapped_bytes'],2048)
  with self.assertRaises(ValueError):b.map_summary(p,end-1)
 def test_t01_exact_coordinate_conversion(self):
  t=CASE['t01'];p=self.put('chunk',b'X'*t['length']);mp=self.put('target.map',f"0 + 1\n0 {t['offset']} ?\n{t['offset']} {t['length']} +\n{t['offset']+t['length']} {CASE['source_bytes']-t['offset']-t['length']} ?\n".encode())
  x=b.target_validation(p,mp,t['offset'],t['length'],self.hash(p),self.hash(mp))
  self.assertTrue(x['complete']);self.assertEqual(x['covered_bytes'],688128);self.assertEqual(x['end_lba'],212559);self.assertEqual(x['usable_ranges'][0]['chunk_offset'],0)
 def test_t01_changes_one_file_full_not_all_integrity(self):
  t=CASE['t01'];base=[{'offset':0,'length':147324928,'status':'+'},{'offset':147324928,'length':CASE['source_bytes']-147324928,'status':'?'}]
  merged=merge_ranges(base,[{'absolute_offset':t['offset'],'length':t['length']}])
  self.assertEqual(coverage(base,t['offset'],t['length'],CASE['source_bytes'])['recovered_bytes'],0)
  self.assertEqual(coverage(merged,t['offset'],t['length'],CASE['source_bytes'])['missing_bytes'],0)
  # Synthetic extent metadata reproduces the observed one-file coverage transition.
  extents=[(i*2048,2048) for i in range(711)]+[(147324928-1024,2048)]+[(t['offset'],t['length'])]+[(600000000+i*2048,2048) for i in range(345)]
  def counts(rows):
   result={'full':0,'partial':0,'unavailable':0}
   for offset,length in extents:
    x=coverage(rows,offset,length,CASE['source_bytes'])
    result['full' if not x['missing_bytes'] else 'partial' if x['recovered_bytes'] else 'unavailable']+=1
   return result
  self.assertEqual(counts(base),CASE['coverage_before']);self.assertEqual(counts(merged),CASE['coverage_after'])
 def test_bad_checksum_prevents_output_creation(self):
  p=self.put('base',b'A'*4096);mp=self.put('base.map',b'0 + 1\n0 4096 +\n4096 4096 ?\n');ch=self.put('chunk',b'B'*2048);tm=self.put('target.map',b'0 + 1\n0 4096 ?\n4096 2048 +\n6144 2048 ?\n')
  with self.assertRaises(ValueError):b.merge_target(p,mp,ch,tm,'0'*64,self.hash(mp),self.hash(ch),self.hash(tm),4096,2048,self.r/'output')
  self.assertFalse((self.r/'output').exists())
 def test_merge_full_verified_and_never_overwrites(self):
  p=self.put('base',b'A'*4096);mp=self.put('base.map',b'0 + 1\n0 4096 +\n4096 4096 ?\n');ch=self.put('chunk',b'B'*2048);tm=self.put('target.map',b'0 + 1\n0 4096 ?\n4096 2048 +\n6144 2048 ?\n')
  args=(p,mp,ch,tm,self.hash(p),self.hash(mp),self.hash(ch),self.hash(tm),4096,2048,self.r/'output');b.merge_target(*args)
  self.assertEqual((self.r/'output/image.iso').read_bytes(),b'A'*4096+b'B'*2048+b'\0'*2048);self.assertEqual(p.read_bytes(),b'A'*4096)
  with self.assertRaises(FileExistsError):b.merge_target(*args)
 def test_conflict_retains_failed_derivative_not_sources(self):
  p=self.put('base',b'A'*4096);mp=self.put('base.map',b'0 + 1\n0 4096 +\n');ch=self.put('chunk',b'B'*2048);tm=self.put('target.map',b'0 + 1\n0 2048 +\n2048 2048 ?\n')
  with self.assertRaises(ValueError):b.merge_target(p,mp,ch,tm,self.hash(p),self.hash(mp),self.hash(ch),self.hash(tm),0,2048,self.r/'failed')
  self.assertEqual(json.loads((self.r/'failed/FAILED.json').read_text())['state'],'failed_do_not_use');self.assertEqual(p.read_bytes(),b'A'*4096)
 def test_partial_target_no_derivative(self):
  p=self.put('base',b'A'*4096);mp=self.put('base.map',b'0 + 1\n0 4096 +\n4096 8192 ?\n');ch=self.put('chunk',b'B'*2048);tm=self.put('target.map',b'0 + 1\n0 4096 ?\n4096 2048 +\n6144 6144 ?\n')
  with self.assertRaises(ValueError):b.merge_target(p,mp,ch,tm,self.hash(p),self.hash(mp),self.hash(ch),self.hash(tm),4096,4096,self.r/'output')
  self.assertFalse((self.r/'output').exists())
 def test_device_symlink_and_optical_mount_rejected(self):
  with self.assertRaises(ValueError):b.fingerprint('/dev/null')
  p=self.put('file',b'hi');(self.r/'link').symlink_to(p)
  with self.assertRaises(ValueError):b.fingerprint(self.r/'link')
  with patch('pathlib.Path.read_text',return_value=f'1 2 3:4 / {self.r} ro - iso9660 /dev/sr0 ro\n'):
   with self.assertRaises(ValueError):b.regular(p)
 def test_input_changed_during_hash_rejected(self):
  p=self.put('file',b'hi');original=hashlib.file_digest
  def mutate(stream,algorithm):
   value=original(stream,algorithm);p.write_bytes(b'changed');return value
  with patch('replay_preservation.baseline.hashlib.file_digest',side_effect=mutate):
   with self.assertRaises(ValueError):b.fingerprint(p)
 def test_sparse_plus_and_eof_not_recovered(self):
  p=self.r/'sparse'
  with p.open('wb') as f:f.truncate(8192)
  mp=self.put('sparse.map',b'0 + 1\n0 12288 +\n')
  code,x=self.invoke('coverage','--image',str(p),'--map',str(mp),'--image-sha256',self.hash(p),'--map-sha256',self.hash(mp),'--offset','0','--length','12288')
  self.assertEqual(code,0);self.assertEqual(x['result']['recovered_bytes'],0)
 def synthetic_package(self):
  p=self.r/'synthetic.iso';fixture(p);data=bytearray(p.read_bytes())
  root=record(b'\0',19,SECTOR,2)+record(b'\1',19,SECTOR,2)+record(b'PKG',20,SECTOR,2)
  data[19*SECTOR:20*SECTOR]=root+b'\0'*(SECTOR-len(root))
  child=record(b'\0',20,SECTOR,2)+record(b'\1',19,SECTOR,2)+record(b'FILE.DAT;1',25,10)
  data[20*SECTOR:20*SECTOR+len(child)]=child;p.write_bytes(data)
  mp=self.put('map',f'0 + 1\n0 {len(data)} +\n'.encode());return p,mp
 def test_extract_only_full_sector_package(self):
  p,mp=self.synthetic_package();out=self.r/'extract';x=b.extract_package(p,mp,self.hash(p),self.hash(mp),'ISO9660','PKG',out)
  self.assertEqual((out/'files/PKG/FILE.DAT').read_bytes(),b'abcdefghij');self.assertEqual(x['known_file_count'],1);self.assertEqual(x['actual_playability'],'not_tested');self.assertFalse((out/'files/PKG/FILE.DAT').stat().st_mode&0o111)
 def test_extract_rejects_unrecovered_padding_and_path(self):
  p,mp=self.synthetic_package();mp.write_text(f'0 + 1\n0 {25*SECTOR+10} +\n{25*SECTOR+10} {7*SECTOR-10} ?\n')
  with self.assertRaises(ValueError):b.extract_package(p,mp,self.hash(p),self.hash(mp),'ISO9660','PKG',self.r/'extract')
  self.assertFalse((self.r/'extract').exists())
  with self.assertRaises(ValueError):b.extract_package(p,mp,self.hash(p),self.hash(mp),'ISO9660','../PKG',self.r/'extract')
 def test_missing_metadata_and_namespace_do_not_invent_files(self):
  p,mp=self.synthetic_package()
  with self.assertRaises(ValueError):b.inspect_image(p,mp,self.hash(p),self.hash(mp),'Joliet')
  mp.write_text('0 ? 1\n0 65536 ?\n')
  with self.assertRaises(ValueError):b.inspect_image(p,mp,self.hash(p),self.hash(mp),'ISO9660')
 def test_malformed_wad_and_mz_are_structural_failures(self):
  for kind,data in [('wad',b'IWAD'+struct.pack('<ii',100,12)),('mz',b'MZ')]:
   p=self.put(kind,data);code,x=self.invoke('static-check',str(p),'--kind',kind);self.assertEqual(code,2);self.assertIn('error',x)
 def events(self,reason='emulator_exit'):
  return [{'event':'session_finished','mode':'gameplay','utc':'2026-10-25T02:38:13Z','termination_reason':reason,'emulator_returncode':0,'forced_kill':False,'game_returned_to_autoexec':reason=='emulator_exit'}]
 def test_actual_human_gameplay_never_becomes_complete_validation(self):
  viewer=copy.deepcopy(CASE['graphical_v2']);raw=copy.deepcopy(viewer)
  result=b.session_summary(viewer,self.events(),{'mode':'authorized_gameplay','authorization':{'authorized':True,'sessions':1}},{'pause_key_tried':'P','menu_exit':'confirmed','multiplayer_non_use':'unconfirmed'})
  self.assertEqual(result['actual_playability'],'limited_interactive_verified');self.assertFalse(result['full_functional_validation']);self.assertIsNone(result['first_menu']);self.assertIsNone(result['first_level_transition']);self.assertEqual(viewer,raw);self.assertEqual(result['raw_controls']['pause_resume']['result'],'Fail')
 def test_deadline_and_missing_controls_remain_incomplete(self):
  v=copy.deepcopy(CASE['graphical_v2']);v['MAP01']={'result':'Not tested'};v['controls']={}
  x=b.session_summary(v,self.events('deadline'),{'mode':'authorized_gameplay','authorization':{'authorized':True,'sessions':1}});self.assertEqual(x['actual_playability'],'unverified');self.assertEqual(x['termination']['termination_reason'],'deadline')
 def test_synthetic_results_cannot_establish_human_play(self):
  for key in ['synthetic_test','accelerated_regression']:
   v=copy.deepcopy(CASE['graphical_v2']);v[key]=True
   with self.assertRaises(ValueError):b.session_summary(v,self.events(),{'mode':'authorized_gameplay','authorization':{'authorized':True,'sessions':1}})
  v=copy.deepcopy(CASE['graphical_v2']);v['controls']['use']['source']='synthetic_regression';self.assertEqual(b.session_summary(v,self.events(),{'mode':'authorized_gameplay','authorization':{'authorized':True,'sessions':1}})['actual_playability'],'unverified')
 def test_missing_authorization_or_schema_types_cannot_pass(self):
  with self.assertRaises(ValueError):b.session_summary(CASE['graphical_v2'],self.events(),{'mode':'authorized_gameplay'})
  record=json.loads((ROOT/'templates/preservation_record.json').read_text());record['evidence']=['unsupported raw string']
  with self.assertRaises(ValueError):b.validate_record(record)
 def test_historical_output_flood_is_bounded(self):
  c=Capture(64)
  for i in range(10000):c.add(b'x'*100)
  x=c.record();self.assertEqual(x['bytes_seen'],1000000);self.assertTrue(x['truncated']);self.assertEqual(len(x['first'])+len(x['tail']),128)
 def test_independent_statuses_require_scoped_human_evidence(self):
  record=json.loads((ROOT/'templates/preservation_record.json').read_text());b.validate_record(record)
  record['statuses']['actual_playability']='limited_interactive_verified'
  with self.assertRaises(ValueError):b.validate_record(record)
  record['scope']='MAP01 controls only';record['evidence']=[{'source':'human_confirmation','result':'pass','check':'MAP01 and controls'}];b.validate_record(record)
  self.assertEqual(record['statuses']['historical_authenticity'],'unverified')
 def test_cli_deterministic_errors_and_readonly_catalog(self):
  p=self.put('map',b'0 + 1\n0 2048 +\n');args=('map-summary','--map',str(p),'--expected-size','4096');self.assertEqual(self.invoke(*args),self.invoke(*args))
  code,x=self.invoke('pilot-plan','--disc-id','../escape');self.assertEqual(code,2)
  import sqlite3
  db=self.r/'catalog';c=sqlite3.connect(db);c.execute('create table test(a)');c.commit();c.close();before=self.hash(db)
  code,x=self.invoke('catalog-check','--catalog',str(db));self.assertEqual(code,0);self.assertEqual(before,self.hash(db))
 def test_manifest_traversal_and_checksum_failure(self):
  p=self.put('file',b'hello');mp=self.r/'manifest';mp.write_text(json.dumps({'schema':'replay.preservation.manifest.v0.1','sha256':{'file':self.hash(p)}}));self.assertEqual(self.invoke('verify-manifest','--manifest',str(mp),'--root',str(self.r))[0],0)
  mp.write_text(json.dumps({'schema':'replay.preservation.manifest.v0.1','sha256':{'../file':self.hash(p)}}));self.assertEqual(self.invoke('verify-manifest','--manifest',str(mp),'--root',str(self.r))[0],2)
if __name__=='__main__':unittest.main()
