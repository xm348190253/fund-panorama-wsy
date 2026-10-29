#!/usr/bin/env python3
"""Run one complete daily refresh; publish only after the full directory is processed.

Run manually with: python3 scripts/update_all.py
This command does not install a scheduler. Failed runs retain their checkpoints
for resumption. A failed build or verification restores the prior website files.
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('Asia/Shanghai')


def run(command):
    print('\nRunning: ' + ' '.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=ROOT, check=True)


def complete_collection(as_of):
    directory = json.loads((ROOT / 'source-cache/current-directory.json').read_text())
    codes = {row[0] for row in directory['rows']}
    folder = ROOT / 'source-cache' / ('backfill-' + as_of.replace('-', ''))
    progress = json.loads((folder / 'progress.json').read_text())
    manifest = json.loads((folder / 'manifest.json').read_text())
    if directory['asOf'] != as_of or progress['asOf'] != as_of or manifest['asOf'] != as_of:
        raise ValueError('Directory and collection dates disagree')
    if not progress.get('finishedAt') or progress['completed'] != len(codes) or progress['targetCount'] != len(codes):
        raise ValueError('Full collection did not finish; website remains unchanged')
    if set(manifest['codes']) != codes or any(not (folder / 'records' / (code + '.json')).exists() for code in codes):
        raise ValueError('Full directory checkpoints are missing; website remains unchanged')
    base = json.loads((ROOT / 'source-cache' / ('base-refresh-' + as_of.replace('-', '') + '.json')).read_text())
    if base['asOf'] != as_of or base['directoryCount'] != len(codes):
        raise ValueError('Base returns and directory disagree')
    if not base['integrity']['ranking']['complete'] or not base['integrity']['money']['complete']:
        raise ValueError('Batch returns have incomplete pagination; website remains unchanged')
    print(f'Processed every directory code: {len(codes)}; source failures: {progress["failed"]}.', flush=True)


def publish_with_rollback(commands):
    release_paths = ['dist', '公募基金_本地离线版.html', '公募基金_领导分享版.html', 'docs/data-audit.json',
                     'docs/detail-evidence.jsonl', 'docs/coverage-gaps.json',
                     'docs/inception-audit.json', 'docs/inception-audit.md']
    with tempfile.TemporaryDirectory(prefix='fund-panorama-release-') as folder:
        backup = Path(folder)
        existed = set()
        for relative in release_paths:
            source, target = ROOT / relative, backup / relative
            if source.exists():
                existed.add(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
        try:
            for command in commands:
                run(command)
        except BaseException:
            for relative in release_paths:
                target, source = ROOT / relative, backup / relative
                if target.is_dir():
                    shutil.rmtree(target)
                elif target.exists():
                    target.unlink()
                if relative in existed:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if source.is_dir():
                        shutil.copytree(source, target)
                    else:
                        shutil.copy2(source, target)
            print('Build/verification failed; previous website files restored.', flush=True)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=8, choices=range(1, 17), metavar='1..16')
    parser.add_argument('--node', default='node', help='Node executable used by existing checks')
    parser.add_argument('--dry-run', action='store_true', help='Print the sequence without changing files')
    args = parser.parse_args()
    as_of = dt.datetime.now(TZ).date().isoformat()
    python = sys.executable
    collection = [[python, 'scripts/refresh_directory.py'],
                  [python, 'scripts/update_market_total.py'],
                  [python, 'scripts/refresh_market_base.py'],
                  [python, 'scripts/refresh_fund_profiles.py', '--as-of', as_of,
                   '--workers', str(min(args.workers, 8)), '--retry-failed'],
                  [python, 'scripts/backfill_market.py', '--directory', 'source-cache/current-directory.json',
                   '--as-of', as_of, '--workers', str(args.workers), '--retry-failed'],
                  [python, 'scripts/test_backfill_market.py'], [python, 'scripts/test_snapshot_merge.py'],
                  [python, 'scripts/test_market_sources.py'],
                  [python, 'scripts/test_refresh_fund_profiles.py'],
                  [python, 'scripts/test_inception_metadata.py']]
    release = [[python, 'scripts/refresh_fund_profiles.py', '--as-of', as_of, '--audit-only', '--write-audit'],
               [python, 'scripts/build_full_snapshot.py', '--as-of', as_of],
               [python, 'scripts/package_local.py'],
               [args.node, 'scripts/verify_logic.cjs'], [args.node, 'scripts/verify_snapshot.cjs']]
    if args.dry_run:
        for command in collection + release:
            print(' '.join(command))
        print('Full-directory completion and batch-count gates run before building; failed release checks restore prior website files.')
        return
    if not shutil.which(args.node):
        parser.error('Node was not found; provide --node /absolute/path/to/node')
    for command in collection:
        run(command)
    complete_collection(as_of)
    publish_with_rollback(release)
    print('Daily refresh, full-directory processing, packaging, and validation completed.', flush=True)


if __name__ == '__main__':
    main()
