#!/usr/bin/env python3
"""Refresh public batch returns and preserve verified company-cache NAV fallbacks.

Outputs an independent, auditable file; never modifies dist or overwrites newer
per-fund details. Each response is cached only after complete semantic parsing.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import math
import re
import time
import urllib.parse
from pathlib import Path
from zoneinfo import ZoneInfo

from collect_data import array, download, number

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'source-cache'
TODAY = dt.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
SOURCES = []
ERRORS = []


def stamp():
    return dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')


def rank_parse(text):
    if not text.rstrip().endswith(';'):
        raise ValueError('truncated ranking response')
    rows = array(text, 'datas')
    total = re.search(r'allRecords\s*:\s*(\d+)', text)
    if not total or not isinstance(rows, list):
        raise ValueError('ranking total or rows missing')
    if any(len(str(row).split(',')) < 17 or not re.fullmatch(r'\d{6}', str(row).split(',')[0]) for row in rows):
        raise ValueError('ranking row structure invalid')
    return {'rows': rows, 'total': int(total[1])}


def money_parse(text):
    data = json.loads(text)
    if data.get('ErrCode') != 0 or not isinstance(data.get('Data'), list):
        raise ValueError('money ranking error or missing rows')
    return {'rows': data['Data'], 'total': int(data['TotalCount'])}


def fetch(url, key, parse, cache_dir):
    file = cache_dir / (key + '.txt')
    last_error = None
    for attempt in range(3):
        try:
            if attempt == 0 and file.exists():
                raw = file.read_bytes()
                retrieved_at = dt.datetime.fromtimestamp(file.stat().st_mtime, ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
            else:
                raw, status, content_range = download(url, 25)
                if content_range:
                    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', content_range)
                    if not match or int(match[1]) != 0:
                        raise ValueError('unexpected partial response')
                    total = int(match[3])
                    while len(raw) < total:
                        start = len(raw)
                        end = min(total - 1, start + 32767)
                        chunk, status, header = download(url, 25, (start, end))
                        if status != 206 or not header.startswith(f'bytes {start}-') or not header.endswith('/' + str(total)) or not chunk:
                            raise ValueError('invalid continuation range')
                        raw += chunk
                    if len(raw) != total:
                        raise ValueError('response length mismatch')
                retrieved_at = stamp()
            parsed = parse(raw.decode('utf-8-sig'))
            if attempt != 0 or not file.exists():
                file.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            original_key = str(file.relative_to(CACHE)).removesuffix('.txt')
            versioned = file.with_name(file.stem + '.sha256-' + digest + '.txt')
            if versioned.exists():
                if versioned.read_bytes() != raw:
                    raise ValueError('immutable_source_evidence_mismatch')
            else:
                versioned.write_bytes(raw)
            evidence = {'key': str(versioned.relative_to(CACHE)).removesuffix('.txt'),
                        'originalKey': original_key, 'url': url, 'bytes': len(raw),
                        'sha256': digest, 'retrievedAt': retrieved_at}
            SOURCES.append(evidence)
            return parsed
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(.5 + attempt)
    raise RuntimeError(f'{key}: {last_error}')


def parallel_pages(indices, fn, workers):
    pages = {}
    failures = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        jobs = {executor.submit(fn, page): page for page in indices}
        for job in cf.as_completed(jobs):
            page = jobs[job]
            try:
                pages[page] = job.result()
            except Exception as error:
                failures[page] = str(error)
            if (len(pages) + len(failures)) % 10 == 0:
                print(f'Pages complete {len(pages)}, failed {len(failures)} / {len(indices)}', flush=True)
    # A failed page is retried after the other pages; transient failures must not
    # silently become a smaller universe.
    for page in list(failures):
        try:
            pages[page] = fn(page)
            del failures[page]
        except Exception as error:
            failures[page] = str(error)
    return pages, failures


def ranking(params, directory, args, cache_dir):
    def get_page(page, pass_id=0, size=None, order='asc'):
        p = {**params, 'pi': page, 'pn': size or args.page_size, 'sc': 'dm', 'st': order}
        url = 'https://fund.eastmoney.com/data/rankhandler.aspx?' + urllib.parse.urlencode(p)
        return fetch(url, f'rank-pass{pass_id}-p{page}-n{p["pn"]}-{order}', rank_parse, cache_dir)

    probes = [get_page(1, size=10), get_page(2, size=10), get_page(1, size=10, order='desc')]
    asc = [[r.split(',')[0] for r in x['rows']] for x in probes[:2]]
    desc = [r.split(',')[0] for r in probes[2]['rows']]
    sort_ok = all(a == sorted(a) for a in asc) and asc[0][-1] < asc[1][0] and desc == sorted(desc, reverse=True) and desc[0] > asc[0][0]
    if not sort_ok:
        raise ValueError('Requested code ordering was not observed; refusing unstable pagination')
    sort_probe = {'parameter': 'sc=dm', 'ascPage1': asc[0], 'ascPage2': asc[1], 'descPage1': desc, 'verified': True}
    combined = {}
    pass_reports = []
    for pass_id in range(args.passes):
        first = get_page(1, pass_id)
        count = math.ceil(first['total'] / args.page_size)
        print(f'Non-money sweep {pass_id + 1}: declared {first["total"]}, {count} pages', flush=True)
        pages, failures = parallel_pages(list(range(2, count + 1)), lambda page: get_page(page, pass_id), args.workers)
        pages[1] = first
        by_code = {}
        duplicates = 0
        declarations = []
        for page in sorted(pages):
            result = pages[page]
            declarations.append(result['total'])
            codes = [r.split(',')[0] for r in result['rows']]
            if codes != sorted(codes):
                raise ValueError(f'Ranking code order changed at page {page}')
            for row in result['rows']:
                fields = row.split(',')
                code = fields[0]
                if code in by_code:
                    duplicates += 1
                old = by_code.get(code)
                if old is None or fields[3] >= old.split(',')[3]:
                    by_code[code] = row
                old = combined.get(code)
                if old is None or fields[3] >= old.split(',')[3]:
                    combined[code] = row
        complete = not failures and not duplicates and len(set(declarations)) == 1 and len(by_code) == declarations[0]
        report = {'pass': pass_id + 1, 'declaredCountMin': min(declarations), 'declaredCountMax': max(declarations),
                  'pageCount': count, 'pagesSucceeded': len(pages), 'failedPages': failures,
                  'uniqueCount': len(by_code), 'duplicateRows': duplicates, 'complete': complete}
        pass_reports.append(report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        if complete:
            # An internally consistent full sweep is the current ranking view.
            # Do not retain rows removed between sweeps.
            combined = by_code
            break
    last = pass_reports[-1]
    if not last['complete']:
        ERRORS.append({'source': 'non-money ranking', 'kind': 'incomplete_or_source_changed', 'detail': last})
    perf = {}
    inceptions = {}
    for code, row in combined.items():
        if code not in directory:
            continue
        f = row.split(',')
        values = {key: number(f[index]) for key, index in [('d1', 6), ('w1', 7), ('m1', 8), ('m3', 9),
                  ('m6', 10), ('y1', 11), ('ytd', 14), ('dwjz', 4)]}
        values.update(jzrq=f[3], source='天天基金批量业绩', sourceType='rankhandler', retrievedAt=stamp())
        if '货币' in directory[code][3]:
            # Money funds are handled only by the separate official money view.
            continue
        perf[code] = values
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', f[16]):
            inceptions[code] = f[16]
    return perf, inceptions, {'sortProbe': sort_probe, 'passes': pass_reports,
                             'uniqueCount': len(combined), 'directoryMatched': len(perf), 'complete': last['complete']}


def money_ranking(directory, args, cache_dir):
    def get_page(page):
        params = {'intCompany': 0, 'MinsgType': '', 'IsSale': 0, 'strSortCol': 'FCODE',
                  'orderType': 'asc', 'pageIndex': page, 'pageSize': 100}
        url = 'https://api.fund.eastmoney.com/FundRank/GetHbRankList?' + urllib.parse.urlencode(params)
        return fetch(url, 'money-p' + str(page), money_parse, cache_dir)
    first = get_page(1)
    count = math.ceil(first['total'] / 100)
    pages, failures = parallel_pages(list(range(2, count + 1)), get_page, args.workers)
    pages[1] = first
    rows = {}
    duplicates = 0
    observed_codes = []
    for page in sorted(pages):
        page_codes = [row['FCODE'] for row in pages[page]['rows']]
        if page_codes != sorted(page_codes):
            raise ValueError(f'Money ranking ignored ascending FCODE order on page {page}')
        observed_codes.extend(page_codes)
        for row in pages[page]['rows']:
            code = row['FCODE']
            duplicates += code in rows
            if code not in rows or row.get('FSRQ', '') >= rows[code].get('FSRQ', ''):
                rows[code] = row
    declarations = [p['total'] for p in pages.values()]
    sort_ok = observed_codes == sorted(observed_codes)
    if not sort_ok:
        raise ValueError('Money ranking page boundaries are not in ascending FCODE order')
    complete = not failures and not duplicates and len(set(declarations)) == 1 and len(rows) == declarations[0]
    report = {'declaredCountMin': min(declarations), 'declaredCountMax': max(declarations), 'uniqueCount': len(rows),
              'duplicateRows': duplicates, 'failedPages': failures, 'complete': complete,
              'sortVerified': sort_ok, 'sortParameter': 'strSortCol=FCODE&orderType=asc'}
    if not complete:
        ERRORS.append({'source': 'money ranking', 'kind': 'incomplete_or_source_changed', 'detail': report})
    result = {}
    for code, row in rows.items():
        if code not in directory:
            continue
        result[code] = {'jzrq': row['FSRQ'], 'wfsy': number(row.get('DWJZ')), 'qrnh': number(row.get('LJJZ')),
                        'm1': number(row.get('SYL_Y')), 'm3': number(row.get('SYL_3Y')), 'm6': number(row.get('SYL_6Y')),
                        'y1': number(row.get('SYL_1N')), 'ytd': number(row.get('SYL_JN')),
                        'd1': None, 'w1': None, 'dwjz': None, 'mdd': None, 'ytdMdd': None,
                        'source': '天天基金货币基金业绩', 'sourceType': 'GetHbRankList', 'retrievedAt': stamp()}
    report['directoryMatched'] = len(result)
    print('Money ranking: ' + json.dumps(report, ensure_ascii=False), flush=True)
    return result, report


def company_fallback(directory, current_perf):
    result = {}
    mapping_checks = []
    files_ok = 0
    for file in sorted(CACHE.glob('company-*.txt')):
        try:
            raw = file.read_bytes()
            text = raw.decode('utf-8-sig')
            if not text.rstrip().endswith('}'):
                raise ValueError('incomplete cached response')
            rows = array(text, 'datas')
            days = array(text, 'showday')
            if not days or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(days[0])):
                raise ValueError('showday date missing')
            digest = hashlib.sha256(raw).hexdigest()
            for row in rows:
                if len(row) < 9 or row[0] not in directory or '货币' in directory[row[0]][3]:
                    continue
                code = row[0]
                nav, change = number(row[3]), number(row[8])
                if nav is None or nav <= 0:
                    continue
                pf = current_perf.get(code, {})
                if pf.get('jzrq') == days[0] and pf.get('dwjz') is not None:
                    if abs(pf['dwjz'] - nav) > 0.000001:
                        continue
                    if len(mapping_checks) < 10:
                        mapping_checks.append({'code': code, 'date': days[0], 'companyNav': nav,
                                               'rankingNav': pf['dwjz'], 'companyD1': change, 'rankingD1': pf.get('d1')})
                candidate = {'dwjz': nav, 'd1': change, 'jzrq': days[0],
                             'sourceType': 'company-cache', 'sourceFile': str(file.relative_to(ROOT)),
                             'sourceHash': digest, 'fallbackOnly': True}
                old = result.get(code)
                if old is None or candidate['jzrq'] > old['jzrq']:
                    result[code] = candidate
            files_ok += 1
        except Exception as error:
            ERRORS.append({'source': file.name, 'kind': 'cached_company_parse_failed', 'error': str(error)})
    if result and not mapping_checks:
        raise ValueError('No overlapping NAV observations verified company-column mapping')
    report = {'filesParsed': files_ok, 'codesWithNav': len(result), 'mappingChecks': mapping_checks,
              'mapping': {'code': 0, 'name': 1, 'dwjz': 3, 'd1': 8, 'jzrq': 'showday[0]'},
              'mergeRule': 'fallback only; do not overwrite newer fields or dates'}
    return result, report


def check_year_boundary(perf, as_of):
    excluded = []
    for code, values in perf.items():
        date = values.get('jzrq') or ''
        if values.get('ytd') is None:
            continue
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) or date[:4] != as_of[:4]:
            reason = 'missing_nav_date' if not date else 'stopped_before_year'
            excluded.append({'code': code, 'sourceDate': date or None, 'sourceYtd': values['ytd'], 'reason': reason})
            values['ytd'] = None
            state = {'status': 'missing', 'reason': reason}
            if date:
                state['asOf'] = date
            values.setdefault('fieldStatus', {})['ytd'] = state
    return {'asOfYear': as_of[:4], 'excludedYtd': excluded}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--page-size', type=int, default=200)
    parser.add_argument('--passes', type=int, default=3)
    parser.add_argument('--output', type=Path, default=CACHE / ('base-refresh-' + TODAY.replace('-', '') + '.json'))
    args = parser.parse_args()
    if not 1 <= args.workers <= 8 or not 10 <= args.page_size <= 500 or not 1 <= args.passes <= 3:
        parser.error('workers 1–8, page-size 10–500, passes 1–3 required')
    source = json.loads((CACHE / 'current-directory.json').read_text())
    directory = {row[0]: row for row in source['rows']}
    cache_dir = CACHE / ('base-refresh-' + TODAY)
    cache_dir.mkdir(exist_ok=True)
    params = {'op': 'ph', 'dt': 'kf', 'ft': 'all', 'rs': '', 'gs': 0,
              'sd': str(dt.date.fromisoformat(TODAY) - dt.timedelta(days=366)), 'ed': TODAY,
              'qdii': '', 'tabSubtype': ',,,,,', 'dx': 1}
    perf, inceptions, ranking_report = ranking(params, directory, args, cache_dir)
    money, money_report = money_ranking(directory, args, cache_dir)
    perf.update(money)
    year_report = check_year_boundary(perf, TODAY)
    fallback, fallback_report = company_fallback(directory, perf)
    output = {'asOf': TODAY, 'retrievedAt': stamp(), 'directoryCount': len(directory), 'perf': perf,
              'inceptions': inceptions, 'companyFallback': fallback, 'sources': SOURCES, 'errors': ERRORS,
              'directorySource': {k: v for k, v in source.items() if k != 'rows'},
              'integrity': {'ranking': ranking_report, 'money': money_report, 'companyFallback': fallback_report,
                            'yearBoundary': year_report}}
    temporary = args.output.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
    temporary.replace(args.output)
    print(json.dumps({'output': str(args.output), 'perfCount': len(perf), 'fallbackCount': len(fallback),
                      'errors': len(ERRORS), 'sources': len(SOURCES),
                      'rankingComplete': ranking_report['complete'], 'moneyComplete': money_report['complete']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
