#!/usr/bin/env python3
"""Rank source-linked historical candidates; never estimate outcome probabilities."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

DIMENSIONS = {
    'event': ('mechanisms', 'constraints', 'stage'),
    'figure': ('decision_types', 'objectives', 'constraints', 'reversibility'),
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp needs timezone')
    return result


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, label):
    if not isinstance(value, list) or any(not nonempty(x) for x in value):
        raise ValueError(f'{label} must be a list of nonempty strings')
    return set(x.strip().casefold() for x in value)


def mapping(value, label):
    if not isinstance(value, dict) or any(not nonempty(k) or not nonempty(v) for k, v in value.items()):
        raise ValueError(f'{label} must be a string mapping')
    return {k.strip().casefold(): v.strip().casefold() for k, v in value.items()}


def features(value, dimensions):
    if not isinstance(value, dict) or set(value) - set(dimensions):
        raise ValueError('features contains unknown dimensions or is not an object')
    return {d: strings(value.get(d, []), d) for d in dimensions}


def rank(request, candidates, mode):
    if mode not in DIMENSIONS or not isinstance(request, dict):
        raise ValueError('unknown mode or invalid request')
    cutoff = instant(request.get('as_of'))
    target = features(request.get('features'), DIMENSIONS[mode])
    active = [d for d, tags in target.items() if tags]
    if not active:
        raise ValueError('at least one nonempty request feature is required')
    known = mapping(request.get('conditions'), 'conditions')
    if not isinstance(candidates, list):
        raise ValueError('candidates must be a list')
    accepted, excluded, seen = [], [], set()
    for c in candidates:
        if not isinstance(c, dict) or not nonempty(c.get('id')) or not nonempty(c.get('title')):
            raise ValueError('each candidate requires id and title')
        cid = c['id']
        if cid in seen:
            raise ValueError('duplicate candidate id')
        seen.add(cid)
        f = features(c.get('features'), DIMENSIONS[mode])
        required = mapping(c.get('required_conditions'), 'required_conditions')
        if not strings(c.get('transfer_limits'), 'transfer_limits'):
            raise ValueError('transfer_limits must not be empty')
        sources = c.get('sources')
        if not isinstance(sources, list) or not sources:
            raise ValueError('candidate requires sources')
        reasons, unknown = [], []
        availability_unknown = False
        for s in sources:
            if not isinstance(s, dict) or any(not nonempty(s.get(k)) for k in ('url', 'locator', 'basis')):
                raise ValueError('source requires url, locator, basis')
            url = urlsplit(s['url'])
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
                raise ValueError('source URL must be HTTP/S without credentials')
            instant(s.get('accessed_at'))
            scope = s.get('access_scope')
            if scope not in ('full_text', 'excerpt', 'snippet'):
                raise ValueError('unknown access_scope')
            if scope == 'snippet':
                reasons.append('snippet_only_evidence')
            if s.get('available_at') is None:
                availability_unknown = True
            elif instant(s['available_at']) > cutoff:
                reasons.append('source_after_cutoff')
        for key, value in required.items():
            if key not in known:
                unknown.append(key)
            elif known[key] != value:
                reasons.append('condition_conflict:' + key)
        matches = {d: sorted(target[d] & f[d]) for d in active}
        score = sum(len(matches[d]) / len(target[d]) for d in active) / len(active)
        if score == 0:
            reasons.append('no_structural_overlap')
        if reasons:
            excluded.append({'id': cid, 'reasons': sorted(set(reasons))})
            continue
        accepted.append({
            'id': cid, 'title': c['title'], 'rank_score': round(score, 6),
            'status': 'provisional' if unknown or availability_unknown else 'candidate',
            'matches': matches, 'missing_dimensions': [d for d in active if not f[d]],
            'unknown_conditions': sorted(unknown),
            'source_availability_unknown': availability_unknown,
            'transfer_limits': c['transfer_limits'], 'sources': sources,
        })
    accepted.sort(key=lambda x: (-x['rank_score'], x['id']))
    return {'mode': mode, 'as_of': request['as_of'],
            'status': 'candidates_found' if accepted else 'no_analogue',
            'score_meaning': 'Equal-weight request-tag coverage for reading priority; not probability or causal validity.',
            'candidates': accepted, 'excluded': excluded}


def main(mode):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--candidates', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = rank(json.loads(args.request.read_text()), json.loads(args.candidates.read_text()), mode)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, TypeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
