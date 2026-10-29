#!/usr/bin/env python3
"""Build a dated public-data snapshot. Failed sources never become zero values."""
import concurrent.futures as cf
import datetime as dt
import hashlib
import http.client
import json
import math
import pathlib
import re
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'source-cache'
CACHE.mkdir(exist_ok=True)
DIST = ROOT / 'dist'
TODAY = dt.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
EVIDENCE = []
ERRORS = []

def download(url, timeout, byte_range=None):
    headers={'User-Agent':'Mozilla/5.0','Referer':'https://fund.eastmoney.com/','Accept-Encoding':'identity'}
    if byte_range:
        headers['Range']='bytes=%s-%s'%byte_range
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        try:
            data=response.read()
        except http.client.IncompleteRead as error:
            data=error.partial
            # Some intervening responses retain the upstream Content-Length.
            # Semantic validation below, never the transport header alone,
            # decides whether a complete public-data response is usable.
        return data,response.status,response.headers.get('Content-Range','')

def ranged_download(url):
    first,status,content_range=download(url,25,(0,1023))
    if status!=206:
        return first
    total=int(content_range.rsplit('/',1)[1])
    chunks={0:first}
    def part(start):
        end=min(total-1,start+65535)
        cache=CACHE/(hashlib.sha256(url.encode()).hexdigest()[:12]+'-'+str(start)+'.part')
        if cache.exists() and cache.stat().st_size==end-start+1:return start,cache.read_bytes()
        data=b'';failures=0
        while start+len(data)<=end:
            position=start+len(data)
            try:
                raw,status,header=download(url,35,(position,end))
                if status!=206 or not raw or len(raw)>end-position+1 or not header.startswith('bytes '+str(position)+'-') or not header.endswith('/'+str(total)):
                    raise ValueError('invalid or changed byte range')
                data+=raw
            except Exception:
                failures+=1
                if failures>=6:raise
                time.sleep(.3+failures*.2)
        cache.write_bytes(data)
        return start,data
    with cf.ThreadPoolExecutor(max_workers=8) as executor:
        for start,raw in executor.map(part,range(len(first),total,65536)):
            chunks[start]=raw
    raw=b''.join(chunks[start] for start in sorted(chunks))
    if len(raw)!=total:
        raise ValueError('incomplete ranged file')
    return raw

def fetch(url, key, timeout=180):
    file = CACHE / (key + '.txt')
    if file.exists():
        raw = file.read_bytes()
    else:
        for attempt in range(3):
            try:
                if key=='directory' or key.startswith('detail-'):
                    raw=ranged_download(url)
                else:
                    attempt_url=url+('&v='+str(time.time_ns()) if attempt else '')
                    raw,_,_=download(attempt_url,timeout)
                decoded=raw.decode('utf-8-sig')
                if key=='directory':
                    rows=array(decoded,'r')
                    if not rows or not decoded.rstrip().endswith(';'):raise ValueError('incomplete directory')
                elif key.startswith('returns-'):
                    array(decoded,'datas')
                    if not decoded.rstrip().endswith(';'):raise ValueError('incomplete return response')
                elif key.startswith('money-'):
                    json.loads(decoded)
                elif key.startswith('company-'):
                    array(decoded,'datas')
                    if not decoded.rstrip().endswith('}'):raise ValueError('incomplete company response')
                elif key.startswith('detail-'):
                    if extract(decoded,'Data_netWorthTrend') is None or extract(decoded,'Data_fluctuationScale') is None:
                        raise ValueError('incomplete detail series')
                file.write_bytes(raw)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
    EVIDENCE.append({'key': key, 'url': url, 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest()})
    return raw.decode('utf-8-sig')

def array(text, name):
    match = re.search(r'(?:["\']?' + re.escape(name) + r'["\']?)\s*[:=]\s*', text)
    if not match:
        raise ValueError('missing ' + name)
    return json.JSONDecoder().raw_decode(text[match.end():].lstrip())[0]

def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def share(name):
    match = re.search(r'([ABCDEHIJNPQRSXY])(?:[（(](?:人民币|美元)[）)])?$', name)
    return match.group(1) if match else '_'

def family_name(name):
    # Keep ETF vs link, hedged vs unhedged and currencies separate.
    return re.sub(r'([ABCDEHIJNPQRSXY])(?=([（(](?:人民币|美元)[）)])?$)', '', name)

def extract(text, name):
    match = re.search(r'\bvar\s+' + re.escape(name) + r'\s*=\s*(.*?);', text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None

def detail(code):
    raw = fetch('https://fund.eastmoney.com/pingzhongdata/' + code + '.js', 'detail-' + code, 35)
    info = {k: extract(raw, k) for k in [
        'Data_netWorthTrend', 'Data_grandTotal', 'Data_fluctuationScale',
        'Data_currentFundManager', 'Data_holderStructure', 'Data_millionCopiesIncome',
        'Data_sevenDaysYearIncome', 'syl_1n', 'syl_6y', 'syl_3y', 'syl_1y']}
    info = {k: v for k, v in info.items() if v is not None}
    return code, info

def company(item):
    company_id, name = item
    url = 'https://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx?' + urllib.parse.urlencode({
        't': 1, 'lx': 1, 'letter': '', 'gsid': company_id, 'text': '',
        'sort': 'zdf,desc', 'page': '1,500', 'dt': TODAY, 'atfc': '', 'onlySale': 0})
    text = fetch(url, 'company-' + company_id, 45)
    rows = array(text, 'datas')
    record = re.search(r'record\s*:\s*["\']?(\d+)', text)
    if record and len(rows) < int(record.group(1)):
        count=int(record.group(1))
        for page in range(2,math.ceil(count/500)+1):
            next_url=url.replace('page=1%2C500','page='+str(page)+'%2C500')
            rows.extend(array(fetch(next_url,'company-'+company_id+'-'+str(page),45),'datas'))
        if len(rows)!=count:raise ValueError(name+' incomplete company list')
    return company_id, name, rows

def fetch_ranks(params):
    params={**params,'pn':500}
    def page(index):
        url='https://fund.eastmoney.com/data/rankhandler.aspx?'+urllib.parse.urlencode({**params,'pi':index})
        return fetch(url,'returns-'+TODAY+'-'+str(index),60)
    first=page(1)
    total=int(re.search(r'allRecords\s*:\s*(\d+)',first).group(1))
    pages={1:array(first,'datas')}
    with cf.ThreadPoolExecutor(max_workers=5) as executor:
        jobs={executor.submit(page,i):i for i in range(2,math.ceil(total/500)+1)}
        for job in cf.as_completed(jobs):
            try:pages[jobs[job]]=array(job.result(),'datas')
            except Exception as error:ERRORS.append({'source':'return page '+str(jobs[job]),'error':str(error)})
    ordered=sorted(pages,key=lambda i:(CACHE/('returns-'+TODAY+'-'+str(i)+'.txt')).stat().st_mtime)
    by_code={};duplicates=0
    for i in ordered:
        for row in pages[i]:
            fields=row.split(',');old=by_code.get(fields[0])
            if old:
                duplicates+=1
                if len(old.split(','))>3 and fields[3]<old.split(',')[3]:continue
            by_code[fields[0]]=row
    rows=list(by_code.values())
    if duplicates:
        ERRORS.append({'source':'return pagination','kind':'source_changed_between_pages',
                       'error':str(duplicates)+' duplicate codes during source updates; kept newest NAV date, then newest retrieved response'})
    if len(rows)!=total:
        ERRORS.append({'source':'return pagination','error':'Received '+str(len(rows))+' of '+str(total)+' source records; missing values remain blank'})
    return 'var rankData = '+json.dumps({'datas':rows,'allRecords':total},ensure_ascii=False)+';'

def main():
    print('Loading full-market directory and dated return data…', flush=True)
    with cf.ThreadPoolExecutor(max_workers=3) as executor:
        pool_job = executor.submit(fetch, 'https://fund.eastmoney.com/js/fundcode_search.js', 'directory', 300)
        params = {'op': 'ph', 'dt': 'kf', 'ft': 'all', 'rs': '', 'gs': 0,
                  'sc': 'zzf', 'st': 'desc', 'sd': str(dt.date.fromisoformat(TODAY)-dt.timedelta(days=366)),
                  'ed': TODAY, 'qdii': '', 'tabSubtype': ',,,,,', 'pi': 1, 'pn': 30000, 'dx': 1}
        rank_url = 'https://fund.eastmoney.com/data/rankhandler.aspx?' + urllib.parse.urlencode(params)
        rank_job = executor.submit(fetch_ranks, params)
        company_job = executor.submit(fetch, 'https://fund.eastmoney.com/js/jjjz_gs.js', 'companies', 60)
        pool_text = pool_job.result()
        rows = array(pool_text, 'r')
        funds = {str(row[0]).zfill(6): {
            'code': str(row[0]).zfill(6), 'name': row[2], 'type': row[3],
            'shareClass': share(row[2]), 'source': '天天基金公开目录',
            'sourceUpdatedAt': TODAY, 'scale': None, 'manager': None,
            'company': None, 'companyId': None} for row in rows if len(row) >= 4}
        print('Directory:', len(funds), 'share codes; REITs:', sum('REIT' in p['name'].upper() or 'REIT' in p['type'].upper() for p in funds.values()), flush=True)
        rank_text = rank_job.result()
        ranks = array(rank_text, 'datas')
        total = re.search(r'allRecords\s*:\s*(\d+)', rank_text)
        if total and len(ranks) != int(total.group(1)):
            print('Return coverage:',len(ranks),'/',int(total.group(1)),flush=True)
        perf = {}
        for row in ranks:
            f = row.split(',')
            if len(f) < 15 or f[0] not in funds:
                continue
            code = f[0]
            money = '货币' in funds[code]['type']
            perf[code] = {key: number(f[index]) for key, index in
                          [('d1',6),('w1',7),('m1',8),('m3',9),('m6',10),('y1',11),('ytd',14),('dwjz',4)]}
            perf[code]['jzrq'] = f[3]
            if money:
                perf[code].update(wfsy=number(f[6]),qrnh=number(f[7]),d1=None,w1=None,dwjz=None)
            if len(f) > 16:
                funds[code]['inception'] = f[16]
        company_list = array(company_job.result(), 'op')
    print('Returns:', len(perf), '; company directories:', len(company_list), flush=True)
    checkpoint={'meta':{'updatedAt':dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
                        'historyCount':0,'processing':True,'errors':ERRORS},'funds':list(funds.values()),'perf':perf,'details':{},'realtime':{}}
    (DIST/'snapshot.js').write_text('window.MARKET_SNAPSHOT='+json.dumps(checkpoint,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf8')
    ok = 0
    with cf.ThreadPoolExecutor(max_workers=6) as executor:
        jobs = {executor.submit(company, item): item for item in company_list}
        for job in cf.as_completed(jobs):
            item = jobs[job]
            try:
                company_id, name, members = job.result()
                for row in members:
                    code = str(row[0]).zfill(6)
                    if code in funds:
                        funds[code].update(company=name, companyId=company_id)
                        if len(row) > 9:
                            funds[code]['purchaseStatus'] = row[9]
                ok += 1
            except Exception as e:
                ERRORS.append({'source': 'company ' + str(item[0]), 'error': str(e)})
            if (ok + len(ERRORS)) % 25 == 0:
                print('Company directories checked:', ok + len(ERRORS), '/', len(company_list), flush=True)
    # A compact, diversified history snapshot; the complete directory and batch
    # returns remain available for all funds. Coverage is disclosed in the UI.
    selected = []
    for pattern in ['股票', '混合', '债券', '货币', 'QDII', 'FOF', 'REIT', '指数']:
        candidates = [p for p in funds.values() if pattern.lower() in (p['type'] + p['name']).lower() and p['shareClass'] in ('A','_')]
        chosen = set()
        for p in candidates:
            firm = p.get('companyId') or p['code']
            if firm in chosen:
                continue
            chosen.add(firm)
            selected.append(p['code'])
            if len(chosen) >= 10:
                break
    selected += ['000001','110022','161725','012414','510300','510500','159915','000198','000216','000248','001180','508000','180101']
    selected = list(dict.fromkeys(c for c in selected if c in funds))
    details = {}
    print('Building offline history snapshot:', len(selected), 'funds…', flush=True)
    with cf.ThreadPoolExecutor(max_workers=4) as executor:
        jobs = {executor.submit(detail, code): code for code in selected}
        for job in cf.as_completed(jobs):
            try:
                code, info = job.result()
                if info:
                    details[code] = info
            except Exception as e:
                ERRORS.append({'source':'detail ' + jobs[job], 'error':str(e)})
    families = {}
    for p in funds.values():
        # Verified company id participates when available; fund short names are
        # complete product names, including the manager brand prefix.
        key = (p.get('companyId') or '', family_name(p['name']))
        p['familyId'] = '|'.join(key)
        families.setdefault(key, []).append(p)
    order = {'A':0, '_':1, 'B':2, 'C':3, 'E':4, 'Y':9}
    for members in families.values():
        members.sort(key=lambda p:(order.get(p['shareClass'],5),p['code']))
        for i,p in enumerate(members):
            p['isPrimary'] = i == 0
    stamp = dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    snapshot = {'meta':{'updatedAt':stamp,'directoryCount':len(funds),'fundFamilyCount':len(families),
                        'returnCount':len(perf),'companyMappedCount':sum(bool(p['companyId']) for p in funds.values()),
                        'companyCount':len({p['companyId'] for p in funds.values() if p['companyId']}),
                        'companySourcesSucceeded':ok,'companySourcesTotal':len(company_list),
                        'historyCount':len(details),'sources':EVIDENCE,'errors':ERRORS,
                        'note':'目录、收益及公司映射来自公开接口；历史净值仅预存部分产品，查看详情时联网补充。'},
                'funds':list(funds.values()),'perf':perf,'details':details,'realtime':{}}
    output = json.dumps(snapshot, ensure_ascii=False, separators=(',',':'),allow_nan=False)
    (DIST/'snapshot.js').write_text('window.MARKET_SNAPSHOT='+output+';\n',encoding='utf8')
    (ROOT/'docs'/'data-audit.json').write_text(json.dumps(snapshot['meta'],ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in snapshot['meta'].items() if k not in ('sources','errors')},ensure_ascii=False),flush=True)
    print('Saved snapshot.js:', len(output.encode('utf8')), 'bytes;',len(ERRORS),'source failures',flush=True)

if __name__ == '__main__':
    main()
