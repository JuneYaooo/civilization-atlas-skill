#!/usr/bin/env python3
"""Recompute a retrospective hypothesis audit, never a forecast accuracy score."""
import hashlib
import json
import math
import operator
from datetime import date
from pathlib import Path

OPS = {'gt': operator.gt, 'lt': operator.lt, 'ge': operator.ge}

def input_status(source, cutoff):
    cutoff = date.fromisoformat(cutoff)
    if date.fromisoformat(source['document_date']) > cutoff:
        return 'reject_future_document'
    revision = source.get('known_revision_date')
    if revision and date.fromisoformat(revision) > cutoff:
        return 'reject_later_revision'
    # A date on a current webpage is not an archived information set.
    return 'historical_version_unverified'

def resolve(claim):
    value = claim.get('reported_value')
    if value is None and claim.get('base') is not None and claim.get('end') is not None:
        base, end = claim['base'], claim['end']
        if base <= 0 or not all(math.isfinite(x) for x in (base, end)):
            raise ValueError('Invalid growth baseline')
        value = (end / base - 1) * 100
    if value is None:
        return {'status': 'unresolved', 'value_percent': None}
    if not math.isfinite(value):
        raise ValueError('Nonfinite outcome')
    supported = OPS[claim['operator']](value, claim['threshold'])
    return {'status': 'consistent' if supported else 'contradicted', 'value_percent': round(value, 4)}

def run(data):
    if data['mode'] != 'historical_reconstruction' or not data['outcomes_known_during_design'] or data['accuracy_estimate_permitted']:
        raise ValueError('This audit cannot be relabelled as prospective evaluation')
    sources = data['sources']
    cases = {c['id']: c for c in data['cases']}
    gates = []
    for case in cases.values():
        for sid in case['inputs']:
            status = input_status(sources[sid], case['cutoff'])
            if status.startswith('reject_'):
                raise ValueError(f'Leaked input: {case["id"]}/{sid}: {status}')
            gates.append(dict(case=case['id'], source=sid, status=status))
    results = []
    for c in data['claims']:
        if c['case'] not in cases or not c['outcome_sources']:
            raise ValueError('Missing case or outcome provenance')
        for sid in c['outcome_sources']:
            if sid not in sources:
                raise ValueError('Unknown outcome source')
        if c['role'] not in ('bounded_hypothesis', 'overclaim_stress_test'):
            raise ValueError('Unknown hypothesis role')
        results.append(dict(id=c['id'], role=c['role'], hypothesis=c['hypothesis'], **resolve(c)))
    excluded = [dict(source=e['source'], status=input_status(sources[e['source']], cases[e['case']]['cutoff'])) for e in data['excluded_inputs']]
    return dict(mode=data['mode'], accuracy_estimate_permitted=False, input_checks=gates, excluded_inputs=excluded, results=results, unassessed=data['unassessed'])

if __name__ == '__main__':
    path = Path(__file__).with_name('audit.json')
    raw = path.read_bytes()
    report = run(json.loads(raw))
    report['input_sha256'] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(report, ensure_ascii=False, indent=2))
