#!/usr/bin/env python3
"""Targeted metric/provenance checks for the full-market backfill."""
import datetime as dt
import json
import unittest
from backfill_market import normalize, decode, reusable_checkpoint, SCHEMA, TZ


def stamp(date):
    return int(dt.datetime.fromisoformat(date).replace(tzinfo=TZ).timestamp() * 1000)


def raw_for(points, **more):
    return {'fS_code': '000001', 'fS_name': '测试基金', '_sourceCode': '000001',
            'Data_netWorthTrend': [{'x': stamp(date), 'y': nav, 'equityReturn': growth}
                                  for date, nav, growth in points], **more}


def result(raw, **product):
    return normalize({'code': '000001', 'name': '测试基金', 'type': '股票型', **product}, raw,
                     {'retrievedAt': '2026-10-29T12:00:00+08:00'}, '2026-10-29')['perf']


class MetricsTest(unittest.TestCase):
    def test_distribution_is_not_a_drawdown(self):
        raw = raw_for([('2025-12-31', 1, 0), ('2026-01-02', .505, 1), ('2026-01-05', .49995, -1)])
        p = result(raw)
        self.assertAlmostEqual(p['ytd'], -.01)
        self.assertEqual(p['ytdMdd'], -1)
        self.assertEqual(p['ytdStart'], '2025-12-31')

    def test_weekly_zero_placeholders_use_cumulative_source(self):
        points = [('2026-09-24', .9999, 0), ('2026-10-09', .9996, 0), ('2026-10-23', .9937, 0)]
        raw = raw_for(points, Data_grandTotal=[{'name': '测试基金', 'data': [[stamp(points[0][0]), 0], [stamp(points[1][0]), -.03], [stamp(points[2][0]), -.62]]}])
        p = result(raw, inception='2026-09-24')
        self.assertIsNone(p['d1'])
        self.assertIsNone(p['w1'])
        self.assertAlmostEqual(p['ytd'], -.62)
        self.assertAlmostEqual(p['ytdMdd'], -.62)

    def test_partial_history_cannot_be_called_year_to_date(self):
        p = result(raw_for([('2026-07-01', 1, 0), ('2026-10-28', 1.1, 10)]), inception='2015-01-01')
        self.assertIsNone(p['ytdMdd'])
        self.assertEqual(p['fieldStatus']['ytd']['reason'], 'insufficient_year_history')

    def test_new_fund_has_no_one_year_return(self):
        p = result(raw_for([('2026-07-01', 1, 0), ('2026-10-28', 1.1, 10)], syl_1n=10), inception='2026-07-01')
        self.assertIsNone(p['y1'])
        self.assertEqual(p['ytd'], 10)
        self.assertEqual(p['ytdStart'], '2026-07-01')

    def test_unknown_inception_does_not_prove_year_history(self):
        p = result(raw_for([('2026-07-01', 1, 0), ('2026-10-28', 1.1, 10)], syl_1n=15))
        self.assertIsNone(p['ytd'])
        self.assertIsNone(p['ytdMdd'])
        self.assertEqual(p['y1'], 15)
        self.assertEqual(p['fieldStatus']['ytd']['reason'], 'insufficient_year_history')

    def test_benchmark_is_never_used_as_fund_history(self):
        p = result(raw_for([], Data_grandTotal=[{'name': '测试基金', 'data': []},
                       {'name': '沪深300', 'data': [[stamp('2025-12-31'), 0], [stamp('2026-10-28'), 25]]}]))
        self.assertIsNone(p['mdd'])
        self.assertIsNone(p['ytd'])

    def test_checkpoint_date_is_part_of_reuse_key(self):
        record = {'schemaVersion': SCHEMA, 'calculationAsOf': '2026-10-29', 'status': 'ok'}
        self.assertTrue(reusable_checkpoint(record, '2026-10-29'))
        self.assertFalse(reusable_checkpoint(record, '2027-01-03'))
        self.assertFalse(reusable_checkpoint({**record, 'schemaVersion': SCHEMA - 1}, '2026-10-29'))

    def test_old_series_has_no_current_year_metric(self):
        p = result(raw_for([('2024-01-01', 1, 0), ('2025-12-31', .9, -10)]))
        self.assertIsNone(p['ytd'])
        self.assertEqual(p['fieldStatus']['ytd']['reason'], 'stopped_before_year')
        self.assertEqual(p['fieldStatus']['dwjz']['status'], 'stale')

    def test_money_metrics_are_separate(self):
        p = result({'ishb': True, 'Data_millionCopiesIncome': [[stamp('2026-10-28'), .2301]],
                    'Data_sevenDaysYearIncome': [[stamp('2026-10-28'), .84]]}, type='货币型-普通货币')
        self.assertEqual(p['wfsy'], .2301)
        self.assertEqual(p['qrnh'], .84)
        self.assertIsNone(p['mdd'])
        self.assertEqual(p['fieldStatus']['ytdMdd']['status'], 'not_applicable')

    def test_missing_scale_is_not_zero(self):
        self.assertIsNone(result(raw_for([]))['scale'])
        self.assertEqual(result(raw_for([], Data_fluctuationScale={'categories': ['2026-09-30'], 'series': [{'y': 0}]}))['scale'], 0)

    def test_alias_needs_returned_canonical_identity(self):
        source = b'var fS_code="000001";var fS_name="test";var Data_netWorthTrend=[];'
        value = decode(source, '000002', 'test(后端)', {'000001': 'test'})
        self.assertEqual(value['_sourceCode'], '000001')
        with self.assertRaises(ValueError):
            decode(source, '000002', 'different(后端)', {'000001': 'test'})
        with self.assertRaises(ValueError):
            decode(b'<title>page not found</title>', '000002', 'test(后端)', {'000001': 'test'})

    def test_truncated_response_is_rejected(self):
        with self.assertRaises(ValueError):
            decode(b'var fS_code="000001";var Data_netWorthTrend=[', '000001')


if __name__ == '__main__':
    unittest.main()
