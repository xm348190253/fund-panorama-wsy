#!/usr/bin/env python3
"""Publish the fund-only snapshot to the separate domestic Static Studio."""
import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from modelscope_sync import (Client, DEFAULT_REPO, StudioCheckout, SyncError,
                            atomic_json, now, redact, validate_site)
from public_funds import build, fingerprint

PUBLIC_REPO = 'wangshuyang2126/fund-panorama-public-wsy'


def domestic_index(text, release):
    """Keep update metadata available entirely within the static page."""
    text, count = re.subn(r'<a\b([^>]*?)href="/updates"([^>]*)>',
                         lambda match: '<a' + re.sub(r'\s+target="[^"]*"', '', match[1])
                         + 'href="#public-updates"'
                         + re.sub(r'\s+target="[^"]*"', '', match[2]) + '>', text)
    if count != 1:
        raise ValueError('Expected one public update progress link')
    text = text.replace('if(anchor.origin===location.origin&&anchor.pathname==="/updates")return;', '')
    text = text.replace('?release=pf1-' + release['sourceVersion'], '?release=' + release['version'])
    values = {key: html.escape(str(release.get(key, '/'))) for key in
              ('dataDate', 'generatedAt', 'sourceVersion')}
    panel = '''<style>
#public-updates{display:none;position:fixed;inset:0;z-index:9999;background:#0008;padding:12vh 20px;overflow:auto}
#public-updates:target{display:flex;align-items:flex-start;justify-content:center}
#public-updates .update-panel{background:var(--bg-2,#fff8f2);color:var(--text-1,#332c26);border:1px solid var(--border,#eadacf);border-radius:16px;padding:28px;width:min(520px,100%%);text-align:center;box-sizing:border-box}
#public-updates h2{font-size:20px;margin:0 0 20px}#public-updates p{font-size:14px;line-height:1.8;overflow-wrap:anywhere}
#public-updates a{display:inline-block;margin-top:12px;color:var(--accent,#ef761c)}
</style><section id="public-updates" role="dialog" aria-modal="true" aria-labelledby="public-update-title"><div class="update-panel">
<h2 id="public-update-title">数据更新</h2><p>数据日期 %(dataDate)s</p><p>本期更新时间 %(generatedAt)s</p>
<p>数据版本 %(sourceVersion)s</p><p>数据采集完成后自动同步，重新打开页面即可查看最新发布。</p><a href="#">返回看板</a>
</div></section>''' % values
    if text.count('</body>') != 1:
        raise ValueError('Expected one document body')
    return text.replace('</body>', panel + '\n</body>')


def build_domestic(source, output):
    release = build(source, output)
    release.update(version='cn1-' + release['sourceVersion'], distribution='public-funds-domestic')
    index = Path(output) / 'index.html'
    index.write_text(domestic_index(index.read_text(encoding='utf-8'), release), encoding='utf-8')
    release['files']['index.html'] = fingerprint(index.read_bytes())
    atomic_json(Path(output) / 'release.json', release)
    validate_site(output)
    return release


def publish(args, token):
    receipt = {'status': 'started', 'studio': PUBLIC_REPO, 'startedAt': now(),
               'pushed': False, 'deployRequested': False, 'verified': False}
    atomic_json(args.receipt, receipt)
    try:
        with tempfile.TemporaryDirectory(prefix='public-funds-domestic-') as temporary:
            folder = Path(temporary)
            source_folder = folder / 'source'
            source_folder.mkdir()
            source = StudioCheckout(source_folder, DEFAULT_REPO, token).clone()
            output = folder / 'public'
            release = build_domestic(source, output)
            _, hashes = validate_site(output)
            receipt.update(version=release['version'], sourceVersion=release['sourceVersion'],
                           dataDate=release['dataDate'], assetCount=len(hashes))
            client = Client(PUBLIC_REPO, token)
            info = client.api()
            host = client.verify_configuration(info)
            target_folder = folder / 'target'
            target_folder.mkdir()
            target = StudioCheckout(target_folder, PUBLIC_REPO, token)
            target.clone()
            tracked = target.git('ls-files').stdout.splitlines()
            if any('insurance' in name.lower() for name in tracked):
                raise SyncError('The separate public Studio contains an unexpected private asset')
            changed = target.sync(output, sorted(set(hashes) | {'release.json'}))
            receipt['commit'] = target.git('rev-parse', 'HEAD').stdout.strip()
            if changed:
                target.push()
                receipt['pushed'] = True
            already_live = False
            if not changed and info.get('runtime', {}).get('status') == 'Running':
                try:
                    client.verify_live(host, release, hashes)
                    already_live = True
                except SyncError:
                    pass
            if not already_live:
                client.api('POST', '/deploy')
                receipt['deployRequested'] = True
                atomic_json(args.receipt, receipt)
                info = client.wait_verified(release, hashes, args.timeout, args.poll_interval)
            receipt.update(status='success', verified=True, completedAt=now(),
                           runtimeHost=info.get('host'), runtimeStatus=info.get('runtime', {}).get('status'))
            atomic_json(args.receipt, receipt)
            print(json.dumps(receipt, ensure_ascii=False), flush=True)
    except BaseException as exc:
        receipt.update(status='failed', completedAt=now(), error=redact(str(exc), token)[:1500])
        atomic_json(args.receipt, receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, default=Path('docs/public-funds-domestic-receipt.json'))
    parser.add_argument('--timeout', type=int, default=1200)
    parser.add_argument('--poll-interval', type=int, default=30)
    args = parser.parse_args()
    token = os.environ.get('MODELSCOPE_API_KEY', '').strip()
    if not token:
        parser.error('Set MODELSCOPE_API_KEY through the automation secret environment')
    try:
        publish(args, token)
    except (Exception, KeyboardInterrupt) as exc:
        print('Public fund domestic publication failed: ' + redact(str(exc), token), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
