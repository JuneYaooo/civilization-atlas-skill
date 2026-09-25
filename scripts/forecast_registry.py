#!/usr/bin/env python3
"""Freeze binary tasks, forecasts and outcomes; score matched resolved tasks.

Local hashes are integrity checks, not authenticated pre-outcome registration.
This tool neither generates forecasts nor verifies the truth of supplied sources.
All input/output records belong outside the skill directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MODES = {'real_time', 'historical_reconstruction', 'synthetic'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def shape(value, required, optional=()):
    require(isinstance(value, dict), 'Expected an object')
    require(set(required) <= value.keys(), 'Missing fields: ' + ', '.join(sorted(set(required) - value.keys())))
    require(value.keys() <= set(required) | set(optional), 'Unknown fields: ' + ', '.join(sorted(value.keys() - set(required) - set(optional))))


def strings(value, fields):
    for field in fields:
        require(isinstance(value[field], str) and bool(value[field].strip()), field + ' must be nonempty text')


def instant(value):
    require(isinstance(value, str), 'Timestamp must be text')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid ISO timestamp') from exc
    require(date.tzinfo is not None, 'Timestamp requires timezone')
    return date


def now():
    return datetime.now(timezone.utc)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def index(records, key):
    require(isinstance(records, list), 'Records must be a list')
    result = {}
    for record in records:
        require(isinstance(record, dict) and key in record, 'Record missing ' + key)
        strings(record, [key])
        require(record[key] not in result, 'Duplicate ' + key)
        result[record[key]] = record
    return result


def sources(records):
    result = index(records, 'id')
    for source in result.values():
        shape(source, ('id', 'url', 'version', 'available_at', 'sha256'))
        strings(source, ('id', 'url', 'version'))
        instant(source['available_at'])
        require(isinstance(source['sha256'], str) and re.fullmatch('[a-f0-9]{64}', source['sha256']), 'Invalid source sha256')
    return result


def validate_taskset(data):
    shape(data, ('schema_version', 'id', 'information_regime', 'task_family', 'unit_definition',
                 'risk_set_definition', 'aggregation', 'tasks'))
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'Unsupported schema_version')
    strings(data, ('id', 'task_family', 'unit_definition', 'risk_set_definition'))
    require(data['information_regime'] in MODES, 'Unknown information_regime')
    require(data['aggregation'] == 'equal_task', 'Only equal_task aggregation is supported')
    tasks = index(data['tasks'], 'id')
    require(tasks, 'Taskset must not be empty')
    seen = set()
    for task in tasks.values():
        shape(task, ('id', 'unit_id', 'target_definition', 'forecast_due', 'event_start',
                     'event_end', 'resolve_after', 'resolution_rule'))
        strings(task, ('id', 'unit_id', 'target_definition', 'resolution_rule'))
        due, start, end, resolve = [instant(task[k]) for k in ('forecast_due', 'event_start', 'event_end', 'resolve_after')]
        require(due <= start < end <= resolve, 'Require forecast_due <= event_start < event_end <= resolve_after')
        identity = (task['unit_id'], task['target_definition'], start, end)
        require(identity not in seen, 'Duplicate unit/target/window under different task IDs')
        seen.add(identity)
    return tasks


def validate_forecasts(data, taskset):
    shape(data, ('schema_version', 'id', 'taskset_sha256', 'method_id', 'method_version',
                 'method_description', 'information_cutoff', 'issued_at', 'sources', 'forecasts'))
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'Unsupported schema_version')
    strings(data, ('id', 'method_id', 'method_version', 'method_description'))
    require(data['taskset_sha256'] == taskset['sha256'], 'Forecast taskset mismatch')
    cutoff, issued = instant(data['information_cutoff']), instant(data['issued_at'])
    require(cutoff <= issued, 'Information cutoff is after forecast issue time')
    parent = taskset['payload']
    tasks = index(parent['tasks'], 'id')
    require(all(issued <= instant(t['forecast_due']) for t in tasks.values()), 'Forecast issued after task deadline')
    refs = sources(data['sources'])
    if parent['information_regime'] == 'real_time':
        require(instant(taskset['frozen_at']) <= issued, 'Forecast predates task registration')
        require(all(instant(s['available_at']) <= cutoff for s in refs.values()), 'Source available after information cutoff')
    predictions = index(data['forecasts'], 'task_id')
    require(predictions.keys() == tasks.keys(), 'Every registered task requires a forecast or explicit abstention')
    for pred in predictions.values():
        if pred.get('status') == 'forecast':
            shape(pred, ('task_id', 'status', 'probability'))
            p = pred['probability']
            require(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1, 'Probability must be a finite number in [0,1], not bool')
        else:
            shape(pred, ('task_id', 'status', 'reason'))
            require(pred['status'] == 'abstain', 'Unknown forecast status')
            strings(pred, ('reason',))


def validate_outcomes(data, taskset):
    shape(data, ('schema_version', 'id', 'taskset_sha256', 'as_of', 'sources', 'outcomes'))
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'Unsupported schema_version')
    strings(data, ('id',))
    require(data['taskset_sha256'] == taskset['sha256'], 'Outcome taskset mismatch')
    as_of = instant(data['as_of'])
    refs = sources(data['sources'])
    require(all(instant(s['available_at']) <= as_of for s in refs.values()), 'Outcome source is after snapshot as_of')
    tasks = index(taskset['payload']['tasks'], 'id')
    outcomes = index(data['outcomes'], 'task_id')
    require(outcomes.keys() == tasks.keys(), 'Every task requires an explicit outcome status')
    for row in outcomes.values():
        if row.get('status') == 'resolved':
            shape(row, ('task_id', 'status', 'value', 'known_at', 'source_ids', 'locator'))
            require(type(row['value']) is int and row['value'] in (0, 1), 'Resolved outcome must be integer 0 or 1, not bool')
            strings(row, ('locator',))
            known = instant(row['known_at'])
            require(instant(tasks[row['task_id']]['resolve_after']) <= known <= as_of, 'Outcome known_at outside allowed resolution interval')
            ids = row['source_ids']
            require(isinstance(ids, list) and ids and all(isinstance(s, str) for s in ids), 'Resolved outcome needs source IDs')
            require(len(set(ids)) == len(ids) and set(ids) <= refs.keys(), 'Unknown or duplicate outcome source ID')
            require(all(instant(refs[s]['available_at']) <= known for s in ids), 'Outcome predates its supporting source version')
        else:
            shape(row, ('task_id', 'status', 'reason'))
            require(row['status'] in ('unresolved', 'invalid'), 'Unknown outcome status')
            strings(row, ('reason',))


def validate_payload(kind, payload, taskset=None):
    if kind == 'taskset':
        require(taskset is None, 'Taskset cannot have a parent taskset')
        validate_taskset(payload)
    else:
        require(taskset is not None, 'Parent taskset required')
        verify(taskset)
        require(taskset['kind'] == 'taskset', 'Parent must be a frozen taskset')
        if kind == 'forecasts':
            validate_forecasts(payload, taskset)
        elif kind == 'outcomes':
            validate_outcomes(payload, taskset)
        else:
            raise ValueError('Unknown record kind')


def check_capture(kind, payload, captured, taskset):
    require(captured <= now(), 'Local capture is in the future')
    mode = payload['information_regime'] if kind == 'taskset' else taskset['payload']['information_regime']
    if kind == 'forecasts':
        require(instant(payload['issued_at']) <= captured, 'Issue time is after capture')
    if kind == 'outcomes':
        require(instant(payload['as_of']) <= captured, 'Outcome as_of is after capture')
    if mode == 'real_time':
        if kind in ('taskset', 'forecasts'):
            tasks = payload['tasks'] if kind == 'taskset' else taskset['payload']['tasks']
            require(all(captured <= instant(t['forecast_due']) for t in tasks), 'Real-time registration missed a deadline; use historical_reconstruction')
        if taskset:
            require(instant(taskset['frozen_at']) <= captured, 'Capture predates parent registration')


def freeze(kind, payload, taskset=None):
    validate_payload(kind, payload, taskset)
    captured = now()
    check_capture(kind, payload, captured, taskset)
    record = {'record_type': 'frozen_binary_record', 'schema_version': 1,
              'kind': kind, 'frozen_at': captured.isoformat(), 'payload': payload}
    record['sha256'] = digest(record)
    return record


def verify(record, taskset=None):
    shape(record, ('record_type', 'schema_version', 'kind', 'frozen_at', 'payload', 'sha256'))
    require(record['record_type'] == 'frozen_binary_record' and type(record['schema_version']) is int and record['schema_version'] == 1, 'Unknown frozen record format')
    require(record['sha256'] == digest({k: v for k, v in record.items() if k != 'sha256'}), 'Record hash mismatch')
    validate_payload(record['kind'], record['payload'], taskset)
    check_capture(record['kind'], record['payload'], instant(record['frozen_at']), taskset)
    return record


def summary(pairs):
    if not pairs:
        return {'n': 0, 'brier': None, 'mean_probability': None, 'observed_rate': None}
    n = len(pairs)
    return {'n': n, 'brier': math.fsum((p - y) ** 2 for p, y in pairs) / n,
            'mean_probability': math.fsum(p for p, _ in pairs) / n,
            'observed_rate': math.fsum(y for _, y in pairs) / n}


def score(taskset, forecast_records, outcome_record):
    verify(taskset)
    require(taskset['kind'] == 'taskset', 'Expected taskset')
    require(isinstance(forecast_records, list) and 1 <= len(forecast_records) <= 2, 'Score accepts one or two forecast batches')
    verify(outcome_record, taskset)
    require(outcome_record['kind'] == 'outcomes', 'Expected outcomes')
    seen = set()
    for record in forecast_records:
        verify(record, taskset)
        require(record['kind'] == 'forecasts', 'Expected forecasts')
        require(record['payload']['id'] not in seen, 'Duplicate forecast batch ID')
        seen.add(record['payload']['id'])
    if len(forecast_records) == 2:
        cutoffs = [instant(r['payload']['information_cutoff']) for r in forecast_records]
        require(cutoffs[0] == cutoffs[1], 'Paired comparison requires the same information cutoff')
    outcomes = index(outcome_record['payload']['outcomes'], 'task_id')
    eligible = {tid: r['value'] for tid, r in outcomes.items() if r['status'] == 'resolved'}
    results, available = [], []
    for record in forecast_records:
        data = record['payload']
        ps = {r['task_id']: r['probability'] for r in data['forecasts'] if r['status'] == 'forecast'}
        available.append(ps)
        result = {'batch_id': data['id'], 'method_id': data['method_id'], 'method_version': data['method_version'],
                  'record_sha256': record['sha256'], 'forecast_count': len(ps), 'abstain_count': len(outcomes) - len(ps),
                  'resolved_coverage': len(ps.keys() & eligible.keys()) / len(eligible) if eligible else None,
                  'own_resolved_sample': summary([(p, eligible[tid]) for tid, p in ps.items() if tid in eligible])}
        results.append(result)
    report = {'record_type': 'binary_score_report', 'schema_version': 1, 'scored_at': now().isoformat(),
              'taskset_sha256': taskset['sha256'], 'outcomes_sha256': outcome_record['sha256'],
              'information_regime': taskset['payload']['information_regime'],
              'task_family': taskset['payload']['task_family'], 'aggregation': 'equal_task',
              'evaluation_as_of': outcome_record['payload']['as_of'],
              'registered_tasks': len(outcomes), 'resolved_tasks': len(eligible),
              'unresolved_tasks': sum(r['status'] == 'unresolved' for r in outcomes.values()),
              'invalid_tasks': sum(r['status'] == 'invalid' for r in outcomes.values()),
              'methods': results, 'task_scores': [],
              'limitations': ['Descriptive scores only; no independence assumption, uncertainty estimate, or automatic winner.',
                              'Own-sample scores may have different coverage; use paired rows for method comparison.',
                              'Equal task weight may mix horizons or dependent units; task design determines interpretation.',
                              'Mean probability versus observed rate is not a full calibration test.',
                              'Hashes and local dates do not authenticate prospective registration; supplied facts are not verified.']}
    for tid in sorted(outcomes):
        row = {'task_id': tid, 'outcome_status': outcomes[tid]['status'], 'value': eligible.get(tid), 'methods': []}
        for result, ps in zip(results, available):
            p = ps.get(tid)
            row['methods'].append({'batch_id': result['batch_id'], 'probability': p,
                                   'brier': (p - eligible[tid]) ** 2 if tid in eligible and p is not None else None})
        report['task_scores'].append(row)
    if len(available) == 2:
        common = sorted(eligible.keys() & available[0].keys() & available[1].keys())
        a, b = [summary([(ps[tid], eligible[tid]) for tid in common]) for ps in available]
        report['paired'] = {'task_ids': common, 'n': len(common), 'batch_a': results[0]['batch_id'],
                            'batch_b': results[1]['batch_id'], 'a': a, 'b': b,
                            'brier_a_minus_b': a['brier'] - b['brier'] if common else None}
    return report


def external(path):
    path = path.expanduser().resolve()
    require(not path.is_relative_to(ROOT), 'Research records must be outside the skill directory')
    return path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON object key')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Non-finite JSON number: ' + value)


def read(path):
    return json.loads(external(path).read_text(encoding='utf-8'), object_pairs_hook=unique_object,
                      parse_constant=invalid_constant)


def write_new(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    with external(path).open('x', encoding='utf-8') as output:
        output.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for kind in ('taskset', 'forecasts', 'outcomes'):
        p = commands.add_parser(kind, help='Validate and freeze a ' + kind + ' payload')
        p.add_argument('input', type=Path)
        p.add_argument('--output', type=Path, required=True)
        if kind != 'taskset':
            p.add_argument('--taskset', type=Path, required=True)
    p = commands.add_parser('verify', help='Verify a frozen record against its parent')
    p.add_argument('input', type=Path)
    p.add_argument('--taskset', type=Path)
    p = commands.add_parser('score', help='Score one or compare two frozen forecast batches')
    p.add_argument('taskset', type=Path)
    p.add_argument('--forecasts', type=Path, nargs='+', required=True)
    p.add_argument('--outcomes', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        parent = read(args.taskset) if getattr(args, 'taskset', None) else None
        if args.command == 'verify':
            verify(read(args.input), parent)
            print('Verified local integrity and declared constraints; not source truth or trusted registration.')
            return 0
        if args.command == 'score':
            result = score(parent, [read(p) for p in args.forecasts], read(args.outcomes))
        else:
            result = freeze(args.command, read(args.input), parent)
        write_new(args.output, result)
        print(args.output)
        return 0
    except (ValueError, OSError, TypeError, KeyError, OverflowError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
