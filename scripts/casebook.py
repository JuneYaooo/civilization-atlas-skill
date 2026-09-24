#!/usr/bin/env python3
"""Validate and freeze research cases; keep later reviews separate from originals.

Validation checks traceability and information dates, not causal truth. A local
digest detects accidental changes; it is not a trusted timestamp or signature.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def timestamp(value):
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('timestamp needs a timezone')
    return date


def validate(case):
    errors, notices = [], []
    if not isinstance(case, dict):
        return ['Case must be an object'], []
    if case.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    for field in ('id', 'question', 'target_definition', 'geography', 'time_scope'):
        if not isinstance(case.get(field), str) or not case[field].strip():
            errors.append(f'{field} needs a nonempty string')
    mode = case.get('information_regime')
    if mode not in ('real_time', 'historical_reconstruction', 'synthetic'):
        errors.append('Unknown information_regime')
    try:
        cutoff = timestamp(case.get('as_of', ''))
    except (TypeError, ValueError, AttributeError):
        errors.append('as_of needs an ISO timestamp with timezone')
        cutoff = None
    if mode == 'historical_reconstruction':
        notices.append('Historical reconstruction: later knowledge may be present; not a real-time test.')
    if mode == 'synthetic':
        notices.append('Synthetic case: no empirical validity follows from execution.')
    collections = {}
    for field in ('sources', 'evidence', 'claims', 'mechanisms', 'predictions'):
        records = case.get(field, [])
        if not isinstance(records, list):
            errors.append(f'{field} must be a list')
            records = []
        table = {}
        for r in records:
            if not isinstance(r, dict) or not isinstance(r.get('id'), str) or not r['id']:
                errors.append(f'{field} record requires id')
                continue
            if r['id'] in table:
                errors.append(f'Duplicate {field} id: {r["id"]}')
            table[r['id']] = r
        collections[field] = table
    if not collections['claims']:
        errors.append('At least one claim is required')
    for sid, s in collections['sources'].items():
        for field in ('title', 'url', 'version', 'access_scope'):
            if not isinstance(s.get(field), str) or not s[field].strip():
                errors.append(f'Source {sid}: missing {field}')
        available = s.get('available_at')
        if available is None:
            if mode == 'real_time':
                errors.append(f'Source {sid}: real-time use requires documented available_at')
            else:
                notices.append(f'Source {sid}: original availability is unknown')
        else:
            try:
                date = timestamp(available)
                if mode == 'real_time' and cutoff is not None and date > cutoff:
                    errors.append(f'Source {sid}: available after cutoff')
            except (TypeError, ValueError, AttributeError):
                errors.append(f'Source {sid}: invalid available_at')
        if s.get('sha256') is not None and not re.fullmatch('[a-f0-9]{64}', str(s['sha256'])):
            errors.append(f'Source {sid}: invalid sha256')
    for eid, e in collections['evidence'].items():
        if e.get('source_id') not in collections['sources']:
            errors.append(f'Evidence {eid}: unknown source')
        for field in ('locator', 'observation'):
            if not isinstance(e.get(field), str) or not e[field].strip():
                errors.append(f'Evidence {eid}: missing {field}')
    for cid, c in collections['claims'].items():
        kind = c.get('kind')
        if kind not in ('observation', 'source_claim', 'hypothesis', 'decision_value'):
            errors.append(f'Claim {cid}: unknown kind')
        if not isinstance(c.get('statement'), str) or not c['statement'].strip():
            errors.append(f'Claim {cid}: missing statement')
        links = c.get('evidence_links', [])
        if not isinstance(links, list):
            errors.append(f'Claim {cid}: evidence_links must be a list')
            links = []
        if kind in ('observation', 'source_claim') and not links:
            errors.append(f'Claim {cid}: observation/source claim requires evidence')
        for link in links:
            if not isinstance(link, dict):
                errors.append(f'Claim {cid}: invalid evidence link')
                continue
            if link.get('evidence_id') not in collections['evidence']:
                errors.append(f'Claim {cid}: unknown evidence')
            if link.get('relation') not in ('supports', 'challenges', 'context') or not link.get('reason'):
                errors.append(f'Claim {cid}: link needs relation and reason')
    for mid, m in collections['mechanisms'].items():
        for field in ('process', 'scope_conditions', 'discriminating_observation'):
            if not m.get(field):
                errors.append(f'Mechanism {mid}: missing {field}')
        refs = m.get('claim_ids', [])
        if not isinstance(refs, list) or any(c not in collections['claims'] for c in refs):
            errors.append(f'Mechanism {mid}: unknown claim reference')
    for pid, p in collections['predictions'].items():
        for field in ('statement', 'target', 'horizon', 'resolution_rule', 'status'):
            if not isinstance(p.get(field), str) or not p[field].strip():
                errors.append(f'Prediction {pid}: missing {field}')
        if not isinstance(p.get('conditions'), list):
            errors.append(f'Prediction {pid}: explicit conditions list required (may be empty)')
        refs = p.get('claim_ids', [])
        if not isinstance(refs, list) or not refs or any(c not in collections['claims'] for c in refs):
            errors.append(f'Prediction {pid}: known claim_ids required')
        if p.get('probability') is not None:
            # v1 is deliberately a traceability tool, not a probability registry.
            errors.append(f'Prediction {pid}: numeric probabilities unsupported in casebook v1')
    return errors, notices


def freeze(case):
    errors, notices = validate(case)
    if errors:
        raise ValueError('\n'.join(errors))
    return {'record_type': 'frozen_research_case', 'schema_version': 1,
            'frozen_at': datetime.now(timezone.utc).isoformat(),
            'case_sha256': digest(case), 'case': case, 'notices': notices,
            'attestation': 'Local capture only; not evidence of pre-outcome registration.'}


def verify(frozen):
    if frozen.get('record_type') != 'frozen_research_case' or digest(frozen['case']) != frozen['case_sha256']:
        raise ValueError('Frozen case digest mismatch or wrong record type')
    errors, notices = validate(frozen['case'])
    if errors:
        raise ValueError('\n'.join(errors))
    return notices


def review(frozen, assessments):
    verify(frozen)
    if not isinstance(assessments, list) or not assessments:
        raise ValueError('Nonempty assessment list required')
    predictions = {p['id']: p for p in frozen['case'].get('predictions', [])}
    seen = set()
    for a in assessments:
        if not isinstance(a, dict):
            raise ValueError('Assessment must be an object')
        pid = a.get('prediction_id')
        if pid not in predictions or pid in seen:
            raise ValueError('Unknown or duplicate prediction_id')
        seen.add(pid)
        # Separate the actual outcome, conditions, and model diagnosis. Conditions
        # changing must never silently delete the original statement or target.
        for field in ('observed_outcome', 'condition_assessment', 'model_diagnosis', 'evidence_locators'):
            if not a.get(field):
                raise ValueError(f'Assessment {pid} missing {field}')
        if a.get('verdict') not in ('supported', 'contradicted', 'unresolved', 'not_yet_due', 'unscorable'):
            raise ValueError('Unknown verdict')
    return {'record_type': 'research_case_review', 'schema_version': 1,
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
            'parent_case_sha256': frozen['case_sha256'],
            'original_predictions': frozen['case'].get('predictions', []),
            'assessments': assessments,
            'unreviewed_prediction_ids': sorted(set(predictions) - seen),
            'evaluation_mode': 'Human-authored assessment; no automated truth adjudication.'}


def write_new(path, value):
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with path.open('x', encoding='utf-8') as f:
        f.write(encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'freeze', 'verify', 'review'):
        p = commands.add_parser(name)
        p.add_argument('input', type=Path)
        if name in ('freeze', 'review'):
            p.add_argument('--output', type=Path, required=True)
        if name == 'review':
            p.add_argument('--assessments', type=Path, required=True)
    args = parser.parse_args()
    try:
        value = json.loads(args.input.read_text(encoding='utf-8'))
        if args.command == 'validate':
            errors, notices = validate(value)
            print(json.dumps({'errors': errors, 'notices': notices}, ensure_ascii=False, indent=2))
            return bool(errors)
        if args.command == 'verify':
            print(json.dumps({'verified': True, 'notices': verify(value)}, ensure_ascii=False, indent=2))
        else:
            result = freeze(value) if args.command == 'freeze' else review(
                value, json.loads(args.assessments.read_text(encoding='utf-8')))
            write_new(args.output, result)
            print(args.output)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
