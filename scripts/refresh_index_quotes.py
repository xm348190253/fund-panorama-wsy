#!/usr/bin/env python3
"""Collect the latest available public index quotes for a fixed cloud release."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('Asia/Shanghai')
SYMBOLS = [
    ('1.000001', '上证指数', 'CN'), ('1.000300', '沪深300', 'CN'),
    ('0.399006', '创业板指', 'CN'), ('1.000688', '科创50', 'CN'),
    ('100.HSI', '恒生指数', 'HK'), ('124.HSTECH', '恒生科技', 'HK'),
    ('100.SPX', '标普500', 'US'), ('100.NDX', '纳斯达克100', 'US'),
    ('100.DJIA', '道琼斯指数', 'US'),
]
SOURCE = '东方财富 push2'


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def quote_stamp(value, collected_at):
    """f124 is the quote epoch; f80/f86 are NOT dates in this endpoint."""
    epoch = number(value)
    if epoch is None or epoch < 946684800:
        return None
    if epoch > 1e12:
        epoch /= 1000
    try:
        stamp = dt.datetime.fromtimestamp(epoch, TZ)
    except (ValueError, OverflowError, OSError):
        return None
    if stamp > dt.datetime.fromisoformat(collected_at) + dt.timedelta(minutes=5):
        return None
    return stamp


def parse_response(payload, collected_at):
    data = payload.get('data') if isinstance(payload, dict) else None
    rows = data.get('diff') if isinstance(data, dict) else None
    if not isinstance(payload, dict) or payload.get('rc') != 0 or not isinstance(rows, list):
        raise ValueError('指数接口未返回有效行情列表')
    by_id = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('指数接口返回了无效记录')
        key = str(row.get('f13')) + '.' + str(row.get('f12'))
        if key in by_id:
            raise ValueError('指数接口返回了重复代码')
        by_id[key] = row
    quotes = []
    for secid, name, market in SYMBOLS:
        row = by_id.get(secid, {})
        value = number(row.get('f2'))
        if value is not None and value <= 0:
            value = None
        stamp = quote_stamp(row.get('f124'), collected_at)
        error = '接口未返回该指数' if not row else '接口未返回有效点位' if value is None else None
        quotes.append(dict(secid=secid, name=name, market=market, val=value,
                           pct=number(row.get('f3')) if value is not None else None,
                           chg=number(row.get('f4')) if value is not None else None,
                           quoteDate=stamp.date().isoformat() if stamp else None,
                           quoteTime=stamp.strftime('%H:%M:%S') if stamp else None,
                           quoteTimestamp=stamp.isoformat(timespec='seconds') if stamp else None,
                           collectedAt=collected_at, source=SOURCE,
                           status='available' if value is not None else 'unavailable',
                           error=error, stale=False))
    return quotes


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('schemaVersion') != 1 or snapshot.get('timezone') != 'Asia/Shanghai':
        raise ValueError('Invalid index snapshot schema')
    stamp = dt.datetime.fromisoformat(snapshot['collectedAt'])
    if stamp.utcoffset() != dt.timedelta(hours=8):
        raise ValueError('Index collection timestamp must use Beijing time')
    quotes = snapshot.get('quotes')
    if not isinstance(quotes, list) or [q.get('secid') for q in quotes] != [s[0] for s in SYMBOLS]:
        raise ValueError('Index snapshot does not cover the configured symbols')
    for quote, (secid, name, market) in zip(quotes, SYMBOLS):
        if quote.get('name') != name or quote.get('market') != market or quote.get('source') != SOURCE:
            raise ValueError('Index identity/source mismatch')
        if quote.get('collectedAt') != snapshot['collectedAt']:
            raise ValueError('Index collection timestamps disagree')
        value = quote.get('val')
        if value is not None and (not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0):
            raise ValueError('Invalid index level')
        for key in ('pct', 'chg'):
            v = quote.get(key)
            if v is not None and (isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)):
                raise ValueError('Invalid index change')
        if quote.get('status') != ('available' if value is not None else 'unavailable'):
            raise ValueError('Index availability is inconsistent')
        if quote.get('quoteTimestamp'):
            observed = dt.datetime.fromisoformat(quote['quoteTimestamp'])
            if observed.utcoffset() != dt.timedelta(hours=8) or observed > stamp + dt.timedelta(minutes=5):
                raise ValueError('Invalid quote time')
            if quote.get('quoteDate') != observed.date().isoformat() or quote.get('quoteTime') != observed.strftime('%H:%M:%S'):
                raise ValueError('Index quote dates disagree')
        elif quote.get('quoteDate') is not None or quote.get('quoteTime') is not None:
            raise ValueError('Index timestamp is missing')
    return snapshot


def collect(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    collected_at = dt.datetime.now(TZ).isoformat(timespec='seconds')
    best = None
    evidence, errors = [], []
    for attempt, host in enumerate(('push2delay.eastmoney.com', 'push2.eastmoney.com') * 2):
        if attempt:
            time.sleep(1)
        params = {'fltt': 2, 'invt': 2, 'ut': 'b2884a393a59ad64002292a3e90d46a5',
                  'fields': 'f2,f3,f4,f12,f13,f14,f124', 'secids': ','.join(s[0] for s in SYMBOLS), '_': time.time_ns()}
        url = 'https://' + host + '/api/qt/ulist.np/get?' + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'})
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError('指数响应过大')
            collected_at = dt.datetime.now(TZ).isoformat(timespec='seconds')
            quotes = parse_response(json.loads(raw), collected_at)
            digest = hashlib.sha256(raw).hexdigest()
            (output.parent / ('index-quotes-' + digest + '.json')).write_bytes(raw)
            evidence.append({'url': url, 'sha256': digest, 'bytes': len(raw), 'retrievedAt': collected_at})
            # Keep the response with the most available quotes, preserving its single collection time.
            if best is None or sum(q['val'] is not None for q in quotes) > sum(q['val'] is not None for q in best):
                best = quotes
            if all(q['val'] is not None for q in quotes):
                break
        except Exception as error:
            errors.append(host + ': ' + type(error).__name__ + ': ' + str(error)[:180])
    if best is None:
        best = parse_response({'rc': 0, 'data': {'diff': []}}, collected_at)
        for quote in best:
            quote['error'] = '本次行情接口请求失败'
    collected_at = best[0]['collectedAt']
    snapshot = validate_snapshot({'schemaVersion': 1, 'timezone': 'Asia/Shanghai',
                                 'collectedAt': collected_at, 'quotes': best,
                                 'evidence': evidence, 'errors': errors})
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temporary.replace(output)
    return snapshot


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'source-cache/index-quotes.json')
    parser.add_argument('--require-any', action='store_true', help='Stop publication when every index is unavailable')
    args = parser.parse_args()
    result = collect(args.output)
    print(json.dumps({'collectedAt': result['collectedAt'], 'available': sum(q['val'] is not None for q in result['quotes']),
                      'total': len(result['quotes']), 'errors': result['errors']}, ensure_ascii=False))
    if args.require_any and not any(q['val'] is not None for q in result['quotes']):
        raise SystemExit('No index quotes could be collected; keep the previous published version.')
