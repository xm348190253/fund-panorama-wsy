import unittest
from cloud_refresh_gate import already_updated, earlier_active


class RefreshGateTests(unittest.TestCase):
    def test_cross_midnight_completion_is_not_todays_data(self):
        receipt = {'status': 'success', 'verified': True, 'dataDate': '2026-10-29',
                   'completedAt': '2026-10-30T00:32:50+08:00'}
        self.assertFalse(already_updated(receipt, '2026-10-30'))

    def test_success_and_manual_force(self):
        receipt = {'status': 'success', 'verified': True, 'dataDate': '2026-10-30'}
        self.assertTrue(already_updated(receipt, '2026-10-30'))
        self.assertFalse(already_updated(receipt, '2026-10-30', True))

    def test_failed_incomplete_or_malformed_never_skips(self):
        for value in (None, [], {}, {'status': 'success', 'verified': True},
                      {'status': 'failed', 'verified': True, 'dataDate': '2026-10-30'},
                      {'status': 'success', 'verified': False, 'dataDate': '2026-10-30'}):
            self.assertFalse(already_updated(value, '2026-10-30'))

    def test_simultaneous_preflights_only_yield_to_earlier_runs(self):
        runs = [{'id': i, 'status': status} for i, status in
                [(1, 'completed'), (2, 'in_progress'), (3, 'queued'), (4, 'in_progress')]]
        self.assertEqual(earlier_active(runs, 2), [])
        self.assertEqual([r['id'] for r in earlier_active(runs, 3)], [2])


if __name__ == '__main__':
    unittest.main()
