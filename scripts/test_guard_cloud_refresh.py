import unittest
from guard_cloud_refresh import check


class CoverageGuardTest(unittest.TestCase):
    def setUp(self):
        self.baseline = {'dataDate': '2026-10-28', 'directoryCount': 28000,
                         'available': {'scale': 27000, 'manager': 27800}}
        self.new = {'dataDate': '2026-10-29', 'directoryCount': 28010,
                    'available': {'scale': 27010, 'manager': 27810}}

    def test_normal_increment(self):
        check(self.baseline, self.new, '2026-10-29')

    def test_incomplete_but_well_formed_directory_stops(self):
        self.new['directoryCount'] = 10000
        with self.assertRaisesRegex(ValueError, 'Directory count'):
            check(self.baseline, self.new, '2026-10-29')

    def test_html_block_pages_cannot_erase_fields(self):
        self.new['available']['scale'] = 1000
        with self.assertRaisesRegex(ValueError, 'scale'):
            check(self.baseline, self.new, '2026-10-29')

    def test_stale_snapshot_cannot_be_relabelled_today(self):
        with self.assertRaisesRegex(ValueError, 'date'):
            check(self.baseline, self.new, '2026-10-30')


if __name__ == '__main__':
    unittest.main()
