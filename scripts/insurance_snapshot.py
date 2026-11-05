#!/usr/bin/env python3
"""Mirror only the public insurance JSON views; never request private files.

Immutable version files are written first, the checksum manifest last. Versions
already on the Studio remain available to pages opened before the next update.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ORIGIN = 'https://fund-panorama-wsy-1028.xmxmxm348190253.chatgpt.site'
RUNTIME = 'https://wangshuyang2126-fund-panorama-wsy.ms.show'
VERSION = re.compile(r'[A-Za-z0-9-]{10,80}\Z')
MONTH = re.compile(r'20\d{2}-(?:0[1-9]|1[0-2])\Z')
SHA = re.compile(r'[a-f0-9]{64}\Z')
LIMIT = 12_000_000


def fingerprint(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def public_json(url, limit=LIMIT):
    # The upstream edge rejects Python's default user agent (Cloudflare 1010).
    # These are anonymous, read-only endpoints: no cookies or credentials.
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json',
        'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('Insurance JSON exceeds size limit')
        if response.headers.get('Content-Encoding') == 'gzip':
            # Read the decompressed stream with a bound as well.
            import io
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Insurance JSON exceeds size limit')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Insurance JSON must be an object')
    return value, raw


def validate_meta(meta):
    months = meta.get('months')
    if (not VERSION.fullmatch(str(meta.get('version', '')))
            or not isinstance(months, list) or not 1 <= len(months) <= 360
            or any(not isinstance(m, str) or not MONTH.fullmatch(m) for m in months)
            or len(set(months)) != len(months) or months != sorted(months)
            or meta.get('latest') != months[-1]):
        raise ValueError('Invalid insurance version or report months')
    return meta


def names_for(meta):
    return {'meta.json'} | {'period-' + month + '.json' for month in meta['months']}


def validate_manifest(manifest):
    validate_meta(manifest)
    files = manifest.get('files')
    if not isinstance(files, dict) or set(files) != names_for(manifest):
        raise ValueError('Insurance manifest contains unexpected or missing files')
    for entry in files.values():
        if (not isinstance(entry, dict) or type(entry.get('bytes')) is not int
                or not 1 <= entry['bytes'] <= LIMIT
                or not SHA.fullmatch(str(entry.get('sha256', '')))):
            raise ValueError('Invalid insurance file checksum or size')
    return manifest


def safe_file(root, relative):
    path = root / relative
    current = root
    if root.is_symlink():
        raise ValueError('Insurance output cannot be a symlink')
    for part in Path(relative).parts:
        if part in ('..', '.') or not part:
            raise ValueError('Unsafe insurance file path')
        current /= part
        if current.is_symlink():
            raise ValueError('Insurance paths cannot contain symlinks')
    if path.exists() and not path.is_file():
        raise ValueError('Insurance output is not a regular file')
    return path


def validate_snapshot(root):
    root = Path(root)
    manifest = validate_manifest(json.loads(safe_file(root, 'manifest.json').read_bytes()))
    hashes = {'insurance-data/manifest.json': fingerprint((root / 'manifest.json').read_bytes())['sha256']}
    for name, spec in manifest['files'].items():
        relative = manifest['version'] + '/' + name
        raw = safe_file(root, relative).read_bytes()
        if fingerprint(raw) != spec:
            raise ValueError('Insurance snapshot checksum mismatch: ' + name)
        value = json.loads(raw)
        if name == 'meta.json':
            validate_meta(value)
            if any(value.get(k) != manifest.get(k) for k in ('version', 'latest', 'months', 'updated')):
                raise ValueError('Insurance metadata differs from manifest')
        elif value.get('month') != name[7:-5]:
            raise ValueError('Insurance report month mismatch')
        hashes['insurance-data/' + relative] = spec['sha256']
    return manifest, hashes


def build_snapshot(root, fetch=public_json):
    root = Path(root)
    if root.is_symlink():
        raise ValueError('Insurance output cannot be a symlink')
    meta, meta_raw = fetch(ORIGIN + '/api/insurance/meta')
    validate_meta(meta)
    # All subsequent requests pin the exact server version; a concurrent upload
    # therefore cannot mix old and new months in one published snapshot.
    content = {'meta.json': meta_raw}
    for month in meta['months']:
        value, raw = fetch(ORIGIN + '/api/insurance/period/' + month +
                           '?version=' + urllib.parse.quote(meta['version']))
        if value.get('month') != month:
            raise ValueError('Insurance source returned a different month')
        content['period-' + month + '.json'] = raw
    manifest = {key: meta[key] for key in ('version', 'latest', 'months', 'updated')}
    manifest.update(syncedAt=dt.datetime.now(dt.timezone.utc).isoformat(),
                    files={name: fingerprint(raw) for name, raw in content.items()})
    validate_manifest(manifest)
    # Finish every download and validation before touching an existing manifest.
    root.mkdir(parents=True, exist_ok=True)
    for name, raw in content.items():
        target = safe_file(root, meta['version'] + '/' + name)
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('An immutable insurance version changed: ' + name)
    manifest_path = safe_file(root, 'manifest.json')
    if manifest_path.exists():
        previous, _ = validate_snapshot(root)
        if previous['version'] == manifest['version']:
            if previous['files'] != manifest['files']:
                raise ValueError('An immutable insurance manifest changed')
            return previous
    with tempfile.TemporaryDirectory(prefix='.insurance-stage-', dir=root.parent) as temporary:
        stage = Path(temporary)
        for name, raw in content.items():
            target = safe_file(root, meta['version'] + '/' + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                pending = stage / name
                pending.write_bytes(raw)
                pending.replace(target)
        pending = stage / 'manifest.json'
        pending.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        pending.replace(manifest_path)
    validate_snapshot(root)
    return manifest


def needs_sync(fetch=public_json):
    source, _ = fetch(ORIGIN + '/api/insurance/meta')
    validate_meta(source)
    try:
        mirrored, _ = fetch(RUNTIME + '/insurance-data/manifest.json?check=' + source['version'])
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return True
        raise
    validate_manifest(mirrored)
    return any(mirrored.get(key) != source.get(key) for key in ('version', 'months', 'latest', 'updated'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        changed = needs_sync()
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                stream.write('changed=' + str(changed).lower() + '\n')
        print(json.dumps({'changed': changed}))
    elif args.output:
        result = build_snapshot(args.output)
        print(json.dumps({'version': result['version'], 'months': result['months'], 'files': len(result['files'])}))
    else:
        parser.error('Choose --output or --check')


if __name__ == '__main__':
    main()
