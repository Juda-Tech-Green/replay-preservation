import struct
import sys
import unittest
from pathlib import Path
from replay_preservation.doom_static import mz_header,wad_directory


class DoomStaticTests(unittest.TestCase):
    def test_valid_mz_with_overlay(self):
        data=bytearray(512+16)
        struct.pack_into('<14H',data,0,0x5a4d,0,1,0,4,0,65535,0,0,0,0,0,28,0)
        result=mz_header(data)
        self.assertEqual(result['overlay_bytes'],16)
        self.assertEqual(result['declared_real_mode_bytes'],512)

    def test_bad_mz_and_relocation_bounds(self):
        with self.assertRaises(ValueError):mz_header(b'MZ')
        data=bytearray(512)
        struct.pack_into('<14H',data,0,0x5a4d,0,1,10,2,0,65535,0,0,0,0,0,28,0)
        with self.assertRaises(ValueError):mz_header(data)

    def test_valid_wad_and_zero_marker(self):
        data=b'IWAD'+struct.pack('<ii',2,16)+b'DATA'+struct.pack('<ii8s',12,4,b'TEST')+struct.pack('<ii8s',0,0,b'F_START')
        result=wad_directory(data)
        self.assertEqual(result['lump_count'],2)
        self.assertTrue(result['directory_ends_at_eof'])

    def test_invalid_counts_offsets_and_payload(self):
        for data in [b'IWAD',b'IWAD'+struct.pack('<ii',-1,12),b'PWAD'+struct.pack('<ii',2,12),
                     b'IWAD'+struct.pack('<ii',1,12)+struct.pack('<ii8s',100,1,b'BAD')]:
            with self.subTest(data=data),self.assertRaises(ValueError):wad_directory(data)

    def test_map_requires_standard_sequence(self):
        data=b'IWAD'+struct.pack('<ii',1,12)+struct.pack('<ii8s',0,0,b'MAP01')
        with self.assertRaises(ValueError):wad_directory(data)
