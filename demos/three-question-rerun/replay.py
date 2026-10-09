#!/usr/bin/env python3
"""Recheck source cutoffs, recorded comparisons and published outcome arithmetic."""
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from mechanism_transfer import check_comparisons
spec = importlib.util.spec_from_file_location('previous_audit', HERE.parent / 'mechanism-replay/replay.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)

def run(data):
    result = previous.run(data)
    comparisons = 0
    for case in data['cases']:
        for control in case['analysis']['selected_analogues']:
            if not set(data['study_controls'][control]['source_ids']) <= set(case['inputs']):
                raise ValueError('Historical control lacks eligible input sources')
        check_comparisons(case['analysis'], set(case['inputs']), set(data['study_controls']))
        comparisons += len(case['analysis']['mechanism_comparisons'])
    for source in data['new_review_sources']:
        if source not in data['sources']:
            raise ValueError('Missing review provenance')
        if any(source in case['inputs'] for case in data['cases']):
            raise ValueError('Review source leaked into historical input')
    result['comparison_rows_checked'] = comparisons
    result['comparison_scope'] = 'Study-local manual controls, not built-in matcher execution'
    result['manual_sensitivity_review'] = 'See reports; no independent model behavior experiment'
    result['method_accuracy_improvement'] = None
    return result

def negative_checks(data):
    mutations = []
    leak = copy.deepcopy(data)
    leak['cases'][2]['inputs'].append('he2020')
    mutations.append(('later_disease_evidence_rejected', leak))
    leak = copy.deepcopy(data)
    leak['cases'][3]['inputs'].append('metr2026')
    mutations.append(('later_ai_update_rejected', leak))
    bad = copy.deepcopy(data)
    bad['cases'][0]['analysis']['mechanism_comparisons'][0]['decision'] = 'transfer'
    mutations.append(('unknown_condition_cannot_certify_transfer', bad))
    bad = copy.deepcopy(data)
    bad['cases'][0]['analysis']['mechanism_comparisons'][0]['modifiers'][0]['target_evidence_ids'] = ['not-a-source']
    mutations.append(('missing_evidence_rejected', bad))
    bad = copy.deepcopy(data)
    bad['accuracy_estimate_permitted'] = True
    mutations.append(('retrospective_accuracy_relabel_rejected', bad))
    results = []
    for label, changed in mutations:
        try:
            run(changed)
        except ValueError:
            results.append({'check': label, 'passed': True})
        else:
            raise AssertionError(label)
    return results

if __name__ == '__main__':
    raw = (HERE / 'audit.json').read_bytes()
    data = json.loads(raw)
    result = run(data)
    result['negative_checks'] = negative_checks(data)
    result['input_sha256'] = hashlib.sha256(raw).hexdigest()
    result['report_sha256'] = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ('housing.md', 'covid.md', 'ai.md')}
    print(json.dumps(result, ensure_ascii=False, indent=2))
