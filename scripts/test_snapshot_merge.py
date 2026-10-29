#!/usr/bin/env python3
"""Regression checks for independently dated fund data and explicit missingness."""
import unittest
from build_full_snapshot import merge, field_date, sanitize_year, validate_collection


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
