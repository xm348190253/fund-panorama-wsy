"""Verified inception metadata shared by collection, calculation and publishing."""
import calendar
import datetime as dt
import hashlib
import json
from pathlib import Path


def valid_date(value, as_of=None):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        return None
    if parsed.isoformat() != value or (as_of and value > as_of):
        return None
    return value


def load_profiles(path):
    if not path or not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text())
    if data.get('schemaVersion') != 1 or not isinstance(data.get('records'), dict):
        raise ValueError('Unsupported fund profile metadata schema')
    return data


def apply_inception(product, base_date=None, profile=None, as_of=None):
    """Fill gaps only; a profile date must have passed identity verification."""
    result = dict(product)
    existing = valid_date(result.get('inception'), as_of)
    base_date = valid_date(base_date, as_of)
    if existing:
        result['inception'] = existing
        return result
    if base_date:
        result['inception'] = base_date
        result['inceptionMeta'] = {'status': 'verified', 'sourceReportedInceptionDate': base_date,
            'sourceName': '天天基金批量排行', 'dateSemantic': '批量排行对当前代码披露的成立日期',
            'retrievedAt': as_of}
        return result
    result.pop('inception', None)
    if not profile:
        return result
    meta = {key: profile[key] for key in ('status', 'sourceReportedInceptionDate', 'issueDate',
            'retrievedAt', 'dateSemantic') if profile.get(key) is not None}
    evidence = profile.get('evidence') or {}
    meta['sourceUrl'] = profile.get('sourceUrl') or profile.get('url') or evidence.get('url')
    meta['sourceHash'] = profile.get('sha256') or evidence.get('sha256')
    meta['retrievedAt'] = profile.get('retrievedAt') or evidence.get('retrievedAt')
    identity = profile.get('identity') or {}
    meta['identityNote'] = identity.get('evidenceText')
    candidate = valid_date(profile.get('inceptionDate'), as_of)
    if profile.get('code') != product['code']:
        meta['status'] = 'identity_mismatch'
    elif profile.get('status') == 'verified' and candidate:
        result['inception'] = candidate
    elif profile.get('status') == 'verified':
        meta['status'] = 'date_conflict'
    result['inceptionMeta'] = {k: v for k, v in meta.items() if v is not None}
    return result


def calculation_input_hash(product, as_of):
    payload = {k: product.get(k) for k in ('code', 'name', 'type')}
    payload['inception'] = valid_date(product.get('inception'), as_of)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def months_before(value, months):
    date = dt.date.fromisoformat(value)
    year, month0 = divmod(date.year * 12 + date.month - 1 - months, 12)
    month = month0 + 1
    return dt.date(year, month, min(date.day, calendar.monthrange(year, month)[1])).isoformat()


def enforce_inception_intervals(record, inception, field_date):
    """Apply after every merge so old/source returns cannot outlive the product."""
    result = {**record, 'fieldStatus': dict(record.get('fieldStatus') or {})}
    inception = valid_date(inception)
    if not inception:
        return result
    for key, months in (('m1', 1), ('m3', 3), ('m6', 6), ('y1', 12)):
        end = valid_date(field_date(result, key))
        if end and inception > months_before(end, months):
            result.pop(key, None)
            result['fieldStatus'][key] = {'status': 'missing', 'reason': 'insufficient_history',
                                         'asOf': end, 'inceptionDate': inception}
    return result
