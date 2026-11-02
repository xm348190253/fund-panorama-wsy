#!/usr/bin/env python3
"""Choose daily fund collection or a due Beijing-time index refresh slot."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')
INDEX_HOURS = (10, 12, 14, 16)


def already_updated(receipt, today, force=False):
    return (not force and isinstance(receipt, dict)
            and receipt.get('status') == 'success' and receipt.get('verified') is True
            and receipt.get('dataDate') == today)


def choose_update(receipt, now, force=False, requested_quotes_only=False):
    now = now.astimezone(TZ)
    today = now.date().isoformat()
    if force:
        return True, requested_quotes_only, '管理员立即更新：' + ('仅指数行情' if requested_quotes_only else '基金与指数')
    if now.hour < 8:
        return False, False, '北京时间尚未到08:00，等待当日更新。'
    if not already_updated(receipt, today) and not requested_quotes_only:
        return True, False, '开始当日基金全量采集及指数更新：' + today
    due = [hour for hour in INDEX_HOURS if hour <= now.hour]
    if not due:
        return False, True, '当日基金数据已更新，等待10:00指数更新时段。'
    slot = now.replace(hour=due[-1], minute=0, second=0, microsecond=0)
    collected = None
    if isinstance(receipt, dict) and receipt.get('status') == 'success' and receipt.get('verified') is True:
        try:
            collected = dt.datetime.fromisoformat(receipt.get('indexQuotesCollectedAt', ''))
            if collected.tzinfo is None:
                collected = None
        except (ValueError, TypeError):
            pass
    if collected is not None and slot <= collected <= now:
        return False, True, slot.strftime('%Y-%m-%d %H:%M') + ' 时段的指数已成功采集并发布，跳过重复更新。'
    return True, True, '仅更新指数行情，覆盖北京时间 ' + slot.strftime('%Y-%m-%d %H:%M') + ' 时段。'


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
    now = dt.datetime.now(TZ)
    today = now.date().isoformat()
    force = os.environ.get('FORCE_REFRESH', '').lower() == 'true'
    requested_quotes_only = os.environ.get('REQUEST_QUOTES_ONLY', '').lower() == 'true'
    proceed, quotes_only, reason = choose_update(latest_receipt(), now, force, requested_quotes_only)
    if args.preflight:
        active = earlier_active(active_runs(os.environ['GITHUB_REPOSITORY'],
                                           os.environ['GH_TOKEN']), os.environ['GITHUB_RUN_ID'])
        if active:
            proceed = False
            reason = '已有更新任务运行或排队，复用该次更新：' + active[0]['html_url']
    print(json.dumps({'proceed': proceed, 'quotesOnly': quotes_only, 'dataDate': today, 'reason': reason}, ensure_ascii=False))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('proceed=' + str(proceed).lower() + '\n')
            output.write('quotes_only=' + str(quotes_only).lower() + '\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write('### 云端更新检查\n\n' + reason + '\n')


if __name__ == '__main__':
    main()
