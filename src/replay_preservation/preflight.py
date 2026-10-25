"""Non-media-reading acquisition preflight. Never opens a device or installs tools."""
import json
import os
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PACKAGES = {'ddrescue':'gddrescue','ddrescuelog':'gddrescue','cd-info':'libcdio-utils','xorriso':'xorriso'}


def capture(command):
    result = {'argv':command,'timestamp_utc':datetime.now(timezone.utc).isoformat()}
    try:
        completed=subprocess.run(command,capture_output=True,text=True,timeout=15,check=False)
        result.update(returncode=completed.returncode,stdout=completed.stdout,stderr=completed.stderr)
    except (OSError,subprocess.TimeoutExpired) as error:
        result['error']=str(error)
    return result


def inspect(root, mount, device, operator_condition, package_authorization):
    commands=[capture(['findmnt','--json','--target',str(mount),'-o','TARGET,SOURCE,FSTYPE,OPTIONS']),
              capture(['lsblk','-J','-b','-e','7','-o','NAME,PATH,TYPE,SIZE,FSTYPE,MOUNTPOINTS,RO,MODEL']),
              capture(['df','-B1',str(root)]),
              capture(['apt-cache','policy','gddrescue','libcdio-utils','xorriso'])]
    info={'path':device,'opened':False,'exists':False,'read_access_reported':False}
    try:
        observed=Path(device).lstat()
        info.update(exists=True,block_device=stat.S_ISBLK(observed.st_mode),
                    is_symlink=stat.S_ISLNK(observed.st_mode),
                    read_access_reported=os.access(device,os.R_OK),mode=oct(stat.S_IMODE(observed.st_mode)))
    except OSError as error:
        info['error']=str(error)
    tools={tool:{'path':shutil.which(tool),'package':package} for tool,package in PACKAGES.items()}
    snapshot={'timestamp_utc':datetime.now(timezone.utc).isoformat(),
              'device':info,'mount':str(mount),'commands':commands,'tools':tools,
              'operator_condition':operator_condition,'package_authorization':package_authorization,
              'free_destination_bytes':shutil.disk_usage(root).free,
              'physical_safety':'operator reported; not independently established by software',
              'source_opened':False,'packages_installed':False,
              'acquisition_status':'not started','sector_recovery_percentage':None,
              'track_session_structure':'unknown; device inspection not performed'}
    mount_info=None
    if commands[0].get('returncode')==0:
        try:
            matches=json.loads(commands[0]['stdout'])['filesystems']
            mount_info=next((item for item in matches if item['target']==str(mount)),None)
        except (ValueError,KeyError,TypeError):
            pass
    snapshot['observed_mount']=mount_info
    barriers=[]
    if not mount_info or mount_info['source']!=device or 'ro' not in mount_info['options'].split(','):
        barriers.append('Expected source and exact read-only mount not confirmed')
    if not info['exists'] or not info.get('block_device') or not info['read_access_reported']:
        barriers.append('Raw optical device unavailable to this execution environment; stop acquisition')
    if operator_condition!='same disc; visually intact; no unusual noise or vibration (user reported)':
        barriers.append('Same-disc physical safety confirmation needs review before spinning')
    if any(not item['path'] for item in tools.values()):
        barriers.append('Acquisition/inspection tools missing; installation authorization and appropriate environment required')
    snapshot['barriers']=barriers
    snapshot['next_gate']='Restore approved read-only device access before installing tools or performing media inspection'
    return snapshot


def save(root, disc_id, snapshot):
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path=Path(root)/'evidence'/'acquisition-preflight'/disc_id/f'{stamp}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(snapshot,indent=2)+'\n')
    return path
