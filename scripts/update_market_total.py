#!/usr/bin/env python3
"""Refresh the official whole-market AUM card from the latest AMAC monthly PDF.

Keeps the previous verified JSON unchanged on any download or parsing failure.
The card is independent of the loaded product directory and current filters.
Requires pypdf; the downloaded source PDF and index HTML are retained for audit.
"""
import argparse
import calendar
import datetime as dt
import hashlib
import html
import io
import json
import re
import time
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
INDEX_URL = 'https://www.amac.org.cn/index/sytjbg/'
REPORT_NAME = re.compile(r'公募基金市场数据[（(]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*[）)]')


def download(url):
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, timeout=25) as response:
                content = response.read()
            if not content:
                raise ValueError('empty response')
            return content
        except Exception as error:
            last_error = error
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f'Cannot obtain official source: {url}: {last_error}')


def text_only(fragment):
    return html.unescape(re.sub(r'<[^>]*>', ' ', fragment))


def latest_report(index_bytes, today):
    index = index_bytes.decode('utf-8-sig')
    records = []
    # The index has dated <li> entries as well as an undated navigation copy.
    # Use the dated entries, rather than inventing a date from the PDF filename.
    for block in re.findall(r'<li\b[^>]*>([\s\S]*?)</li>', index, flags=re.I):
        clean = text_only(block)
        published = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', clean)
        if not published:
            continue
        for href, label in re.findall(r'<a\b[^>]*href=[\"\']([^\"\']+)[\"\'][^>]*>([\s\S]*?)</a>', block, flags=re.I):
            title = text_only(label)
            match = REPORT_NAME.search(title)
            if not match:
                continue
            url = urllib.parse.urljoin(INDEX_URL, html.unescape(href))
            parsed = urllib.parse.urlparse(url)
            if parsed.hostname != 'www.amac.org.cn' or not parsed.path.lower().endswith('.pdf'):
                continue
            year, month = map(int, match.groups())
            as_of = dt.date(year, month, calendar.monthrange(year, month)[1])
            published_at = dt.date.fromisoformat(published[1])
            if as_of > today or published_at > today:
                continue
            records.append({'asOf': as_of.isoformat(), 'publishedAt': published_at.isoformat(),
                            'sourceUrl': url, 'reportTitle': match[0]})
    if not records:
        raise ValueError('No dated monthly PDF found on the official AMAC index')
    return max(records, key=lambda row: (row['asOf'], row['publishedAt']))


def parse_report(pdf_bytes, selected):
    if not pdf_bytes.startswith(b'%PDF-'):
        raise ValueError('Official response is not a PDF')
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    heading = REPORT_NAME.search(text)
    if not heading:
        raise ValueError('Monthly report heading was not extractable')
    year, month = map(int, heading.groups())
    expected = dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    if expected != selected['asOf']:
        raise ValueError('Index date and report period disagree')
    stated = re.search(r'公募基金资产净值合计\s*([\d.]+)\s*万亿元', text)
    # The total row is: number of funds, shares, NAV, prior-period fields.
    total = re.search(r'全部\s+([\d,]+)\s+([\d,.]+)\s+([\d,.]+)', text)
    managers = re.search(r'公募基金管理机构共\s*(\d+)\s*家', text)
    if not stated or not total:
        raise ValueError('AUM prose or exact total row is missing; previous value retained')
    exact_yi = Decimal(total[3].replace(',', ''))
    precise_trillion = exact_yi / Decimal(10000)
    reported_trillion = Decimal(stated[1])
    if exact_yi <= 0 or abs(precise_trillion - reported_trillion) > Decimal('0.005'):
        raise ValueError('Rounded headline and exact total row disagree')
    result = {
        **selected,
        'totalTrillionYuan': float(reported_trillion),
        'totalYiYuan': float(exact_yi),
        'preciseTrillionYuan': float(precise_trillion),
        'fundCount': int(total[1].replace(',', '')),
        'managerCount': int(managers[1]) if managers else None,
        'sourceName': '中国证券投资基金业协会',
        'indexUrl': INDEX_URL,
        'sourceHash': hashlib.sha256(pdf_bytes).hexdigest(),
        'sourceBytes': len(pdf_bytes),
        'sourcePages': len(reader.pages),
        'scope': '境内公募基金资产净值；基金数量不含已向证监会报送清盘的基金',
        'unit': '万亿元',
        'displayDecimals': 2,
        'roundingNote': '精确净值以亿元保存，换算为万亿元后显示两位小数',
    }
    return result, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs' / 'market-total.json')
    args = parser.parse_args()
    now = dt.datetime.now(ZoneInfo('Asia/Shanghai'))
    index_bytes = download(INDEX_URL)
    selected = latest_report(index_bytes, now.date())
    pdf_bytes = download(selected['sourceUrl'])
    result, report_text = parse_report(pdf_bytes, selected)
    result['verifiedAt'] = now.isoformat(timespec='seconds')
    result['indexHash'] = hashlib.sha256(index_bytes).hexdigest()
    evidence = ROOT / 'source-cache' / 'official-market-total'
    evidence.mkdir(parents=True, exist_ok=True)
    period = selected['asOf'][:7]
    pdf_file = evidence / f'amac-{period}.pdf'
    text_file = evidence / f'amac-{period}.txt'
    index_file = evidence / f'index-{now.date()}.html'
    pdf_file.write_bytes(pdf_bytes)
    text_file.write_text(report_text, encoding='utf-8')
    index_file.write_bytes(index_bytes)
    result['evidenceFiles'] = [str(p.relative_to(ROOT)) for p in (pdf_file, text_file, index_file)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + '.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(args.output)
    print(json.dumps({key: result[key] for key in ('totalTrillionYuan', 'totalYiYuan', 'asOf',
          'publishedAt', 'sourceUrl', 'sourceHash')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
