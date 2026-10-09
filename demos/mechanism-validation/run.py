#!/usr/bin/env python3
"""Paired validator audit of fixed commits, not an LLM reasoning experiment."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
VERSIONS = {'before': '9069f71', 'after': 'b8b7067'}


def load(rev):
    raw = subprocess.check_output(['git','show',rev+':scripts/research_engine.py'],cwd=ROOT)
    module = types.ModuleType('engine_'+rev)
    module.__file__ = str(ROOT/'scripts/research_engine.py')
    exec(compile(raw,module.__file__,'exec'),module.__dict__)
    # Shared catalogues, matcher and evidence handling isolate the validator change.
    return module,hashlib.sha256(raw).hexdigest()


def base():
    request=dict(question='Synthetic audit only',target='synthetic outcome',geography='synthetic region',horizon='one month',goal='check protocol',as_of='2026-10-09T04:00:00Z',mode='event',information_regime='current',topics=['economy'],features={'mechanisms':['bank-run']},conditions={'financial_network':'connected'})
    evidence=dict(id='current-fixture',role='current',observation='Synthetic fixture, not historical evidence',limitations='No real factual support',upstream_id='fixture',source=dict(url='https://example.org/audit-fixture',locator='synthetic fixture',basis='test only',access_method='synthetic_test',access_scope='excerpt',available_at='2026-10-08T00:00:00Z',accessed_at='2026-10-09T03:00:00Z'))
    history=copy.deepcopy(evidence);history.update(id='history-fixture',role='history',catalogue_id='banking-1931')
    modifier=dict(variable='response capacity',source_state='synthetic known state',target_state='synthetic known state',effect_on_mechanism='constrains response',status='preserved',source_evidence_ids=['history-fixture'],target_evidence_ids=['current-fixture'])
    row=dict(id='mechanism-one',analogue_id='banking-1931',target_outcome='synthetic outcome',mechanism='capacity constrains feasible response',invariant_hypothesis='relationship presumed stable',modifiers=[modifier],propagation_vs_response='compare delay, coverage and capacity',phase_switch='reassess when capacity changes',observation_process='reporting may change',falsifier='capacity does not constrain response',conclusion='conditional pathway, test fixture only',decision='transfer')
    a=dict(verdict='conditional',answer='Test only, not advice',claims=[dict(kind='observation',statement='Synthetic fixture',evidence_ids=['current-fixture'])],dominant_factors=[dict(factor='capacity',mechanism='synthetic relation',scope='fixture',timelag='unknown',falsifier='relation absent',evidence_ids=['current-fixture'])],selected_analogues=['banking-1931'],historical_increment='Synthetic comparison only',era_differences=['Synthetic differences'],counterevidence_search='Synthetic receipt, no live search',alternatives='Other mechanisms',conflicts=[],uncertainty='Unknown',unknowns=['Effect size'],actions=[dict(option='research',condition='uncertainty',cost='time',reversibility='high',stop_signal='resolved')],review_signals=[dict(indicator='new evidence',trigger='contradiction',decision_change='revise',check_after='next review')],mechanism_comparisons=[row])
    return request,[evidence,history],a


def cases():
    result=[]
    def add(name,kind,expected,mutate):
        r,ev,a=base();mutate(r,ev,a)
        result.append(dict(id=name,kind=kind,expected=expected,request=r,evidence=ev,analysis=a))
    def mod(a):return a['mechanism_comparisons'][0]['modifiers'][0]
    def row(a):return a['mechanism_comparisons'][0]
    add('valid-preserved','positive_control','accepted',lambda r,e,a:None)
    def unknown(r,e,a):mod(a).update(status='unknown',source_evidence_ids=[],target_evidence_ids=[]);row(a)['decision']='conditional'
    add('valid-unknown-conditional','positive_control','accepted',unknown)
    def changed(r,e,a):mod(a).update(status='changed',reassessment='Remeasure parameters in target environment')
    add('valid-changed-reassessed','positive_control','accepted',changed)
    add('missing-comparison','structural_negative','rejected',lambda r,e,a:a.pop('mechanism_comparisons'))
    add('unknown-unconditional','structural_negative','rejected',lambda r,e,a:mod(a).update(status='unknown',source_evidence_ids=[],target_evidence_ids=[]))
    add('broken-transferred','structural_negative','rejected',lambda r,e,a:mod(a).update(status='broken'))
    add('changed-not-reassessed','structural_negative','rejected',lambda r,e,a:mod(a).update(status='changed'))
    add('missing-target-evidence','structural_negative','rejected',lambda r,e,a:mod(a).update(target_evidence_ids=[]))
    add('unknown-source-reference','structural_negative','rejected',lambda r,e,a:mod(a).update(source_evidence_ids=['not-present']))
    add('empty-modifiers','structural_negative','rejected',lambda r,e,a:row(a).update(modifiers=[]))
    add('missing-response-comparison','structural_negative','rejected',lambda r,e,a:row(a).pop('propagation_vs_response'))
    add('future-current-evidence','existing_guard','rejected',lambda r,e,a:e[0]['source'].update(available_at='2099-01-01T00:00:00Z'))
    def false_claim(r,e,a):
        a['answer']='A single favourable label guarantees every future outcome.'
        row(a)['conclusion']='The historical coefficient is universally exact.'
        mod(a).update(target_state='Zero response capacity',source_state='Unlimited response capacity',status='preserved')
    add('semantic-contradiction-labelled-preserved','semantic_negative','rejected',false_claim)
    def irrelevant(r,e,a):
        e[0]['observation']='This source only reports the colour of a building; it contains no capacity measurement.'
        mod(a)['target_state']='Precisely measured response capacity'
    add('irrelevant-evidence-cited','semantic_negative','rejected',irrelevant)
    def omitted(r,e,a):
        a['answer']='The outcome is certain although the fixture supplies no adoption, coverage or response data.'
        mod(a).update(variable='publication label',source_state='same label',target_state='same label',effect_on_mechanism='not established')
    add('critical-conditions-omitted','semantic_negative','rejected',omitted)
    return result


def run():
    all_cases=cases();engines={};hashes={}
    for label,rev in VERSIONS.items():engines[label],hashes[label]=load(rev)
    rows=[]
    for item in all_cases:
        row=dict(id=item['id'],kind=item['kind'],expected=item['expected'])
        for label,engine in engines.items():
            with tempfile.TemporaryDirectory() as tmp:
                work=Path(tmp)/'work';engine.init(work,item['request'])
                for ev in item['evidence']:engine.add_evidence(work,ev)
                for stage in engine.STAGES:
                    engine.add_search(work,dict(id=stage,stage=stage,query='synthetic',provider='fixture',searched_at='2026-10-09T03:00:00Z',status='searched',result_urls=[],outcome='Synthetic test; no live search'))
                try:engine.validate_analysis(work,item['analysis']);state='accepted';reason=None
                except ValueError as exc:state='rejected';reason=str(exc)
                row[label]=dict(actual=state,meets_expectation=state==item['expected'],reason=reason)
        rows.append(row)
    return dict(type='synthetic_paired_validator_audit',versions=VERSIONS,engine_sha256=hashes,shared_dependencies='Current catalogue, matcher, search plan and mechanism validator; only research_engine.py loaded from fixed Git revisions.',forecast_accuracy_established=False,independent_llm_ab_test_performed=False,results=rows)

if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
