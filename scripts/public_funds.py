#!/usr/bin/env python3
"""Publish a fund-only immutable release from the existing validated snapshot."""
import argparse
import base64
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

from modelscope_sync import DEFAULT_REPO, StudioCheckout, validate_site

REPOSITORY = 'xm348190253/fund-panorama-wsy'
POINTER_PATH = 'public-funds/latest.json'
ADMIN_URL = 'https://github.com/' + REPOSITORY + '/actions/workflows/daily-modelscope.yml'
PRIVATE_MARKERS = (
    'insurance-dashboard-bootstrap', '__INSURANCE_', '/api/insurance',
    '/insurance-data/', 'fund-panorama-wsy-1028.xmxmxm348190253.chatgpt.site',
    'wangshuyang2126-fund-panorama-wsy.ms.show', '保险资产管理产品行业报告',
)


def fingerprint(data):
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def sanitize_index(html, version):
    pattern = r'<script\b[^>]*\bid=["\']insurance-dashboard-bootstrap["\'][^>]*>[\s\S]*?</script>'
    html, count = re.subn(pattern, '', html)
    if count != 1:
        raise ValueError('Expected exactly one combined-dashboard bootstrap')
    capture = '<script>window.__INSURANCE_FETCH__=window.fetch.bind(window);</script>'
    if html.count(capture) != 1:
        raise ValueError('Expected the combined-dashboard request capture')
    html = html.replace(capture, '')
    html = html.replace("connect-src 'self'", "connect-src 'none'")
    html = html.replace('connect-src &#x27;self&#x27;', 'connect-src &#x27;none&#x27;')
    old_guard = 'if(anchor.href===' + json.dumps(ADMIN_URL) + ')return;'
    if old_guard not in html or 'href="' + ADMIN_URL + '"' not in html:
        raise ValueError('Update entry changed and requires review')
    html = html.replace(old_guard, 'if(anchor.origin===location.origin&&anchor.pathname==="/updates")return;')
    html = html.replace('href="' + ADMIN_URL + '"', 'href="/updates"')
    html = re.sub(
        r'(<script\s+src=")(snapshot(?:-perf-\d+)?\.js|market\.js)(?:\?release=[\w.-]+)?(")',
        lambda match: match[1] + match[2] + '?release=' + version + match[3], html)
    html = html.replace('href="echarts.min.js"', 'href="echarts.min.js?release=' + version + '"')
    html, count = re.subn(r'window\.__echartsTries\s*=\s*\[[\s\S]*?\];',
                          'window.__echartsTries = ' + json.dumps(['echarts.min.js?release=' + version]) + ';', html)
    if count != 1:
        raise ValueError('Chart loader changed and requires review')
    if any(marker in html for marker in PRIVATE_MARKERS):
        raise ValueError('Fund HTML contains a combined-dashboard reference')
    return html


def build(source, output):
    source, output = Path(source), Path(output)
    release, _ = validate_site(source)
    version = 'pf1-' + release['version']
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, expected in release['files'].items():
        data = (source / name).read_bytes()
        if len(data) != expected['bytes']:
            raise ValueError('Source size mismatch for ' + name)
        if name == 'index.html':
            data = sanitize_index(data.decode('utf-8'), version).encode('utf-8')
        else:
            text = data.decode('utf-8')
            if any(marker in text for marker in PRIVATE_MARKERS):
                raise ValueError('Fund asset contains a combined-dashboard reference: ' + name)
        (output / name).write_bytes(data)
        files[name] = fingerprint(data)
    public = {**release, 'version': version, 'sourceVersion': release['version'],
              'distribution': 'public-funds', 'files': files}
    data = (json.dumps(public, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    (output / 'release.json').write_bytes(data)
    validate_site(output)
    return public


def gh(args, payload=None, optional=False):
    result = subprocess.run(['gh', *args], input=json.dumps(payload) if payload is not None else None,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
    if result.returncode and not optional:
        raise RuntimeError('GitHub publication command failed: ' + result.stderr[-500:])
    return result


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'public-funds-release-verifier'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read(12 * 1024 * 1024)


def publish_assets(folder, manifest):
    tag = 'public-funds-' + manifest['version']
    result = gh(['release', 'view', tag, '--repo', REPOSITORY, '--json', 'assets'], optional=True)
    if result.returncode:
        gh(['release', 'create', tag, '--repo', REPOSITORY, '--target', os.environ['GITHUB_SHA'],
            '--title', '公募基金数据 ' + manifest['dataDate'], '--notes',
            '仅包含公开公募基金数据、行情和独立公募页面。', '--latest=false'])
        assets = {}
    else:
        assets = {item['name']: item for item in json.loads(result.stdout)['assets']}
    expected = {**manifest['files'], 'release.json': fingerprint((folder / 'release.json').read_bytes())}
    if set(assets) - set(expected):
        raise ValueError('Immutable public release contains an unexpected asset')
    for name, info in expected.items():
        if name in assets:
            if assets[name]['size'] != info['bytes']:
                raise ValueError('Immutable public asset size changed: ' + name)
        else:
            gh(['release', 'upload', tag, str(folder / name), '--repo', REPOSITORY])
    base = 'https://github.com/' + REPOSITORY + '/releases/download/' + tag + '/'

    def verify(item):
        name, expected_info = item
        for attempt in range(3):
            try:
                actual = fingerprint(download(base + name))
                if actual != expected_info:
                    raise ValueError('Published bytes differ for ' + name)
                return name
            except Exception:
                if attempt == 2:
                    raise
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        verified = list(pool.map(verify, expected.items()))
    print(json.dumps({'verifiedPublicFiles': len(verified), 'version': manifest['version']}), flush=True)
    return expected['release.json']['sha256']


def update_pointer(manifest, manifest_hash):
    pointer = {'version': manifest['version'], 'sourceVersion': manifest['sourceVersion'],
               'dataDate': manifest['dataDate'], 'sourceGeneratedAt': manifest['generatedAt'],
               'manifestSha256': manifest_hash, 'distribution': 'public-funds'}
    endpoint = 'repos/' + REPOSITORY + '/contents/' + POINTER_PATH
    for attempt in range(4):
        result = gh(['api', endpoint], optional=True)
        old = json.loads(result.stdout) if result.returncode == 0 else None
        if old:
            previous = json.loads(base64.b64decode(old['content']))
            if dt.datetime.fromisoformat(previous['sourceGeneratedAt']) > dt.datetime.fromisoformat(pointer['sourceGeneratedAt']):
                print('A newer public release is already current', flush=True)
                return
            if previous == pointer:
                print('Public fund release is already current', flush=True)
                return
        body = {'message': 'Update public fund release pointer', 'branch': 'main',
                'content': base64.b64encode((json.dumps(pointer, ensure_ascii=False, indent=2) + '\n').encode()).decode()}
        if old:
            body['sha'] = old['sha']
        result = gh(['api', '--method', 'PUT', endpoint, '--input', '-'], body, optional=True)
        if result.returncode == 0:
            print('Published current public fund version ' + manifest['version'], flush=True)
            return
        if attempt == 3:
            raise RuntimeError('Could not update the public fund version pointer')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='public-funds-') as temporary:
        folder = Path(temporary)
        if args.source:
            source = args.source
        else:
            token = os.environ['MODELSCOPE_API_KEY']
            source = StudioCheckout(folder, DEFAULT_REPO, token).clone()
        output = args.output or folder / 'public'
        manifest = build(source, output)
        if args.publish:
            manifest_hash = publish_assets(output, manifest)
            update_pointer(manifest, manifest_hash)
        else:
            print(json.dumps({'version': manifest['version'], 'dataDate': manifest['dataDate'],
                              'files': len(manifest['files']), 'output': str(output)}))


if __name__ == '__main__':
    main()
