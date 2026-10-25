"""Bounded pipe collection for future authorized probes; executes no command on import."""
import os,selectors,subprocess,time
class Capture:
 def __init__(self,limit=65536):self.limit=limit;self.first=bytearray();self.tail=bytearray();self.total=0
 def add(self,data):
  self.total+=len(data)
  n=min(len(data),self.limit-len(self.first));self.first.extend(data[:n])
  if n<len(data):self.tail.extend(data[n:]);self.tail=self.tail[-self.limit:]
 def record(self):return {'bytes_seen':self.total,'truncated':self.total>len(self.first)+len(self.tail),'first':bytes(self.first).decode(errors='replace'),'tail':bytes(self.tail).decode(errors='replace')}
def run(argv,timeout_seconds=60,grace_seconds=5):
 p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE);sel=selectors.DefaultSelector();caps={'stdout':Capture(),'stderr':Capture()}
 for stream,name in [(p.stdout,'stdout'),(p.stderr,'stderr')]:os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,name)
 started=time.monotonic();deadline=started+timeout_seconds;terminated=False;killed=False
 try:
  while sel.get_map():
   now=time.monotonic()
   if now>=deadline and not terminated:
    if p.poll() is None:p.terminate()
    terminated=True
   if now>=deadline+grace_seconds and not killed:
    if p.poll() is None:p.kill()
    killed=True
   if now>=deadline+grace_seconds+1:break
   for key,event in sel.select(.1):
    data=os.read(key.fileobj.fileno(),65536)
    if data:caps[key.data].add(data)
    else:sel.unregister(key.fileobj);key.fileobj.close()
  if p.poll() is None:p.wait(timeout=1)
 finally:
  if p.poll() is None:p.kill();p.wait()
  for key in list(sel.get_map().values()):key.fileobj.close()
  sel.close()
 return {'returncode':p.returncode,'elapsed_seconds':time.monotonic()-started,'deadline_reached':terminated,'forced_kill':killed,**{name:cap.record() for name,cap in caps.items()}}
