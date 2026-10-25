import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from replay_preservation.target_strategy import command_for,file_targets,validate_chunk,OPTIONS


class TargetStrategyTests(unittest.TestCase):
    def test_exact_doom2_absolute_input_and_compact_output(self):
        command=command_for(212224*2048,336*2048,Path('/tmp/not-executed'))
        self.assertIn('--input-position=434634752',command)
        self.assertIn('--output-position=0',command)
        self.assertIn('--size=688128',command)
        self.assertIn('--ask',command)
        self.assertIn('--max-read-errors=0',command)
        for forbidden in ['--force','--try-again','--retrim','--idirect','--reverse']:
            self.assertNotIn(forbidden,command)
        with self.assertRaises(ValueError):command_for(1,2048,Path('/tmp/a'))

    def test_split_known_failure_from_untried_span(self):
        item={'path':'a.exe','extents':[{'offset':2048,'length':4096}]}
        ranges=[{'offset':0,'length':2048,'status':'+'},{'offset':2048,'length':2048,'status':'*'},
                {'offset':4096,'length':2048,'status':'?'}]
        spans=file_targets(item,ranges,2048)
        self.assertEqual([span['status'] for span in spans],['*','?'])
        self.assertEqual([span['sector_count'] for span in spans],[1,1])

    @unittest.skipUnless(shutil.which('ddrescue'),'GNU ddrescue unavailable')
    def test_real_ddrescue_bounds_on_synthetic_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'synthetic-source'
            payload=b'A'*2048+b'B'*2048+b'C'*2048+b'D'*2048
            source.write_bytes(payload)
            command=command_for(2048,4096,root)
            command.remove('--ask') # Only synthetic regular-file tests may bypass the interactive gate.
            command[-3]=str(source)
            completed=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertEqual((root/'target.chunk').read_bytes(),b'B'*2048+b'C'*2048)
            self.assertEqual(source.read_bytes(),payload)
            operations=[line.split() for line in (root/'reads.log').read_text().splitlines()
                        if line and not line.startswith('#')]
            self.assertTrue(operations)
            self.assertTrue(all(2048<=int(row[0],0) and int(row[0],0)+int(row[1])<=6144 for row in operations))
            result=validate_chunk({'offset':2048,'length':4096},root/'target.chunk',root/'target.map')
            self.assertTrue(result['complete'])
            self.assertEqual(result['usable_ranges'],[{'absolute_offset':2048,'chunk_offset':0,'length':4096}])

    @unittest.skipUnless(shutil.which('ddrescue'),'GNU ddrescue unavailable')
    def test_first_simulated_read_error_stops_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'synthetic-source'
            source.write_bytes(b'A'*8192)
            test_map=root/'simulated-bad.map'
            test_map.write_text('0 ? 1\n0 2048 +\n2048 2048 -\n4096 4096 +\n')
            command=command_for(2048,4096,root);command.remove('--ask');command[-3]=str(source)
            command.insert(1,f'--test-mode={test_map}')
            completed=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertEqual(completed.returncode,1)
            self.assertEqual((root/'target.chunk').stat().st_size,0)
            log=(root/'reads.log').read_text()
            self.assertTrue(log)
            operations=[line.split() for line in log.splitlines() if line and not line.startswith('#')]
            self.assertEqual(len(operations),1)
            result=validate_chunk({'offset':2048,'length':4096},root/'target.chunk',root/'target.map')
            self.assertFalse(result['complete'])
            self.assertEqual(result['covered_bytes'],0)

    def test_reject_false_plus_and_out_of_domain_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);chunk=root/'chunk';chunk.write_bytes(b'A'*2048)
            mapfile=root/'map';mapfile.write_text('0 ? 1\n0 2048 +\n')
            with self.assertRaises(ValueError):validate_chunk({'offset':2048,'length':2048},chunk,mapfile)
            mapfile.write_text('0 ? 1\n2048 4096 +\n')
            with self.assertRaises(ValueError):validate_chunk({'offset':2048,'length':4096},chunk,mapfile)

if __name__=='__main__':unittest.main()
