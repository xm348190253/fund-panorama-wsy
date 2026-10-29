#!/usr/bin/env python3
"""Meaningful identity/date regressions for profile metadata ingestion."""
import unittest
from refresh_fund_profiles import parse_profile


def page(code='012489（前端）', inception='2021年05月27日 / --', issue='2016年11月22日', state='开放申购 开放赎回', header=None):
    fields = [('基金全称', '测试基金'), ('基金简称', '测试基金D'), ('基金代码', code),
              ('发行日期', issue), ('成立日期/规模', inception)]
    table = ''.join('<th>'+k+'</th><td>'+v+'</td>' for k,v in fields)
    return ('<html><head><title>测试基金概况</title></head><body>'
            + ('成立日期：'+header if header else '') + '交易状态：'+state+'购买手续费'
            + '<table>'+table+'</table></body></html>').encode()


def parse(raw, code='012489', known=None):
    return parse_profile({'code':code, 'name':'测试基金D', 'inception':known}, raw, '2026-10-29')


class ProfileTests(unittest.TestCase):
    def test_later_share_date_is_not_earlier_issue_date(self):
        r=parse(page())
        self.assertEqual(r['inceptionDate'],'2021-05-27')
        self.assertEqual(r['issueDate'],'2016-11-22')
        self.assertIsNone(r['contractEffectiveDate'])

    def test_existing_dates_are_never_silently_overwritten(self):
        r=parse(page(),known='2016-12-07')
        self.assertEqual(r['status'],'date_conflict')
        self.assertIsNone(r['inceptionDate'])
        self.assertEqual(r['sourceReportedInceptionDate'],'2021-05-27')

    def test_backend_needs_both_codes_in_profile(self):
        r=parse(page('000001（前端）、000002（后端）'),code='000002')
        self.assertEqual(r['status'],'verified')
        self.assertEqual(r['identity']['alias']['canonicalCode'],'000001')

    def test_same_name_or_returned_primary_code_is_not_alias_proof(self):
        r=parse(page('515290（主代码）'),code='515293')
        self.assertEqual(r['status'],'identity_mismatch')
        self.assertIsNone(r['inceptionDate'])

    def test_future_issue_with_empty_inception_is_not_established(self):
        r=parse(page(inception='/ --',issue='2026年11月03日',state=''))
        self.assertEqual(r['status'],'not_established')
        self.assertIsNone(r['inceptionDate'])

    def test_past_issue_empty_inception_is_only_missing(self):
        r=parse(page(inception='/ --',issue='2026年10月01日',state=''))
        self.assertEqual(r['status'],'not_disclosed')

    def test_current_fundraising_is_explicit(self):
        r=parse(page(inception='/ --',issue='2026年10月01日',state='认购期'))
        self.assertEqual(r['status'],'not_established')

    def test_header_table_date_conflict_is_retained(self):
        r=parse(page(header='2016-12-07'))
        self.assertEqual(r['status'],'date_conflict')
        self.assertIsNone(r['inceptionDate'])

    def test_future_inception_is_not_a_current_date(self):
        r=parse(page(inception='2027年01月01日 / --'))
        self.assertEqual(r['status'],'date_conflict')

    def test_not_found_and_truncation_are_separate(self):
        self.assertEqual(parse(b'<html><title>not found</title></html>')['status'],'source_unavailable')
        self.assertEqual(parse(page()[:-14])['status'],'parse_failed')


if __name__=='__main__':
    unittest.main()
