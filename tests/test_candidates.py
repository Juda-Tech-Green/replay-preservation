from contextlib import closing
"""Candidate identification must not claim playability or corrupt untested files."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from replay_preservation.candidates import identify,catalog_candidates
from replay_preservation.catalog import initialize
from replay_preservation.assessment import ASSESSMENT_SCHEMA


def entry(path,status='not assessed',classification=None):
    return {'path':path,'kind':'file','status':status,'classification':classification}


class CandidateTests(unittest.TestCase):
    def test_known_directories_and_support_not_independent_games(self):
        rows=[entry('DOOM2/DOOM2.EXE','readable, historical integrity unverified',{'format':'MZ','platform':'DOS or extended executable'}),
              entry('DOOM2/DOOM2.WAD'),entry('DOOM2/SETUP.EXE'),
              entry('Doom/DOOM.EXE'),entry('Doom/DROOLING.ZIP','read error'),
              entry('Duke3d/DUKE3D.EXE'),entry('HERETIC/HERETIC.EXE'),
              entry('QUAKE/QUAKE.EXE'),entry('MK4/Install.exe'),entry('VCOP2/VC2.EXE')]
        candidates=identify(rows)
        self.assertEqual(len(candidates),7)
        bydir={item['original_directory']:item for item in candidates}
        self.assertIsNone(bydir['MK4']['executable_path'])
        self.assertIn('MK4/Install.exe',bydir['MK4']['support_executables'])
        self.assertEqual(bydir['Duke3d']['recovery_status'],'not fully assessed')
        self.assertIn('read error observed',bydir['Doom']['recovery_status'])
        self.assertEqual(bydir['DOOM2']['launcher_candidates'],['DOOM2/DOOM2.EXE'])
        self.assertTrue(all(not item['playable'] and item['compatibility_status']=='untested' for item in candidates))

    def test_emulator_bundles_grouped_by_directory(self):
        rows=[entry('JUEGOS/MICKEY/SNES9X.EXE'),entry('JUEGOS/MICKEY/GO.BAT'),
              entry('JUEGOS/MICKEY/game.smc'),entry('JUEGOS/MICKEY/snesnaps/save.srm'),
              entry('JUEGOS/GOEMON/SNES9X.EXE'),entry('JUEGOS/GOEMON/Goemon4.1')]
        candidates=identify(rows)
        self.assertEqual(len(candidates),2)
        self.assertTrue(all('SNES software candidate' in item['platform'] for item in candidates))
        self.assertEqual(candidates[0]['resource_paths'],[])

    def test_arbitrary_binary_not_a_game_and_unsafe_path_rejected(self):
        self.assertEqual(identify([entry('DATA/readme.txt')]),[])
        with self.assertRaises(ValueError): identify([entry('../unsafe.exe')])

    def test_catalog_provenance_and_hash_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'catalog').mkdir()
            assessment=root/'evidence/assessments/disc01/run1'
            assessment.mkdir(parents=True)
            (root/'reports/disc01').mkdir(parents=True)
            initialize(root/'catalog/catalog.sqlite')
            with closing(sqlite3.connect(root/'catalog/catalog.sqlite')) as db, db:
                db.executescript(ASSESSMENT_SCHEMA)
                db.execute("INSERT INTO discs(disc_id,source_description) VALUES('disc01','fixture')")
                db.execute("INSERT INTO assessment_runs VALUES('run1','disc01','now',NULL,'fixture','{}','[]','stopped',NULL,'fixture')")
            content=json.dumps([entry('DOOM2/DOOM2.EXE')]).encode()
            (assessment/'files.json').write_bytes(content)
            (assessment/'checksums.json').write_text(json.dumps({'files.json':hashlib.sha256(content).hexdigest()}))
            (assessment/'summary.json').write_text('{"disc_id":"disc01","run_id":"run1"}')
            output,result=catalog_candidates(root,'disc01',assessment)
            self.assertEqual(result['candidate_count'],1)
            self.assertTrue((output/'software_inventory.csv').exists())
            with closing(sqlite3.connect(root/'catalog/catalog.sqlite')) as db, db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM software_candidate_observations').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM compatibility_tests').fetchone()[0],0)
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            (assessment/'files.json').write_text('[]')
            with self.assertRaises(ValueError): catalog_candidates(root,'disc01',assessment)


if __name__=='__main__': unittest.main()
