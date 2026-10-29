#!/usr/bin/env python3
"""Offline tests; never contact ModelScope or read real credentials."""
import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import modelscope_sync as sync

TOKEN = 'fake-secret-for-tests-only'


class ModelScopeSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.site = self.root / 'site'
        self.site.mkdir()
        names = sync.REQUIRED_ASSETS | {'snapshot-perf-001.js'}
        for name in names:
            (self.site / name).write_bytes(('fixture:' + name).encode())
        self.release = {'version': '20261029-run-123-1', 'files': {
            name: {'sha256': sync.digest((self.site / name).read_bytes())} for name in sorted(names)}}
        self.write_release()
        self.info = {'id': sync.DEFAULT_REPO, 'sdk_type': 'static',
                     'hardware': 'platform/2v-cpu-8g-mem',
                     'host': 'https://wangshuyang2126-fund-panorama-wsy.ms.show',
                     'runtime': {'status': 'Running'}}

    def write_release(self):
        (self.site / 'release.json').write_text(json.dumps(self.release))

    def test_manifest_valid_and_tampered_asset(self):
        release, hashes = sync.validate_site(self.site)
        self.assertEqual(release, self.release)
        self.assertEqual(len(hashes), 5)
        (self.site / 'index.html').write_text('tampered')
        with self.assertRaisesRegex(sync.SyncError, 'checksum mismatch'):
            sync.validate_site(self.site)

    def test_manifest_cannot_take_ownership_of_configuration(self):
        self.release['files']['ms_deploy.json'] = '0' * 64
        self.write_release()
        with self.assertRaisesRegex(sync.SyncError, 'unowned asset'):
            sync.validate_site(self.site)

    def test_symlink_and_unlisted_assets_rejected(self):
        (self.site / 'snapshot-perf-002.js').write_text('unlisted')
        with self.assertRaisesRegex(sync.SyncError, 'Unlisted'):
            sync.validate_site(self.site)
        (self.site / 'snapshot-perf-002.js').unlink()
        (self.site / 'market.js').unlink()
        (self.site / 'market.js').symlink_to(self.site / 'index.html')
        with self.assertRaisesRegex(sync.SyncError, 'symlink'):
            sync.validate_site(self.site)

    def test_secret_redaction(self):
        encoded = base64.b64encode(('oauth2:' + TOKEN).encode()).decode()
        redacted = sync.redact(TOKEN + ' ' + encoded + ' https://oauth2:other@modelscope.cn Bearer test', TOKEN)
        self.assertNotIn(TOKEN, redacted)
        self.assertNotIn(encoded, redacted)
        self.assertNotIn('oauth2:other', redacted)
        self.assertNotIn('Bearer test', redacted)

    def test_no_secret_in_git_url_or_askpass_file(self):
        checkout = sync.StudioCheckout(self.root, sync.DEFAULT_REPO, TOKEN)
        self.assertNotIn(TOKEN, (self.root / 'git-askpass.sh').read_text())
        fake = SimpleNamespace(returncode=0, stdout='', stderr='')
        with patch.object(sync.subprocess, 'run', return_value=fake) as run:
            checkout.clone()
        args, kwargs = run.call_args
        self.assertNotIn(TOKEN, ' '.join(args[0]))
        self.assertIn('https://modelscope.cn/studios/' + sync.DEFAULT_REPO + '.git', args[0])
        self.assertEqual(kwargs['env']['MODELSCOPE_API_KEY'], TOKEN)
        self.assertEqual(kwargs['env']['GIT_TERMINAL_PROMPT'], '0')
        self.assertIn('credential.helper=', args[0])
        self.assertIn('--depth', args[0])
        self.assertEqual(args[0][args[0].index('--depth') + 1], '1')
        self.assertIn('--no-tags', args[0])

    def test_post_has_no_body(self):
        client = sync.Client(sync.DEFAULT_REPO, TOKEN)
        client.api_opener.open = Mock(return_value=io.BytesIO(b'{"success":true,"data":{"status":"Building"}}'))
        self.assertEqual(client.api('POST', '/deploy')['status'], 'Building')
        request = client.api_opener.open.call_args.args[0]
        self.assertEqual(request.method, 'POST')
        self.assertIsNone(request.data)
        self.assertEqual(request.full_url, sync.API_BASE + '/studios/' + sync.DEFAULT_REPO + '/deploy')

    def test_deploy_accepts_success_acknowledgement_without_object_data(self):
        client = sync.Client(sync.DEFAULT_REPO, TOKEN)
        for response in ({'success': True}, {'success': True, 'data': None},
                         {'success': True, 'data': True}):
            with self.subTest(response=response):
                client.api_opener.open = Mock(return_value=io.BytesIO(json.dumps(response).encode()))
                self.assertEqual(client.api('POST', '/deploy'), {})
        client.api_opener.open = Mock(return_value=io.BytesIO(b'{"success":false,"data":{}}'))
        with self.assertRaisesRegex(sync.SyncError, 'unsuccessful'):
            client.api('POST', '/deploy')

    def test_get_still_requires_object_data(self):
        client = sync.Client(sync.DEFAULT_REPO, TOKEN)
        for response in ({'success': True}, {'success': True, 'data': None},
                         {'success': True, 'data': True}, {'success': True, 'data': []}):
            with self.subTest(response=response):
                client.api_opener.open = Mock(return_value=io.BytesIO(json.dumps(response).encode()))
                with self.assertRaisesRegex(sync.SyncError, 'malformed'):
                    client.api()

    def test_refuses_paid_hardware_and_other_hosts(self):
        client = sync.Client(sync.DEFAULT_REPO, TOKEN)
        self.assertEqual(client.verify_configuration(self.info), self.info['host'])
        with self.assertRaisesRegex(sync.SyncError, 'hardware'):
            client.verify_configuration(dict(self.info, hardware='paid/ecs.gpu'))
        with self.assertRaisesRegex(sync.SyncError, 'unexpected runtime host'):
            client.verify_configuration(dict(self.info, host='https://example.com'))

    def test_sync_preserves_settings_and_removes_only_obsolete_shards(self):
        checkout = sync.StudioCheckout(self.root, sync.DEFAULT_REPO, TOKEN)
        checkout.path.mkdir()
        originals = {'ms_deploy.json': '{"hardware":"keep"}', 'README.md': 'keep README',
                     'custom.txt': 'keep custom', 'snapshot-perf-extra.js': 'unowned filename'}
        for name, value in originals.items():
            (checkout.path / name).write_text(value)
        (checkout.path / 'snapshot-perf-999.js').write_text('obsolete')
        calls = []
        def git(*args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=1 if args[0] == 'diff' else 0, stdout='', stderr='')
        checkout.git = git
        checkout.sync(self.site, sorted(set(self.release['files']) | {'release.json'}))
        for name, value in originals.items():
            self.assertEqual((checkout.path / name).read_text(), value)
        self.assertFalse((checkout.path / 'snapshot-perf-999.js').exists())
        self.assertEqual((checkout.path / 'index.html').read_bytes(), (self.site / 'index.html').read_bytes())
        added = next(call for call in calls if call[0] == 'add')
        self.assertNotIn('README.md', added)
        self.assertNotIn('ms_deploy.json', added)

    def test_remote_dangling_symlink_is_rejected(self):
        checkout = sync.StudioCheckout(self.root, sync.DEFAULT_REPO, TOKEN)
        checkout.path.mkdir()
        (checkout.path / 'index.html').symlink_to(self.root / 'missing')
        with self.assertRaisesRegex(sync.SyncError, 'non-regular'):
            checkout.sync(self.site, sorted(set(self.release['files']) | {'release.json'}))
        self.assertFalse((self.root / 'missing').exists())

    def test_bootstrap_changes_only_baseline(self):
        dist = self.root / 'dist'
        dist.mkdir()
        for name in ('index.html', 'market.js', 'echarts.min.js', 'snapshot.js', 'snapshot-perf-999.js'):
            (dist / name).write_text('old:' + name)
        source = self.root / 'remote'
        source.mkdir()
        (source / 'snapshot.js').write_text('new snapshot')
        (source / 'snapshot-perf-001.js').write_text('new shard')
        (source / 'echarts.min.js').write_text('new chart library')
        (source / 'index.html').write_text('must not copy')
        with patch.object(sync, 'ROOT', self.root), patch.object(sync.StudioCheckout, 'clone', return_value=source):
            sync.bootstrap(SimpleNamespace(repo=sync.DEFAULT_REPO, dist=dist), TOKEN)
        self.assertEqual((dist / 'index.html').read_text(), 'old:index.html')
        self.assertEqual((dist / 'market.js').read_text(), 'old:market.js')
        self.assertEqual((dist / 'snapshot.js').read_text(), 'new snapshot')
        self.assertEqual((dist / 'echarts.min.js').read_text(), 'new chart library')
        self.assertFalse((dist / 'snapshot-perf-999.js').exists())
        self.assertEqual(list((self.root / '.temp').iterdir()), [])

    def test_bootstrap_copy_failure_restores_chart_and_snapshots(self):
        dist, source = self.root / 'dist', self.root / 'remote'
        dist.mkdir()
        source.mkdir()
        originals = {'snapshot.js': 'old snapshot', 'snapshot-perf-999.js': 'old shard',
                     'echarts.min.js': 'old chart library'}
        for name, value in originals.items():
            (dist / name).write_text(value)
        for name in ('snapshot.js', 'snapshot-perf-001.js', 'echarts.min.js'):
            (source / name).write_text('new:' + name)
        original_copy = sync.shutil.copyfile
        def fail_chart_copy(src, dest, **kwargs):
            if Path(src) == source / 'echarts.min.js':
                Path(dest).write_text('incomplete chart')
                raise OSError('simulated disk write failure')
            return original_copy(src, dest, **kwargs)
        with patch.object(sync, 'ROOT', self.root), patch.object(sync.StudioCheckout, 'clone', return_value=source), patch.object(sync.shutil, 'copyfile', side_effect=fail_chart_copy):
            with self.assertRaisesRegex(OSError, 'simulated'):
                sync.bootstrap(SimpleNamespace(repo=sync.DEFAULT_REPO, dist=dist), TOKEN)
        self.assertEqual({p.name: p.read_text() for p in dist.iterdir()}, originals)

    def test_bootstrap_rejects_empty_or_symlink_chart_before_changes(self):
        dist, source = self.root / 'dist', self.root / 'remote'
        dist.mkdir()
        source.mkdir()
        (dist / 'echarts.min.js').write_text('old chart library')
        (dist / 'snapshot.js').write_text('old snapshot')
        (source / 'snapshot.js').write_text('new snapshot')
        (source / 'snapshot-perf-001.js').write_text('new shard')
        for use_symlink in (False, True):
            chart = source / 'echarts.min.js'
            chart.unlink(missing_ok=True)
            if use_symlink:
                chart.symlink_to(source / 'snapshot.js')
            else:
                chart.write_bytes(b'')
            with patch.object(sync, 'ROOT', self.root), patch.object(sync.StudioCheckout, 'clone', return_value=source):
                with self.assertRaisesRegex(sync.SyncError, 'incomplete'):
                    sync.bootstrap(SimpleNamespace(repo=sync.DEFAULT_REPO, dist=dist), TOKEN)
            self.assertEqual((dist / 'echarts.min.js').read_text(), 'old chart library')
            self.assertEqual((dist / 'snapshot.js').read_text(), 'old snapshot')

    def test_live_verification_requires_version_and_all_asset_hashes(self):
        client = sync.Client(sync.DEFAULT_REPO, TOKEN)
        _, hashes = sync.validate_site(self.site)
        def public(url, *args, **kwargs):
            name = sync.urllib.parse.urlparse(url).path.lstrip('/')
            return (self.site / name).read_bytes()
        client.public_bytes = public
        client.verify_live(self.info['host'], self.release, hashes)
        (self.site / 'market.js').write_text('bad deployed content')
        with self.assertRaisesRegex(sync.SyncError, 'checksum mismatch'):
            client.verify_live(self.info['host'], self.release, hashes)
        self.release['version'] = 'old-version'
        self.write_release()
        with self.assertRaisesRegex(sync.SyncError, 'previous release'):
            client.verify_live(self.info['host'], dict(self.release, version='expected-new-version'), hashes)

    def test_running_old_release_does_not_succeed(self):
        client = sync.Client(sync.DEFAULT_REPO, TOKEN)
        client.api = Mock(return_value=self.info)
        client.verify_live = Mock(side_effect=[sync.SyncError('previous release'), None])
        with patch.object(sync.time, 'sleep'):
            info = client.wait_verified(self.release, {}, timeout=1, interval=.01)
        self.assertEqual(info, self.info)
        self.assertEqual(client.verify_live.call_count, 2)

    def test_terminal_deploy_failure_and_timeout(self):
        client = sync.Client(sync.DEFAULT_REPO, TOKEN)
        client.api = Mock(return_value=dict(self.info, runtime={'status': 'BuildFailed'}))
        with self.assertRaisesRegex(sync.SyncError, 'entered BuildFailed'):
            client.wait_verified(self.release, {}, timeout=1, interval=.01)
        client.api = Mock(return_value=dict(self.info, runtime={'status': 'Building'}))
        with patch.object(sync.time, 'monotonic', side_effect=[0, .1, .2, .3, .4]):
            with self.assertRaisesRegex(sync.SyncError, 'timed out'):
                client.wait_verified(self.release, {}, timeout=.25, interval=.01)

    def test_receipt_success_and_deployment_failure(self):
        args = SimpleNamespace(repo=sync.DEFAULT_REPO, site=self.site, receipt=self.root / 'receipt.json',
                               timeout=1800, poll_interval=30)
        checkout = Mock()
        checkout.git.return_value = SimpleNamespace(stdout='abcdef\n')
        checkout.sync.return_value = True
        client = Mock()
        client.api.return_value = self.info
        client.wait_verified.return_value = self.info
        with patch.object(sync, 'ROOT', self.root), patch.object(sync, 'StudioCheckout', return_value=checkout), patch.object(sync, 'Client', return_value=client):
            sync.publish(args, TOKEN)
        receipt = json.loads(args.receipt.read_text())
        self.assertEqual(receipt['status'], 'success')
        self.assertTrue(receipt['verified'])
        self.assertTrue(receipt['pushed'])
        self.assertTrue(receipt['deployRequested'])
        self.assertIn(('push', 'origin', 'HEAD:master'), [call.args for call in checkout.git.call_args_list])
        self.assertFalse(any('--force' in call.args for call in checkout.git.call_args_list))
        client.api.side_effect = [self.info, sync.SyncError('API error ' + TOKEN)]
        with patch.object(sync, 'ROOT', self.root), patch.object(sync, 'StudioCheckout', return_value=checkout), patch.object(sync, 'Client', return_value=client):
            with self.assertRaises(sync.SyncError):
                sync.publish(args, TOKEN)
        receipt = json.loads(args.receipt.read_text())
        self.assertEqual(receipt['status'], 'failed')
        self.assertTrue(receipt['pushed'])
        self.assertFalse(receipt['verified'])
        self.assertFalse(receipt['automaticRollback'])
        self.assertNotIn(TOKEN, args.receipt.read_text())


if __name__ == '__main__':
    unittest.main()
