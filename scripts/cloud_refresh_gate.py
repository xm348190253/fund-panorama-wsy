#!/usr/bin/env python3
"""Deduplicate cloud collection by its data date, outside and inside the job lock."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from zoneinfo import ZoneInfo


def already_updated(receipt, today, force=False):
    return (not force and isinstance(receipt, dict)
            and receipt.get('status') == 'success' and receipt.get('verified') is True
            and receipt.get('dataDate') == today)


def earlier_active(runs, current_id):
    # Simultaneous preflights yield only to older runs, never to one another.
    return [r for r in runs if int(r['id']) < int(current_id)
            and r.get('status') in ('queued', 'in_progress', 'waiting', 'pending', 'requested')]


def latest_receipt():
    subprocess.run(['git', 'fetch', '--no-tags', '--depth=1', 'origin',
                    '+refs/heads/main:refs/remotes/origin/main'], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    result = subprocess.run(['git', 'show', 'refs/remotes/origin/main:last-success.json'],
                            capture_output=True, text=True)
    try:
        return json.loads(result.stdout) if result.returncode == 0 else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def active_runs(repository, token):
    runs = []
    for status in ('queued', 'in_progress', 'waiting', 'pending', 'requested'):
        url = ('https://api.github.com/repos/' + repository
               + '/actions/workflows/daily-modelscope.yml/runs?per_page=100&status=' + status)
        request = urllib.request.Request(url, headers={
            'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'fund-panorama-scheduler'})
        with urllib.request.urlopen(request, timeout=30) as response:
            runs.extend(json.load(response)['workflow_runs'])
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    today = dt.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    force = os.environ.get('FORCE_REFRESH', '').lower() == 'true'
    reason, proceed = '开始采集 ' + today, True
    if args.preflight:
        active = earlier_active(active_runs(os.environ['GITHUB_REPOSITORY'],
                                           os.environ['GH_TOKEN']), os.environ['GITHUB_RUN_ID'])
        if active:
            proceed = False
            reason = '已有更新任务运行或排队，复用该次更新：' + active[0]['html_url']
    if proceed and already_updated(latest_receipt(), today, force):
        proceed = False
        reason = today + ' 的云端数据已经成功发布，跳过重复采集。'
    print(json.dumps({'proceed': proceed, 'dataDate': today, 'reason': reason}, ensure_ascii=False))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('proceed=' + str(proceed).lower() + '\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write('### 云端更新检查\n\n' + reason + '\n')


if __name__ == '__main__':
    main()
