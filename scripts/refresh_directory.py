#!/usr/bin/env python3
"""Refresh and validate the entire public fund/share-class directory atomically."""
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from backfill_market import atomic_json, download

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('Asia/Shanghai')


def parse_directory(raw):
    text = raw.decode('utf-8-sig').strip()
    match = re.match(r'var\s+r\s*=\s*', text)
    if not match:
        raise ValueError('Directory response does not begin with var r')
    rows, end = json.JSONDecoder().raw_decode(text, match.end())
    if text[end:].strip() != ';' or not isinstance(rows, list) or not rows:
        raise ValueError('Incomplete directory response')
    codes = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != 5 or not all(isinstance(value, str) for value in row):
            raise ValueError('Unexpected directory row structure')
        if not re.fullmatch(r'\d{6}', row[0]) or not row[2].strip():
            raise ValueError('Invalid fund code or missing name')
        if row[0] in codes:
            raise ValueError('Duplicate directory code: ' + row[0])
        codes.add(row[0])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Validate an already downloaded response without downloading again')
    parser.add_argument('--output', type=Path, default=ROOT / 'source-cache/current-directory.json')
    args = parser.parse_args()
    today = dt.datetime.now(TZ).date().isoformat()
    if args.input:
        raw = args.input.read_bytes()
        retrieved_at = dt.datetime.fromtimestamp(args.input.stat().st_mtime, TZ).isoformat(timespec='seconds')
        today = retrieved_at[:10]
        status, requests = None, 0
    else:
        # The downloader follows every Content-Range continuation and checks its
        # offset, total length, and size before this semantic validation.
        url = 'https://fund.eastmoney.com/js/fundcode_search.js?v=' + today.replace('-', '')
        raw, status, requests = download(url, timeout=30, max_bytes=16 * 1024 * 1024)
        retrieved_at = dt.datetime.now(TZ).isoformat(timespec='seconds')
    url = 'https://fund.eastmoney.com/js/fundcode_search.js?v=' + today.replace('-', '')
    rows = parse_directory(raw)
    digest = hashlib.sha256(raw).hexdigest()
    cache = ROOT / 'source-cache/directory'
    cache.mkdir(parents=True, exist_ok=True)
    raw_path = cache / (today + '-' + digest[:16] + '.js')
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    previous_count = None
    if args.output.exists():
        previous_count = len(json.loads(args.output.read_text())['rows'])
    result = {'asOf': today, 'url': url, 'sha256': digest, 'bytes': len(raw),
              'retrievedAt': retrieved_at, 'sourceFile': str(raw_path.relative_to(ROOT)),
              'sourceMode': 'existing_raw' if args.input else 'network',
              'httpStatus': status, 'requests': requests, 'rowCount': len(rows),
              'previousRowCount': previous_count, 'rows': rows}
    atomic_json(args.output, result)
    print(json.dumps({k: result[k] for k in ('asOf', 'rowCount', 'previousRowCount', 'bytes', 'sha256', 'sourceFile')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
