import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from replay_preservation.preflight import inspect


class PreflightTests(unittest.TestCase):
    def test_missing_device_blocks_without_open_or_install(self):
        def capture(argv):
            data={'filesystems':[{'target':'/source','source':'/dev/sr0','fstype':'iso9660','options':'ro'}]}
            return {'argv':argv,'returncode':0,'stdout':json.dumps(data),'stderr':''}
        with tempfile.TemporaryDirectory() as tmp, patch('replay_preservation.preflight.capture',side_effect=capture), \
             patch('replay_preservation.preflight.shutil.which',return_value=None), \
             patch('replay_preservation.preflight.Path.lstat',side_effect=FileNotFoundError('device hidden')):
            result=inspect(Path(tmp),Path('/source'),'/dev/sr0',
                'same disc; visually intact; no unusual noise or vibration (user reported)',
                'authorized after access restored')
        self.assertFalse(result['source_opened'])
        self.assertFalse(result['packages_installed'])
        self.assertIsNone(result['sector_recovery_percentage'])
        self.assertTrue(any('stop acquisition' in item for item in result['barriers']))

    def test_wrong_mount_is_not_validated(self):
        def capture(argv):
            data={'filesystems':[{'target':'/','source':'/dev/sda2','fstype':'ext4','options':'rw'}]}
            return {'argv':argv,'returncode':0,'stdout':json.dumps(data),'stderr':''}
        with tempfile.TemporaryDirectory() as tmp, patch('replay_preservation.preflight.capture',side_effect=capture):
            result=inspect(Path(tmp),Path('/source'),'/dev/nonexistent','unknown','not authorized')
        self.assertIsNone(result['observed_mount'])
        self.assertTrue(any('read-only mount not confirmed' in item for item in result['barriers']))

if __name__=='__main__': unittest.main()
