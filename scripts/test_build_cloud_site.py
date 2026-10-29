"""Cloud release integrity and safe replacement checks; no network requests."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from build_cloud_site import build, fingerprint, owned_output


class CloudSiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.dist = self.root / 'dist'
        self.dist.mkdir(parents=True)
        self.output = Path(self.temp.name) / 'site'
        self.node = shutil.which('node')
        if not self.node:
            self.skipTest('Node is required for JavaScript syntax validation')
        self.source(2)

    def source(self, count):
        funds = [{'code': f'{i:06d}'} for i in range(1, count + 1)]
        meta = {'directoryCount': count, 'collection': {'asOf': '2026-10-29', 'attempted': count}}
        snapshot = {'meta': meta, 'funds': funds, 'perf': {}}
        (self.dist / 'snapshot.js').write_text('window.MARKET_SNAPSHOT=' + json.dumps(snapshot) + ';\n')
        for path in self.dist.glob('snapshot-perf-*.js'):
            path.unlink()
        shards = []
        for index, fund in enumerate(funds, 1):
            name = f'snapshot-perf-{index:03d}.js'
            shards.append(f'<script src="{name}"></script>')
            (self.dist / name).write_text('Object.assign(window.MARKET_SNAPSHOT.perf,' +
                                          json.dumps({fund['code']: {}}) + ');\n')
        (self.dist / 'index.html').write_text('''<!doctype html>
<html><head><meta charset="UTF-8">
<script>window.__echartsTries = ['echarts.min.js'];</script></head>
<body>
<script src="snapshot.js"></script>
''' + '\n'.join(shards) + '\n<script src="market.js"></script>\n</body></html>')
        (self.dist / 'market.js').write_text('window.__FUND_OFFLINE__ = window.__FUND_OFFLINE__ || false;')
        (self.dist / 'echarts.min.js').write_text('window.echarts={};')

    def test_release_hashes_notice_and_source_preservation(self):
        before = {p.name: fingerprint(p) for p in self.dist.iterdir()}
        report = build(self.root, self.output, 'test-1', self.node)
        release = json.loads((self.output / 'release.json').read_text())
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(release['version'], 'test-1')
        self.assertEqual(release['dataDate'], '2026-10-29')
        self.assertTrue(release['generatedAt'].endswith('+08:00'))
        self.assertEqual(set(p.name for p in self.output.iterdir()), set(release['files']) | {'release.json'})
        for name, expected in release['files'].items():
            self.assertEqual(fingerprint(self.output / name), expected)
        html = (self.output / 'index.html').read_text()
        self.assertIn('数据快照 2026-10-29', html)
        self.assertIn('每天北京时间 08:00 由云端开始采集', html)
        self.assertIn('刷新读取最新已成功发布版本', html)
        self.assertEqual({p.name: fingerprint(p) for p in self.dist.iterdir()}, before)

    def test_owned_release_replaces_and_removes_old_shards(self):
        build(self.root, self.output, 'first', self.node)
        self.source(1)
        build(self.root, self.output, 'second', self.node)
        owned_output(self.output)
        self.assertFalse((self.output / 'snapshot-perf-002.js').exists())
        self.assertEqual(json.loads((self.output / 'release.json').read_text())['version'], 'second')

    def test_unknown_user_files_are_not_removed(self):
        self.output.mkdir()
        note = self.output / 'notes.txt'
        note.write_text('keep me')
        with self.assertRaises(ValueError):
            build(self.root, self.output, 'test', self.node)
        self.assertEqual(note.read_text(), 'keep me')

    def test_modified_owned_asset_is_not_overwritten(self):
        build(self.root, self.output, 'first', self.node)
        target = self.output / 'index.html'
        target.write_text('user change')
        with self.assertRaises(ValueError):
            build(self.root, self.output, 'second', self.node)
        self.assertEqual(target.read_text(), 'user change')

    def test_failed_syntax_check_keeps_previous_release(self):
        build(self.root, self.output, 'first', self.node)
        before = {p.name: fingerprint(p) for p in self.output.iterdir()}
        (self.dist / 'market.js').write_text('function (')
        with self.assertRaises(subprocess.CalledProcessError):
            build(self.root, self.output, 'second', self.node)
        self.assertEqual({p.name: fingerprint(p) for p in self.output.iterdir()}, before)

    def test_symbolic_link_output_is_rejected(self):
        elsewhere = Path(self.temp.name) / 'elsewhere'
        elsewhere.mkdir()
        self.output.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(ValueError):
            build(self.root, self.output, 'test', self.node)
        self.assertEqual(list(elsewhere.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
