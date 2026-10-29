#!/usr/bin/env python3
"""Build an IT-deployable static site with no external data or CDN requests."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import zipfile

from package_delivery import AssetReferences, eligible
from package_local import restricted_html, snapshot_metadata

ROOT = Path(__file__).resolve().parents[1]
NGINX_EXAMPLE = '''# Example only: IT must set the actual host, TLS, filesystem path, and access rules.
# This example serves the app under /fund-panorama/; preserve the trailing slash.
server {
    listen 80;
    server_name funds.internal.example;
    include mime.types;
    charset utf-8;
    gzip on;
    gzip_types application/javascript text/css application/json text/plain;

    location = /fund-panorama { return 301 /fund-panorama/; }
    location /fund-panorama/ {
        alias /srv/www/fund-panorama/;
        index index.html;
        add_header Cache-Control "no-cache" always;
        add_header X-Content-Type-Options "nosniff" always;
    }
}
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_site(site, meta):
    html = (site / 'index.html').read_text()
    if 'window.__FUND_OFFLINE__=true;' not in html or 'Content-Security-Policy' not in html:
        raise ValueError('Default intranet snapshot mode or resource policy is missing')
    if re.search(r'<(?:script|link)\b[^>]*(?:src|href)=["\']https?://', html, re.I):
        raise ValueError('Intranet page still references a third-party resource')
    refs = AssetReferences(); refs.feed(html)
    for name in refs.paths:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not (site / name).is_file():
            raise ValueError('Missing or root-relative resource breaks subpath deployment: ' + name)
    listed = re.findall(r'<script\b[^>]*\bsrc=["\'](snapshot-perf-\d+\.js)["\'][^>]*>', html)
    present = sorted(path.name for path in site.glob('snapshot-perf-*.js'))
    if not listed or listed != present or listed != [f'snapshot-perf-{i:03d}.js' for i in range(1, len(listed) + 1)]:
        raise ValueError('Intranet snapshot shard references are incomplete')
    snapshot = json.loads((site / 'snapshot.js').read_text().split('=', 1)[1].strip().removesuffix(';'))
    codes = {p['code'] for p in snapshot['funds']}
    if len(codes) != len(snapshot['funds']) or len(codes) != meta['directoryCount']:
        raise ValueError('Directory counts disagree')
    perf = set(snapshot.get('perf') or {})
    for name in listed:
        text = (site / name).read_text()
        prefix = 'Object.assign(window.MARKET_SNAPSHOT.perf,'
        if not text.startswith(prefix) or not text.rstrip().endswith(');'):
            raise ValueError('Invalid snapshot shard: ' + name)
        chunk = json.loads(text[len(prefix):].strip().removesuffix(');'))
        if perf.intersection(chunk):
            raise ValueError('Duplicate code across shards: ' + name)
        perf.update(chunk)
    if perf != codes or meta.get('collection', {}).get('attempted') != len(codes):
        raise ValueError('Intranet snapshot does not include every processed directory code')
    return {'directoryCount': len(codes), 'snapshotShards': listed}


def package(root, output=None, dry_run=False):
    dist = root / 'dist'
    market = (dist / 'market.js').read_text()
    if 'window.__FUND_OFFLINE__' not in market:
        raise ValueError('Frontend offline-mode support is not yet present')
    guide = root / 'docs/内网部署说明.md'
    if not guide.is_file():
        raise ValueError('IT deployment instructions are missing')
    meta = snapshot_metadata(root)
    output = Path(output or root.parent / '公募基金_内网部署包.zip').resolve()
    if output.is_relative_to(root):
        raise ValueError('Deployment ZIP must be outside the source project')
    with tempfile.TemporaryDirectory(prefix='fund-intranet-') as temporary:
        stage = Path(temporary)
        site = stage / 'site'; site.mkdir()
        original = {}
        for path in sorted(dist.rglob('*')):
            relative = path.relative_to(dist)
            if not eligible(relative):
                continue
            if path.is_symlink():
                raise ValueError('Static deployment must not include symlinks: ' + str(relative))
            if not path.is_file():
                continue
            target = site / relative; target.parent.mkdir(parents=True, exist_ok=True)
            content = path.read_bytes(); original[path] = sha(content)
            target.write_bytes(content)
        index = site / 'index.html'
        index.write_text(restricted_html(index.read_text(), meta, same_origin_assets=True), encoding='utf-8')
        validation = validate_site(site, meta)
        as_of = meta['collection']['asOf']
        preface = f'快照日期：{as_of}\n目录份额代码：{meta["directoryCount"]:,}\n默认模式：内网固定快照，无外部数据连接。\n\n'
        (stage / '部署说明.md').write_text(preface + guide.read_text(), encoding='utf-8')
        (stage / 'Nginx示例.conf').write_text(NGINX_EXAMPLE, encoding='utf-8')
        files = sorted(path for path in stage.rglob('*') if path.is_file())
        entries = {path.relative_to(stage).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in files}
        manifest = {'snapshotDate': as_of, 'mode': 'fixed_snapshot_no_external_requests',
                    'requiresBackend': False, **validation, 'files': entries}
        (stage / 'DEPLOYMENT_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for path, expected in original.items():
            if sha(path.read_bytes()) != expected:
                raise ValueError('Source assets changed during packaging: ' + str(path))
        if dry_run:
            return {k: v for k, v in manifest.items() if k != 'files'} | {'dryRun': True, 'fileCount': len(entries) + 1}
        output.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(prefix=output.name + '.', suffix='.tmp', dir=output.parent, delete=False)
        pending = Path(handle.name); handle.close()
        try:
            with zipfile.ZipFile(pending, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for path in sorted(stage.rglob('*')):
                    if path.is_file():
                        archive.write(path, path.relative_to(stage).as_posix())
            with zipfile.ZipFile(pending) as archive:
                if archive.testzip() is not None:
                    raise ValueError('Deployment ZIP failed CRC verification')
                if set(archive.namelist()) != set(entries) | {'DEPLOYMENT_MANIFEST.json'}:
                    raise ValueError('Deployment ZIP contents differ from manifest')
                for name, evidence in entries.items():
                    if sha(archive.read(name)) != evidence['sha256']:
                        raise ValueError('Deployment ZIP hash mismatch: ' + name)
            pending.replace(output)
        finally:
            pending.unlink(missing_ok=True)
    return {k: v for k, v in manifest.items() if k != 'files'} | {
        'output': str(output), 'zipBytes': output.stat().st_size, 'zipSha256': sha(output.read_bytes()),
        'fileCount': len(entries) + 1, 'verification': 'All snapshot codes, relative resources, ZIP CRC and SHA256 passed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps(package(ROOT, args.output, args.dry_run), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
