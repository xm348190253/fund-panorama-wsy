#!/usr/bin/env python3
"""Resumable public-fund detail backfill. Never edits dist or an existing snapshot.

Raw replies and per-code checkpoints live in ignored source-cache/. Each result
records provenance and field-specific reasons; missing values never become zero.
"""
from __future__ import annotations

import argparse
import bisect
import calendar
import concurrent.futures as cf
import datetime as dt
import gzip
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import statistics
import threading
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo
from inception_metadata import apply_inception, load_profiles, valid_date, calculation_input_hash

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo('Asia/Shanghai')
SCHEMA = 5
VARS = ('fS_code', 'fS_name', 'ishb', 'Data_netWorthTrend', 'Data_grandTotal',
        'Data_fluctuationScale', 'Data_currentFundManager', 'Data_millionCopiesIncome',
        'Data_sevenDaysYearIncome', 'syl_1n', 'syl_6y', 'syl_3y', 'syl_1y')
VAR_RE = re.compile(r'\bvar\s+(' + '|'.join(VARS) + r')\s*=\s*')
FIELDS = ('dwjz', 'd1', 'w1', 'm1', 'm3', 'm6', 'y1', 'ytd', 'scale', 'manager',
          'mdd', 'ytdMdd', 'wfsy', 'qrnh')
REASON = {
    'not_disclosed': '源接口未提供该字段',
    'insufficient_history': '可得历史不足该统计区间',
    'insufficient_year_history': '缺少年初基准，或尚未取得成立日期以核验本年成立以来区间',
    'missing_growth_series': '缺少可核验的复权收益序列',
    'not_applicable_money': '货币基金不适用该指标',
    'not_applicable_non_money': '非货币基金不适用该指标',
    'stopped_before_year': '可得序列未覆盖今年',
    'fetch_failed': '详情接口请求失败，未取得数据',
    'source_unavailable': '详情源未返回该代码的可用记录',
    'raw_not_available': '未保存该代码的原始详情，离线重算未联网',
}


def now():
    return dt.datetime.now(TZ).isoformat(timespec='seconds')


def num(value):
    if value is None or value == '' or value == '--':
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def day(timestamp):
    return dt.datetime.fromtimestamp(float(timestamp) / 1000, TZ).date().isoformat()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
    os.replace(tmp, path)


def source_path(path):
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def decode(raw, expected, expected_name=None, canonical_names=None):
    text = raw.decode('utf-8-sig')
    if '<html' in text.lower() or '<!doctype html' in text.lower():
        if '页面未找到' in text or '404' in text or 'not found' in text.lower():
            raise ValueError('source_not_found_page')
        raise ValueError('source_html_payload')
    decoder = json.JSONDecoder()
    values = {}
    for match in VAR_RE.finditer(text):
        try:
            value, _ = decoder.raw_decode(text[match.end():])
        except ValueError as error:
            raise ValueError('incomplete_variable:' + match.group(1)) from error
        values[match.group(1)] = value
    source_code = str(values.get('fS_code', '')).zfill(6)
    if source_code != expected:
        base = re.sub(r'[（(]后端[）)]$', '', expected_name or '')
        is_backend = base != (expected_name or '')
        canonical = (canonical_names or {}).get(source_code)
        if not (is_backend and canonical and base == canonical == values.get('fS_name')):
            raise ValueError('source_code_mismatch' if values.get('fS_code') else 'source_missing_identity')
        values['_aliasProof'] = {'requestedName': expected_name, 'canonicalName': canonical, 'reason': 'explicit_backend_fee_code'}
    values['_sourceCode'] = source_code
    if not text.rstrip().endswith(';'):
        raise ValueError('incomplete_source_ending')
    if not any(k in values for k in ('Data_netWorthTrend', 'Data_millionCopiesIncome', 'Data_fluctuationScale')):
        raise ValueError('source_has_no_supported_fields')
    return values


def drawdown(points):
    if len(points) < 2:
        return None
    peak, worst = points[0][1], 0.0
    for _, value in points:
        peak = max(peak, value)
        worst = min(worst, (value / peak - 1) * 100)
    return round(worst, 6)


def months_before(date, months):
    index = date.year * 12 + date.month - 1 - months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    return dt.date(year, month, min(date.day, calendar.monthrange(year, month)[1]))


def normalized_growth(raw):
    nav = raw.get('Data_netWorthTrend') or []
    nav = [p for p in nav if isinstance(p, dict) and num(p.get('x')) is not None and num(p.get('y')) is not None]
    nav = sorted({int(p['x']): p for p in nav}.values(), key=lambda p: p['x'])
    zero_placeholder = zero_growth_placeholders(nav)
    if len(nav) >= 2 and not zero_placeholder and all(num(p.get('equityReturn')) is not None and num(p.get('equityReturn')) > -100 for p in nav[1:]):
        index, points = 1.0, []
        for i, point in enumerate(nav):
            if i:
                index *= 1 + num(point['equityReturn']) / 100
            if not math.isfinite(index) or index <= 0:
                break
            points.append((day(point['x']), index))
        if len(points) == len(nav):
            return nav, points, '公开日增长率连乘序列'
    # The first series is the fund; later series are peers or benchmarks.
    # Never replace a missing fund return history with a comparison series.
    for series in (raw.get('Data_grandTotal') or [])[:1]:
        if not isinstance(series, dict) or not isinstance(series.get('data'), list):
            continue
        pts = [(day(p[0]), 1 + num(p[1]) / 100) for p in series['data']
               if isinstance(p, list) and len(p) > 1 and num(p[0]) is not None and num(p[1]) is not None and num(p[1]) > -100]
        pts = sorted(dict(pts).items())
        if len(pts) >= 2:
            return nav, pts, '源累计收益可得区间'
    return nav, [], None


def zero_growth_placeholders(nav):
    return (len(nav) > 1 and all(num(p.get('equityReturn')) == 0 for p in nav[1:])
            and max(num(p['y']) for p in nav) - min(num(p['y']) for p in nav) > 1e-10)


def normalize(product, raw, evidence, as_of):
    code = product['code']
    money = '货币' in (product.get('type') or '') or raw.get('ishb') is True
    perf = {field: None for field in FIELDS}
    states = {}
    methods = {}

    def missing(field, reason, asof=None):
        states[field] = {'status': 'not_applicable' if reason.startswith('not_applicable') else 'missing', 'reason': reason}
        if asof:
            states[field]['asOf'] = asof

    scale = raw.get('Data_fluctuationScale') or {}
    cats = scale.get('categories') or []
    for i, entry in reversed(list(enumerate(scale.get('series') or []))):
        value = num(entry.get('y')) if isinstance(entry, dict) else num(entry)
        if value is not None and value >= 0:
            perf.update(scale=value, scaleDate=cats[i] if i < len(cats) else None, scaleSourceCode=raw.get('_sourceCode') or code)
            break
    managers = [p.get('name') for p in raw.get('Data_currentFundManager') or [] if isinstance(p, dict) and p.get('name')]
    if managers:
        perf['manager'] = '、'.join(dict.fromkeys(managers))
    nav, points, risk_method = normalized_growth(raw)
    inception = valid_date(product.get('inception'), as_of)
    if inception:
        perf['inceptionDate'] = inception
    if nav and not money:
        perf['dwjz'] = num(nav[-1]['y'])
        perf['jzrq'] = day(nav[-1]['x'])
        zero_placeholder = zero_growth_placeholders(nav)
        perf['d1'] = None if zero_placeholder else num(nav[-1].get('equityReturn'))
        if perf['d1'] is not None:
            methods['d1'] = 'source_daily_growth'
    if money:
        for field, source in [('wfsy', 'Data_millionCopiesIncome'), ('qrnh', 'Data_sevenDaysYearIncome')]:
            series = [p for p in raw.get(source) or [] if isinstance(p, list) and len(p) > 1 and num(p[0]) is not None and num(p[1]) is not None]
            if series:
                last = max(series, key=lambda p: p[0])
                perf[field] = num(last[1])
                perf[field + 'AsOf'] = day(last[0])
                perf['jzrq'] = max(perf.get('jzrq') or '', day(last[0]))
        for field in ('dwjz', 'd1', 'w1', 'mdd', 'ytdMdd'):
            missing(field, 'not_applicable_money')
    else:
        for field in ('wfsy', 'qrnh'):
            missing(field, 'not_applicable_non_money')

    dates = [p[0] for p in points]
    last_date = perf.get('jzrq') or (dates[-1] if dates else None)
    if last_date and not perf.get('jzrq'):
        perf['jzrq'] = last_date
    if last_date:
        period_end = dt.date.fromisoformat(last_date)
        for field, months, source in [('m1', 1, 'syl_1y'), ('m3', 3, 'syl_3y'), ('m6', 6, 'syl_6y'), ('y1', 12, 'syl_1n')]:
            target = months_before(period_end, months).isoformat()
            published = num(raw.get(source))
            if inception and inception > target:
                missing(field, 'insufficient_history', last_date)
            elif published is not None:
                perf[field] = published
                methods[field] = 'source_' + source
            elif points and not money:
                idx = bisect.bisect_right(dates, target) - 1
                if idx >= 0 and points[-1][0] == last_date:
                    perf[field] = round((points[-1][1] / points[idx][1] - 1) * 100, 6)
                    methods[field] = risk_method
                else:
                    missing(field, 'insufficient_history', last_date)
    if points and not money:
        perf.update(historyStart=points[0][0], mddAsOf=points[-1][0], riskMethod=risk_method, mdd=drawdown(points))
        if len(points) >= 6 and points[-1][0] == last_date and (dt.date.fromisoformat(points[-1][0]) - dt.date.fromisoformat(points[-6][0])).days <= 14:
            perf['w1'] = round((points[-1][1] / points[-6][1] - 1) * 100, 6)
            methods['w1'] = 'five_published_trading_observations:' + risk_method
        else:
            missing('w1', 'insufficient_history', last_date)
        year_start = as_of[:4] + '-01-01'
        idx = bisect.bisect_left(dates, year_start)
        if idx == len(points):
            for field in ('ytd', 'ytdMdd'):
                missing(field, 'stopped_before_year', points[-1][0])
        elif idx > 0 or (inception and inception >= year_start and dates[0] <= inception):
            start = max(0, idx - 1)
            perf.update(ytd=round((points[-1][1] / points[start][1] - 1) * 100, 6),
                        ytdMdd=drawdown(points[start:]), ytdStart=points[start][0], ytdAsOf=points[-1][0])
            methods['ytd'] = risk_method
        else:
            for field in ('ytd', 'ytdMdd'):
                missing(field, 'insufficient_year_history', points[-1][0])
    elif not money:
        for field in ('w1', 'ytd', 'mdd', 'ytdMdd'):
            missing(field, 'missing_growth_series', last_date)
    for field in FIELDS:
        if perf[field] is None and field not in states:
            missing(field, 'not_disclosed', perf.get('scaleDate') if field == 'scale' else last_date)
    perf['detailFetchedAt'] = evidence['retrievedAt']
    perf['fieldStatus'] = states
    stale_days = max(0, (dt.date.fromisoformat(as_of) - dt.date.fromisoformat(last_date)).days) if last_date else None
    if stale_days is not None and stale_days > 14:
        for field in ('dwjz', 'd1', 'w1', 'm1', 'm3', 'm6', 'y1', 'ytd', 'mdd', 'ytdMdd', 'wfsy', 'qrnh'):
            if perf.get(field) is not None:
                states[field] = {'status': 'stale', 'reason': 'source_date_older_than_14_days', 'asOf': last_date}
    if raw.get('_aliasProof'):
        perf['aliasOf'] = raw['_sourceCode']
    spark = [[day(p['x']), num(p['y'])] for p in nav[-120:]] if not money else []
    return {'schemaVersion': SCHEMA, 'calculationAsOf': as_of,
            'calculationInputHash': calculation_input_hash(product, as_of), 'code': code, 'name': product['name'],
            'status': 'ok' if perf['scale'] is not None and perf['manager'] and (last_date or money) else 'partial',
            'perf': perf, 'evidence': evidence,
            'quality': {'staleDays': stale_days, 'verifiedInception': inception,
                        'historyStart': day(nav[0]['x']) if nav else None, 'observations': len(nav),
                        'riskObservations': len(points), 'fieldMethods': methods,
                        'aliasEvidence': raw.get('_aliasProof')}, 'sparkline': spark}


def download(url, timeout, max_bytes=16 * 1024 * 1024):
    raw, total, failures, attempts = bytearray(), None, 0, 0
    first_status = None
    while total is None or len(raw) < total:
        if len(raw) >= max_bytes:
            raise ValueError('source_exceeds_safety_limit')
        start = len(raw)
        end = (max_bytes - 1) if total is None else total - 1
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/',
                                                  'Accept-Encoding': 'identity', 'Range': f'bytes={start}-{end}'})
        attempts += 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if first_status is None:
                    first_status = response.status
                if response.status == 206:
                    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                    if not match or int(match[1]) != start:
                        raise ValueError('invalid_content_range')
                    declared_total = int(match[3])
                    if declared_total > max_bytes or (total is not None and total != declared_total):
                        raise ValueError('source_size_changed_or_exceeds_limit')
                    total = declared_total
                elif response.status == 200 and start == 0:
                    length = response.headers.get('Content-Length')
                    total = int(length) if length else None
                else:
                    raise ValueError('range_not_supported_for_continuation')
                try:
                    data = response.read(max_bytes + 1)
                except http.client.IncompleteRead as error:
                    data = error.partial
                if not data:
                    raise ValueError('empty_source_response')
                raw.extend(data)
                if total is None:
                    total = len(raw)
                if len(raw) > total:
                    raise ValueError('response_exceeds_declared_length')
                failures = 0
        except urllib.error.HTTPError as error:
            if error.code in (403, 404, 410, 429):
                raise
            failures += 1
            if failures >= 3:
                raise
            time.sleep(failures * .5)
        except (OSError, ValueError, http.client.HTTPException):
            failures += 1
            if failures >= 3:
                raise
            time.sleep(failures * .5)
    return bytes(raw), first_status, attempts


def load_funds(directory, base_refresh=None, profiles_path=None, as_of=None):
    baseline_text = (ROOT / 'dist/snapshot.js').read_text()
    baseline = json.loads(baseline_text.split('=', 1)[1].strip().rstrip(';'))
    known = {p['code']: p for p in baseline['funds']}
    inceptions = {}
    if base_refresh and Path(base_refresh).exists():
        inceptions = json.loads(Path(base_refresh).read_text()).get('inceptions') or {}
    profiles = load_profiles(profiles_path).get('records', {})
    if directory:
        data = json.loads(Path(directory).read_text())
    else:
        data = baseline
    if isinstance(data, dict):
        data = data.get('funds') or data.get('data') or data.get('rows') or []
    result = []
    for item in data:
        if isinstance(item, list):
            item = {'code': item[0], 'name': item[2], 'type': item[3]}
        if not isinstance(item, dict) or not re.fullmatch(r'\d{6}', str(item.get('code', ''))):
            continue
        merged = {**known.get(item['code'], {}), **item}
        merged = apply_inception(merged, inceptions.get(item['code']), profiles.get(item['code']), as_of)
        result.append(merged)
    return list({p['code']: p for p in result}.values())


def reusable_checkpoint(record, as_of, retry_failed=False, product=None):
    if not (record.get('schemaVersion') == SCHEMA and record.get('calculationAsOf') == as_of
            and (record.get('status') != 'failed' or not retry_failed)):
        return False
    if product is None:
        return True
    if record.get('calculationInputHash'):
        return record['calculationInputHash'] == calculation_input_hash(product, as_of)
    # Legacy same-day checkpoints carry the verified calculation date separately.
    return (record.get('quality', {}).get('verifiedInception') == valid_date(product.get('inception'), as_of)
            and record.get('code') == product.get('code') and record.get('name') == product.get('name'))


def raw_is_current(path, as_of):
    return dt.datetime.fromtimestamp(path.stat().st_mtime, TZ).date().isoformat() == as_of


def source_unavailable(error):
    return any(token in (error or '') for token in ('source_not_found_page', 'source_html_payload',
               'source_code_mismatch', 'source_missing_identity', 'source_has_no_supported_fields'))


def run(args):
    out = Path(args.output or ROOT / 'source-cache' / ('backfill-' + args.as_of.replace('-', ''))).resolve()
    for sub in ('records', 'raw'):
        (out / sub).mkdir(parents=True, exist_ok=True)
    base_refresh = args.base_refresh or ROOT / 'source-cache' / ('base-refresh-' + args.as_of.replace('-', '') + '.json')
    profiles_path = args.profiles or ROOT / 'source-cache' / ('fund-profiles-' + args.as_of.replace('-', '') + '.json')
    funds = load_funds(args.directory, base_refresh, profiles_path, args.as_of)
    canonical_names = {p['code']: p['name'] for p in funds}
    if args.codes:
        wanted = set(args.codes.split(',')); funds = [p for p in funds if p['code'] in wanted]
    if args.limit:
        funds = funds[:args.limit]
    state = {'schemaVersion': SCHEMA, 'startedAt': now(), 'asOf': args.as_of, 'targetCount': len(funds),
             'workers': args.workers, 'completed': 0, 'ok': 0, 'partial': 0, 'failed': 0, 'reusedCheckpoint': 0,
             'reusedRaw': 0, 'networkBytes': 0, 'fields': {k: 0 for k in FIELDS}}
    started = time.monotonic()
    timings = []

    def worker(product):
        tick = time.monotonic()
        code = product['code']; dest = out / 'records' / (code + '.json')
        if dest.exists() and not args.normalize_only and not args.fresh_source:
            previous = json.loads(dest.read_text())
            if reusable_checkpoint(previous, args.as_of, args.retry_failed, product):
                return previous, True, time.monotonic() - tick
        url = 'https://fund.eastmoney.com/pingzhongdata/' + code + '.js'
        evidence = {'url': url, 'retrievedAt': now(), 'mode': None, 'sha256': None, 'bytes': 0}
        candidates = [] if args.fresh_source else [out / 'raw' / (code + '.js.gz'), ROOT / 'source-cache' / ('detail-' + code + '.txt')]
        last_error = None
        for file in candidates:
            if not file.exists():
                continue
            if not (args.normalize_only or args.cache_only) and not raw_is_current(file, args.as_of):
                continue
            try:
                raw = gzip.decompress(file.read_bytes()) if file.suffix == '.gz' else file.read_bytes()
                evidence.update(mode='existing_raw', retrievedAt=dt.datetime.fromtimestamp(file.stat().st_mtime, TZ).isoformat(timespec='seconds'),
                                sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), sourceFile=source_path(file))
                values = decode(raw, code, product['name'], canonical_names)
                record = normalize(product, values, evidence, args.as_of)
                atomic_json(dest, record)
                return record, False, time.monotonic() - tick
            except Exception as error:
                last_error = str(error)
        for attempt in range(0 if (args.normalize_only or args.cache_only) else args.retries + 1):
            try:
                raw, status, requests = download(url, args.timeout)
                file = out / 'raw' / (code + '.js.gz')
                file.write_bytes(gzip.compress(raw, compresslevel=3))
                evidence.update(mode='network', retrievedAt=now(), sha256=hashlib.sha256(raw).hexdigest(),
                                bytes=len(raw), httpStatus=status, requests=requests, sourceFile=source_path(file))
                values = decode(raw, code, product['name'], canonical_names)
                evidence['responseCode'] = values['_sourceCode']
                record = normalize(product, values, evidence, args.as_of)
                atomic_json(dest, record)
                return record, False, time.monotonic() - tick
            except Exception as error:
                last_error = type(error).__name__ + ':' + str(error)
                if isinstance(error, urllib.error.HTTPError) and error.code in (403, 404, 410, 429):
                    break
                if source_unavailable(str(error)):
                    break
                if attempt < args.retries:
                    time.sleep(.5 * (attempt + 1))
        evidence['error'] = last_error or 'raw_not_available'
        reason = 'source_unavailable' if source_unavailable(last_error) else ('raw_not_available' if last_error is None else 'fetch_failed')
        states = {k: {'status': 'missing', 'reason': reason} for k in FIELDS}
        record = {'schemaVersion': SCHEMA, 'calculationAsOf': args.as_of, 'code': code, 'name': product['name'], 'status': 'failed',
                  'calculationInputHash': calculation_input_hash(product, args.as_of),
                  'perf': {'detailFetchedAt': None, 'fieldStatus': states}, 'evidence': evidence, 'quality': {}, 'sparkline': []}
        atomic_json(dest, record)
        return record, False, time.monotonic() - tick

    def report(final=False):
        state['updatedAt'] = now(); state['elapsedSeconds'] = round(time.monotonic() - started, 1)
        state['codesPerSecond'] = round(state['completed'] / max(state['elapsedSeconds'], .01), 3)
        state['medianTaskSeconds'] = round(statistics.median(timings), 3) if timings else 0
        atomic_json(out / 'progress.json', state)
        summary = {k: state[k] for k in ('completed', 'targetCount', 'ok', 'partial', 'failed', 'reusedCheckpoint', 'reusedRaw', 'networkBytes', 'elapsedSeconds', 'codesPerSecond')}
        if final:
            summary['fields'] = state['fields']
        print(json.dumps(summary, ensure_ascii=False), flush=True)

    report()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as executor:
        iterator = iter(funds)
        active = {executor.submit(worker, p) for p in [next(iterator, None) for _ in range(args.workers)] if p is not None}
        last_report = time.monotonic()
        while active:
            done, active = cf.wait(active, timeout=5, return_when=cf.FIRST_COMPLETED)
            for future in done:
                record, reused, duration = future.result()
                state['completed'] += 1; state[record['status']] += 1
                if reused:
                    state['reusedCheckpoint'] += 1
                elif record['evidence'].get('mode') == 'existing_raw':
                    state['reusedRaw'] += 1
                elif record['evidence'].get('mode') == 'network':
                    state['networkBytes'] += record['evidence']['bytes']
                for key in FIELDS:
                    value = record['perf'].get(key)
                    if value is not None and value != '':
                        state['fields'][key] += 1
                timings.append(duration)
                p = next(iterator, None)
                if p is not None:
                    active.add(executor.submit(worker, p))
            if time.monotonic() - last_report >= 15 or (done and state['completed'] % 100 == 0):
                report(); last_report = time.monotonic()
    state['finishedAt'] = now(); report(True)
    atomic_json(out / 'manifest.json', {'schemaVersion': SCHEMA, 'asOf': args.as_of, 'codes': [p['code'] for p in funds],
                                      'summary': state, 'reasonLabels': REASON})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', help='Optional current-directory JSON file; otherwise uses current snapshot')
    parser.add_argument('--base-refresh', help='Base refresh JSON with verified inception dates; defaults to same-date cache')
    parser.add_argument('--profiles', help='Verified per-code profile metadata; defaults to same-date cache')
    parser.add_argument('--output')
    parser.add_argument('--codes', help='Comma-separated test codes')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--timeout', type=int, default=20)
    parser.add_argument('--retries', type=int, default=1)
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--normalize-only', action='store_true', help='Recompute all records from saved raw, without network access')
    parser.add_argument('--cache-only', action='store_true', help='Reuse matching checkpoints; recompute changed metadata from raw without network access')
    parser.add_argument('--fresh-source', action='store_true', help='Ignore all raw/checkpoint caches and refetch sources')
    parser.add_argument('--as-of', default=dt.datetime.now(TZ).date().isoformat())
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error('--workers must be 1..16')
    if (args.normalize_only or args.cache_only) and args.fresh_source:
        parser.error('Offline calculation modes and --fresh-source are mutually exclusive')
    run(args)


if __name__ == '__main__':
    main()
