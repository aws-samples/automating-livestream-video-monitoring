from unittest import TestCase
from ..testutils import read_file
from common.manifest_parser import get_last_segment_and_start_timestamp, is_master_manifest
import os
from datetime import datetime

TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


class TestManifestParser(TestCase):
    def test_manifest_parser(self):
        manifest = read_file(os.path.join(TEST_DATA_DIR, 'segment_right_after_program_time.m3u8'))
        last_segment, start_time, duration_sec = get_last_segment_and_start_timestamp(manifest)
        self.assertEqual(last_segment, 'test_1_00006.ts')
        self.assertEqual(start_time, datetime(2020, 1, 21, hour=16, minute=35, second=15, microsecond=430000))
        self.assertEqual(duration_sec, 6.00600)

        manifest = read_file(os.path.join(TEST_DATA_DIR, 'test_program_time.m3u8'))
        last_segment, start_time, duration_sec = get_last_segment_and_start_timestamp(manifest)
        self.assertEqual(last_segment, 'test_1_00019.ts')
        self.assertEqual(start_time, datetime(2020, 1, 21, hour=16, minute=58, second=41, microsecond=976000))
        self.assertEqual(duration_sec, 6.00600)

        manifest = read_file(os.path.join(TEST_DATA_DIR, 'test_no_program_time.m3u8'))
        last_segment, start_time, duration_sec = get_last_segment_and_start_timestamp(manifest)
        self.assertEqual(last_segment, 'test_1_00006.ts')
        self.assertIsNone(start_time)
        self.assertEqual(duration_sec, 12.01200)

    def test_is_master_manifest(self):
        manifest = read_file(os.path.join(TEST_DATA_DIR, 'master_manifest.m3u'))
        self.assertEqual(True, is_master_manifest(manifest), 'The manifest should be categorized as master.')

        manifest = read_file(os.path.join(TEST_DATA_DIR, 'test_no_program_time.m3u8'))
        self.assertEqual(False, is_master_manifest(manifest), 'The manifest should be categorized as child.')
