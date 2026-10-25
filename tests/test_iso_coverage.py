"""Synthetic ISO/map tests: sector coverage never implies historical integrity."""
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from replay_preservation.iso_coverage import coverage,Inspector,SECTOR,FULL,PARTIAL,OUTSIDE,UNKNOWN,directory_record,both32
from replay_preservation.mapfile import parse_mapfile,summarize


def dual32(buffer,offset,value):
    struct.pack_into('<I',buffer,offset,value);struct.pack_into('>I',buffer,offset+4,value)


def dual16(buffer,offset,value):
    struct.pack_into('<H',buffer,offset,value);struct.pack_into('>H',buffer,offset+2,value)


def record(name,lba,size,flags=0,sequence=1):
    length=33+len(name)+(0 if len(name)%2 else 1)
    data=bytearray(length);data[0]=length
    dual32(data,2,lba);dual32(data,10,size);data[25]=flags;dual16(data,28,sequence)
    data[32]=len(name);data[33:33+len(name)]=name
    return data


def fixture(path,joliet=False,multi=False,zero_seq=False):
    data=bytearray(32*SECTOR)
    vd=memoryview(data)[16*SECTOR:17*SECTOR]
    vd[0]=2 if joliet else 1;vd[1:6]=b'CD001';vd[6]=1
    vd[40:72]=(b'\x00T\x00E\x00S\x00T'+b'\0'*24) if joliet else b'TEST'+b' '*28
    if joliet:vd[88:91]=b'%/E'
    dual32(vd,80,40);dual16(vd,120,1);dual16(vd,124,1);dual16(vd,128,SECTOR)
    vd[156:190]=record(b'\0',19,SECTOR,2,0 if zero_seq else 1)
    data[17*SECTOR]=255;data[17*SECTOR+1:17*SECTOR+7]=b'CD001\x01'
    name='Español.dat'.encode('utf-16-be') if joliet else b'FILE.DAT;1'
    entries=record(b'\0',19,SECTOR,2,0 if zero_seq else 1)+record(b'\1',19,SECTOR,2,0 if zero_seq else 1)
    entries+=record(name,25,10,128 if multi else 0,0 if zero_seq else 1)
    if multi:entries+=record(name,30,10)
    data[19*SECTOR:19*SECTOR+len(entries)]=entries
    data[25*SECTOR:25*SECTOR+10]=b'abcdefghij'
    data[30*SECTOR:30*SECTOR+10]=b'klmnopqrst'
    path.write_bytes(data)


class CoverageTests(unittest.TestCase):
    def test_ddrescue130_sweeping_header_not_data_status(self):
        result=parse_mapfile('0x20 % 1\n0 0x10 +\n0x10 0x10 *\n')
        self.assertEqual(summarize(result)['read_bytes'],16)
        with self.assertRaises(ValueError):parse_mapfile('0 10 %')

    def test_eof_holes_and_unmapped_are_not_recovered(self):
        ranges=[{'offset':0,'length':100,'status':'+'}]
        result=coverage(ranges,0,120,80,[(20,10)])
        self.assertEqual(result['recovered_bytes'],70)
        self.assertEqual(result['status_bytes'],{'+':70,'sparse hole':10,'image EOF':20,'unmapped':20})

    def test_range_boundaries_and_zero_length(self):
        ranges=[{'offset':0,'length':10,'status':'+'},{'offset':10,'length':10,'status':'-'}]
        self.assertEqual(coverage(ranges,0,10,20)['missing_bytes'],0)
        self.assertEqual(coverage(ranges,9,2,20)['missing_bytes'],1)
        self.assertTrue(coverage(ranges,10,0,20)['empty'])
        with self.assertRaises(ValueError):coverage(ranges,-1,2,20)

    def test_valid_iso_and_covered_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.iso';fixture(p)
            i=Inspector(p,[{'offset':0,'length':p.stat().st_size,'status':'+'}],holes=[])
            desc=i.descriptors()[0];tree=i.annotate(i.tree(desc))
            f=tree['files'][0]
            self.assertEqual(f['path'],'FILE.DAT')
            self.assertEqual(f['coverage_status'],FULL)
            self.assertEqual(f['integrity_status'],'not independently established')
            self.assertIsNotNone(f['file_sha256'])

    def test_joliet_preserves_non_english_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.iso';fixture(p,joliet=True)
            i=Inspector(p,[{'offset':0,'length':32*SECTOR,'status':'+'}],holes=[])
            tree=i.tree(i.descriptors()[0])
            self.assertEqual(tree['files'][0]['path'],'Español.dat')

    def test_unrecovered_directory_metadata_never_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.iso';fixture(p)
            ranges=[{'offset':0,'length':19*SECTOR,'status':'+'},{'offset':19*SECTOR,'length':13*SECTOR,'status':'?'}]
            i=Inspector(p,ranges,holes=[])
            tree=i.tree(i.descriptors()[0])
            self.assertFalse(tree['metadata_complete'])
            self.assertEqual(tree['files'],[])
            self.assertEqual(len(tree['errors']),1)

    def test_multi_extent_file_and_partial_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.iso';fixture(p,multi=True)
            i=Inspector(p,[{'offset':0,'length':26*SECTOR,'status':'+'},
                           {'offset':26*SECTOR,'length':6*SECTOR,'status':'?'}],holes=[])
            f=i.annotate(i.tree(i.descriptors()[0]))['files'][0]
            self.assertEqual(len(f['extents']),2)
            self.assertEqual(f['coverage_status'],PARTIAL)
            self.assertEqual(f['recovered_bytes'],10)
            self.assertIsNone(f['file_sha256'])

    def test_partial_final_sector_is_not_full_sector_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.iso';fixture(p)
            i=Inspector(p,[{'offset':0,'length':25*SECTOR+10,'status':'+'},
                           {'offset':25*SECTOR+10,'length':7*SECTOR-10,'status':'?'}],holes=[])
            f=i.annotate(i.tree(i.descriptors()[0]))['files'][0]
            self.assertEqual(f['coverage_status'],PARTIAL)
            self.assertEqual(f['missing_bytes'],0)
            self.assertFalse(f['sector_coverage_complete'])

    def test_nonconformant_zero_volume_sequence_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.iso';fixture(p,zero_seq=True)
            i=Inspector(p,[{'offset':0,'length':32*SECTOR,'status':'+'}],holes=[])
            self.assertEqual(len(i.tree(i.descriptors()[0])['files']),1)
            self.assertTrue(any('nonconformant zero' in message for message in i.warnings))

    def test_inconsistent_endian_and_malformed_record_rejected(self):
        with self.assertRaises(ValueError):both32(b'\x01'+b'\0'*7,0)
        with self.assertRaises(ValueError):directory_record(b'\x22'+b'\0'*3,0,False)


if __name__=='__main__':unittest.main()

class PackagePriorityTests(unittest.TestCase):
    def test_union_and_priority_avoid_shared_extent_double_count(self):
        from replay_preservation.image_report import union_ranges,package_analysis
        self.assertEqual(union_ranges([{'offset':0,'length':10},{'offset':5,'length':10}]),[{'offset':0,'length':15}])
        def file(path,offset):
            return {'path':path,'extents':[{'offset':offset,'length':2048}],
                    'coverage_status':OUTSIDE,'missing_bytes':2048}
        files=[file('A/a.exe',2048),file('A/b.dat',2048),file('B/a.exe',4096)]
        ranges=[{'offset':0,'length':2048,'status':'+'},{'offset':2048,'length':2048,'status':'-'},
                {'offset':4096,'length':2048,'status':'?'}]
        packages=package_analysis(files,ranges,2048)
        self.assertEqual(packages[0]['package'],'B')
        self.assertEqual(packages[1]['missing_allocated_bytes'],2048)
        self.assertTrue(packages[1]['touches_map_bad_sector'])
