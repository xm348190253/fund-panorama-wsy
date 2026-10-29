#!/usr/bin/env python3
"""Build the normal self-contained page and a fixed offline sharing page."""
import argparse
import html as html_module
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFLINE = '公募基金_本地离线版.html'
SHARE = '公募基金_领导分享版.html'


def inline_script(text):
    return '<script>' + re.sub(r'</script', r'<\\/script', text, flags=re.I) + '</script>'


def snapshot_metadata(root):
    source = (root / 'dist/snapshot.js').read_text()
    return json.loads(source.split('=', 1)[1].strip().removesuffix(';'))['meta']


def standalone_html(root):
    dist = root / 'dist'
    html = (dist / 'index.html').read_text()
    script = lambda name: inline_script((dist / name).read_text())
    html = html.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n' + script('echarts.min.js'), 1)
    html = html.replace('<link rel="preload" as="script" href="echarts.min.js">', '')
    html = re.sub(r'<link[^>]+rel="(?:preconnect|dns-prefetch)"[^>]*>', '', html)
    html = re.sub(r'<script src="(snapshot(?:-perf-\d+)?\.js)"></script>', lambda match: script(match.group(1)), html)
    html = html.replace('<script src="market.js"></script>', script('market.js'))
    if re.search(r'<script\b[^>]*\bsrc\s*=', html, re.I):
        raise ValueError('Self-contained page still contains an external script')
    return html


def restricted_html(html, meta, *, same_origin_assets=False):
    """Enable the supported offline flag and block external resources with CSP."""
    sources = "'self' 'unsafe-inline'" if same_origin_assets else "'unsafe-inline'"
    images = "'self' data: blob:" if same_origin_assets else 'data: blob:'
    policy = ("default-src 'none'; script-src " + sources + "; style-src 'unsafe-inline'; "
              "img-src " + images + "; font-src data:; connect-src 'none'; media-src 'none'; "
              "object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'")
    as_of = str((meta.get('collection') or {}).get('asOf') or meta.get('updatedAt', '')[:10])
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', as_of):
        raise ValueError('A valid snapshot date is required for restricted distribution')
    label = '内网快照版' if same_origin_assets else '离线快照版'
    banner = f'{label} · 数据快照 {as_of} · 不连接外部数据源'
    config = {'snapshotDate': as_of, 'mode': 'intranet' if same_origin_assets else 'offline',
              'directoryCount': meta.get('directoryCount')}
    bootstrap = """window.__FUND_OFFLINE__=true;
window.__FUND_DELIVERY__=CONFIG;
// External source URLs remain citations; this distribution does not navigate to them.
function stopExternalSource(event){
  const anchor=event.target&&event.target.closest?event.target.closest('a[href]'):null;
  if(!anchor||!/^https?:/i.test(anchor.getAttribute('href')||''))return;
  event.preventDefault();event.stopImmediatePropagation();
  if(typeof showToast==='function')showToast('当前为固定快照，外部来源网址仅供核验。','info');
}
document.addEventListener('click',stopExternalSource,true);
document.addEventListener('auxclick',stopExternalSource,true);
""".replace('CONFIG', json.dumps(config, ensure_ascii=False).replace('<', '\\u003c'))
    head = ('<meta http-equiv="Content-Security-Policy" content="' + html_module.escape(policy, quote=True) + '">\n'
            '<meta name="referrer" content="no-referrer">\n' + inline_script(bootstrap) + '\n'
            '<style>#deliveryBanner{padding:10px 20px;background:#122331;color:#d9e8f2;'
            'font:13px/1.6 system-ui,sans-serif;border-bottom:1px solid #35566b;text-align:center}'
            '#refreshBtn{display:none!important}</style>')
    html, count = re.subn(r'(<meta\s+charset=["\']UTF-8["\']\s*>)', lambda match: match[1] + '\n' + head, html, count=1, flags=re.I)
    if count != 1:
        raise ValueError('UTF-8 header not found; cannot place CSP before page scripts')
    html = re.sub(r'<link[^>]+rel=["\'](?:preconnect|dns-prefetch)["\'][^>]*>', '', html, flags=re.I)
    local_candidates = "['echarts.min.js']" if same_origin_assets else '[]'
    html, count = re.subn(r'window\.__echartsTries\s*=\s*\[[\s\S]*?\];',
                          'window.__echartsTries = ' + local_candidates + ';', html, count=1)
    if count != 1:
        raise ValueError('ECharts fallback list was not found; package needs review')
    html = html.replace('请检查网络连接，或手动下载 echarts.min.js 放到本目录', '请联系部署管理员检查随附图表资源是否完整')
    html = html.replace('自选与离线缓存保存在当前浏览器', '自选与主题保存在当前浏览器；数据使用随附快照')
    # Inlined vendor code contains HTML strings such as '<body style="...">'.
    # The page's actual opening body tag is on its own line.
    html, count = re.subn(r'(^[ \t]*<body\b[^>]*>)', lambda match: match[1] + '\n<div id="deliveryBanner" role="status">' + banner + '</div>', html, count=1, flags=re.I | re.M)
    if count != 1:
        raise ValueError('Page body was not found')
    return html


def build(root, output_dir=None):
    market = (root / 'dist/market.js').read_text()
    if 'window.__FUND_OFFLINE__' not in market:
        raise ValueError('Frontend does not yet support the explicit offline flag')
    regular = standalone_html(root)
    shared = restricted_html(regular, snapshot_metadata(root))
    output_dir = Path(output_dir or root)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in [(OFFLINE, regular), (SHARE, shared)]:
        target = output_dir / name
        temporary = target.with_suffix('.html.tmp')
        temporary.write_text(value, encoding='utf-8')
        temporary.replace(target)
        print(f'Self-contained HTML: {target} bytes: {target.stat().st_size}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='Optional independent output folder for verification')
    args = parser.parse_args()
    build(ROOT, args.output_dir)


if __name__ == '__main__':
    main()
