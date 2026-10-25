from contextlib import closing
"""Synthetic assessment fixtures: no optical media required."""
import errno
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from replay_preservation.assessment import (READABLE, READ_ERROR, CHANGED, NOT_ASSESSED,
    HEADER_LIMIT, assess_file, discover, metadata, mount_snapshot, run_assessment)


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source = self.base/'source'
        self.source.mkdir()
        self.root = self.base/'workspace'
        for name in ('catalog','reports','evidence'):
            (self.root/name).mkdir(parents=True)
        (self.root/'reports/forensic_manifest.json').write_text('{"stage":"preparation","images":[]}')
        self.fd = os.open(self.source,os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.close,self.fd)

    def entry(self,name):
        return {'path':name,'metadata':metadata((self.source/name).lstat())}

    def mount(self,source):
        info = metadata(source.lstat())
        return {'mount_id':'synthetic-1','source':'/dev/synthetic','filesystem':'iso9660',
                'options':'ro','root_identity':{key:info[key] for key in ('device','inode','mode')}}

    def run_scan(self,**kwargs):
        return run_assessment(self.root,self.source,'disc01',['synthetic-test'],
            mount_probe=kwargs.pop('mount_probe',self.mount),progress=lambda value:None,**kwargs)

    def test_single_forward_read_and_hash(self):
        payload=b'\0'*(HEADER_LIMIT+23)
        (self.source/'payload').write_bytes(payload)
        offsets=[]
        def read(fd,size):
            offsets.append(os.lseek(fd,0,os.SEEK_CUR))
            return os.read(fd,size)
        result=assess_file(self.fd,self.entry('payload'),reader=read)
        self.assertEqual(result['status'],READABLE)
        self.assertEqual(result['bytes_read'],len(payload))
        self.assertEqual(result['sha256'],hashlib.sha256(payload).hexdigest())
        self.assertEqual(offsets,sorted(set(offsets)))

    def test_empty_file_and_unknown_are_readable(self):
        for name,payload in [('empty',b''),('unknown',b'not a known file format'),('malformed.exe',b'MZ')]:
            (self.source/name).write_bytes(payload)
            result=assess_file(self.fd,self.entry(name))
            self.assertEqual(result['status'],READABLE)
            self.assertEqual(result['sha256'],hashlib.sha256(payload).hexdigest())
        self.assertIn('warning',result['classification'])

    def test_first_io_error_stops_with_remaining_files_retained(self):
        for name in ('a','b','c'):
            (self.source/name).write_bytes(b'data')
        calls=[]
        def assessor(fd,entry):
            calls.append(entry['path'])
            if entry['path']=='b':
                def fail(fd,size):
                    raise OSError(errno.EIO,'simulated read error')
                return assess_file(fd,entry,reader=fail)
            return assess_file(fd,entry)
        summary,output=self.run_scan(file_assessor=assessor)
        self.assertEqual(calls,['a','b'])
        self.assertEqual(summary['file_status_counts'],{READABLE:1,READ_ERROR:1,NOT_ASSESSED:1})
        self.assertEqual(summary['status'],'stopped')
        self.assertFalse(summary['coverage_complete'])
        entries=json.loads((output/'files.json').read_text())
        self.assertIsNone(entries[1]['sha256'])
        with closing(sqlite3.connect(self.root/'catalog/catalog.sqlite')) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM assessment_entries').fetchone()[0],3)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_file_changed_before_or_during_read(self):
        path=self.source/'a'
        path.write_bytes(b'original')
        old=self.entry('a')
        path.write_bytes(b'new')
        self.assertEqual(assess_file(self.fd,old)['status'],CHANGED)
        current=self.entry('a')
        changed=False
        def read(fd,size):
            nonlocal changed
            data=os.read(fd,size)
            if not changed:
                path.write_bytes(b'different length')
                changed=True
            return data
        result=assess_file(self.fd,current,reader=read)
        self.assertEqual(result['status'],CHANGED)
        self.assertIsNone(result['sha256'])

    def test_links_and_special_files_are_never_read(self):
        (self.source/'real').write_bytes(b'ok')
        (self.source/'link').symlink_to(self.source/'real')
        (self.source/'dirlink').symlink_to(self.source,target_is_directory=True)
        os.mkfifo(self.source/'fifo')
        summary,output=self.run_scan()
        self.assertEqual(summary['file_status_counts'],{READABLE:1})
        self.assertEqual(summary['skipped_entries'],3)
        self.assertEqual(len(json.loads((output/'files.json').read_text())),4)

    def test_symlink_replacement_and_parent_link_not_followed(self):
        (self.source/'target').write_bytes(b'payload')
        entry=self.entry('target')
        (self.source/'target').unlink()
        (self.source/'target').symlink_to('/etc/passwd')
        self.assertEqual(assess_file(self.fd,entry)['status'],READ_ERROR)
        self.assertEqual(assess_file(self.fd,entry)['bytes_read'],0)

    def test_mount_change_stops_before_content_reads(self):
        (self.source/'a').write_bytes(b'data')
        calls=0
        def probe(source):
            nonlocal calls
            calls+=1
            result=self.mount(source)
            if calls>1: result['mount_id']='changed'
            return result
        summary,output=self.run_scan(mount_probe=probe)
        self.assertEqual(summary['bytes_read'],0)
        self.assertEqual(summary['file_status_counts'],{NOT_ASSESSED:1})

    def test_enumeration_failure_retains_unknown_coverage(self):
        (self.source/'nested').mkdir()
        actual_scandir=os.scandir
        def scan(fd):
            if isinstance(fd,int) and os.fstat(fd).st_ino==(self.source/'nested').stat().st_ino:
                raise OSError(errno.EIO,'directory read error')
            return actual_scandir(fd)
        with patch('replay_preservation.assessment.os.scandir',side_effect=scan):
            summary,output=self.run_scan()
        self.assertEqual(summary['enumeration_errors'],1)
        self.assertFalse(summary['coverage_complete'])
        self.assertEqual(summary['bytes_read'],0)

    def test_rerun_preserves_previous_observations_and_no_acquisition_claim(self):
        (self.source/'Español.exe').write_bytes(b'MZ')
        first,first_output=self.run_scan()
        second,second_output=self.run_scan()
        self.assertNotEqual(first_output,second_output)
        self.assertTrue((first_output/'checksums.json').exists())
        with closing(sqlite3.connect(self.root/'catalog/catalog.sqlite')) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM assessment_runs').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM assessment_entries').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT image_hash FROM discs').fetchone()[0],None)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM compatibility_tests').fetchone()[0],0)
        self.assertEqual(json.loads((first_output/'files.json').read_text())[0]['path'],'Español.exe')

    def test_expected_mount_and_disc_id_validation(self):
        with self.assertRaises(ValueError): self.run_scan(expected_device='/dev/wrong')
        with self.assertRaises(ValueError): self.run_scan(expected_filesystem='ext4')
        with self.assertRaises(ValueError):
            run_assessment(self.root,self.source,'../bad',[],mount_probe=self.mount)

    def test_real_writable_or_non_mount_directory_rejected(self):
        with self.assertRaises(ValueError): mount_snapshot(self.source)


if __name__=='__main__':
    unittest.main()
