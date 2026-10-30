#!/usr/bin/env python3
"""Build a verified, self-contained site for the daily cloud publishing workflow."""
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import tempfile
from zoneinfo import ZoneInfo

from package_intranet import validate_site
from package_local import restricted_html, snapshot_metadata
from refresh_index_quotes import validate_snapshot

ROOT = Path(__file__).resolve().parents[1]
ASSET = re.compile(r'(?:index\.html|market\.js|echarts\.min\.js|snapshot(?:-perf-\d{3})?\.js)')
MANIFEST = 'release.json'
MAX_ASSET_BYTES = 25 * 1024 * 1024
ADMIN_URL = 'https://github.com/xm348190253/fund-panorama-wsy/actions/workflows/daily-modelscope.yml'


def fingerprint(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


class ResourcePolicy(HTMLParser):
    def __init__(self):
        super().__init__()
        self.csp = ''
        self.external = []
        self.banners = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'content-security-policy':
            self.csp = attrs.get('content', '')
        self.banners += attrs.get('id') == 'deliveryBanner'
        if tag in ('script', 'link', 'img', 'iframe', 'video', 'audio', 'source'):
            self.external.extend(value for key in ('src', 'href')
                                 if (value := attrs.get(key, '')).startswith(('https://', 'http://', '//')))


def owned_output(output):
    """Accept only a new/empty directory or an intact release produced by this builder."""
    if output.is_symlink():
        raise ValueError('Output must not be a symbolic link')
    if not output.exists():
        return
    if not output.is_dir():
        raise ValueError('Output must be a directory')
    entries = {p.name for p in output.iterdir()}
    if not entries:
        return
    manifest = output / MANIFEST
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('Existing output has no owned release manifest')
    saved = json.loads(manifest.read_text())
    files = saved.get('files')
    if not isinstance(files, dict) or not files or entries != set(files) | {MANIFEST}:
        raise ValueError('Existing output contains files outside its release manifest')
    for name, expected in files.items():
        path = output / name
        if not ASSET.fullmatch(name) or path.is_symlink() or not path.is_file() or fingerprint(path) != expected:
            raise ValueError('Existing output has an unrecognized or modified asset: ' + name)
    if not all(saved.get(key) for key in ('version', 'dataDate', 'generatedAt')):
        raise ValueError('Existing output has an incomplete release manifest')


def validate_scripts(stage, node):
    code = r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=process.argv[1];let external=0,inline=0;
for(const name of fs.readdirSync(root).filter(name=>name.endsWith('.js'))){
  new vm.Script(fs.readFileSync(path.join(root,name),'utf8'),{filename:name});external++;
}
for(const match of fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)){
  if(match[1].trim()){new vm.Script(match[1]);inline++;}
}
console.log(JSON.stringify({externalScriptsParsed:external,inlineScriptsParsed:inline}));
"""
    return json.loads(subprocess.check_output([node, '-e', code, str(stage)], text=True))


def build(root, output, version, node='node'):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', version):
        raise ValueError('Version must be 1–128 letters, digits, dots, underscores or hyphens')
    root, output = Path(root).resolve(), Path(output).absolute()
    owned_output(output)
    meta = snapshot_metadata(root)
    data_date = (meta.get('collection') or {}).get('asOf')
    if not isinstance(data_date, str) or dt.date.fromisoformat(data_date).isoformat() != data_date:
        raise ValueError('Snapshot collection date must be an ISO date')
    index_snapshot = validate_snapshot(json.loads((root / 'source-cache/index-quotes.json').read_text()))
    dist = root / 'dist'
    names = ['index.html', 'market.js', 'echarts.min.js', 'snapshot.js'] + sorted(
        path.name for path in dist.glob('snapshot-perf-*.js'))
    for name in names:
        path = dist / name
        if not ASSET.fullmatch(name) or path.is_symlink() or not path.is_file():
            raise ValueError('Invalid source asset: ' + name)
    originals = {name: fingerprint(dist / name) for name in names}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.fund-cloud-build-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'site'
        stage.mkdir()
        for name in names:
            (stage / name).write_bytes((dist / name).read_bytes())
        index = stage / 'index.html'
        html = restricted_html(index.read_text(), meta, same_origin_assets=True)
        html = html.replace('内网快照', '云端快照').replace('"mode": "intranet"', '"mode": "cloud_snapshot"')
        # Embed the quote snapshot inside the hashed HTML; both hosted entries use this exact asset.
        quote_json = json.dumps(index_snapshot, ensure_ascii=False, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
        marker = '<script src="market.js"></script>'
        if html.count(marker) != 1:
            raise ValueError('Index snapshot bootstrap position is missing or ambiguous')
        html = html.replace(marker, '<script>window.__FUND_INDEX_SNAPSHOT__=' + quote_json + ';</script>\n' + marker)
        # Permit only the fixed administrator entry; all fund source links stay citations.
        html = html.replace("  event.preventDefault();event.stopImmediatePropagation();",
                            "  if(anchor.href===" + json.dumps(ADMIN_URL) + ")return;\n"
                            "  event.preventDefault();event.stopImmediatePropagation();", 1)
        notice = ('<br>共用云端版本 ' + version
                  + ' · 每天北京时间 08:00 计划开始采集，错峰补偿；刷新读取最新已成功发布版本。'
                  + '<br><a style="color:#b9e6ff;text-decoration:underline" target="_blank" rel="noopener noreferrer" href="'
                  + ADMIN_URL + '">立即更新（管理员）／查看更新进度</a>'
                  + ' · 管理员登录 GitHub 后点击 Run workflow；普通访问只读。')
        html, count = re.subn(r'(<div id="deliveryBanner" role="status">[^<]*)(</div>)',
                             lambda m: m[1] + notice + m[2], html)
        if count != 1:
            raise ValueError('Cloud update notice could not be placed in the snapshot banner')
        index.write_text(html, encoding='utf-8')
        market = stage / 'market.js'
        market.write_text(market.read_text().replace('内网快照', '云端快照'), encoding='utf-8')
        validation = validate_site(stage, meta)
        policy = ResourcePolicy()
        policy.feed(html)
        if policy.external or "connect-src 'none'" not in policy.csp or policy.banners != 1:
            raise ValueError('Cloud snapshot resource policy failed')
        syntax = validate_scripts(stage, node)
        files = {name: fingerprint(stage / name) for name in names}
        if any(info['bytes'] >= MAX_ASSET_BYTES for info in files.values()):
            raise ValueError('A static asset reaches the 25 MiB per-file limit')
        release = {'version': version, 'dataDate': data_date,
                   'generatedAt': dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
                   'indexQuotesCollectedAt': index_snapshot['collectedAt'],
                   'indexQuotesAvailable': sum(q['val'] is not None for q in index_snapshot['quotes']),
                   'files': files}
        (stage / MANIFEST).write_text(json.dumps(release, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        owned_output(stage)
        if originals != {name: fingerprint(dist / name) for name in names}:
            raise ValueError('Source assets changed during cloud build')
        owned_output(output)
        backup = Path(temporary) / 'previous'
        if output.exists():
            output.rename(backup)
        try:
            stage.rename(output)
        except BaseException:
            if backup.exists():
                backup.rename(output)
            raise
    owned_output(output)
    return {'status': 'PASS', 'output': str(output), 'version': version, 'dataDate': data_date,
            'fileCount': len(files), 'published': False, **validation, **syntax}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--node', default='node')
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.output, args.version, args.node), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
