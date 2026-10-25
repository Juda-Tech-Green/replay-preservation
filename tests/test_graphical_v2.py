import hashlib,importlib.util,json,socket,struct,sys,tempfile,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from replay_preservation.compat.viewer_state_v2 import Evidence,countdown,OUTER_SECONDS,GAME_SECONDS,CPU_SECONDS,AS_BYTES
from replay_preservation.compat.private_display_protocol import Client
try:
 from replay_preservation.compat.viewer_v2 import Viewer,ALLOWED
except ImportError:
 Viewer=None;ALLOWED=set()
class WorkflowTests(unittest.TestCase):
 def test_deadline_beyond_old_stop(self):
  self.assertEqual(countdown(600,150),('07:30',450));self.assertEqual(countdown(600,599.01),('00:01',1));self.assertEqual(countdown(600,600),('00:00',0));self.assertEqual(countdown(600,900),('00:00',0))
 def test_resource_budget_review(self):
  self.assertGreater(CPU_SECONDS,OUTER_SECONDS);self.assertLess(GAME_SECONDS,OUTER_SECONDS-10);self.assertEqual(AS_BYTES,1024**3)
 def test_first_observation_and_synthetic_provenance(self):
  with tempfile.TemporaryDirectory() as d:
   e=Evidence(Path(d)/'v.json',0,600,True);e.event('first_visible_game_menu',now=5);e.event('first_visible_game_menu',now=10);e.control('movement','Pass')
   self.assertEqual(e.data['observations']['first_visible_game_menu']['elapsed_seconds'],5);self.assertEqual(e.data['controls']['movement']['source'],'synthetic_regression');self.assertEqual(e.data['controls']['firing']['result'],'Not tested')
 def test_screenshot_hash_unique_and_bounded(self):
  with tempfile.TemporaryDirectory() as d:
   e=Evidence(Path(d)/'v.json',0,600);i=e.save_frame(b'data','test',lambda x:x);j=e.save_frame(b'data','test',lambda x:x);self.assertNotEqual(i['path'],j['path']);self.assertEqual(i['sha256'],hashlib.sha256(b'data').hexdigest());self.assertIn('utc',i)
   e.data['screenshots']=[{}]*32
   with self.assertRaises(ValueError):e.save_frame(b'data','test',lambda x:x)
 def test_invalid_control_result_not_accepted(self):
  with tempfile.TemporaryDirectory() as d:
   e=Evidence(Path(d)/'v.json',0,600)
   with self.assertRaises(ValueError):e.control('movement','playable')
 @unittest.skipUnless(Viewer is not None,'Optional Tk unavailable')
 def test_no_host_keys_added(self):
  for key in ['clipboard','START','/bin/sh','XF86AudioMute','F11','semicolon']:self.assertNotIn(key,ALLOWED)
  self.assertIn('Control_L',ALLOWED);self.assertIn('space',ALLOWED)
 @unittest.skipUnless(Viewer is not None,'Optional Tk unavailable')
 def test_focus_blocks_keys_and_no_duplicate_down(self):
  v=Viewer.__new__(Viewer);v.ended=False;v.focused=False;v.pressed=set();events=[];v.enqueue=events.append;v.key('Up',True);self.assertEqual(events,[])
  v.focused=True;v.key('Up',True);v.key('Up',True);v.key('Up',False);self.assertEqual(events,[('Up',True),('Up',False)])
 @unittest.skipUnless(Viewer is not None,'Optional Tk unavailable')
 def test_focus_loss_releases_all_held_keys(self):
  v=Viewer.__new__(Viewer);v.pressed={'Up','Control_L'};events=[];v.enqueue=events.append;v.release_all();self.assertEqual(set(events),{('Up',False),('Control_L',False)});self.assertEqual(v.pressed,set())
 def test_forged_frame_length_rejected_before_allocation(self):
  with tempfile.TemporaryDirectory() as d:
   path=str(Path(d)/'s');server=socket.socket(socket.AF_UNIX);server.bind(path);server.listen()
   def serve():
    s,_=server.accept();s.recv(256);s.sendall(b'F'+struct.pack('>I',0xffffffff));s.close()
   t=threading.Thread(target=serve);t.start();client=Client(path)
   with self.assertRaises(ValueError):client.request('frame')
   client.close();t.join();server.close()
if __name__=='__main__':unittest.main()
