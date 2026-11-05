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
from insurance_snapshot import build_snapshot, validate_snapshot, VERSION as INSURANCE_VERSION

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

    def push(self):
        # Upload any remaining repository LFS objects explicitly because hooks
        # are disabled; ModelScope rejects branch updates with missing objects.
        self.git('lfs', 'push', 'origin', 'HEAD')
        self.git('push', 'origin', 'HEAD:master')

    def stage_assets(self, names):
        names = sorted(set(names))
        archives = [name for name in names if name.startswith('insurance-data/') and name.endswith('.zip')]
        if archives:
            # The static Studio serves LFS pointers verbatim. Keep these small
            # public report bundles as ordinary blobs, including future months.
            directory = self.path / 'insurance-data'
            attributes = directory / '.gitattributes'
            if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
                raise SyncError('Insurance download directory is not a regular directory')
            if attributes.is_symlink() or (attributes.exists() and not regular_file(attributes)):
                raise SyncError('Insurance download attributes are not a regular file')
            directory.mkdir(parents=True, exist_ok=True)
            current = attributes.read_text(encoding='utf-8') if attributes.exists() else ''
            rule = '*.zip -filter -diff -merge -text'
            lines = [line for line in current.splitlines() if line.strip()]
            if not lines or lines[-1] != rule:
                attributes.write_text(current + ('\n' if current and not current.endswith('\n') else '')
                                      + rule + '\n', encoding='utf-8')
            names.append('insurance-data/.gitattributes')
        self.git('add', '--', *names)
        if archives:
            # Re-clean tracked files as well, replacing existing LFS pointers
            # without changing the downloaded ZIP bytes or version history.
            self.git('add', '--renormalize', '--', *archives)

    def sync(self, site, names):
        """Only take ownership of known runtime assets, never deployment settings."""
        current = {p.name for p in self.path.iterdir() if SHARD_RE.fullmatch(p.name)}
        obsolete = current - set(names)
        for name in set(names) | obsolete:
            target = self.path / name
            if '/' in name:
                parts = Path(name).parts
                valid = (name == 'insurance-data/manifest.json' or
                         (len(parts) == 3 and parts[0] == 'insurance-data'
                          and INSURANCE_VERSION.fullmatch(parts[1])
                          and (parts[2] in {'meta.json', 'database.xlsx'} or re.fullmatch(r'(?:period-20\d{2}-(?:0[1-9]|1[0-2])\.json|report-20\d{2}-(?:0[1-9]|1[0-2])\.(?:docx|xlsx|zip))', parts[2]))))
                if not valid:
                    raise SyncError('Unowned nested asset: ' + name)
                for parent in target.parents:
                    if parent == self.path:
                        break
                    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                        raise SyncError('Refusing to overwrite a non-directory asset parent: ' + name)
                if len(parts) == 3 and target.is_file() and target.read_bytes() != (Path(site) / name).read_bytes():
                    raise SyncError('Refusing to overwrite immutable insurance version: ' + name)
            if target.is_symlink() or (target.exists() and not regular_file(target)):
                raise SyncError('Refusing to overwrite a non-regular repository file: ' + name)
        for name in names:
            (self.path / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(site) / name, self.path / name)
        for name in obsolete:
            (self.path / name).unlink()
        self.stage_assets(set(names) | obsolete)
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
        quote_cache = getattr(args, 'quote_cache', None)
        quote_snapshot = None
        if quote_cache:
            # Layout-only publication reuses the verified published quotes.
            # Refreshing independent external feeds must not block a UI repair.
            validate_site(source)
            from refresh_index_quotes import validate_snapshot as validate_quotes
            match = re.search(r'<script>window\.__FUND_INDEX_SNAPSHOT__=(.+?);</script>',
                              (source / 'index.html').read_text(encoding='utf-8'), re.S)
            if not match:
                raise SyncError('Published index quote snapshot is missing')
            quote_snapshot = validate_quotes(json.loads(match.group(1)))
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
            if quote_cache:
                atomic_json(quote_cache, quote_snapshot)
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
        if 'insurance-dashboard-bootstrap' in (Path(args.site) / 'index.html').read_text(encoding='utf-8'):
            build_snapshot(Path(args.site) / 'insurance-data')
            insurance, insurance_hashes = validate_snapshot(Path(args.site) / 'insurance-data')
            hashes.update(insurance_hashes)
            receipt['insuranceVersion'] = insurance['version']
        receipt.update(version=release['version'], dataDate=release.get('dataDate'), assetCount=len(hashes),
                       indexQuotesCollectedAt=release.get('indexQuotesCollectedAt'),
                       indexQuotesAvailable=release.get('indexQuotesAvailable'))
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
                checkout.push()
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


def sync_insurance(args, token):
    """Update only public insurance views, retaining every existing fund asset."""
    receipt = {'status': 'started', 'phase': 'clone', 'startedAt': now(),
               'studio': args.repo, 'pushed': False, 'verified': False}
    atomic_json(args.receipt, receipt)
    try:
        client = Client(args.repo, token)
        client.verify_configuration(client.api())
        with temp_checkout(args.repo, token) as folder:
            checkout = StudioCheckout(folder, args.repo, token)
            source = checkout.clone()
            release, fund_hashes = validate_site(source)
            if 'insurance-dashboard-bootstrap' not in (source / 'index.html').read_text(encoding='utf-8'):
                raise SyncError('Publish the insurance dashboard interface before synchronizing its data')
            manifest = build_snapshot(source / 'insurance-data')
            _, insurance_hashes = validate_snapshot(source / 'insurance-data')
            receipt.update(insuranceVersion=manifest['version'], fundVersion=release['version'])
            checkout.stage_assets(insurance_hashes)
            changed = checkout.git('diff', '--cached', '--quiet', allowed=(0, 1)).returncode == 1
            if not changed:
                receipt.update(status='unchanged', phase='complete', completedAt=now())
            else:
                if validate_site(source)[1] != fund_hashes:
                    raise SyncError('Insurance sync unexpectedly changed fund assets')
                checkout.git('-c', 'user.name=Fund Panorama Automation', '-c',
                             'user.email=automation@users.noreply.github.com',
                             'commit', '-m', 'Synchronize public insurance analysis ' + manifest['version'])
                checkout.push()
                receipt.update(pushed=True, phase='deploy')
                atomic_json(args.receipt, receipt)
                client.api('POST', '/deploy')
                receipt['phase'] = 'verify'
                atomic_json(args.receipt, receipt)
                client.wait_verified(release, {**fund_hashes, **insurance_hashes}, args.timeout, args.poll_interval)
                receipt.update(status='success', phase='complete', verified=True, completedAt=now())
        atomic_json(args.receipt, receipt)
        print('Insurance synchronization: ' + receipt['status'], flush=True)
    except BaseException as exc:
        receipt.update(status='failed', completedAt=now(), error=redact(str(exc), token)[:1500])
        atomic_json(args.receipt, receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    boot = commands.add_parser('bootstrap', help='Fetch snapshot and chart-library baselines; no website publication')
    boot.add_argument('--dist', type=Path, default=ROOT / 'dist')
    boot.add_argument('--quote-cache', type=Path, help='Reuse verified published index quotes for a layout-only build')
    pub = commands.add_parser('publish', help='Publish and verify a validated static release')
    pub.add_argument('--site', required=True, type=Path)
    pub.add_argument('--receipt', type=Path, default=ROOT / 'docs/cloud-deployment-receipt.json')
    pub.add_argument('--timeout', type=int, default=1800)
    pub.add_argument('--poll-interval', type=int, default=30)
    insurance = commands.add_parser('sync-insurance', help='Synchronize only public insurance JSON when its version changes')
    insurance.add_argument('--receipt', type=Path, default=ROOT / 'docs/insurance-sync-receipt.json')
    insurance.add_argument('--timeout', type=int, default=1800)
    insurance.add_argument('--poll-interval', type=int, default=30)
    for command in (boot, pub, insurance):
        command.add_argument('--repo', default=DEFAULT_REPO)
    args = parser.parse_args()
    token = os.environ.get('MODELSCOPE_API_KEY', '').strip()
    if not token:
        parser.error('Set MODELSCOPE_API_KEY through the automation secret environment')
    try:
        checked_repo(args.repo)
        if args.command in ('publish', 'sync-insurance'):
            if not 1 <= args.timeout <= 1800 or not 1 <= args.poll_interval <= 60:
                raise SyncError('Timeout must be 1..1800 seconds and polling interval 1..60 seconds')
            (publish if args.command == 'publish' else sync_insurance)(args, token)
        else:
            bootstrap(args, token)
    except (Exception, KeyboardInterrupt) as exc:
        print('ModelScope sync failed: ' + redact(str(exc), token), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
