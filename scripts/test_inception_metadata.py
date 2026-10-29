#!/usr/bin/env python3
"""Checks for verified inception enrichment and cached-data recalculation."""
import argparse
import contextlib
import datetime as dt
import gzip
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import backfill_market as collector
from backfill_market import decode, normalize, reusable_checkpoint, SCHEMA, TZ
from build_full_snapshot import field_date, merge
from inception_metadata import apply_inception, calculation_input_hash, enforce_inception_intervals, valid_date

ROOT = Path(__file__).resolve().parents[1]
AS_OF = '2026-10-29'


def stamp(day):
    return int(dt.datetime.fromisoformat(day).replace(tzinfo=TZ).timestamp() * 1000)


def raw_points(points, **extra):
    return {'_sourceCode': '000001', 'Data_netWorthTrend': [
        {'x': stamp(day), 'y': nav, 'equityReturn': growth} for day, nav, growth in points], **extra}


def profile(code='000001', date='2026-07-01', status='verified'):
    return {'code': code, 'status': status, 'inceptionDate': date,
            'sourceReportedInceptionDate': date, 'dateSemantic': 'source-specific listed code inception',
            'identity': {'listedCodes': [code], 'classification': 'requested_code_in_profile',
                         'evidenceText': code + '（前端）'},
            'evidence': {'url': 'https://fundf10.eastmoney.com/jbgk_' + code + '.html',
                         'sha256': 'a' * 64, 'retrievedAt': AS_OF + 'T14:00:00+08:00'}}


class InceptionMetadataTests(unittest.TestCase):
    def test_calendar_and_future_dates_are_rejected(self):
        self.assertEqual(valid_date('2024-02-29', AS_OF), '2024-02-29')
        for value in ['2026-02-29', '2026-99-99', '2026-10-30', '2026-1-01', '', None]:
            self.assertIsNone(valid_date(value, AS_OF))

    def test_existing_date_survives_conflicting_base_and_profile(self):
        p = {'code': '000001', 'inception': '2001-12-18'}
        value = apply_inception(p, '2002-01-01', profile(date='2026-07-01'), AS_OF)
        self.assertEqual(value['inception'], p['inception'])
        self.assertEqual(p, {'code': '000001', 'inception': '2001-12-18'})

    def test_verified_profile_fills_only_a_matching_code_and_keeps_evidence(self):
        value = apply_inception({'code': '000001'}, None, profile(), AS_OF)
        self.assertEqual(value['inception'], '2026-07-01')
        self.assertEqual(value['inceptionMeta']['sourceHash'], 'a' * 64)
        self.assertEqual(value['inceptionMeta']['retrievedAt'], AS_OF + 'T14:00:00+08:00')
        self.assertTrue(value['inceptionMeta']['sourceUrl'].endswith('jbgk_000001.html'))
        for invalid in [profile(code='000002'), {k: v for k, v in profile().items() if k != 'code'},
                        profile(date='2026-11-01'), profile(status='identity_mismatch')]:
            self.assertNotIn('inception', apply_inception({'code': '000001'}, None, invalid, AS_OF))

    def test_issue_date_and_contract_date_are_not_used_as_inception(self):
        data = {**profile(status='not_established'), 'inceptionDate': None,
                'sourceReportedInceptionDate': None, 'issueDate': '2026-11-02',
                'contractEffectiveDate': '2010-01-01'}
        value = apply_inception({'code': '000001'}, None, data, AS_OF)
        self.assertNotIn('inception', value)
        self.assertEqual(value['inceptionMeta']['status'], 'not_established')

    def test_same_day_changed_metadata_invalidates_checkpoint(self):
        p = {'code': '000001', 'name': '测试基金', 'type': '股票型'}
        record = {'schemaVersion': SCHEMA, 'calculationAsOf': AS_OF, 'status': 'partial',
                  'code': p['code'], 'name': p['name'], 'quality': {'verifiedInception': None},
                  'calculationInputHash': calculation_input_hash(p, AS_OF)}
        self.assertTrue(reusable_checkpoint(record, AS_OF, product=p))
        for changed in [{**p, 'inception': '2026-07-01'}, {**p, 'type': '货币型-普通货币'}, {**p, 'name': '变更名称'}]:
            self.assertFalse(reusable_checkpoint(record, AS_OF, product=changed))
        legacy = {k: v for k, v in record.items() if k != 'calculationInputHash'}
        self.assertTrue(reusable_checkpoint(legacy, AS_OF, product=p))
        self.assertFalse(reusable_checkpoint(legacy, AS_OF, product={**p, 'inception': '2026-07-01'}))

    def test_new_inception_recalculates_ytd_and_removes_retained_long_window(self):
        raw = raw_points([('2026-07-01', 1, 0), ('2026-10-28', 1.1, 10)], syl_1n=10)
        p = {'code': '000001', 'name': '测试基金', 'type': '股票型'}
        evidence = {'retrievedAt': AS_OF + 'T12:00:00+08:00'}
        old = normalize(p, raw, evidence, AS_OF)['perf']
        new = normalize({**p, 'inception': '2026-07-01'}, raw, evidence, AS_OF)['perf']
        self.assertIsNone(old['ytd'])
        self.assertEqual(new['ytd'], 10)
        self.assertIsNone(new['y1'])
        merged = merge(merge(old, new), {'y1': 10, 'jzrq': '2026-10-28'})
        self.assertEqual(merged['y1'], 10)  # The final lifespan gate is necessary.
        final = enforce_inception_intervals(merged, '2026-07-01', field_date)
        self.assertNotIn('y1', final)
        self.assertEqual(final['fieldStatus']['y1']['reason'], 'insufficient_history')
        self.assertEqual(final['ytd'], 10)

    def test_interval_gate_uses_each_fields_own_date_and_month_end(self):
        record = {'m1': 0, 'm3': 2, 'm6': 3, 'y1': 4, 'jzrq': '2026-10-28',
                  'fieldStatus': {'m1': {'status': 'available', 'asOf': '2026-07-31'}}}
        value = enforce_inception_intervals(record, '2026-07-01', field_date)
        self.assertNotIn('m1', value)
        self.assertEqual(value['m3'], 2)
        self.assertNotIn('m6', value)
        self.assertNotIn('y1', value)
        boundary = enforce_inception_intervals({'m1': 0, 'jzrq': '2026-03-31'}, '2026-02-28', field_date)
        self.assertEqual(boundary['m1'], 0)

    def test_cache_only_recomputes_changed_record_without_network_or_manifest_subset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'dist').mkdir()
            out = root / 'source-cache/backfill-20261029'
            (out / 'records').mkdir(parents=True); (out / 'raw').mkdir()
            products = [{'code': '000001', 'name': '测试A', 'type': '股票型'},
                        {'code': '000002', 'name': '测试B', 'type': '股票型'}]
            (root / 'dist/snapshot.js').write_text('window.MARKET_SNAPSHOT=' + json.dumps({'funds': products}) + ';')
            directory = root / 'source-cache/current-directory.json'
            directory.write_text(json.dumps({'rows': [[p['code'], '', p['name'], p['type'], ''] for p in products]}))
            base = root / 'source-cache/base.json'; base.write_text('{"inceptions":{}}')
            profiles = root / 'source-cache/profiles.json'
            profiles.write_text(json.dumps({'schemaVersion': 1, 'asOf': AS_OF, 'records': {'000001': profile()}}))
            raw = raw_points([('2026-07-01', 1, 0), ('2026-10-28', 1.1, 10)])
            for p in products:
                record = normalize(p, raw, {'retrievedAt': AS_OF + 'T12:00:00+08:00'}, AS_OF)
                (out / 'records' / (p['code'] + '.json')).write_text(json.dumps(record))
            payload = ('var fS_code="000001";var fS_name="测试A";var Data_netWorthTrend=' +
                       json.dumps(raw['Data_netWorthTrend']) + ';').encode()
            raw_file = out / 'raw/000001.js.gz'; raw_file.write_bytes(gzip.compress(payload))
            os.utime(raw_file, (1_600_000_000, 1_600_000_000))
            args = argparse.Namespace(output=str(out), as_of=AS_OF, base_refresh=str(base), profiles=str(profiles),
                directory=str(directory), codes=None, limit=None, workers=1, normalize_only=False,
                fresh_source=False, retry_failed=False, cache_only=True, retries=0, timeout=1)
            with mock.patch.object(collector, 'ROOT', root), mock.patch.object(collector, 'download') as network:
                with contextlib.redirect_stdout(io.StringIO()):
                    collector.run(args)
            network.assert_not_called()
            manifest = json.loads((out / 'manifest.json').read_text())
            self.assertEqual(set(manifest['codes']), {'000001', '000002'})
            self.assertEqual(manifest['summary']['reusedCheckpoint'], 1)
            self.assertEqual(manifest['summary']['reusedRaw'], 1)
            changed = json.loads((out / 'records/000001.json').read_text())
            self.assertEqual(changed['perf']['ytd'], 10)
            self.assertEqual(changed['quality']['verifiedInception'], '2026-07-01')


class LocalEvidenceRegressionTests(unittest.TestCase):
    def test_20678_existing_rank_dates_remain_unchanged(self):
        path = ROOT / 'source-cache/base-refresh-20261029.json'
        if not path.exists():
            self.skipTest('Frozen local source evidence is not included in delivery packages')
        existing = json.loads(path.read_text())['inceptions']
        self.assertEqual(len(existing), 20678)
        for code, value in existing.items():
            result = apply_inception({'code': code, 'inception': value}, '2000-01-01', profile(code), AS_OF)
            self.assertEqual(result['inception'], value, code)

    def test_real_cached_010579_and_028922_gain_year_metrics(self):
        for code, inception, ytd, mdd in [('010579', '2026-01-08', -.641589, -1.803921),
                                           ('028922', '2026-09-24', -.62, -.62)]:
            raw_path = ROOT / 'source-cache/backfill-20261029/raw' / (code + '.js.gz')
            record_path = ROOT / 'source-cache/backfill-20261029/records' / (code + '.json')
            if not raw_path.exists() or not record_path.exists():
                self.skipTest('Frozen local source evidence is not included in delivery packages')
            with self.subTest(code=code):
                record = json.loads(record_path.read_text())
                raw = decode(gzip.decompress(raw_path.read_bytes()), code, record['name'])
                product = {'code': code, 'name': record['name'], 'type': '混合型'}
                old = normalize(product, raw, record['evidence'], AS_OF)
                new = normalize({**product, 'inception': inception}, raw, record['evidence'], AS_OF)
                self.assertIsNone(old['perf']['ytd'])
                self.assertAlmostEqual(new['perf']['ytd'], ytd, places=6)
                self.assertAlmostEqual(new['perf']['ytdMdd'], mdd, places=6)
                self.assertEqual(new['quality']['verifiedInception'], inception)


if __name__ == '__main__':
    unittest.main()
