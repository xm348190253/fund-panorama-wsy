import json
import io
import zipfile
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlparse, parse_qs

import insurance_snapshot as snapshot


class InsuranceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'insurance-data'
        self.meta = {'version': '20261105T011720-2cb36d02', 'latest': '2026-09',
                     'months': ['2025-12', '2026-09'], 'updated': '2026-11-05T01:17:20Z'}
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        parsed = urlparse(url)
        self.assertEqual(parsed.netloc, urlparse(snapshot.ORIGIN).netloc)
        if parsed.path.endswith('/meta'):
            value = dict(self.meta)
        else:
            self.assertRegex(parsed.path, r'/api/insurance/period/20\d{2}-\d{2}$')
            self.assertEqual(parse_qs(parsed.query), {'version': [self.meta['version']]})
            value = {'month': parsed.path.rsplit('/', 1)[1], 'products': [], 'report': {}}
        return value, json.dumps(value).encode()

    def download(self, url):
        self.urls.append(url)
        parsed = urlparse(url)
        self.assertEqual(parsed.netloc, urlparse(snapshot.ORIGIN).netloc)
        self.assertEqual(parse_qs(parsed.query), {'version': [self.meta['version']]})
        self.assertRegex(parsed.path, r'/api/insurance/download/(?:database.xlsx|report-20\d{2}-\d{2}\.(?:docx|xlsx|zip))$')
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w') as archive:
            for name in (['report.docx', 'report.xlsx'] if parsed.path.endswith('.zip') else ['[Content_Types].xml']):
                info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                archive.writestr(info, 'test')
        return content.getvalue()

    def test_public_only_version_pinned_checksums_and_noop(self):
        manifest = snapshot.build_snapshot(self.root, self.fetch, self.download)
        checked, hashes = snapshot.validate_snapshot(self.root)
        self.assertEqual(checked, manifest)
        self.assertEqual(len(hashes), 11)
        self.assertEqual(set(manifest['files']), snapshot.names_for(manifest))
        self.assertEqual(snapshot.build_snapshot(self.root, self.fetch, self.download), manifest)
        self.assertTrue(all('/sources/' not in u and '/admin' not in u for u in self.urls))

    def test_failed_download_keeps_existing_manifest_and_history(self):
        first = snapshot.build_snapshot(self.root, self.fetch, self.download)
        old = (self.root / 'manifest.json').read_bytes()
        self.meta['version'] = '20261106T011720-aaaaaaaa'
        def failing(url):
            if '/period/' in url:
                raise OSError('upstream unavailable')
            return self.fetch(url)
        with self.assertRaises(OSError):
            snapshot.build_snapshot(self.root, failing, self.download)
        self.assertEqual((self.root / 'manifest.json').read_bytes(), old)
        self.assertTrue((self.root / first['version'] / 'meta.json').exists())
        snapshot.build_snapshot(self.root, self.fetch, self.download)
        self.assertTrue((self.root / first['version'] / 'meta.json').exists())
        self.assertEqual(snapshot.validate_snapshot(self.root)[0]['version'], self.meta['version'])

    def test_wrong_month_and_immutable_version_change_are_rejected(self):
        original = snapshot.build_snapshot(self.root, self.fetch, self.download)
        def bad_month(url):
            value, raw = self.fetch(url)
            if '/period/' in url:
                value['month'] = '2026-03'
                raw = json.dumps(value).encode()
            return value, raw
        with self.assertRaisesRegex(ValueError, 'different month'):
            snapshot.build_snapshot(self.root, bad_month, self.download)
        self.meta['updated'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'immutable'):
            snapshot.build_snapshot(self.root, self.fetch, self.download)
        self.assertEqual(snapshot.validate_snapshot(self.root)[0], original)

    def test_traversal_extra_file_checksum_and_symlink_rejected(self):
        manifest = snapshot.build_snapshot(self.root, self.fetch, self.download)
        for key, value in [('version', '../../private'), ('months', ['2026-99'])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                snapshot.validate_meta({**self.meta, key: value})
        manifest['files']['original-source.docx'] = {'bytes': 1, 'sha256': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            snapshot.validate_manifest(manifest)
        target = self.root / self.meta['version'] / 'period-2026-09.json'
        target.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            snapshot.validate_snapshot(self.root)
        target.unlink()
        target.symlink_to(self.root / 'manifest.json')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            snapshot.validate_snapshot(self.root)

    def test_check_compares_current_source_with_public_mirror(self):
        mirrored = snapshot.build_snapshot(self.root, self.fetch, self.download)
        def check_fetch(url):
            if url.startswith(snapshot.RUNTIME):
                return mirrored, json.dumps(mirrored).encode()
            return self.fetch(url)
        self.assertFalse(snapshot.needs_sync(check_fetch))
        self.meta['version'] = '20261106T011720-aaaaaaaa'
        self.assertTrue(snapshot.needs_sync(check_fetch))

    def test_existing_json_only_version_adds_exports_without_changing_data(self):
        full = snapshot.build_snapshot(self.root, self.fetch, self.download)
        previous = {**full, 'schema': 1, 'files': {n: v for n, v in full['files'].items() if n.endswith('.json')}}
        (self.root / 'manifest.json').write_text(json.dumps(previous))
        upgraded = snapshot.build_snapshot(self.root, self.fetch, self.download)
        self.assertEqual(upgraded['schema'], 2)
        self.assertEqual(upgraded['version'], previous['version'])
        for name, spec in previous['files'].items():
            self.assertEqual(upgraded['files'][name], spec)
        self.assertIn('database.xlsx', upgraded['files'])


if __name__ == '__main__':
    unittest.main()
