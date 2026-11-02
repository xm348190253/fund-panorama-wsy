import unittest
import datetime as dt
from cloud_refresh_gate import already_updated, earlier_active, choose_update


class RefreshGateTests(unittest.TestCase):
    def receipt(self, collected='2026-11-02T09:06:00+08:00'):
        return {'status': 'success', 'verified': True, 'dataDate': '2026-11-02',
                'indexQuotesCollectedAt': collected}

    def choose(self, clock, receipt=None, **kwargs):
        return choose_update(self.receipt() if receipt is None else receipt,
                             dt.datetime.fromisoformat('2026-11-02T' + clock + '+08:00'), **kwargs)[:2]

    def test_each_intraday_slot_runs_despite_daily_fund_success(self):
        for clock, previous in [('10:00:00', '09:06:00'), ('12:00:00', '10:00:30'), ('14:00:00', '12:00:30')]:
            with self.subTest(clock=clock):
                self.assertEqual(self.choose(clock, self.receipt('2026-11-02T' + previous + '+08:00')), (True, True))

    def test_duplicate_triggers_and_evening_retries_skip_completed_slot(self):
        for clock, collected in [('10:00:00', '10:00:00'), ('11:59:59', '10:01:00'),
                                 ('13:59:59', '12:01:00'), ('23:59:59', '14:01:00')]:
            self.assertEqual(self.choose(clock, self.receipt('2026-11-02T' + collected + '+08:00')), (False, True))

    def test_publication_after_boundary_does_not_hide_old_collection(self):
        receipt = dict(self.receipt('2026-11-02T11:58:00+08:00'), completedAt='2026-11-02T12:05:00+08:00')
        self.assertEqual(self.choose('12:07:00', receipt), (True, True))

    def test_delayed_trigger_catches_up_latest_slot_only(self):
        self.assertEqual(self.choose('14:43:00'), (True, True))
        self.assertEqual(self.choose('16:17:00', self.receipt('2026-11-02T14:43:10+08:00')), (False, True))

    def test_daily_funds_still_refresh_when_yesterday_finished_today(self):
        receipt = dict(self.receipt(), dataDate='2026-11-01')
        for clock in ('08:00:00', '10:00:00', '14:00:00'):
            self.assertEqual(self.choose(clock, receipt), (True, False))

    def test_automatic_does_not_start_before_eight(self):
        self.assertEqual(self.choose('07:59:59', {}), (False, False))
        self.assertEqual(self.choose('08:00:00', {}), (True, False))
        self.assertEqual(self.choose('09:59:59'), (False, True))

    def test_manual_force_preserves_selected_mode(self):
        self.assertEqual(self.choose('07:00:00', force=True), (True, False))
        self.assertEqual(self.choose('07:00:00', force=True, requested_quotes_only=True), (True, True))

    def test_missing_invalid_future_timestamp_never_suppresses_slot(self):
        for stamp in (None, '', 'bad', '2026-11-02T14:01:00', '2026-11-03T14:01:00+08:00'):
            self.assertEqual(self.choose('14:17:00', self.receipt(stamp)), (True, True))

    def test_utc_timestamp_and_execution_clock_use_beijing(self):
        result = choose_update(self.receipt('2026-11-02T02:01:00+00:00'),
                               dt.datetime.fromisoformat('2026-11-02T02:07:00+00:00'))
        self.assertEqual(result[:2], (False, True))

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
