"""Exercise every installed CLI command using temporary synthetic artifacts."""
import hashlib,json,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_iso_coverage import fixture,record,SECTOR
ROOT=Path(__file__).resolve().parents[1]
class InstalledCommands(unittest.TestCase):
 def test_all_thirteen_operations(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);exe=str(Path(sys.executable).parent/'replay-preservation');seen=[]
   def run(command,*args):
    result=subprocess.run([exe,command,*map(str,args)],capture_output=True,text=True,timeout=20)
    self.assertEqual(result.returncode,0,result.stderr);seen.append(command);return json.loads(result.stdout)['result']
   def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
   image=r/'synthetic.iso';fixture(image);data=bytearray(image.read_bytes())
   entries=record(b'\0',19,SECTOR,2)+record(b'\1',19,SECTOR,2)+record(b'PKG',20,SECTOR,2)
   data[19*SECTOR:20*SECTOR]=entries+b'\0'*(SECTOR-len(entries))
   child=record(b'\0',20,SECTOR,2)+record(b'\1',19,SECTOR,2)+record(b'FILE.DAT;1',25,10)
   data[20*SECTOR:20*SECTOR+len(child)]=child;image.write_bytes(data)
   mp=r/'image.map';mp.write_text(f'0 + 1\n0 {len(data)} +\n')
   imageargs=['--image',image,'--map',mp,'--image-sha256',digest(image),'--map-sha256',digest(mp)]
   self.assertEqual(run('hash',image,'--expected',digest(image))['size'],len(data))
   self.assertEqual(run('map-summary','--map',mp,'--expected-size',len(data))['completion'],'complete')
   self.assertEqual(run('coverage',*imageargs,'--offset',25*SECTOR,'--length',10)['recovered_bytes'],10)
   self.assertTrue(run('inspect-image',*imageargs,'--namespace','ISO9660')['tree']['metadata_complete'])
   self.assertEqual(run('extract-package',*imageargs,'--namespace','ISO9660','--package','PKG','--output-dir',r/'stage')['known_file_count'],1)
   wad=r/'synthetic.wad';wad.write_bytes(b'PWAD'+(0).to_bytes(4,'little')+(12).to_bytes(4,'little'))
   self.assertEqual(run('static-check',wad,'--kind','wad')['lump_count'],0)
   chunk=r/'chunk';chunk.write_bytes(data[25*SECTOR:26*SECTOR]);target=r/'target.map';target.write_text(f'0 + 1\n0 {25*SECTOR} ?\n{25*SECTOR} {SECTOR} +\n{26*SECTOR} {6*SECTOR} ?\n')
   self.assertTrue(run('validate-target','--chunk',chunk,'--map',target,'--chunk-sha256',digest(chunk),'--map-sha256',digest(target),'--offset',25*SECTOR,'--length',SECTOR)['complete'])
   self.assertEqual(run('merge-target','--base-image',image,'--base-map',mp,'--base-sha256',digest(image),'--base-map-sha256',digest(mp),'--chunk',chunk,'--target-map',target,'--chunk-sha256',digest(chunk),'--target-map-sha256',digest(target),'--offset',25*SECTOR,'--length',SECTOR,'--output-dir',r/'derivative')['state'],'verified_derivative')
   self.assertTrue(run('validate-record',ROOT/'templates/preservation_record.json')['valid'])
   manifest=r/'manifest.json';manifest.write_text(json.dumps({'schema':'replay.preservation.manifest.v0.1','sha256':{'synthetic.iso':digest(image)}}));self.assertTrue(run('verify-manifest','--manifest',manifest,'--root',r)['verified'])
   db=r/'catalog.sqlite';connection=sqlite3.connect(db);connection.execute('create table example(id integer)');connection.commit();connection.close();self.assertEqual(run('catalog-check','--catalog',db)['integrity'],['ok'])
   viewer=json.loads((ROOT/'tests/fixtures/disc01_cases.json').read_text())['graphical_v2'];(r/'viewer.json').write_text(json.dumps(viewer));(r/'controller.json').write_text(json.dumps({'mode':'authorized_gameplay','authorization':{'authorized':True,'sessions':1}}));(r/'events.jsonl').write_text(json.dumps({'event':'session_finished','mode':'gameplay','termination_reason':'emulator_exit'})+'\n')
   self.assertFalse(run('session-summary','--viewer',r/'viewer.json','--controller',r/'controller.json','--worker-events',r/'events.jsonl')['full_functional_validation'])
   self.assertFalse(run('pilot-plan','--disc-id','synthetic-disc')['reads_authorized'])
   self.assertEqual(len(set(seen)),13)
