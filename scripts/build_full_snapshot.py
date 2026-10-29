#!/usr/bin/env python3
"""Build a publishable snapshot only after every directory code has a checkpoint.

Actual source values and their dates are preserved independently. Processing
coverage is reported separately from field availability. Raw source histories
remain in source-cache; the website receives computed metrics in small assets.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from inception_metadata import apply_inception, load_profiles, valid_date, enforce_inception_intervals

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('dwjz', 'd1', 'w1', 'm1', 'm3', 'm6', 'y1', 'ytd', 'scale', 'manager', 'mdd', 'ytdMdd', 'wfsy', 'qrnh', 'inceptionDate')
RETURNS = {'dwjz', 'd1', 'w1', 'm1', 'm3', 'm6', 'y1', 'ytd', 'wfsy', 'qrnh'}
RISK = {'mdd', 'ytdMdd', 'historyStart', 'mddAsOf', 'riskMethod', 'ytdStart', 'ytdAsOf'}
TZ = dt.timezone(dt.timedelta(hours=8))


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def present(value):
    return value is not None and value not in ('', '-', '--')


def field_date(record, key):
    status = (record.get('fieldStatus') or {}).get(key, {})
    if 'asOf' in status:
        return status['asOf'] or ''
    if key in ('scale', 'scaleDate', 'scaleSourceCode'):
        return record.get('scaleDate') or ''
    if key in RISK:
        if key in ('ytdMdd', 'ytdStart', 'ytdAsOf'):
            return record.get('ytdAsOf') or record.get('mddAsOf') or ''
        return record.get('mddAsOf') or ''
    if key in RETURNS or key == 'jzrq':
        return record.get(key + 'AsOf') or record.get('jzrq') or ''
    return record.get('detailFetchedAt') or record.get('retrievedAt') or ''


def merge(old, incoming, *, fallback=False):
    result = dict(old)
    states = dict(old.get('fieldStatus') or {})
    dates = {key: field_date(old, key) for key in FIELDS if present(old.get(key))}
    for key, value in incoming.items():
        if key == 'fieldStatus' or not present(value):
            continue
        old_date, new_date = field_date(old, key), field_date(incoming, key)
        if present(old.get(key)):
            if fallback and (not new_date or new_date <= old_date):
                continue
            if old_date and (not new_date or new_date < old_date):
                continue
        result[key] = value
        if key in FIELDS:
            dates[key] = new_date
            state = (incoming.get('fieldStatus') or {}).get(key)
            if state:
                states[key] = dict(state)
            else:
                states.pop(key, None)
    for key, state in (incoming.get('fieldStatus') or {}).items():
        if not present(result.get(key)):
            states[key] = state
        if state.get('status') == 'not_applicable':
            result.pop(key, None)
            states[key] = state
            dates.pop(key, None)
    # A newer NAV date must not relabel an older retained return as current.
    for key, stamp in dates.items():
        if stamp != field_date({**result, 'fieldStatus': {}}, key):
            states[key] = {**states.get(key, {'status': 'available', 'reason': 'retained_source_value'}), 'asOf': stamp or None}
    result['fieldStatus'] = states
    return result


def sanitize_year(record, as_of):
    result = {**record, 'fieldStatus': dict(record.get('fieldStatus') or {})}
    for key in ('ytd', 'ytdMdd'):
        stamp = field_date(result, key)
        if present(result.get(key)) and (not stamp or stamp[:4] != as_of[:4]):
            result.pop(key, None)
            result['fieldStatus'][key] = {'status': 'missing', 'reason': 'stopped_before_year' if stamp else 'missing_nav_date', 'asOf': stamp or None}
    return result


def validate_collection(directory, manifest, base, codes, as_of):
    summary = manifest.get('summary') or {}
    if directory.get('asOf') != as_of or base.get('asOf') != as_of or base.get('directoryCount') != len(codes):
        raise ValueError('Directory and batch snapshot dates or directory counts do not match the build target')
    if (manifest.get('asOf') != as_of or set(manifest.get('codes', [])) != set(codes)
            or len(manifest.get('codes', [])) != len(codes) or not summary.get('finishedAt')
            or summary.get('targetCount') != len(codes) or summary.get('completed') != len(codes)
            or sum(summary.get(k, 0) for k in ('ok', 'partial', 'failed')) != len(codes)):
        raise ValueError('Collection manifest does not confirm completion of the current full directory')
    for source in ('ranking', 'money'):
        if base.get('integrity', {}).get(source, {}).get('complete') is not True:
            raise ValueError(f'Batch {source} collection is incomplete')


def load_snapshot():
    source = (ROOT / 'dist/snapshot.js').read_text()
    snapshot = json.loads(source.split('=', 1)[1].strip().rstrip(';'))
    for part in sorted((ROOT / 'dist').glob('snapshot-perf-*.js')):
        body = part.read_text().split('Object.assign(window.MARKET_SNAPSHOT.perf,', 1)[1].strip()
        snapshot['perf'].update(json.loads(body.removesuffix(');').strip()))
    return snapshot


def family_name(name):
    return re.sub(r'([ABCDEHIJNPQRSXY])(?=(?:[（(](?:人民币|美元)[）)])?$)', '', name)


def build(args):
    directory = read(ROOT / 'source-cache/current-directory.json')
    rows = directory['rows']
    codes = [str(row[0]).zfill(6) for row in rows]
    assert len(codes) == len(set(codes)) and all(re.fullmatch(r'\d{6}', c) for c in codes)
    detail_dir = ROOT / 'source-cache' / ('backfill-' + args.as_of.replace('-', ''))
    absent = [c for c in codes if not (detail_dir / 'records' / (c + '.json')).exists()]
    if absent:
        raise SystemExit(f'Full collection unfinished: {len(absent)} codes without checkpoints; snapshot unchanged')
    manifest = read(detail_dir / 'manifest.json')
    base = read(ROOT / 'source-cache' / ('base-refresh-' + args.as_of.replace('-', '') + '.json'))
    profiles_path = ROOT / 'source-cache' / ('fund-profiles-' + args.as_of.replace('-', '') + '.json')
    profiles = load_profiles(profiles_path)
    if profiles and profiles.get('asOf') != args.as_of:
        raise SystemExit('Profile metadata date differs from build target; snapshot unchanged')
    try:
        validate_collection(directory, manifest, base, codes, args.as_of)
    except ValueError as error:
        raise SystemExit(str(error) + '; snapshot unchanged') from error
    old = load_snapshot()
    baseline = ROOT / 'source-cache' / ('baseline-before-full-' + args.as_of + '.json')
    if not baseline.exists():
        write(baseline, old)
    official = read(ROOT / 'docs/market-total.json')
    by_code = {p['code']: p for p in old['funds']}
    funds, perf, audit, statuses = [], {}, [], collections.Counter()
    preserve = ('company', 'companyId', 'inception', 'inceptionMeta', 'purchaseStatus')
    for row, code in zip(rows, codes):
        prior = by_code.get(code, {})
        fund = {'code': code, 'name': row[2], 'type': row[3], 'sourceUpdatedAt': directory['asOf']}
        fund.update({k: prior[k] for k in preserve if present(prior.get(k))})
        fund = apply_inception(fund, base.get('inceptions', {}).get(code),
                               profiles.get('records', {}).get(code), args.as_of)
        funds.append(fund)
        record = read(detail_dir / 'records' / (code + '.json'))
        assert record['code'] == code
        assert record['schemaVersion'] == manifest['schemaVersion'], f'Outdated calculation checkpoint: {code}'
        assert record['status'] in ('ok', 'partial', 'failed'), f'Unknown checkpoint state: {code}'
        if record['status'] != 'failed' and record.get('quality', {}).get('verifiedInception') != valid_date(fund.get('inception'), args.as_of):
            raise SystemExit(f'Inception metadata changed for {code}; recompute its cached detail before publishing')
        if any(state.get('reason') == 'fetch_failed' for state in (record['perf'].get('fieldStatus') or {}).values()):
            raise SystemExit(f'Unresolved transport failure for {code}; retry collection before replacing the snapshot')
        statuses[record['status']] += 1
        value = merge(old.get('perf', {}).get(code, {}), record['perf'])
        value = merge(value, base.get('companyFallback', {}).get(code, {}), fallback=True)
        value = merge(value, base['perf'].get(code, {}))
        value['detailAttemptedAt'] = record['evidence'].get('retrievedAt') or args.as_of
        value['detailStatus'] = record['status']
        # Returns may refer to old discontinued products; "今年" always means
        # this snapshot's calendar year, never the last year they traded.
        value = sanitize_year(value, args.as_of)
        value = enforce_inception_intervals(value, fund.get('inception'), field_date)
        if fund.get('inception'):
            value['inceptionDate'] = fund['inception']
            value['fieldStatus']['inceptionDate'] = {'status': 'available', 'reason': 'verified_inception',
                'asOf': (fund.get('inceptionMeta') or {}).get('retrievedAt', args.as_of)[:10]}
        else:
            value.pop('inceptionDate', None)
            value['fieldStatus']['inceptionDate'] = {'status': 'missing',
                'reason': (fund.get('inceptionMeta') or {}).get('status', 'not_collected')}
        money = '货币' in fund['type']
        for key in (('dwjz', 'd1', 'w1', 'mdd', 'ytdMdd') if money else ('wfsy', 'qrnh')):
            value.pop(key, None)
            value['fieldStatus'][key] = {'status': 'not_applicable', 'reason': 'not_applicable_money' if money else 'not_applicable_non_money'}
        for key in FIELDS:
            if not present(value.get(key)) and key not in value['fieldStatus']:
                value['fieldStatus'][key] = {'status': 'missing', 'reason': 'not_disclosed'}
        # Keep file/source hashes in the audit, not repeated in every browser row.
        for key in ('sourceFile', 'sourceHash', 'fallbackOnly'):
            value.pop(key, None)
        perf[code] = {k: v for k, v in value.items() if present(v)}
        audit.append({'code': code, 'name': fund['name'], 'status': record['status'], 'evidence': record['evidence'],
                      'quality': record.get('quality', {}), 'missing': {k: v for k, v in value['fieldStatus'].items() if not present(value.get(k))}})
    coverage = {}
    for field in FIELDS:
        reasons = collections.Counter((p.get('fieldStatus', {}).get(field) or {}).get('reason', 'not_disclosed')
                                      for p in perf.values() if not present(p.get(field)))
        available = sum(present(p.get(field)) for p in perf.values())
        na = sum(v for k, v in reasons.items() if k.startswith('not_applicable'))
        coverage[field] = {'available': available, 'notApplicable': na, 'missing': len(codes) - available - na,
                           'total': len(codes), 'reasons': dict(reasons)}
    now = dt.datetime.now(TZ).isoformat(timespec='seconds')
    sources = list(old['meta'].get('sources', [])) + base['sources']
    unique_sources = list({(s['url'], s['sha256']): s for s in sources}.values())
    details = {c: v for c, v in old.get('details', {}).items() if c in perf}
    for code, raw in details.items():
        raw.setdefault('_fetchedAt', old['meta']['updatedAt'])
    meta = {**old['meta'], 'updatedAt': now, 'directoryCount': len(codes), 'fundFamilyCount': len({family_name(p['name']) for p in funds}),
            'returnCount': sum(any(present(p.get(k)) for k in RETURNS) for p in perf.values()),
            'companyMappedCount': sum(bool(p.get('companyId')) for p in funds),
            'companyCount': len({p['companyId'] for p in funds if p.get('companyId')}),
            'historyCount': len(details), 'moneyReturnCount': sum(present(p.get('wfsy')) for p in perf.values()),
            'note': '全目录逐代码采集；字段缺口按未披露、历史不足、源不可用及不适用分别标注。完整历史留存本地来源缓存。',
            'sources': unique_sources, 'sourceCount': len(unique_sources), 'marketTotal': official,
            'collection': {'directoryCount': len(codes), 'attempted': len(codes), **dict(statuses), 'asOf': args.as_of},
            'coverage': coverage, 'baseIntegrity': base['integrity'], 'directorySource': {k: v for k, v in directory.items() if k != 'rows'}}
    if profiles:
        meta['inceptionCollection'] = {'asOf': profiles['asOf'], 'summary': profiles.get('summary', {}),
            'metadataFile': str(profiles_path.relative_to(ROOT)),
            'metadataSha256': hashlib.sha256(profiles_path.read_bytes()).hexdigest()}
    meta['errors'] = base.get('errors', [])
    snapshot = {'meta': meta, 'funds': funds, 'perf': {}, 'details': details, 'realtime': {}}
    (ROOT / 'dist/snapshot.js').write_text('window.MARKET_SNAPSHOT=' + compact(snapshot) + ';\n')
    chunks, chunk, size = [], {}, 0
    for code, value in perf.items():
        row_size = len(compact({code: value}).encode())
        if chunk and size + row_size > 4_000_000:
            chunks.append(chunk); chunk, size = {}, 0
        chunk[code] = value; size += row_size
    if chunk:
        chunks.append(chunk)
    for part in (ROOT / 'dist').glob('snapshot-perf-*.js'):
        part.unlink()
    files = []
    for i, chunk in enumerate(chunks, 1):
        name = f'snapshot-perf-{i:03d}.js'
        (ROOT / 'dist' / name).write_text('Object.assign(window.MARKET_SNAPSHOT.perf,' + compact(chunk) + ');\n')
        files.append(name)
    html_path = ROOT / 'dist/index.html'
    html = re.sub(r'\n?<script src="snapshot-perf-\d+\.js"></script>', '', html_path.read_text())
    html = html.replace('<script src="snapshot.js"></script>', '<script src="snapshot.js"></script>\n' + '\n'.join(f'<script src="{f}"></script>' for f in files))
    html_path.write_text(html)
    write(ROOT / 'docs/data-audit.json', meta)
    with (ROOT / 'docs/detail-evidence.jsonl').open('w') as output:
        for item in audit:
            output.write(compact(item) + '\n')
    write(ROOT / 'docs/coverage-gaps.json', {'asOf': args.as_of, 'coverage': coverage,
          'failedCodes': [x['code'] for x in audit if x['status'] == 'failed'],
          'partialCodes': [x['code'] for x in audit if x['status'] == 'partial'],
          'note': '处理率与字段有值率分别统计；全部字段缺口及来源证据见detail-evidence.jsonl'})
    print(json.dumps({'collection': meta['collection'], 'coverage': coverage, 'assets': len(files) + 1}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', default=dt.datetime.now(TZ).date().isoformat())
    build(parser.parse_args())
