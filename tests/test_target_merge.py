import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from replay_preservation.target_merge import merge_ranges,apply_target,copy_known_ranges
from replay_preservation.target_strategy import validate_chunk


class TargetMergeTests(unittest.TestCase):
    def test_overlay_only_target_preserves_failures_and_domain(self):
        base=[{'offset':0,'length':2048,'status':'+'},{'offset':2048,'length':2048,'status':'-'},
              {'offset':4096,'length':8192,'status':'?'}]
        merged=merge_ranges(base,[{'absolute_offset':6144,'length':2048,'chunk_offset':0}])
        self.assertEqual(merged,[base[0],base[1],{'offset':4096,'length':2048,'status':'?'},
             {'offset':6144,'length':2048,'status':'+'},{'offset':8192,'length':4096,'status':'?'}])
        with self.assertRaises(ValueError):merge_ranges(base,[{'absolute_offset':12288,'length':2048}])

    def test_compact_chunk_correct_absolute_offset_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/'base';base.write_bytes(b'A'*4096)
            chunk=root/'chunk';chunk.write_bytes(b'B'*2048)
            mp=root/'target.map';mp.write_text('0 + 1\n0 8192 ?\n8192 2048 +\n10240 2048 ?\n')
            validation=validate_chunk({'offset':8192,'length':2048},chunk,mp)
            ranges=[{'offset':0,'length':4096,'status':'+'},{'offset':4096,'length':8192,'status':'?'}]
            merged=apply_target(base,ranges,chunk,validation,root/'derived')
            expected=b'A'*4096+b'\0'*4096+b'B'*2048+b'\0'*2048
            self.assertEqual((root/'derived').read_bytes(),expected)
            self.assertEqual(base.read_bytes(),b'A'*4096)
            self.assertEqual(chunk.read_bytes(),b'B'*2048)
            copy_known_ranges(root/'derived',merged,root/'working',12288)
            self.assertEqual((root/'working').read_bytes(),expected)
            with self.assertRaises(FileExistsError):apply_target(base,ranges,chunk,validation,root/'derived')

    def test_conflicting_plus_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/'base';base.write_bytes(b'A'*4096)
            chunk=root/'chunk';chunk.write_bytes(b'B'*2048)
            validation={'complete':True,'missing_bytes':0,'chunk_sha256':hashlib.sha256(chunk.read_bytes()).hexdigest(),
                        'usable_ranges':[{'absolute_offset':0,'chunk_offset':0,'length':2048}]}
            with self.assertRaises(ValueError):apply_target(base,[{'offset':0,'length':4096,'status':'+'}],chunk,validation,root/'derived')
            self.assertEqual(base.read_bytes(),b'A'*4096)
