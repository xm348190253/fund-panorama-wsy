import datetime as dt
import unittest
from run_update_deadline import remaining_seconds


class UpdateDeadlineTests(unittest.TestCase):
    def at(self, value):
        return dt.datetime.fromisoformat(value)

    def test_early_collection_reserves_fifty_minutes(self):
        self.assertEqual(remaining_seconds(self.at('2026-11-18T06:00:00+08:00'), 3000), 6000)

    def test_collection_stops_at_seven_forty(self):
        self.assertEqual(remaining_seconds(self.at('2026-11-18T07:40:00+08:00'), 3000), 0)

    def test_build_requires_forty_minutes_for_publication(self):
        self.assertEqual(remaining_seconds(self.at('2026-11-18T07:50:00+08:00'), 2400), 0)

    def test_publication_budget_ends_at_eight_thirty(self):
        self.assertEqual(remaining_seconds(self.at('2026-11-18T08:00:00+08:00')), 1800)
        self.assertEqual(remaining_seconds(self.at('2026-11-18T08:30:00+08:00')), 0)

    def test_noon_and_other_days_have_no_special_deadline(self):
        for value in ('2026-11-18T12:00:00+08:00', '2026-11-17T06:00:00+08:00', '2026-11-19T06:00:00+08:00'):
            self.assertIsNone(remaining_seconds(self.at(value), 3000))


if __name__ == '__main__':
    unittest.main()
