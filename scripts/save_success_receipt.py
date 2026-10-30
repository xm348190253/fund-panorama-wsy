#!/usr/bin/env python3
"""Commit only a verified receipt using an isolated checkout of the latest main.

The caller's HEAD, index and working files are never reset, staged or committed.
Git fetch/worktree metadata is shared so the existing checkout authentication can
be used without reading or copying credentials. Pushes are always fast-forward.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


class GitFailure(RuntimeError):
    def __init__(self, operation, returncode):
        super().__init__(f'git {operation} failed with exit code {returncode}')


def git(repo, *args, allowed=(0,)):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                'GIT_TRACE', 'GIT_TRACE_CURL', 'GIT_CURL_VERBOSE'):
        env.pop(key, None)
    try:
        result = subprocess.run(['git', '-C', str(repo), '-c', 'core.hooksPath=/dev/null', *args],
                                env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=120)
    except subprocess.TimeoutExpired as error:
        raise GitFailure(args[0], 'timeout') from error
    if result.returncode not in allowed:
        # Do not echo remote stderr: authenticated URLs may appear in Git errors.
        raise GitFailure(args[0], result.returncode)
    return result


def save_receipt(repo, receipt, attempts=3, retry_delay=1):
    if not 1 <= attempts <= 5 or retry_delay < 0:
        raise ValueError('Use 1–5 attempts and a nonnegative retry delay')
    repo, receipt = Path(repo).resolve(), Path(receipt).absolute()
    if receipt.is_symlink() or not receipt.is_file():
        raise ValueError('Receipt must be a regular file')
    raw = receipt.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('status') != 'success' or value.get('verified') is not True:
        raise ValueError('Only a successfully verified deployment receipt may be saved')
    git(repo, 'rev-parse', '--show-toplevel')
    last_error = None
    with tempfile.TemporaryDirectory(prefix='fund-receipt-worktree-') as temporary:
        for attempt in range(1, attempts + 1):
            worktree = Path(temporary) / f'attempt-{attempt}'
            added = False
            try:
                git(repo, 'fetch', '--no-tags', '--depth=1', 'origin',
                    '+refs/heads/main:refs/remotes/origin/main')
                base = git(repo, 'rev-parse', 'refs/remotes/origin/main').stdout.strip()
                git(repo, 'worktree', 'add', '--detach', str(worktree), base)
                added = True
                target = worktree / 'last-success.json'
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    raise ValueError('Remote receipt path is not a regular file')
                target.write_bytes(raw)
                git(worktree, 'add', '--', 'last-success.json')
                changed = git(worktree, 'diff', '--cached', '--quiet', allowed=(0, 1)).returncode == 1
                if not changed:
                    return {'status': 'success', 'attempts': attempt, 'changed': False,
                            'commit': base, 'version': value.get('version')}
                staged = git(worktree, 'diff', '--cached', '--name-only').stdout.splitlines()
                if staged != ['last-success.json']:
                    raise ValueError('Refusing to commit files other than the deployment receipt')
                git(worktree, '-c', 'user.name=github-actions[bot]',
                    '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                    'commit', '-m', 'Record verified dashboard update')
                commit = git(worktree, 'rev-parse', 'HEAD').stdout.strip()
                git(worktree, 'push', 'origin', 'HEAD:refs/heads/main')
                return {'status': 'success', 'attempts': attempt, 'changed': True,
                        'commit': commit, 'version': value.get('version')}
            except GitFailure as error:
                last_error = error
                if attempt < attempts:
                    print(f'Receipt save attempt {attempt}/{attempts} failed; refreshing main and retrying.', flush=True)
            finally:
                if added:
                    git(repo, 'worktree', 'remove', '--force', str(worktree))
            if attempt < attempts:
                time.sleep(retry_delay)
    raise RuntimeError(f'Receipt was not saved after {attempts} attempts ({last_error}). '
                       'Retry receipt saving only; the verified website deployment is unaffected.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--receipt', type=Path, default=Path('last-success.json'))
    parser.add_argument('--attempts', type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(save_receipt(args.repo, args.receipt, args.attempts), ensure_ascii=False))


if __name__ == '__main__':
    main()
