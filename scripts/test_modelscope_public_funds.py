import json
from pathlib import Path
import tempfile
import unittest

from modelscope_public_funds import PUBLIC_REPO, build_domestic, domestic_index
from modelscope_sync import DEFAULT_REPO, validate_site
from public_funds import fingerprint
from test_public_funds import combined_html


class DomesticPublicFunds(unittest.TestCase):
    def test_domestic_target_is_separate(self):
        self.assertNotEqual(PUBLIC_REPO, DEFAULT_REPO)
        self.assertEqual(PUBLIC_REPO, 'wangshuyang2126/fund-panorama-public-wsy')

    def test_build_preserves_all_fund_data_and_uses_local_update_panel(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source'
            source.mkdir()
            assets = {'index.html': combined_html().replace('href="' , 'target="_blank" href="', 1),
                      'market.js': 'const funds=[];', 'echarts.min.js': '/* chart */',
                      'snapshot.js': 'const funds={};', 'snapshot-perf-001.js': 'const perf={};'}
            for name, text in assets.items():
                (source / name).write_text(text)
            release = {'version': 'source-1', 'dataDate': '2026-11-18',
                       'generatedAt': '2026-11-18T08:00:00+08:00',
                       'files': {name: fingerprint((source / name).read_bytes()) for name in assets}}
            (source / 'release.json').write_text(json.dumps(release))
            output = Path(temporary) / 'domestic'
            result = build_domestic(source, output)
            validate_site(output)
            self.assertEqual(result['version'], 'cn1-source-1')
            for name in assets.keys() - {'index.html'}:
                self.assertEqual((source / name).read_bytes(), (output / name).read_bytes())
            index = (output / 'index.html').read_text()
            self.assertIn('href="#public-updates"', index)
            self.assertIn('数据日期 2026-11-18', index)
            self.assertIn('snapshot-perf-001.js?release=cn1-source-1', index)
            self.assertNotIn('href="/updates"', index)
            self.assertNotIn('target="_blank"', index)
            self.assertNotIn('pf1-', index)

    def test_changed_update_link_requires_review(self):
        with self.assertRaises(ValueError):
            domestic_index('<html><body>changed</body></html>', {})


if __name__ == '__main__':
    unittest.main()
