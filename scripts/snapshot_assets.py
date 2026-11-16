"""Lossless snapshot shards under the Studio's 10 MiB ordinary-file limit.

Keep the existing snapshot-perf-NNN.js transport names so both published
entry points can load and verify new snapshots without a frontend rollout.
Each shard contains one JSON-only assignment to funds, perf, or details.
"""
import json
from pathlib import Path
import re

MAIN = 'window.MARKET_SNAPSHOT='
PREFIXES = {
    'funds': 'window.MARKET_SNAPSHOT.funds=window.MARKET_SNAPSHOT.funds.concat(',
    'perf': 'Object.assign(window.MARKET_SNAPSHOT.perf,',
    'details': 'Object.assign(window.MARKET_SNAPSHOT.details,',
}
LIMIT = 4_000_000


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def read_snapshot(directory):
    directory = Path(directory)
    source = (directory / 'snapshot.js').read_text(encoding='utf-8').strip()
    if not source.startswith(MAIN) or not source.endswith(';'):
        raise ValueError('Invalid main snapshot')
    snapshot = json.loads(source[len(MAIN):-1])
    files = sorted(directory.glob('snapshot-perf-*.js'))
    if [p.name for p in files] != [f'snapshot-perf-{i:03d}.js' for i in range(1, len(files) + 1)]:
        raise ValueError('Snapshot shard sequence is incomplete')
    for path in files:
        body = path.read_text(encoding='utf-8').strip()
        matches = [key for key, prefix in PREFIXES.items() if body.startswith(prefix) and body.endswith(');')]
        if len(matches) != 1:
            raise ValueError('Invalid snapshot shard: ' + path.name)
        key = matches[0]
        chunk = json.loads(body[len(PREFIXES[key]):-2])
        if key == 'funds':
            if not isinstance(chunk, list):
                raise ValueError('Invalid directory shard')
            snapshot.setdefault(key, []).extend(chunk)
        else:
            current = snapshot.setdefault(key, {})
            if not isinstance(chunk, dict) or set(current).intersection(chunk):
                raise ValueError('Duplicate or invalid snapshot records: ' + path.name)
            current.update(chunk)
    codes = [fund['code'] for fund in snapshot.get('funds', [])]
    if len(codes) != len(set(codes)):
        raise ValueError('Duplicate directory code across snapshot shards')
    return snapshot


def write_snapshot(directory, snapshot, limit=LIMIT):
    directory = Path(directory)
    main = {**snapshot, **{key: [] if key == 'funds' else {}
                          for key in PREFIXES if key in snapshot}}
    assets = {'snapshot.js': MAIN + compact(main) + ';\n'}
    for key, prefix in PREFIXES.items():
        records = snapshot.get(key, [] if key == 'funds' else {})
        items = list(records) if key == 'funds' else list(records.items())
        chunk, size = [], len(prefix.encode()) + 6

        def emit():
            value = chunk if key == 'funds' else dict(chunk)
            name = f'snapshot-perf-{len(assets):03d}.js'
            assets[name] = prefix + compact(value) + ');\n'

        for item in items:
            cost = len(compact(item if key == 'funds' else {item[0]: item[1]}).encode()) + 1
            if chunk and size + cost >= limit:
                emit()
                chunk, size = [], len(prefix.encode()) + 6
            chunk.append(item)
            size += cost
        if chunk:
            emit()
    if any(len(body.encode()) >= limit for body in assets.values()):
        raise ValueError('A snapshot record or metadata exceeds the shard byte limit')
    # Validate all new bytes before replacing any old assets.
    for name, body in assets.items():
        (directory / name).write_text(body, encoding='utf-8')
    for path in directory.glob('snapshot-perf-*.js'):
        if path.name not in assets:
            path.unlink()
    html_path = directory / 'index.html'
    html = re.sub(r'\n?<script src="snapshot-perf-\d+\.js"></script>', '', html_path.read_text())
    marker = '<script src="snapshot.js"></script>'
    if html.count(marker) != 1:
        raise ValueError('Snapshot bootstrap position is missing or ambiguous')
    names = list(assets)[1:]
    html = html.replace(marker, marker + '\n' + '\n'.join(f'<script src="{name}"></script>' for name in names))
    html_path.write_text(html, encoding='utf-8')
    return names
