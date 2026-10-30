"""Index identity, quote time and failure semantics; all requests mocked."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from refresh_index_quotes import SYMBOLS, TZ, collect, parse_response, quote_stamp, validate_snapshot

STAMP = '2026-10-30T17:55:00+08:00'
EPOCH = int(dt.datetime.fromisoformat('2026-10-30T15:00:00+08:00').timestamp())


def payload():
    return {'rc': 0, 'data': {'diff': [
        {'f13': int(secid.split('.')[0]), 'f12': secid.split('.')[1],
         'f2': 100.5, 'f3': 0, 'f4': 0, 'f124': EPOCH}
        for secid, _, _ in SYMBOLS]}}


def snapshot():
    return {'schemaVersion': 1, 'timezone': 'Asia/Shanghai', 'collectedAt': STAMP,
            'quotes': parse_response(payload(), STAMP), 'evidence': [], 'errors': []}


class IndexQuoteTests(unittest.TestCase):
    def test_time_is_source_epoch_not_collection_time_or_other_fields(self):
        data = payload()
        data['data']['diff'][0].update(f80=32.55, f86=32.39)
        quote = parse_response(data, STAMP)[0]
        self.assertEqual(quote['quoteTimestamp'], '2026-10-30T15:00:00+08:00')
        self.assertEqual(quote['quoteTime'], '15:00:00')
        self.assertEqual(quote['collectedAt'], STAMP)
        data['data']['diff'][0].pop('f124')
        self.assertIsNone(parse_response(data, STAMP)[0]['quoteDate'])

    def test_us_overnight_quote_is_preserved_in_beijing_time(self):
        data = payload()
        epoch = int(dt.datetime.fromisoformat('2026-10-29T20:00:00+00:00').timestamp())
        data['data']['diff'][-1]['f124'] = epoch
        self.assertEqual(parse_response(data, STAMP)[-1]['quoteTimestamp'], '2026-10-30T04:00:00+08:00')

    def test_missing_and_bad_values_never_become_zero(self):
        data = payload()
        data['data']['diff'][0]['f2'] = '-'
        data['data']['diff'][1]['f2'] = 'NaN'
        data['data']['diff'][2]['f2'] = 0
        data['data']['diff'].pop()
        quotes = parse_response(data, STAMP)
        for i in [0, 1, 2, 8]:
            self.assertIsNone(quotes[i]['val'])
            self.assertEqual(quotes[i]['status'], 'unavailable')
        self.assertEqual(quotes[3]['pct'], 0)
        self.assertEqual(len(quotes), 9)

    def test_code_matching_includes_market(self):
        data = payload()
        data['data']['diff'][0]['f13'] = 0
        self.assertIsNone(parse_response(data, STAMP)[0]['val'])
        self.assertEqual(parse_response(data, STAMP)[7]['name'], '纳斯达克100')

    def test_duplicates_and_api_error_are_rejected(self):
        data = payload()
        data['data']['diff'].append(dict(data['data']['diff'][0]))
        with self.assertRaises(ValueError):
            parse_response(data, STAMP)
        with self.assertRaises(ValueError):
            parse_response({'rc': 1, 'data': None}, STAMP)

    def test_invalid_or_future_epoch_is_not_labeled_as_quote_time(self):
        for value in [None, '-', 32.39, 10**30, EPOCH + 86400]:
            self.assertIsNone(quote_stamp(value, STAMP))
        self.assertEqual(quote_stamp(EPOCH * 1000, STAMP).hour, 15)

    def test_validation_checks_time_identity_and_coverage(self):
        self.assertEqual(len(validate_snapshot(snapshot())['quotes']), 9)
        for change in ['time', 'identity', 'coverage']:
            value = snapshot()
            if change == 'time':
                value['quotes'][0]['quoteTime'] = '17:55:00'
            elif change == 'identity':
                value['quotes'][0]['name'] = 'wrong'
            else:
                value['quotes'].pop()
            with self.assertRaises(ValueError):
                validate_snapshot(value)

    def test_network_failure_publishes_explicit_missing_not_old_values(self):
        with tempfile.TemporaryDirectory() as tmp, patch('refresh_index_quotes.urllib.request.urlopen', side_effect=TimeoutError('test')), patch('refresh_index_quotes.time.sleep'):
            output = Path(tmp) / 'index-quotes.json'
            output.write_text(json.dumps(snapshot()))
            result = collect(output)
            self.assertEqual(len(result['errors']), 4)
            self.assertTrue(all(q['val'] is None for q in result['quotes']))
            self.assertTrue(all(q['quoteTimestamp'] is None for q in result['quotes']))
            self.assertEqual(json.loads(output.read_text()), result)


if __name__ == '__main__':
    unittest.main()
