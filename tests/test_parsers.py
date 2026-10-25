from contextlib import closing
import io
import sqlite3
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from replay_preservation.signatures import classify
from replay_preservation.mapfile import parse_mapfile, summarize, affected_extents
from replay_preservation.archives import safe_member, inspect_zip, extract_zip
from replay_preservation.catalog import initialize


class Signatures(unittest.TestCase):
    def test_ne_target_is_not_assumed_windows(self):
        data = bytearray(256)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 64)
        data[64:66] = b'NE'
        data[64+0x36] = 1
        self.assertEqual(classify(data)['platform'], 'OS/2')
        data[64+0x36] = 2
        self.assertEqual(classify(data)['platform'], 'Windows 16-bit')

    def test_pe_not_automatically_windows_or_win95(self):
        data = bytearray(256)
        data[:2] = b'MZ'
        struct.pack_into('<I', data, 0x3c, 64)
        data[64:68] = b'PE\0\0'
        self.assertEqual(classify(data)['platform'], 'PE target undetermined')
        struct.pack_into('<H', data, 84, 100)
        struct.pack_into('<H', data, 88, 0x10b)
        struct.pack_into('<H', data, 156, 3)
        self.assertEqual(classify(data)['platform'], 'Windows PE (version undetermined)')

    def test_truncation_and_far_offset(self):
        self.assertIn('warning', classify(b'MZ'))
        data=bytearray(64)
        data[:2]=b'MZ'
        struct.pack_into('<I', data, 60, 2**32-1)
        self.assertEqual(classify(data)['format'], 'MZ')
        self.assertIn('warning', classify(data))

    def test_extension_never_proves_com(self):
        self.assertEqual(classify(b'not executable', 'game.com')['confidence'], 'extension_only')
        self.assertEqual(classify(b'PK\x03\x04', 'game.exe')['format'], 'ZIP')
        self.assertEqual(classify(b'not executable', 'game.exe')['format'], 'unknown')


class Maps(unittest.TestCase):
    def test_totals_and_overlap_boundaries(self):
        ranges=parse_mapfile('# map\n0x100 + 1\n0 0x800 +\n0x800 0x800 -\n0x1000 0x800 ?\n')
        result=summarize(ranges)
        self.assertEqual(result['read_bytes'], 2048)
        self.assertEqual(result['unrecovered_bytes'], 4096)
        self.assertEqual(affected_extents(ranges, 0, 2048), [])
        self.assertEqual(affected_extents(ranges, 2000, 100)[0]['overlap_length'], 52)
        self.assertEqual(result['completion'], 'unknown_without_expected_source_size')

    def test_reject_invalid_maps(self):
        for text in ['', '0 0 +', '0 20 +\n10 20 -', '0 20 X', '-1 20 +', '0 + 1\n0 + 1']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_mapfile(text)

    def test_unmapped_gaps(self):
        result=summarize(parse_mapfile('10 10 +\n30 10 +'))
        self.assertEqual(result['unmapped_ranges'], [{'offset':0,'length':10},{'offset':20,'length':10}])


class Archives(unittest.TestCase):
    def make_zip(self, root, members):
        path=root/'source.zip'
        with zipfile.ZipFile(path,'w') as z:
            for name,value in members:
                z.writestr(name,value)
        return path

    def test_unsafe_names(self):
        for name in ['../escape','/absolute','C:escape','C:/escape','a\\..\\b','//server/a','.', '']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_member(name)

    def test_links_collisions_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            info=zipfile.ZipInfo('link')
            info.create_system=3
            info.external_attr=0o120777 << 16
            path=self.make_zip(root,[(info,'../../outside')])
            with self.assertRaises(ValueError): inspect_zip(path)
            path=self.make_zip(root,[('A','one'),('a','two')])
            with self.assertRaises(ValueError): inspect_zip(path)
            path=self.make_zip(root,[('a','12345')])
            with self.assertRaises(ValueError): inspect_zip(path,max_bytes=4)
            with self.assertRaises(ValueError): inspect_zip(path,max_files=0)

    def test_extract_no_overwrite_or_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=self.make_zip(root,[('game/run.exe',b'MZ')])
            output=root/'output'
            records=extract_zip(source,output)
            self.assertEqual((output/'game/run.exe').read_bytes(), b'MZ')
            self.assertEqual((output/'game/run.exe').stat().st_mode & 0o111,0)
            self.assertEqual(records[0]['size'],2)
            with self.assertRaises(FileExistsError): extract_zip(source,output)

    def test_crc_failure_removes_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=self.make_zip(root,[('game.dat',b'UNIQUE_PAYLOAD')])
            source.write_bytes(source.read_bytes().replace(b'UNIQUE_PAYLOAD',b'BROKEN_PAYLOAD'))
            with self.assertRaises(zipfile.BadZipFile): extract_zip(source,root/'output')
            self.assertFalse((root/'output').exists())
            self.assertTrue(source.exists())

    def test_path_conflict_cleans_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=self.make_zip(root,[('a','file'),('a/b','conflict')])
            with self.assertRaises(OSError): extract_zip(source,root/'output')
            self.assertFalse((root/'output').exists())


class Catalog(unittest.TestCase):
    def test_empty_idempotent_schema_and_traceability(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'catalog.sqlite'
            initialize(path)
            initialize(path)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('PRAGMA foreign_keys=ON')
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                for table in ['discs','files','software','recovery_events','compatibility_tests','reconstructions','file_extents']:
                    self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0],0)
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute("INSERT INTO software(disc_id,title) VALUES('nonexistent','Unknown')")

if __name__ == '__main__':
    unittest.main()
