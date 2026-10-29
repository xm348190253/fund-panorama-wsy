#!/usr/bin/env python3
"""Stop a cloud release if the new collection loses much of a verified baseline."""
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from package_local import snapshot_metadata

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('scale', 'manager', 'inceptionDate', 'dwjz', 'm1', 'y1', 'mdd', 'ytdMdd')


def compact(meta):
    return {'dataDate': meta['collection']['asOf'], 'directoryCount': meta['directoryCount'],
            'available': {name: meta['coverage'][name]['available']
                          for name in FIELDS if name in meta['coverage']}}


def check(old, new, today):
    problems = []
    if new['dataDate'] != today:
        problems.append('Collection date is not today in Asia/Shanghai')
    if new['directoryCount'] < old['directoryCount'] * .98:
        problems.append('Directory count fell by more than 2 percent')
    for name, previous in old['available'].items():
        if previous > 0 and new['available'].get(name, 0) < previous * .95:
            problems.append(name + ' available count fell by more than 5 percent')
    if problems:
        raise ValueError('; '.join(problems) + '; investigate the source before publishing')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    current = compact(snapshot_metadata(ROOT))
    if args.capture:
        args.baseline.write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n')
        print('Baseline coverage saved for release validation.')
    else:
        old = json.loads(args.baseline.read_text())
        today = dt.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        check(old, current, today)
        print(json.dumps({'status': 'PASS', 'dataDate': current['dataDate'],
                          'directoryCount': current['directoryCount'], 'available': current['available']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
