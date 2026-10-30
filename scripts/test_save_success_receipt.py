"""No network: exercise receipt saves against a temporary local bare remote."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import save_success_receipt as saver


def run(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='receipt-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote, self.primary, self.writer = [self.root / name for name in ('remote.git', 'primary', 'writer')]
        run(self.root, 'init', '--bare', '--initial-branch=main', str(self.remote))
        run(self.root, 'clone', str(self.remote), str(self.primary))
        self.configure(self.primary)
        (self.primary / 'source.txt').write_text('original source\n')
        run(self.primary, 'add', 'source.txt')
        run(self.primary, 'commit', '-m', 'Initial source')
        run(self.primary, 'push', 'origin', 'main')
        run(self.root, 'clone', str(self.remote), str(self.writer))
        self.configure(self.writer)
        self.receipt = self.primary / 'last-success.json'
        self.receipt.write_text(json.dumps({'status': 'success', 'verified': True, 'version': 'test-version'}) + '\n')
        # An independently staged source edit must stay untouched throughout saves.
        (self.primary / 'source.txt').write_text('staged user change\n')
        run(self.primary, 'add', 'source.txt')
        (self.primary / 'notes.txt').write_text('untracked user note\n')
        self.before = self.primary_state()

    def configure(self, repo):
        run(repo, 'config', 'user.name', 'Local test')
        run(repo, 'config', 'user.email', 'test@example.invalid')

    def primary_state(self):
        paths = [p for p in self.primary.iterdir() if p.is_file()]
        return {'head': run(self.primary, 'rev-parse', 'HEAD'),
                'status': run(self.primary, 'status', '--porcelain=v1'),
                'index': run(self.primary, 'write-tree'),
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}

    def advance_remote(self, name='new-source.txt'):
        run(self.writer, 'pull', '--ff-only', 'origin', 'main')
        (self.writer / name).write_text('remote code change\n')
        run(self.writer, 'add', name)
        run(self.writer, 'commit', '-m', 'Concurrent code change')
        run(self.writer, 'push', 'origin', 'main')
        return run(self.writer, 'rev-parse', 'HEAD')

    def assert_preserved_and_saved(self):
        self.assertEqual(self.primary_state(), self.before)
        remote_receipt = run(self.remote, 'show', 'main:last-success.json')
        self.assertEqual(json.loads(remote_receipt), json.loads(self.receipt.read_text()))
        self.assertEqual(run(self.remote, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'main'), 'last-success.json')
        worktrees = run(self.primary, 'worktree', 'list', '--porcelain')
        self.assertEqual(worktrees.count('worktree '), 1)

    def test_normal_save_preserves_primary_head_index_and_files(self):
        result = saver.save_receipt(self.primary, self.receipt, retry_delay=0)
        self.assertEqual(result['attempts'], 1)
        self.assertTrue(result['changed'])
        self.assert_preserved_and_saved()

    def test_stale_head_uses_new_remote_main(self):
        remote_base = self.advance_remote()
        result = saver.save_receipt(self.primary, self.receipt, retry_delay=0)
        self.assertEqual(run(self.remote, 'rev-parse', 'main^'), remote_base)
        self.assertEqual(run(self.remote, 'show', 'main:new-source.txt'), 'remote code change')
        self.assertEqual(result['attempts'], 1)
        self.assert_preserved_and_saved()

    def test_push_race_fetches_again_without_overwriting_remote_change(self):
        original = saver.git
        pushes = 0
        def race(repo, *args, **kwargs):
            nonlocal pushes
            if args and args[0] == 'push':
                pushes += 1
                if pushes == 1:
                    self.advance_remote('racing-source.txt')
            return original(repo, *args, **kwargs)
        with mock.patch.object(saver, 'git', side_effect=race):
            result = saver.save_receipt(self.primary, self.receipt, retry_delay=0)
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(pushes, 2)
        self.assertEqual(run(self.remote, 'show', 'main:racing-source.txt'), 'remote code change')
        self.assert_preserved_and_saved()

    def test_fetch_retry_and_identical_receipt_noop(self):
        original = saver.git
        fetches = 0
        def flaky(repo, *args, **kwargs):
            nonlocal fetches
            if args and args[0] == 'fetch':
                fetches += 1
                if fetches == 1:
                    raise saver.GitFailure('fetch', 128)
            return original(repo, *args, **kwargs)
        with mock.patch.object(saver, 'git', side_effect=flaky):
            self.assertEqual(saver.save_receipt(self.primary, self.receipt, retry_delay=0)['attempts'], 2)
        before = run(self.remote, 'rev-parse', 'main')
        result = saver.save_receipt(self.primary, self.receipt, retry_delay=0)
        self.assertFalse(result['changed'])
        self.assertEqual(run(self.remote, 'rev-parse', 'main'), before)
        self.assert_preserved_and_saved()

    def test_push_retries_are_bounded_and_cleanup_worktrees(self):
        original = saver.git
        pushes = 0
        def reject(repo, *args, **kwargs):
            nonlocal pushes
            if args and args[0] == 'push':
                pushes += 1
                raise saver.GitFailure('push', 1)
            return original(repo, *args, **kwargs)
        with mock.patch.object(saver, 'git', side_effect=reject), self.assertRaisesRegex(RuntimeError, 'after 2 attempts'):
            saver.save_receipt(self.primary, self.receipt, attempts=2, retry_delay=0)
        self.assertEqual(pushes, 2)
        self.assertEqual(self.primary_state(), self.before)
        self.assertEqual(run(self.primary, 'worktree', 'list', '--porcelain').count('worktree '), 1)

    def test_failed_or_unverified_receipts_do_not_invoke_git(self):
        remote_before = run(self.remote, 'rev-parse', 'main')
        for payload in ({'status': 'failed', 'verified': True},
                        {'status': 'success', 'verified': False},
                        {'status': 'success'},
                        {'status': 'success', 'verified': 'true'}):
            with self.subTest(payload=payload):
                self.receipt.write_text(json.dumps(payload))
                before = self.primary_state()
                with mock.patch.object(saver, 'git') as mocked, self.assertRaises(ValueError):
                    saver.save_receipt(self.primary, self.receipt, retry_delay=0)
                mocked.assert_not_called()
                self.assertEqual(self.primary_state(), before)
                self.assertEqual(run(self.remote, 'rev-parse', 'main'), remote_before)

    def test_detached_shallow_checkout_preserves_primary(self):
        self.advance_remote('shallow-source.txt')
        raw = self.receipt.read_bytes()
        self.primary = self.root / 'shallow-primary'
        # file:// makes Git honor --depth using only the local filesystem.
        run(self.root, 'clone', '--depth=1', self.remote.as_uri(), str(self.primary))
        self.configure(self.primary)
        run(self.primary, 'checkout', '--detach')
        (self.primary / 'source.txt').write_text('staged shallow checkout change\n')
        run(self.primary, 'add', 'source.txt')
        (self.primary / 'notes.txt').write_text('untracked shallow checkout note\n')
        self.receipt = self.primary / 'last-success.json'
        self.receipt.write_bytes(raw)
        self.before = self.primary_state()
        self.assertEqual(run(self.primary, 'rev-parse', '--is-shallow-repository'), 'true')
        self.assertEqual(saver.git(self.primary, 'symbolic-ref', '--quiet', 'HEAD', allowed=(0, 1)).returncode, 1)
        result = saver.save_receipt(self.primary, self.receipt, retry_delay=0)
        self.assertTrue(result['changed'])
        self.assert_preserved_and_saved()


if __name__ == '__main__':
    unittest.main()
