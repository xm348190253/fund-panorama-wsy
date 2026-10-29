#!/usr/bin/env python3
"""Fetch code-specific fund overview dates with cached evidence and strict identity checks.

Does not edit the application or historical-return checkpoints. Missing inception
dates stay missing unless the overview explicitly identifies the requested code.
"""
from __future__ import annotations

import argparse
from collections import Counter
import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import time
import urllib.error

from backfill_market import ROOT, TZ, atomic_json, download, now

SCHEMA = 1
LABELS = ('基金全称', '基金简称', '基金代码', '发行日期', '成立日期/规模', '净资产规模', '基金经理人')
SEMANTIC = ('东方财富基金概况对所列代码报告的成立日期；不自动等同基金合同最早生效日。'
            '后设份额、转型或合同变更如需法律事件日期，应另核基金公告。')


def clean(text):
    text = re.sub(r'<script\b[\s\S]*?</script>|<style\b[\s\S]*?</style>', '', text, flags=re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()


def date_from(text):
    m = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?', text or '')
    if not m:
        return None
    try:
        return dt.date(*map(int, m.groups())).isoformat()
    except ValueError:
        return None


def parse_profile(product, raw, as_of):
    code = product['code']
    result = {'schemaVersion': SCHEMA, 'asOf': as_of, 'code': code, 'name': product['name'],
              'status': None, 'reason': None, 'inceptionDate': None,
              'sourceReportedInceptionDate': None, 'issueDate': None, 'dateSemantic': SEMANTIC,
              'sourceLabel': '成立日期/规模', 'knownInceptionDate': product.get('inception'),
              'contractEffectiveDate': None, 'shareClassAdditionDate': None}
    text = raw.decode('utf-8-sig')
    plain = clean(text)
    title_match = re.search(r'<title\b[^>]*>(.*?)</title>', text, re.I | re.S)
    title = clean(title_match[1]) if title_match else ''
    fields = {}
    for label in LABELS:
        m = re.search(r'<th\b[^>]*>\s*' + re.escape(label) + r'\s*</th>\s*<td\b[^>]*>([\s\S]*?)(?=</td>|<th\b)', text)
        if m:
            fields[label] = clean(m[1])
    trade = re.search(r'交易状态：(.*?)购买手续费', plain)
    result['profileFields'] = fields
    result['tradeState'] = trade[1].strip() if trade else None
    code_text = fields.get('基金代码', '')
    listed = list(dict.fromkeys(re.findall(r'(?<!\d)\d{6}(?!\d)', code_text)))
    matches = re.findall(r'(?<!\d)(\d{6})[（(]([^）)]+)[）)]', code_text)
    primary = next((c for c, label in matches if '前端' in label or '主代码' in label), None)
    alias = None
    if code in listed:
        classification = 'requested_code_in_profile'
        if primary and primary != code and any(c == code and '后端' in label for c, label in matches):
            classification = 'explicit_front_back_fee_code_relationship'
            alias = {'type': 'backend_fee_code', 'canonicalCode': primary, 'evidenceText': code_text}
    elif listed and primary:
        classification = 'primary_code_returned_but_alias_not_explicit'
    else:
        classification = 'requested_code_not_verified'
    result['identity'] = {'requestedCode': code, 'listedCodes': listed, 'primaryCode': primary,
                          'classification': classification, 'evidenceText': code_text,
                          'pageTitle': title, 'alias': alias}
    result['sourceReportedInceptionDate'] = date_from(fields.get('成立日期/规模'))
    result['issueDate'] = date_from(fields.get('发行日期'))
    top = re.search(r'成立日期：\s*(\d{4}-\d{2}-\d{2})', plain)
    result['headerReportedInceptionDate'] = date_from(top[1]) if top else None
    if not fields.get('基金全称') or not code_text:
        result.update(status='source_unavailable', reason='fund_profile_table_missing')
    elif '</html>' not in text.lower():
        result.update(status='parse_failed', reason='incomplete_html_document')
    elif code not in listed:
        result.update(status='identity_mismatch', reason='explicit_code_alias_evidence_required')
    elif result['sourceReportedInceptionDate']:
        date = result['sourceReportedInceptionDate']
        other = result['headerReportedInceptionDate']
        known = product.get('inception')
        if other and date != other:
            result.update(status='date_conflict', reason='header_table_date_disagree')
        elif known and known != date:
            result.update(status='date_conflict', reason='existing_verified_date_disagrees')
        elif date > as_of:
            result.update(status='date_conflict', reason='reported_inception_is_in_future')
        else:
            result.update(status='verified', reason='explicit_profile_inception_date', inceptionDate=date)
    elif result['issueDate'] and result['issueDate'] > as_of:
        result.update(status='not_established', reason='future_issue_date_and_no_inception')
    elif result['tradeState'] and any(x in result['tradeState'] for x in ('认购期', '发行中', '募集期', '正在发行')):
        result.update(status='not_established', reason='explicit_current_fundraising_state')
    else:
        result.update(status='not_disclosed', reason='profile_does_not_disclose_inception')
    return result


def error_record(product, as_of, status, error):
    return {'schemaVersion': SCHEMA, 'asOf': as_of, 'code': product['code'], 'name': product['name'],
            'status': status, 'reason': error, 'inceptionDate': None,
            'sourceReportedInceptionDate': None, 'issueDate': None, 'dateSemantic': SEMANTIC,
            'knownInceptionDate': product.get('inception')}


def write_audit(result):
    """Verify every saved reply and emit compact, independently inspectable audit files."""
    records = result['records']; as_of = result['asOf']; counts = Counter(); reasons = Counter()
    errors = []; raw_count = raw_bytes = verified_new = 0; aliases = []; unresolved = []
    for code, r in records.items():
        counts[r['status']] += 1; reasons[r['reason']] += 1
        if r['code'] != code or r['schemaVersion'] != SCHEMA or r['asOf'] != as_of:
            errors.append({'code': code, 'error': 'record_identity_schema_or_date'})
        if r['status'] == 'verified':
            if (not r.get('inceptionDate') or r['inceptionDate'] != r['sourceReportedInceptionDate']
                    or code not in r.get('identity', {}).get('listedCodes', []) or r['inceptionDate'] > as_of):
                errors.append({'code': code, 'error': 'verified_date_or_identity_invalid'})
            verified_new += not bool(r.get('knownInceptionDate'))
            if r['identity'].get('alias'):
                aliases.append({'code': code, 'date': r['inceptionDate'], **r['identity']['alias']})
        else:
            if r.get('inceptionDate') is not None:
                errors.append({'code': code, 'error': 'unverified_date_exposed_as_canonical'})
            unresolved.append({k: r.get(k) for k in ('code', 'name', 'status', 'reason', 'issueDate',
                                                      'sourceReportedInceptionDate', 'tradeState', 'identity')})
        e = r['evidence']
        if e.get('rawPath'):
            p = ROOT / e['rawPath']
            raw = p.read_bytes(); raw_count += 1; raw_bytes += len(raw)
            if hashlib.sha256(raw).hexdigest() != e['sha256'] or len(raw) != e['bytes']:
                errors.append({'code': code, 'error': 'raw_hash_or_size_mismatch'})
            if ROOT / 'source-cache' / (e['key'] + '.txt') != p:
                errors.append({'code': code, 'error': 'source_key_path_mismatch'})
    if len(records) != result['summary']['targetCount']:
        errors.append({'error': 'target_count_mismatch'})
    probe_path = ROOT / 'source-cache' / ('fund-profile-probes-' + as_of.replace('-', '') + '.json')
    probes = json.loads(probe_path.read_text())['records'] if probe_path.exists() else {}
    calibration = [{'code': r['code'], 'name': r['name'], 'existingDate': r['knownInceptionDate'],
                    'profileDate': r['sourceReportedInceptionDate'], 'status': r['status'],
                    'url': r['evidence']['url'], 'sha256': r['evidence']['sha256']} for r in probes.values()]
    audit = {'schemaVersion': SCHEMA, 'asOf': as_of, 'targetCodes': len(records), 'statuses': dict(counts),
             'reasons': dict(reasons), 'newVerifiedDates': verified_new,
             'verifiedCodes': [c for c, r in records.items() if r['status'] == 'verified'],
             'explicitBackendAliases': aliases, 'unresolved': unresolved, 'calibration': calibration,
             'dateSemantic': SEMANTIC, 'rawIntegrity': {'checked': raw_count, 'bytes': raw_bytes, 'errors': errors},
             'runSummary': result['summary'],
             'dailyRefresh': {'universe': 'latest directory plus snapshot, same-date batch dates fill blanks',
                              'targets': 'missing dates; same-day target manifest retained for audit/resume',
                              'knownDates': 'locked; successful dates inherited from snapshot on next day',
                              'unestablishedAndUnknown': 'refresh on next-day run; source statuses remain distinct'},
             'notModified': ['dist', 'backfill history records', 'README']}
    atomic_json(ROOT / 'docs/inception-audit.json', audit)
    labels = {'verified': '代码与日期已核验', 'not_established': '明确在募集或尚未发行',
              'not_disclosed': '概况未披露成立日', 'identity_mismatch': '代码关系尚未明确',
              'date_conflict': '日期冲突', 'source_unavailable': '概况不可用',
              'network_failed': '网络请求失败', 'parse_failed': '解析或完整性失败'}
    lines = ['# 成立日期补采审计', '', f'截至{as_of}，本轮处理{len(records):,}个目标代码。仅核验通过的日期可进入产品成立日期字段。', '',
             '| 结果 | 代码数 |', '|---|---:|']
    for status, count in counts.items(): lines.append(f'| {labels.get(status, status)} | {count:,} |')
    lines += ['', f'新增可用日期{verified_new:,}项；其余{len(records)-counts["verified"]:,}项保留具体状态，不使用发行日、净值首日或名称匹配补造日期。', '',
              '## 日期与份额口径', '', SEMANTIC, '',
              '先用已有日期校准了A/C及后设份额：招商安庆A为2019-01-31、C为2026-07-31；招商招顺A/C为2016-12-07、D为2021-05-27；工银中高等级A/B为2015-12-02、D为2024-01-05。概况按具体代码报告日期，没有统一填成基金最早日期。原有日期只作校验，未覆盖。', '',
              f'校准样本{len(calibration)}个，明细见JSON。对前后端收费代码，只有概况基金代码行同时列出两个代码并标明前端/后端才记录别名，本轮{len(aliases)}项；仅返回另一主代码而没有明确关系的记录继续待核验。', '',
              '“尚未成立”仅用于明确募集期或发行日尚未来到且成立日为空的页面；历史发行日期存在而成立日空，只记未披露。基金法律层面的合同生效日和份额新增日没有明确证据时分别留空。', '',
              '## 原始证据与校验', '',
              f'逐项核对{raw_count:,}份原始HTML响应（按.txt保存），共{raw_bytes:,}字节；SHA256、字节数、代码、日期、字段可用规则发现{len(errors)}项错误。主结果为`source-cache/fund-profiles-{as_of.replace("-", "")}.json`，每项包括URL、检索时间、原文路径、哈希及身份核验文本。', '',
              '## 日常增量策略', '',
              '读取最新基金目录，继承snapshot已知日期，再用同日批量排行明确日期填空；仅请求仍缺日期的代码。补齐成功的日期随snapshot保留，日常不重复抓全部已知日期。未成立、未披露、身份待核验和请求失败的代码在下一日刷新；同日保留目标清单和缓存用于断点续采。', '',
              '本轮只采小型概况页面并复用同日样本原文，没有重新下载历史净值。回撤重算由主流程使用既有历史数据完成。', '']
    (ROOT / 'docs/inception-audit.md').write_text('\n'.join(lines))
    if errors:
        raise ValueError('Profile evidence audit failed: ' + str(errors[:3]))
    return audit


def run(args):
    snapshot_file = ROOT / 'dist/snapshot.js'
    snapshot_raw = snapshot_file.read_bytes()
    snapshot = json.loads(snapshot_raw.decode().split('=', 1)[1].strip().rstrip(';'))
    known = {p['code']: p for p in snapshot['funds']}
    directory = Path(args.directory) if args.directory else ROOT / 'source-cache/current-directory.json'
    base = Path(args.base_refresh) if args.base_refresh else ROOT / 'source-cache' / ('base-refresh-' + args.as_of.replace('-', '') + '.json')
    all_funds = dict(known)
    input_evidence = {'snapshot': hashlib.sha256(snapshot_raw).hexdigest()}
    if directory.exists():
        directory_raw = directory.read_bytes()
        directory_data = json.loads(directory_raw)
        rows = directory_data.get('rows') or directory_data.get('funds') or []
        all_funds = {}
        for item in rows:
            if isinstance(item, list): item = {'code': item[0], 'name': item[2], 'type': item[3]}
            code = item['code']
            all_funds[code] = {**known.get(code, {}), **item}
            if known.get(code, {}).get('inception'):
                all_funds[code]['inception'] = known[code]['inception']
        input_evidence['directory'] = hashlib.sha256(directory_raw).hexdigest()
    if base.exists():
        base_raw = base.read_bytes(); base_data = json.loads(base_raw)
        # Existing snapshot dates are locked. Same-date batch dates may only fill blanks.
        if base_data.get('asOf') == args.as_of:
            for code, date in (base_data.get('inceptions') or {}).items():
                if code in all_funds and not all_funds[code].get('inception') and date and date_from(date) == date:
                    all_funds[code]['inception'] = date
            input_evidence['baseRefresh'] = hashlib.sha256(base_raw).hexdigest()
    out = Path(args.output or ROOT / 'source-cache' / ('fund-profiles-' + args.as_of.replace('-', ''))).resolve()
    for name in ('raw', 'records'):
        (out / name).mkdir(parents=True, exist_ok=True)
    if args.codes:
        selected = args.codes.split(',')
        products = [all_funds[c] for c in selected]
    else:
        selected = [p['code'] for p in all_funds.values() if not p.get('inception')]
        target_file = out / 'targets.json'
        if target_file.exists():
            frozen = json.loads(target_file.read_text())
            if frozen.get('asOf') == args.as_of:
                selected = list(dict.fromkeys([c for c in frozen['codes'] if c in all_funds] + selected))
        atomic_json(target_file, {'asOf': args.as_of, 'codes': selected, 'inputHashes': input_evidence})
        products = [all_funds[c] for c in selected]
    state = {'schemaVersion': SCHEMA, 'asOf': args.as_of, 'startedAt': now(), 'targetCount': len(products),
             'completed': 0, 'statuses': {}, 'workers': args.workers, 'networkBytes': 0, 'reusedRaw': 0,
             'reusedRecord': 0, 'snapshotSha256': hashlib.sha256(snapshot_raw).hexdigest()}
    state['inputHashes'] = input_evidence
    counts = Counter()
    started = time.monotonic()

    def worker(product):
        code = product['code']; dest = out / 'records' / (code + '.json'); file = out / 'raw' / (code + '.txt')
        if dest.exists() and not args.reparse:
            old = json.loads(dest.read_text())
            if (old.get('schemaVersion') == SCHEMA and old.get('asOf') == args.as_of
                    and old.get('name') == product['name']
                    and old.get('knownInceptionDate') == product.get('inception')):
                if old['status'] != 'network_failed' or not args.retry_failed:
                    return old, 'record'
        url = 'https://fundf10.eastmoney.com/jbgk_' + code + '.html'
        evidence = {'url': url, 'retrievedAt': None, 'sha256': None, 'bytes': 0}
        raw = None; mode = 'network'
        candidates = [file, ROOT / 'source-cache/gap-investigation-20261029' / ('jbgk-' + code + '.html')]
        for cached in candidates:
            if not cached.exists():
                continue
            source_date = dt.datetime.fromtimestamp(cached.stat().st_mtime, TZ).date().isoformat()
            if source_date != args.as_of:
                continue
            raw = cached.read_bytes(); mode = 'raw'
            if cached != file:
                shutil.copy2(cached, file)
            evidence['retrievedAt'] = dt.datetime.fromtimestamp(cached.stat().st_mtime, TZ).isoformat(timespec='seconds')
            evidence['reusedFrom'] = str(cached.relative_to(ROOT))
            break
        error = None
        unavailable = False
        if raw is None:
            for attempt in range(args.retries + 1):
                try:
                    raw, status, requests = download(url, args.timeout)
                    tmp = file.with_suffix('.tmp'); tmp.write_bytes(raw); os.replace(tmp, file)
                    evidence.update(retrievedAt=now(), httpStatus=status, requests=requests)
                    break
                except Exception as exc:
                    error = type(exc).__name__ + ':' + str(exc)
                    unavailable = isinstance(exc, urllib.error.HTTPError) and exc.code in (404, 410)
                    if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 404, 410, 429):
                        break
                    if attempt < args.retries:
                        time.sleep(.5 * (attempt + 1))
        if raw is None:
            result = error_record(product, args.as_of, 'source_unavailable' if unavailable else 'network_failed', error)
        else:
            evidence.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                            rawPath=str(file.relative_to(ROOT)),
                            key=str(file.relative_to(ROOT / 'source-cache')).removesuffix('.txt'))
            try:
                result = parse_profile(product, raw, args.as_of)
            except Exception as exc:
                result = error_record(product, args.as_of, 'parse_failed', type(exc).__name__ + ':' + str(exc))
        result['evidence'] = evidence
        result['fetchedAt'] = now()
        atomic_json(dest, result)
        return result, mode

    def report(final=False):
        state.update(statuses=dict(counts), elapsedSeconds=round(time.monotonic() - started, 1), updatedAt=now())
        atomic_json(out / 'progress.json', state)
        print(json.dumps(state, ensure_ascii=False), flush=True)
    report()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        iterator = iter(products)
        active = {pool.submit(worker, p) for p in [next(iterator, None) for _ in range(args.workers)] if p}
        last = time.monotonic()
        while active:
            done, active = cf.wait(active, timeout=5, return_when=cf.FIRST_COMPLETED)
            for future in done:
                result, mode = future.result()
                counts[result['status']] += 1; state['completed'] += 1
                if mode == 'record': state['reusedRecord'] += 1
                elif mode == 'raw': state['reusedRaw'] += 1
                else: state['networkBytes'] += result['evidence']['bytes']
                item = next(iterator, None)
                if item: active.add(pool.submit(worker, item))
            if time.monotonic() - last > 15 or (done and state['completed'] % 100 == 0):
                report(); last = time.monotonic()
    state['finishedAt'] = now(); report(True)
    records = {p['code']: json.loads((out / 'records' / (p['code'] + '.json')).read_text()) for p in products}
    sources = [{k: r['evidence'][k] for k in ('key', 'url', 'sha256', 'bytes', 'retrievedAt')}
               for r in records.values() if r['evidence'].get('rawPath')]
    result = {'schemaVersion': SCHEMA, 'asOf': args.as_of, 'records': records, 'summary': state, 'sources': sources}
    summary_path = Path(args.summary_output).resolve() if args.summary_output else out.with_suffix('.json')
    atomic_json(summary_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', default=dt.datetime.now(TZ).date().isoformat())
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--timeout', type=int, default=20)
    parser.add_argument('--retries', type=int, default=2)
    parser.add_argument('--output')
    parser.add_argument('--summary-output')
    parser.add_argument('--directory', help='Latest directory; defaults to source-cache/current-directory.json if present')
    parser.add_argument('--base-refresh', help='Same-date batch dates used to fill snapshot blanks before choosing targets')
    parser.add_argument('--codes', help='Only explicit calibration codes; default is current missing inception dates')
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--reparse', action='store_true')
    parser.add_argument('--audit-only', action='store_true', help='Verify the saved summary and write docs/inception-audit files without fetching')
    parser.add_argument('--write-audit', action='store_true', help='Verify evidence and write audit files after collection')
    args = parser.parse_args()
    if not 1 <= args.workers <= 8: parser.error('--workers must be 1..8')
    if args.audit_only:
        out = Path(args.output or ROOT / 'source-cache' / ('fund-profiles-' + args.as_of.replace('-', ''))).resolve()
        summary_path = Path(args.summary_output).resolve() if args.summary_output else out.with_suffix('.json')
        result = json.loads(summary_path.read_text())
        audit = write_audit(result)
        print(json.dumps({k: audit[k] for k in ('targetCodes', 'statuses', 'newVerifiedDates', 'rawIntegrity')}, ensure_ascii=False))
    else:
        result = run(args)
        if args.write_audit: write_audit(result)


if __name__ == '__main__':
    main()
