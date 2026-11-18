import json
from pathlib import Path
import tempfile
import unittest

from public_funds import ADMIN_URL, PRIVATE_MARKERS, build, fingerprint, sanitize_index


def combined_html():
    return ('<html><head><script>window.__INSURANCE_FETCH__=window.fetch.bind(window);</script>'
            '<meta content="connect-src &#x27;self&#x27;">'
            '<script>window.__echartsTries=["echarts.min.js"];</script></head><body>'
            '<div id="deliveryBanner"><a href="' + ADMIN_URL + '">更新进度</a></div>'
            '<script>function stop(anchor){if(anchor.href===' + json.dumps(ADMIN_URL) + ')return;}</script>'
            '<script src="snapshot.js?release=source-1"></script>'
            '<script src="snapshot-perf-001.js?release=source-1"></script>'
            '<script>window.__FUND_INDEX_SNAPSHOT__={"quotes":[{"name":"公开指数"}]};</script>'
            '<script src="market.js?release=source-1"></script>'
            '<script id="insurance-dashboard-bootstrap">const privatePath="/api/insurance";</script>'
            '</body></html>')


class PublicFundIsolation(unittest.TestCase):
    def test_remove_combined_bootstrap_and_keep_fund_functionality(self):
        result = sanitize_index(combined_html(), 'pf1-source-1')
        self.assertFalse(any(marker in result for marker in PRIVATE_MARKERS))
        self.assertIn('window.__FUND_INDEX_SNAPSHOT__', result)
        self.assertIn('snapshot-perf-001.js?release=pf1-source-1', result)
        self.assertIn('echarts.min.js?release=pf1-source-1', result)
        self.assertIn('href="/updates"', result)
        self.assertNotIn(ADMIN_URL, result)

    def test_changed_or_additional_private_bootstrap_fails_closed(self):
        with self.assertRaises(ValueError):
            sanitize_index(combined_html().replace('insurance-dashboard-bootstrap', 'changed-private-loader'), 'v1')
        with self.assertRaises(ValueError):
            sanitize_index(combined_html() + '<script>fetch("/insurance-data/manifest.json")</script>', 'v1')

    def test_only_fund_files_are_published_and_data_bytes_are_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source'
            source.mkdir()
            contents = {'index.html': combined_html(), 'market.js': 'const funds=[];',
                        'echarts.min.js': '/* chart library */', 'snapshot.js': 'const publicFundData={};',
                        'snapshot-perf-001.js': 'const publicPerformance={};'}
            for name, text in contents.items():
                (source / name).write_text(text)
            release = {'version': 'source-1', 'dataDate': '2026-11-18', 'generatedAt': '2026-11-18T08:00:00+08:00',
                       'files': {name: fingerprint((source / name).read_bytes()) for name in contents}}
            (source / 'release.json').write_text(json.dumps(release))
            (source / 'insurance-data').mkdir()
            (source / 'insurance-data/private.docx').write_bytes(b'never published')
            output = Path(temporary) / 'public'
            public = build(source, output)
            self.assertEqual(set(p.name for p in output.iterdir()), set(contents) | {'release.json'})
            for name in contents.keys() - {'index.html'}:
                self.assertEqual(public['files'][name], release['files'][name])
            self.assertEqual(public['sourceVersion'], release['version'])
            self.assertEqual(public['dataDate'], release['dataDate'])
            release['files']['insurance-data/private.docx'] = fingerprint(b'never published')
            (source / 'release.json').write_text(json.dumps(release))
            with self.assertRaises(Exception):
                build(source, Path(temporary) / 'forbidden')


if __name__ == '__main__':
    unittest.main()
