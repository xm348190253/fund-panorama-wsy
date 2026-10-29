#!/usr/bin/env python3
"""Bootstrap snapshots and publish a validated static site to its existing Studio.

Credentials come only from MODELSCOPE_API_KEY. No configuration or visibility
changes are made. A successful push is not reported as a successful deployment:
we also wait for Running and verify the unique release manifest and every asset.
A failed deployment is recorded; automatic rollback is intentionally not used.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_BASE = 'https://modelscope.cn/openapi/v1'
DEFAULT_REPO = 'wangshuyang2126/fund-panorama-wsy'
REQUIRED_ASSETS = {'index.html', 'market.js', 'snapshot.js', 'echarts.min.js'}
SHARD_RE = re.compile(r'snapshot-perf-[0-9]+\.js\Z')
VERSION_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')
SHA_RE = re.compile(r'[0-9a-f]{64}\Z')


class SyncError(RuntimeError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def redact(message, token):
    text = str(message)
    if token:
        text = text.replace(token, '[REDACTED]')
        text = text.replace(base64.b64encode(('oauth2:' + token).encode()).decode(), '[REDACTED]')
    text = re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@', r'\1[REDACTED]@', text)
    text = re.sub(r'(?i)Bearer\s+[^\s"\']+', 'Bearer [REDACTED]', text)
    return text


def checked_repo(repo):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise SyncError('Invalid Studio repository identifier')
    return repo


def runtime_asset(name):
    return name in REQUIRED_ASSETS or bool(SHARD_RE.fullmatch(name))


def regular_file(path):
    return path.is_file() and not path.is_symlink()


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + '.tmp')
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pending.replace(path)


def validate_site(site):
    """The manifest is a strict allowlist and all digests must match disk."""
    site = Path(site).resolve()
    if not regular_file(site / 'release.json'):
        raise SyncError('release.json is missing or is not a regular file')
    try:
        release = json.loads((site / 'release.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise SyncError('release.json is not valid JSON') from exc
    if not isinstance(release, dict) or not isinstance(release.get('version'), str) or not VERSION_RE.fullmatch(release['version']):
        raise SyncError('release.json requires a unique, safe version string')
    files = release.get('files')
    if not isinstance(files, dict) or not REQUIRED_ASSETS.issubset(files) or not any(SHARD_RE.fullmatch(name) for name in files):
        raise SyncError('release.json does not list the complete required static assets')
    hashes = {}
    for name, entry in files.items():
        if not runtime_asset(name):
            raise SyncError('release.json contains an unowned asset: ' + str(name))
        expected = entry.get('sha256') if isinstance(entry, dict) else entry
        if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
            raise SyncError('Invalid SHA-256 for ' + name)
        path = site / name
        if not regular_file(path) or not path.stat().st_size:
            raise SyncError('Static asset is missing, empty or a symlink: ' + name)
        if digest(path.read_bytes()) != expected:
            raise SyncError('Static asset checksum mismatch: ' + name)
        hashes[name] = expected
    present = {p.name for p in site.iterdir() if runtime_asset(p.name)}
    if present != set(files):
        raise SyncError('Unlisted static assets exist in the release directory')
    return release, hashes


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Authenticated requests must never forward a token to another endpoint.
        return None


class Client:
    def __init__(self, repo, token):
        self.repo = checked_repo(repo)
        self.token = token
        self.api_opener = urllib.request.build_opener(NoRedirect())

    def api(self, method='GET', suffix='', request_timeout=60):
        request = urllib.request.Request(
            API_BASE + '/studios/' + self.repo + suffix,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/json',
                     'User-Agent': 'fund-panorama-daily/1.0'}, method=method)
        try:
            with self.api_opener.open(request, timeout=request_timeout) as response:
                value = json.load(response)
        except urllib.error.HTTPError as exc:
            raise SyncError('ModelScope API returned HTTP ' + str(exc.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise SyncError('ModelScope API request failed (' + type(exc).__name__ + ')') from None
        if not isinstance(value, dict) or value.get('success') is not True:
            raise SyncError('ModelScope API returned an unsuccessful or malformed response')
        data = value.get('data')
        if method == 'POST' and suffix == '/deploy':
            # The deployment acknowledgement may omit data. It only confirms
            # acceptance; wait_verified performs the actual publication checks.
            return data if isinstance(data, dict) else {}
        if not isinstance(data, dict):
            raise SyncError('ModelScope API returned an unsuccessful or malformed response')
        return data

    def verify_configuration(self, info):
        if info.get('id') != self.repo or info.get('sdk_type') != 'static':
            raise SyncError('The configured repository is not the expected existing Static Studio')
        hardware = info.get('hardware', '')
        if not isinstance(hardware, str) or not hardware.startswith('platform/'):
            raise SyncError('Studio no longer uses the expected free platform hardware; deployment stopped')
        host = info.get('host', '').rstrip('/')
        parsed = urllib.parse.urlparse(host)
        if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port
                or parsed.path or parsed.query or parsed.fragment
                or parsed.hostname != self.repo.replace('/', '-') + '.ms.show'):
            raise SyncError('Studio returned an unexpected runtime host')
        return host

    def public_bytes(self, url, limit=100 * 1024 * 1024, request_timeout=60):
        request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'fund-panorama-daily/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                data = response.read(limit + 1)
            if len(data) > limit:
                raise SyncError('Published asset exceeds verification size limit')
            return data
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SyncError('Published asset is not reachable (' + type(exc).__name__ + ')') from None

    def verify_live(self, host, release, hashes, deadline=None):
        def remaining():
            value = 60 if deadline is None else min(60, deadline - time.monotonic())
            if value <= 0:
                raise SyncError('Deployment verification time budget exhausted')
            return value
        query = urllib.parse.urlencode({'release': release['version'], '_': time.time_ns()})
        try:
            online = json.loads(self.public_bytes(host + '/release.json?' + query, 1024 * 1024, remaining()))
        except (ValueError, UnicodeError):
            raise SyncError('Published release manifest is not valid JSON') from None
        if not isinstance(online, dict) or online.get('version') != release['version']:
            raise SyncError('The previous release is still being served')
        if online != release:
            raise SyncError('Published release manifest differs from the prepared manifest')
        for name, expected in hashes.items():
            if digest(self.public_bytes(host + '/' + urllib.parse.quote(name) + '?' + query,
                                        request_timeout=remaining())) != expected:
                raise SyncError('Published asset checksum mismatch: ' + name)

    def wait_verified(self, release, hashes, timeout=1800, interval=30):
        deadline = time.monotonic() + timeout
        last_problem = 'Deployment has not reached Running'
        last_status = None
        while time.monotonic() < deadline:
            try:
                info = self.api(request_timeout=max(.1, min(60, deadline - time.monotonic())))
                host = self.verify_configuration(info)
                status = info.get('runtime', {}).get('status', info.get('status'))
                if status != last_status:
                    print('Deployment status: ' + str(status), flush=True)
                    last_status = status
                if status in {'BuildFailed', 'DeployFailed'}:
                    raise SyncError('Studio deployment entered ' + status)
                if status == 'Running':
                    try:
                        self.verify_live(host, release, hashes, deadline)
                    except SyncError as exc:
                        last_problem = str(exc)
                    else:
                        return info
            except SyncError as exc:
                # Explicit build failures or unsafe configuration are terminal.
                if any(term in str(exc) for term in ('entered ', 'configured repository', 'hardware', 'unexpected runtime host')):
                    raise
                last_problem = str(exc)
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(interval, remaining))
        raise SyncError('Deployment verification timed out: ' + last_problem)


class StudioCheckout:
    def __init__(self, folder, repo, token):
        self.folder = Path(folder)
        self.repo = checked_repo(repo)
        self.token = token
        self.path = self.folder / 'studio'
        askpass = self.folder / 'git-askpass.sh'
        askpass.write_text('#!/bin/sh\ncase "$1" in\n*Username*) printf "%s\\n" oauth2 ;;\n*Password*) printf "%s\\n" "$MODELSCOPE_API_KEY" ;;\n*) exit 1 ;;\nesac\n', encoding='utf-8')
        askpass.chmod(0o700)
        self.env = dict(os.environ, MODELSCOPE_API_KEY=token, GIT_ASKPASS=str(askpass), GIT_TERMINAL_PROMPT='0')
        self.env.pop('GIT_TRACE', None)
        self.env.pop('GIT_TRACE_CURL', None)
        self.env.pop('GIT_CURL_VERBOSE', None)

    def git(self, *args, cwd=None, allowed=(0,)):
        try:
            result = subprocess.run(['git', '-c', 'credential.helper=', '-c', 'core.hooksPath=/dev/null', *args],
                                    cwd=cwd or self.path, env=self.env, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SyncError('Git operation failed (' + type(exc).__name__ + ')') from None
        if result.returncode not in allowed:
            detail = redact(result.stderr, self.token).strip()[-1000:]
            raise SyncError('Git operation failed: ' + detail)
        return result

    def clone(self):
        self.git('clone', '--depth', '1', '--no-tags', '--single-branch', '--branch', 'master',
                 'https://modelscope.cn/studios/' + self.repo + '.git', str(self.path), cwd=self.folder)
        return self.path

    def sync(self, site, names):
        """Only take ownership of known runtime assets, never deployment settings."""
        current = {p.name for p in self.path.iterdir() if SHARD_RE.fullmatch(p.name)}
        obsolete = current - set(names)
        for name in set(names) | obsolete:
            target = self.path / name
            if target.is_symlink() or (target.exists() and not regular_file(target)):
                raise SyncError('Refusing to overwrite a non-regular repository file: ' + name)
        for name in names:
            shutil.copyfile(Path(site) / name, self.path / name)
        for name in obsolete:
            (self.path / name).unlink()
        self.git('add', '--', *sorted(set(names) | obsolete))
        changed = self.git('diff', '--cached', '--quiet', allowed=(0, 1)).returncode == 1
        if changed:
            self.git('-c', 'user.name=Fund Panorama Automation', '-c', 'user.email=automation@users.noreply.github.com',
                     'commit', '-m', 'Update validated public fund snapshot')
        return changed


def temp_checkout(repo, token):
    temp_root = ROOT / '.temp'
    temp_root.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(prefix='modelscope-', dir=temp_root)


def bootstrap(args, token):
    dist = Path(args.dist).resolve()
    dist.mkdir(parents=True, exist_ok=True)
    with temp_checkout(args.repo, token) as folder:
        checkout = StudioCheckout(folder, args.repo, token)
        source = checkout.clone()
        names = {'snapshot.js', 'echarts.min.js'} | {p.name for p in source.iterdir() if SHARD_RE.fullmatch(p.name)}
        if len(names) < 3 or any(not regular_file(source / n) or not (source / n).stat().st_size for n in names):
            raise SyncError('Remote snapshot/chart baseline is incomplete')
        # Validate all inputs before modifying the local baseline. Back it up for
        # rollback if a local disk copy fails; index.html and market.js are untouched.
        old = {'snapshot.js', 'echarts.min.js'} | {p.name for p in dist.iterdir() if SHARD_RE.fullmatch(p.name)}
        if any((dist / n).is_symlink() or ((dist / n).exists() and not regular_file(dist / n)) for n in old | names):
            raise SyncError('Local snapshot path is not a regular file')
        backup = Path(folder) / 'baseline-backup'
        backup.mkdir()
        existed = {n for n in old if (dist / n).exists()}
        for name in existed:
            shutil.copy2(dist / name, backup / name)
        try:
            for name in names:
                shutil.copyfile(source / name, dist / name)
            for name in old - names:
                (dist / name).unlink(missing_ok=True)
        except BaseException:
            for name in old | names:
                (dist / name).unlink(missing_ok=True)
            for name in existed:
                shutil.copy2(backup / name, dist / name)
            raise
    print('Bootstrapped current Studio repository snapshot/chart assets: ' + str(len(names)), flush=True)


def publish(args, token):
    receipt = {'status': 'started', 'phase': 'validate', 'startedAt': now(),
               'studio': args.repo, 'url': 'https://modelscope.cn/studios/' + args.repo,
               'pushed': False, 'deployRequested': False, 'verified': False,
               'automaticRollback': False}
    atomic_json(args.receipt, receipt)
    try:
        release, hashes = validate_site(args.site)
        receipt.update(version=release['version'], assetCount=len(hashes))
        client = Client(args.repo, token)
        info = client.api()
        client.verify_configuration(info)
        with temp_checkout(args.repo, token) as folder:
            receipt['phase'] = 'clone'
            checkout = StudioCheckout(folder, args.repo, token)
            checkout.clone()
            receipt['previousCommit'] = checkout.git('rev-parse', 'HEAD').stdout.strip()
            receipt['phase'] = 'sync'
            changed = checkout.sync(args.site, sorted(set(hashes) | {'release.json'}))
            receipt['commit'] = checkout.git('rev-parse', 'HEAD').stdout.strip()
            if changed:
                receipt['phase'] = 'push'
                checkout.git('push', 'origin', 'HEAD:master')
                receipt['pushed'] = True
            receipt['phase'] = 'deploy'
            atomic_json(args.receipt, receipt)
            client.api('POST', '/deploy')  # No body is defined by the official API.
            receipt['deployRequested'] = True
            receipt['phase'] = 'verify'
            atomic_json(args.receipt, receipt)
            info = client.wait_verified(release, hashes, args.timeout, args.poll_interval)
            receipt.update(status='success', phase='complete', verified=True,
                           runtimeStatus=info.get('runtime', {}).get('status'),
                           runtimeHost=info.get('host'), completedAt=now())
        atomic_json(args.receipt, receipt)
        print('Published release verified: ' + release['version'], flush=True)
    except BaseException as exc:
        receipt.update(status='failed', completedAt=now(), error=redact(str(exc), token)[:1500])
        atomic_json(args.receipt, receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    boot = commands.add_parser('bootstrap', help='Fetch snapshot and chart-library baselines; no website publication')
    boot.add_argument('--dist', type=Path, default=ROOT / 'dist')
    pub = commands.add_parser('publish', help='Publish and verify a validated static release')
    pub.add_argument('--site', required=True, type=Path)
    pub.add_argument('--receipt', type=Path, default=ROOT / 'docs/cloud-deployment-receipt.json')
    pub.add_argument('--timeout', type=int, default=1800)
    pub.add_argument('--poll-interval', type=int, default=30)
    for command in (boot, pub):
        command.add_argument('--repo', default=DEFAULT_REPO)
    args = parser.parse_args()
    token = os.environ.get('MODELSCOPE_API_KEY', '').strip()
    if not token:
        parser.error('Set MODELSCOPE_API_KEY through the automation secret environment')
    try:
        checked_repo(args.repo)
        if args.command == 'publish':
            if not 1 <= args.timeout <= 1800 or not 1 <= args.poll_interval <= 60:
                raise SyncError('Timeout must be 1..1800 seconds and polling interval 1..60 seconds')
            publish(args, token)
        else:
            bootstrap(args, token)
    except (Exception, KeyboardInterrupt) as exc:
        print('ModelScope sync failed: ' + redact(str(exc), token), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
