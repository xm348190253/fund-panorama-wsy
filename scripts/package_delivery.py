#!/usr/bin/env python3
"""Package and verify the finished website and its reproducible update scripts.

Default output: ../公募基金_产品全景_交付包.zip
Use --dry-run to validate and list the package without creating it.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

from package_local import SHARE

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = 'fund-panorama'
OFFLINE = '公募基金_本地离线版.html'
REQUIRED = (OFFLINE, SHARE, 'README.md', 'dist/index.html', 'dist/snapshot.js',
            'dist/market.js', 'dist/echarts.min.js', 'scripts/update_all.py',
            'docs/market-total.json', 'docs/data-audit.json',
            'docs/detail-evidence.jsonl', 'docs/coverage-gaps.json', 'docs/内网部署说明.md')
EXCLUDED_PARTS = {'.git', '.openai', 'source-cache', 'qa', 'secrets', '__pycache__', 'node_modules'}
EXCLUDED_NAMES = {'credentials.json', 'credentials.toml', 'id_rsa', 'id_ed25519', 'authorized_keys'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.pem', '.key', '.p12', '.pfx', '.zip', '.tmp', '.bak'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def eligible(relative):
    return (not any(part.startswith('.') or part.lower() in EXCLUDED_PARTS for part in relative.parts)
            and relative.name.lower() not in EXCLUDED_NAMES
            and relative.suffix.lower() not in EXCLUDED_SUFFIXES)


class AssetReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for name in ('src', 'href'):
            value = attrs.get(name)
            if not value or value.startswith('#'):
                continue
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc:
                continue
            path = unquote(parsed.path)
            if path:
                self.paths.add(path)


def validate_sources(root):
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError('Required finished delivery file is missing or empty: ' + relative)
    html = (root / 'dist/index.html').read_text()
    refs = AssetReferences()
    refs.feed(html)
    for name in refs.paths:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not (root / 'dist' / name).is_file():
            raise ValueError('Missing or invalid local website asset: ' + name)
    listed = re.findall(r'<script\b[^>]*\bsrc=["\'](snapshot-perf-\d+\.js)["\'][^>]*>', html, re.I)
    present = sorted(path.name for path in (root / 'dist').glob('snapshot-perf-*.js'))
    if not listed or len(listed) != len(set(listed)) or sorted(listed) != present:
        raise ValueError('Snapshot shards on disk and in index.html disagree')
    expected = [f'snapshot-perf-{i:03d}.js' for i in range(1, len(listed) + 1)]
    if listed != expected:
        raise ValueError('Snapshot shards must be listed once in consecutive order')
    source = (root / 'dist/snapshot.js').read_text()
    prefix = 'window.MARKET_SNAPSHOT='
    if not source.startswith(prefix) or not source.rstrip().endswith(';'):
        raise ValueError('Main snapshot structure is invalid')
    snapshot = json.loads(source[len(prefix):].strip().removesuffix(';'))
    codes = [item['code'] for item in snapshot['funds']]
    if not codes or len(codes) != len(set(codes)) or any(not re.fullmatch(r'\d{6}', code) for code in codes):
        raise ValueError('Snapshot directory codes are empty, malformed, or duplicated')
    combined = dict(snapshot.get('perf') or {})
    offline = (root / OFFLINE).read_text()
    shared = (root / SHARE).read_text()
    if re.search(r'<script\b[^>]*\bsrc\s*=', offline, re.I):
        raise ValueError('Offline HTML still depends on an external script file')
    if 'window.__FUND_OFFLINE__=true;' not in shared or 'Content-Security-Policy' not in shared:
        raise ValueError('Sharing HTML does not explicitly prevent external requests')
    for filename in ['snapshot.js'] + listed:
        content = (root / 'dist' / filename).read_text()
        escaped = re.sub(r'</script', r'<\\/script', content, flags=re.I)
        if '<script>' + escaped + '</script>' not in offline:
            raise ValueError('Offline HTML does not embed the current asset: ' + filename)
        if '<script>' + escaped + '</script>' not in shared:
            raise ValueError('Sharing HTML does not embed the current asset: ' + filename)
        if filename == 'snapshot.js':
            continue
        prefix = 'Object.assign(window.MARKET_SNAPSHOT.perf,'
        if not content.startswith(prefix) or not content.rstrip().endswith(');'):
            raise ValueError('Snapshot shard structure is invalid: ' + filename)
        chunk = json.loads(content[len(prefix):].strip().removesuffix(');'))
        if set(combined).intersection(chunk):
            raise ValueError('Duplicate performance code across snapshot shards: ' + filename)
        combined.update(chunk)
    if set(combined) != set(codes):
        raise ValueError('Snapshot shards do not cover every directory code exactly once')
    collection = snapshot['meta'].get('collection', {})
    if collection.get('attempted') != len(codes) or collection.get('directoryCount') != len(codes):
        raise ValueError('Snapshot does not report completed full-directory processing')
    audit = json.loads((root / 'docs/data-audit.json').read_text())
    if audit != snapshot['meta']:
        raise ValueError('Snapshot metadata and data-audit.json disagree')
    evidence_codes = []
    with (root / 'docs/detail-evidence.jsonl').open() as evidence:
        for line in evidence:
            if line.strip():
                evidence_codes.append(json.loads(line)['code'])
    if len(evidence_codes) != len(codes) or set(evidence_codes) != set(codes):
        raise ValueError('Per-code evidence does not cover the complete directory exactly once')
    return {'directoryCount': len(codes), 'snapshotShards': listed, 'collection': collection}


def collect_files(root):
    files = [root / OFFLINE, root / SHARE, root / 'README.md']
    if any(path.is_symlink() for path in files):
        raise ValueError('Delivery root files must not be symbolic links')
    for folder in ('dist', 'scripts', 'docs'):
        for path in sorted((root / folder).rglob('*')):
            relative = path.relative_to(root)
            if not eligible(relative):
                continue
            if path.is_symlink():
                raise ValueError('Delivery sources must not contain symbolic links: ' + str(relative))
            if path.is_file():
                files.append(path)
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def package(root, output=None, dry_run=False):
    validation = validate_sources(root)
    files = collect_files(root)
    entries = {path.relative_to(root).as_posix(): {'bytes': path.stat().st_size, 'sha256': digest(path.read_bytes())}
               for path in files}
    report = {**validation, 'fileCount': len(files), 'sourceBytes': sum(value['bytes'] for value in entries.values()),
              'offlineSha256': entries[OFFLINE]['sha256'], 'files': entries}
    if dry_run:
        return {**report, 'dryRun': True}
    output = Path(output or root.parent / '公募基金_产品全景_交付包.zip').resolve()
    if output.is_relative_to(root):
        raise ValueError('Delivery ZIP must be outside the source project')
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=output.name + '.', suffix='.tmp', dir=output.parent)
    os.close(handle)
    temporary = Path(temporary)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            for path in files:
                archive.write(path, ARCHIVE_ROOT + '/' + path.relative_to(root).as_posix())
            archive.writestr(ARCHIVE_ROOT + '/DELIVERY_MANIFEST.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        with zipfile.ZipFile(temporary) as archive:
            damaged = archive.testzip()
            if damaged:
                raise ValueError('ZIP CRC verification failed: ' + damaged)
            names = archive.namelist()
            wanted = {ARCHIVE_ROOT + '/' + name for name in entries} | {ARCHIVE_ROOT + '/DELIVERY_MANIFEST.json'}
            if len(names) != len(set(names)) or set(names) != wanted:
                raise ValueError('ZIP contents disagree with the delivery manifest')
            for relative, metadata in entries.items():
                if digest(archive.read(ARCHIVE_ROOT + '/' + relative)) != metadata['sha256']:
                    raise ValueError('ZIP source hash mismatch: ' + relative)
                if digest((root / relative).read_bytes()) != metadata['sha256']:
                    raise ValueError('Source changed while packaging: ' + relative)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {**report, 'output': str(output), 'zipBytes': output.stat().st_size,
            'zipSha256': digest(output.read_bytes()), 'verification': 'CRC and every source SHA256 passed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    result = package(ROOT, args.output, args.dry_run)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
