#!/usr/bin/env python3
"""Regression checks for market-source parsing and current-year labels."""
import datetime as dt
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from refresh_directory import parse_directory
from refresh_market_base import check_year_boundary, company_fallback, fetch
from update_market_total import latest_report


class MarketSourceTests(unittest.TestCase):
    def test_same_day_refetch_preserves_each_response_under_its_own_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            day = cache / 'base-refresh-2026-10-29'
            day.mkdir()
            records = []
            key = 'rank-pass0-p1-n10-asc'
            url = 'https://fund.eastmoney.com/data/rankhandler.aspx?test'
            with mock.patch('refresh_market_base.CACHE', cache), mock.patch('refresh_market_base.SOURCES', records), \
                    mock.patch('refresh_market_base.download', side_effect=[(b'old', 200, ''), (b'new', 200, '')]):
                self.assertEqual(fetch(url, key, lambda text: text, day), 'old')
                (day / (key + '.txt')).unlink()  # A new same-day collection, retaining prior evidence.
                self.assertEqual(fetch(url, key, lambda text: text, day), 'new')
                self.assertEqual(fetch(url, key, lambda text: text, day), 'new')
            self.assertNotEqual(records[0]['key'], records[1]['key'])
            self.assertEqual(records[1]['key'], records[2]['key'])
            self.assertEqual(records[0]['originalKey'], records[1]['originalKey'])
            for source, raw in zip(records, (b'old', b'new', b'new')):
                self.assertEqual((cache / (source['key'] + '.txt')).read_bytes(), raw)
                self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest())

    def test_directory_accepts_only_complete_unique_codes(self):
        row = '["000001","HX","华夏成长","混合型","HUAXIA"]'
        self.assertEqual(parse_directory(('var r = [' + row + '];').encode())[0][0], '000001')
        for invalid in ['var r = [' + row + ']', 'var r = [];', 'var r = [' + row + ',' + row + '];']:
            with self.assertRaises(ValueError):
                parse_directory(invalid.encode())

    def test_previous_year_ytd_is_not_current_year(self):
        values = {'000001': {'jzrq': '2025-07-31', 'ytd': .91},
                  '000002': {'jzrq': '', 'ytd': -.21},
                  '000003': {'jzrq': '2026-10-28', 'ytd': 0}}
        report = check_year_boundary(values, '2026-10-29')
        self.assertIsNone(values['000001']['ytd'])
        self.assertIsNone(values['000002']['ytd'])
        self.assertEqual(values['000003']['ytd'], 0)
        self.assertEqual(len(report['excludedYtd']), 2)
        self.assertEqual(values['000001']['fieldStatus']['ytd']['reason'], 'stopped_before_year')

    def test_delivery_without_raw_caches_can_refresh(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch('refresh_market_base.CACHE', Path(folder)):
            fallback, report = company_fallback({}, {})
        self.assertEqual(fallback, {})
        self.assertEqual(report['filesParsed'], 0)

    def test_official_total_uses_latest_published_report(self):
        index = '''<ul>
          <li><a href="/sjtj/sep.pdf">公募基金市场数据（2026年9月）</a><span>2026-10-28</span></li>
          <li><a href="/sjtj/aug.pdf">公募基金市场数据（2026年8月）</a><span>2026-09-25</span></li>
          <li><a href="/sjtj/oct.pdf">公募基金市场数据（2026年10月）</a><span>2026-11-25</span></li>
          <li><a href="https://unrelated.example/nov.pdf">公募基金市场数据（2026年11月）</a><span>2026-10-28</span></li>
        </ul>'''
        result = latest_report(index.encode(), dt.date(2026, 10, 29))
        self.assertEqual(result['asOf'], '2026-09-30')
        self.assertEqual(result['publishedAt'], '2026-10-28')
        self.assertEqual(result['sourceUrl'], 'https://www.amac.org.cn/sjtj/sep.pdf')


if __name__ == '__main__':
    unittest.main()
