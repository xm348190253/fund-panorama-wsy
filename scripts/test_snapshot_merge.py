#!/usr/bin/env python3
"""Regression checks for independently dated fund data and explicit missingness."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from build_full_snapshot import merge, field_date, sanitize_year, validate_collection, merge_source_evidence


class SourceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.cache = Path(self.folder.name)
        self.key = 'base-refresh-2026-10-29/rank-pass0-p1-n10-asc'

    def source(self, raw, key=None, save=True):
        key = key or self.key
        if save:
            path = self.cache / (key + '.txt')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return {'key': key, 'url': 'https://fund.eastmoney.com/data/rankhandler.aspx?date=2026-10-29',
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'retrievedAt': '2026-10-29'}

    def test_same_day_bootstrap_preserves_old_hash_without_pointing_to_new_raw(self):
        old = self.source(b'old valid response', save=False)
        current = self.source(b'new valid response')
        merged = merge_source_evidence([old], [current], self.cache)
        self.assertEqual(len(merged), 2)
        inherited, fresh = merged
        self.assertNotEqual(inherited['key'], fresh['key'])
        self.assertEqual(inherited['sha256'], old['sha256'])
        self.assertEqual(inherited['localEvidenceStatus'], 'inherited_metadata_only')
        self.assertFalse((self.cache / (inherited['key'] + '.txt')).exists())
        self.assertEqual(fresh['sha256'], current['sha256'])
        self.assertEqual((self.cache / (fresh['key'] + '.txt')).read_bytes(), b'new valid response')
        # This is the same key-to-file hash check used by verify_snapshot.cjs.
        for source in merged:
            path = self.cache / (source['key'] + '.txt')
            if path.exists():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source['sha256'])
        repeated = merge_source_evidence(merged, [current], self.cache)
        self.assertEqual(repeated, merged)
        self.assertEqual([(s['key'], s['sha256']) for s in repeated],
                         [(s['key'], s['sha256']) for s in merged])

    def test_tampered_current_raw_and_conflicting_current_entries_are_rejected(self):
        old = self.source(b'old', save=False)
        current = self.source(b'new')
        with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
            merge_source_evidence([], [old, current], self.cache)
        (self.cache / (self.key + '.txt')).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
            merge_source_evidence([], [current], self.cache)

    def test_versioned_current_collector_migrates_legacy_bootstrap_reference(self):
        old = self.source(b'old', save=False)
        current = self.source(b'new')
        versioned = current['key'] + '.sha256-' + current['sha256']
        (self.cache / (versioned + '.txt')).write_bytes(b'new')
        current = {**current, 'key': versioned, 'originalKey': self.key}
        merged = merge_source_evidence([old], [current], self.cache)
        self.assertEqual(merged[0]['localEvidenceStatus'], 'inherited_metadata_only')
        self.assertEqual(merged[1]['key'], versioned)
        self.assertEqual(merged[1]['localEvidenceStatus'], 'verified')

    def test_unexplained_inherited_corruption_is_not_treated_as_supersession(self):
        old = self.source(b'original')
        (self.cache / (self.key + '.txt')).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'Inherited source evidence hash mismatch'):
            merge_source_evidence([old], [], self.cache)

    def test_versioned_history_and_separate_keys_remain_verifiable(self):
        original = self.source(b'old')
        first = merge_source_evidence([], [original], self.cache)
        current = self.source(b'new')
        other = self.source(b'new', key='base-refresh-2026-10-30/rank-pass0-p1-n10-asc')
        merged = merge_source_evidence(first, [current, other], self.cache)
        self.assertEqual(len(merged), 3)
        self.assertEqual(len({source['key'] for source in merged}), 3)
        for source in merged:
            self.assertEqual(source['localEvidenceStatus'], 'verified')
            self.assertEqual(hashlib.sha256((self.cache / (source['key'] + '.txt')).read_bytes()).hexdigest(),
                             source['sha256'])
        (self.cache / (first[0]['key'] + '.txt')).write_bytes(b'corrupted version')
        with self.assertRaisesRegex(ValueError, 'hash/size mismatch'):
            merge_source_evidence(first, [current], self.cache)


class MergeTests(unittest.TestCase):
    def test_older_detail_cannot_replace_newer_returns(self):
        value = merge({'d1': 1.2, 'm1': 2.0, 'jzrq': '2026-10-28'},
                      {'d1': 1.1, 'm1': None, 'jzrq': '2026-10-27', 'scale': 0, 'scaleDate': '2026-09-30'})
        self.assertEqual((value['d1'], value['m1'], value['scale']), (1.2, 2.0, 0))

    def test_new_nav_does_not_redate_retained_return(self):
        value = merge({'d1': 1.2, 'm1': 2.0, 'jzrq': '2026-10-27'}, {'d1': 1.1, 'jzrq': '2026-10-28'})
        self.assertEqual(field_date(value, 'm1'), '2026-10-27')
        self.assertEqual(field_date(value, 'd1'), '2026-10-28')
        self.assertEqual(field_date(merge(value, {'jzrq': '2026-10-29'}), 'm1'), '2026-10-27')

    def test_money_rank_restores_ytd_and_clears_missing_flag(self):
        value = merge({'fieldStatus': {'ytd': {'status': 'missing', 'reason': 'not_disclosed'}}},
                      {'ytd': 1.5, 'jzrq': '2026-10-28'})
        self.assertEqual(value['ytd'], 1.5)
        self.assertNotIn('ytd', value['fieldStatus'])

    def test_inapplicable_is_not_zero(self):
        value = merge({'d1': 0}, {'fieldStatus': {'d1': {'status': 'not_applicable', 'reason': 'not_applicable_money'}}})
        self.assertNotIn('d1', value)

    def test_scale_and_risk_use_own_dates(self):
        value = merge({'jzrq': '2026-10-28', 'scale': 12, 'scaleDate': '2026-06-30', 'mdd': -9, 'mddAsOf': '2026-10-28'},
                      {'jzrq': '2026-10-27', 'scale': 14, 'scaleDate': '2026-09-30', 'mdd': -8, 'mddAsOf': '2026-10-27'})
        self.assertEqual((value['scale'], value['mdd'], value['jzrq']), (14, -9, '2026-10-28'))

    def test_undated_return_stays_undated(self):
        value = merge({'m1': 1.2}, {'d1': 0.5, 'jzrq': '2026-10-28'})
        self.assertEqual(field_date(value, 'm1'), '')

    def test_explicit_unknown_date_survives_merge(self):
        value = merge({}, {'m1': 2, 'jzrq': '2026-10-28', 'fieldStatus': {'m1': {'status': 'available', 'asOf': None}}})
        self.assertEqual(field_date(value, 'm1'), '')
        self.assertEqual(field_date(merge(value, {'jzrq': '2026-10-29'}), 'm1'), '')

    def test_stale_state_and_independent_date_survive(self):
        state = {'status': 'stale', 'reason': 'source_date_older_than_14_days', 'asOf': '2021-10-01'}
        value = merge({}, {'m1': 2, 'jzrq': '2021-10-01', 'fieldStatus': {'m1': state}})
        self.assertEqual(value['fieldStatus']['m1'], state)
        self.assertEqual(merge(value, {'jzrq': '2026-10-29'})['fieldStatus']['m1'], state)

    def test_risk_and_money_dates_are_independent(self):
        self.assertEqual(field_date({'ytdAsOf': '2026-10-27', 'mddAsOf': '2026-10-28'}, 'ytdMdd'), '2026-10-27')
        self.assertEqual(field_date({'mddAsOf': '2026-10-28'}, 'ytdMdd'), '2026-10-28')
        self.assertEqual(field_date({'wfsyAsOf': '2026-10-27', 'jzrq': '2026-10-28'}, 'wfsy'), '2026-10-27')

    def test_ytd_guard_checks_the_retained_value_date(self):
        unknown = sanitize_year({'ytd': 2, 'ytdMdd': -1}, '2026-10-29')
        self.assertNotIn('ytd', unknown)
        self.assertNotIn('ytdMdd', unknown)
        self.assertEqual(unknown['fieldStatus']['ytd']['reason'], 'missing_nav_date')
        old = sanitize_year({'ytd': 2, 'jzrq': '2021-10-01'}, '2026-10-29')
        self.assertNotIn('ytd', old)
        detail = {'ytd': 3, 'jzrq': '2026-10-28'}
        retained = sanitize_year(merge(detail, {'ytd': 2, 'jzrq': ''}), '2026-10-29')
        self.assertEqual(retained['ytd'], 3)
        self.assertEqual(field_date(retained, 'ytd'), '2026-10-28')


class CollectionGateTests(unittest.TestCase):
    def fixtures(self):
        return ({'asOf': '2026-10-29'},
                {'asOf': '2026-10-29', 'codes': ['000001'], 'summary': {
                    'finishedAt': '2026-10-29T12:00:00+08:00', 'targetCount': 1, 'completed': 1, 'ok': 1}},
                {'asOf': '2026-10-29', 'directoryCount': 1,
                 'integrity': {'ranking': {'complete': True}, 'money': {'complete': True}}})

    def test_complete_collection_passes(self):
        validate_collection(*self.fixtures(), ['000001'], '2026-10-29')

    def test_partial_batch_is_rejected(self):
        directory, manifest, base = self.fixtures()
        base['integrity']['money']['complete'] = False
        with self.assertRaisesRegex(ValueError, 'money collection is incomplete'):
            validate_collection(directory, manifest, base, ['000001'], '2026-10-29')

    def test_incomplete_manifest_and_stale_batch_are_rejected(self):
        directory, manifest, base = self.fixtures()
        manifest['summary']['completed'] = 0
        with self.assertRaisesRegex(ValueError, 'manifest'):
            validate_collection(directory, manifest, base, ['000001'], '2026-10-29')
        directory, manifest, base = self.fixtures()
        base['asOf'] = '2026-10-28'
        with self.assertRaisesRegex(ValueError, 'dates or directory counts'):
            validate_collection(directory, manifest, base, ['000001'], '2026-10-29')


if __name__ == '__main__':
    unittest.main()
