import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from snapshot_assets import read_snapshot, write_snapshot


class SnapshotAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'index.html').write_text('<script src="snapshot.js"></script>')

    def snapshot(self):
        funds = [{'code': str(i).zfill(6), 'name': '基金' * 20,
                  'inceptionMeta': {'sourceUrl': 'https://example.com/' + str(i)}} for i in range(100)]
        return {'meta': {'directoryCount': len(funds)}, 'funds': funds,
                'perf': {f['code']: {'scale': 0, 'ytd': -1.2} for f in funds},
                'details': {'000001': {'history': [1, 2, 3]}}, 'realtime': {}}

    def test_lossless_multibyte_shards_and_browser_execution(self):
        value = self.snapshot()
        files = write_snapshot(self.root, value, limit=1000)
        self.assertEqual(read_snapshot(self.root), value)
        self.assertTrue(all(p.stat().st_size < 1000 for p in self.root.glob('*.js')))
        node = shutil.which('node')
        if node:
            code = "const fs=require('fs'),vm=require('vm');let c={window:{}};vm.createContext(c);for(const n of JSON.parse(process.argv[2]))vm.runInContext(fs.readFileSync(process.argv[1]+'/'+n,'utf8'),c);console.log(JSON.stringify(c.window.MARKET_SNAPSHOT));"
            raw = subprocess.check_output([node, '-e', code, str(self.root), json.dumps(['snapshot.js'] + files)], text=True)
            self.assertEqual(json.loads(raw), value)

    def test_reads_existing_published_format(self):
        value = self.snapshot()
        main = {**value, 'perf': {}}
        (self.root / 'snapshot.js').write_text('window.MARKET_SNAPSHOT=' + json.dumps(main) + ';')
        (self.root / 'snapshot-perf-001.js').write_text('Object.assign(window.MARKET_SNAPSHOT.perf,' + json.dumps(value['perf']) + ');')
        self.assertEqual(read_snapshot(self.root), value)

    def test_removes_obsolete_chunks_after_smaller_rebuild(self):
        value = self.snapshot()
        write_snapshot(self.root, value, limit=1000)
        files = write_snapshot(self.root, value)
        self.assertEqual(sorted(p.name for p in self.root.glob('snapshot-perf-*.js')), files)
        self.assertEqual(read_snapshot(self.root), value)

    def test_missing_and_duplicate_chunks_fail(self):
        value = self.snapshot()
        files = write_snapshot(self.root, value, limit=1000)
        first = self.root / files[0]
        second = self.root / files[1]
        second.write_bytes(first.read_bytes())
        with self.assertRaises(ValueError):
            read_snapshot(self.root)
        first.unlink()
        with self.assertRaises(ValueError):
            read_snapshot(self.root)

    def test_oversized_record_does_not_replace_previous_snapshot(self):
        value = self.snapshot()
        write_snapshot(self.root, value)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        value['funds'][0]['name'] = 'x' * 4000
        with self.assertRaises(ValueError):
            write_snapshot(self.root, value, limit=1000)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)


if __name__ == '__main__':
    unittest.main()
