"""Bounded compressed download and compatibility checks without network access."""
import gzip
import io
import unittest
from unittest import mock

from backfill_market import download

FUND = 'https://fund.eastmoney.com/pingzhongdata/000001.js?v=test'
PAYLOAD = b'var fS_code="000001";var Data_netWorthTrend=[];'


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = io.BytesIO(body)
        self.status = status
        self.headers = headers or {}

    def read(self, size):
        return self.body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def identity(body=PAYLOAD):
    return Response(body, headers={'Content-Length': str(len(body))})


class DownloadTests(unittest.TestCase):
    def assert_fallback_headers(self, network):
        first, second = [call.args[0] for call in network.call_args_list[:2]]
        self.assertEqual(first.get_header('Accept-encoding'), 'gzip')
        self.assertIsNone(first.get_header('Range'))
        self.assertEqual(second.get_header('Accept-encoding'), 'identity')
        self.assertIsNotNone(second.get_header('Range'))

    def test_complete_gzip_is_identical_and_uses_one_request(self):
        raw = gzip.compress(PAYLOAD)
        with mock.patch('backfill_market.urllib.request.urlopen', return_value=Response(raw, headers={
                'Content-Encoding': 'gzip', 'Content-Length': str(len(raw))})) as network:
            self.assertEqual(download(FUND, 20), (PAYLOAD, 200, 1))
        self.assertEqual(network.call_count, 1)
        self.assertIsNone(network.call_args.args[0].get_header('Range'))

    def test_chunked_gzip_without_content_length_is_valid(self):
        with mock.patch('backfill_market.urllib.request.urlopen', return_value=Response(
                gzip.compress(PAYLOAD), headers={'Content-Encoding': 'gzip', 'Transfer-Encoding': 'chunked'})):
            self.assertEqual(download(FUND, 20), (PAYLOAD, 200, 1))

    def test_truncated_gzip_and_invalid_crc_fall_back(self):
        full = gzip.compress(PAYLOAD)
        for broken in (full[:-4], full[:-8] + bytes([full[-8] ^ 1]) + full[-7:]):
            with self.subTest(body=broken), mock.patch('backfill_market.urllib.request.urlopen', side_effect=[
                    Response(broken, headers={'Content-Encoding': 'gzip'}), identity()]) as network:
                self.assertEqual(download(FUND, 20), (PAYLOAD, 200, 2))
                self.assert_fallback_headers(network)

    def test_partial_gzip_response_uses_original_range_continuation(self):
        split = 10
        responses = [Response(b'incomplete', status=206, headers={'Content-Encoding': 'gzip'}),
                     Response(PAYLOAD[:split], status=206, headers={
                         'Content-Range': f'bytes 0-{split - 1}/{len(PAYLOAD)}'}),
                     Response(PAYLOAD[split:], status=206, headers={
                         'Content-Range': f'bytes {split}-{len(PAYLOAD) - 1}/{len(PAYLOAD)}'})]
        with mock.patch('backfill_market.urllib.request.urlopen', side_effect=responses) as network:
            self.assertEqual(download(FUND, 20), (PAYLOAD, 206, 3))
            self.assert_fallback_headers(network)
            self.assertEqual(network.call_args_list[2].args[0].get_header('Range'),
                             f'bytes={split}-{len(PAYLOAD) - 1}')

    def test_oversized_decompression_falls_back_safely(self):
        with mock.patch('backfill_market.urllib.request.urlopen', side_effect=[
                Response(gzip.compress(b'x' * 100000), headers={'Content-Encoding': 'gzip'}), identity()]) as network:
            self.assertEqual(download(FUND, 20, max_bytes=256), (PAYLOAD, 200, 2))
            self.assert_fallback_headers(network)

    def test_bad_transport_metadata_or_oversized_body_fall_back(self):
        examples = [Response(PAYLOAD, headers={'Content-Length': str(len(PAYLOAD) + 1)}),
                    Response(PAYLOAD, headers={'Content-Length': '-1'}),
                    Response(PAYLOAD, headers={'Content-Range': f'bytes 0-1/{len(PAYLOAD)}'}),
                    Response(PAYLOAD, headers={'Content-Encoding': 'br'}),
                    Response(b'x' * 257),
                    Response(PAYLOAD, headers={'Content-Length': '257'})]
        for response in examples:
            with self.subTest(headers=response.headers), mock.patch('backfill_market.urllib.request.urlopen',
                    side_effect=[response, identity()]):
                self.assertEqual(download(FUND, 20, max_bytes=256), (PAYLOAD, 200, 2))

    def test_server_without_gzip_can_return_complete_identity(self):
        with mock.patch('backfill_market.urllib.request.urlopen', return_value=identity()) as network:
            self.assertEqual(download(FUND, 20), (PAYLOAD, 200, 1))
            self.assertEqual(network.call_count, 1)

    def test_timeout_in_fast_request_falls_back(self):
        with mock.patch('backfill_market.urllib.request.urlopen', side_effect=[TimeoutError('test'), identity()]):
            self.assertEqual(download(FUND, 20), (PAYLOAD, 200, 2))

    def test_other_urls_keep_identity_range_path(self):
        for url in ('https://fund.eastmoney.com/js/fundcode_search.js',
                    'https://other.example/pingzhongdata/000001.js'):
            with self.subTest(url=url), mock.patch('backfill_market.urllib.request.urlopen',
                    return_value=identity()) as network:
                self.assertEqual(download(url, 20), (PAYLOAD, 200, 1))
                self.assertEqual(network.call_count, 1)
                request = network.call_args.args[0]
                self.assertEqual(request.get_header('Accept-encoding'), 'identity')
                self.assertEqual(request.get_header('Range'), 'bytes=0-16777215')


if __name__ == '__main__':
    unittest.main()
