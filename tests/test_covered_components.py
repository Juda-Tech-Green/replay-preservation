import sys
import unittest
from pathlib import Path
from replay_preservation.covered_components import inspect_components
from replay_preservation.iso_coverage import FULL,OUTSIDE


class CoveredComponentTests(unittest.TestCase):
    def test_embedded_documentation_is_candidate_not_certified_game(self):
        files=[{'path':'Duke3d/BUILDHLP.EXE','coverage_status':FULL,'file_sha256':'fixture'}]
        results=inspect_components(files,lambda item:b'MZ Build for Duke Nukem 3D Help / Info')
        self.assertEqual(len(results),1)
        self.assertTrue(results[0]['candidate_single_file_component'])
        self.assertFalse(results[0]['certified_self_contained'])
        self.assertFalse(results[0]['game'])
        self.assertFalse(results[0]['playable'])

    def test_missing_dependency_prevents_complete_component_claim(self):
        files=[{'path':'VCOP2/VC2.EXE','coverage_status':FULL,'file_sha256':'fixture'},
               {'path':'VCOP2/CLASS.EXE','coverage_status':FULL,'file_sha256':'fixture'},
               {'path':'VCOP2/PPJ2DD.EXE','coverage_status':OUTSIDE,'file_sha256':None}]
        results=inspect_components(files,lambda item:b'MZ PPJ2dd.exe')
        launcher=next(item for item in results if item['path']=='VCOP2/VC2.EXE')
        self.assertFalse(launcher['observed_dependency_set_covered'])

    def test_uncovered_file_is_never_read_and_marker_required(self):
        files=[{'path':'QUAKE/CWSDPMI.EXE','coverage_status':OUTSIDE,'file_sha256':None}]
        def fail(item):raise AssertionError('Uncovered payload read')
        self.assertEqual(inspect_components(files,fail),[])
        files[0]['coverage_status']=FULL
        self.assertEqual(inspect_components(files,lambda item:b'unknown'),[])
