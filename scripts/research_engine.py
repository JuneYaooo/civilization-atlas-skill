#!/usr/bin/env python3
"""Evidence-led research workspaces. Search and interpretation are performed by the host agent."""
from mechanism_transfer import check_comparisons
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import subprocess
from urllib.parse import urlsplit
from analogue_matcher import DIMENSIONS, features, instant, mapping, nonempty, rank
from search_plan import plan

ROOT = Path(__file__).resolve().parents[1]
STAGES = ('facts', 'mechanisms', 'historical_comparison', 'update_check')


def now():
    return datetime.now(timezone.utc).isoformat()


def occurred(value, label):
    require(instant(value) <= instant(now()), label + ' cannot be in the future; use actual event time or disclose retrospective registration')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        f.write(encode(value))


def require(value, message):
    if not value:
        raise ValueError(message)


def url(value):
    require(nonempty(value), 'URL required')
    u = urlsplit(value)
    require(u.scheme in ('http', 'https') and u.hostname and not u.username and not u.password,
            'URL must be HTTP/S without credentials')


def texts(value, label):
    require(isinstance(value, list) and value and all(nonempty(x) for x in value), label + ' requires nonempty strings')


def catalogue(mode):
    return read(ROOT / 'catalog' / ('crises.json' if mode == 'event' else 'figures.json'))


def check_request(r):
    require(isinstance(r, dict), 'request must be an object')
    for k in ('question', 'target', 'geography', 'horizon', 'goal'):
        require(nonempty(r.get(k)), k + ' required')
    instant(r.get('as_of'))
    require(isinstance(r.get('max_current_age_days', 30), int) and not isinstance(r.get('max_current_age_days', 30), bool) and r.get('max_current_age_days', 30) > 0, 'max_current_age_days must be a positive integer')
    require(r.get('mode') in ('event', 'personal'), 'mode must be event or personal')
    require(r.get('information_regime') in ('current', 'historical_reconstruction'), 'information_regime required')
    require(isinstance(r.get('topics', []), list), 'topics must be a list')
    require(set(r.get('topics', [])) <= {'health', 'economy', 'history', 'personal', 'technology', 'climate'}, 'unknown topic')
    mode = 'event' if r['mode'] == 'event' else 'figure'
    require(any(features(r.get('features'), DIMENSIONS[mode]).values()), 'nonempty structural features required')
    mapping(r.get('conditions'), 'conditions')


def init(work, r):
    check_request(r)
    require(not work.exists(), 'workspace already exists; choose a new path')
    require(not work.resolve().is_relative_to(ROOT), 'research workspace must be outside installed skill')
    work.mkdir(parents=True)
    for folder in ('searches', 'evidence', 'reports', 'reviews', 'local_queries'):
        (work / folder).mkdir()
    write_new(work / 'request.json', r)
    write_new(work / 'search-plan.json', plan(r['question'], r['mode'], r.get('topics', []), r['as_of']))
    return status(work)


def records(work, folder):
    return [read(p) for p in sorted((work / folder).glob('*.json'))]


def add_record(work, folder, value):
    require(isinstance(value, dict), 'record must be an object')
    cid = value.get('id', '')
    require(isinstance(cid, str) and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}', cid), 'invalid record id')
    write_new(work / folder / (cid + '.json'), value)


def add_search(work, item):
    require(item.get('stage') in STAGES, 'unknown search stage')
    for k in ('query', 'provider', 'outcome'):
        require(nonempty(item.get(k)), 'search ' + k + ' required')
    occurred(item.get('searched_at'), 'searched_at')
    require(item.get('status') in ('searched', 'unavailable'), 'search status required')
    require(isinstance(item.get('result_urls'), list), 'result_urls list required')
    for u in item['result_urls']:
        url(u)
    require(item['status'] != 'unavailable' or not item['result_urls'], 'unavailable search cannot claim results')
    add_record(work, 'searches', item)


def check_source(s):
    require(isinstance(s, dict), 'source object required')
    url(s.get('url'))
    for k in ('locator', 'basis', 'access_method'):
        require(nonempty(s.get(k)), 'source ' + k + ' required')
    require(s.get('access_scope') in ('full_text', 'excerpt', 'snippet'), 'invalid access_scope')
    instant(s.get('accessed_at'))
    if s.get('available_at') is not None:
        instant(s['available_at'])
    # A publication date is different from the observation date described in a report.
    if s.get('observation_as_of') is not None:
        instant(s['observation_as_of'])


def add_evidence(work, item):
    for k in ('observation', 'limitations', 'upstream_id'):
        require(nonempty(item.get(k)), 'evidence ' + k + ' required')
    require(item.get('role') in ('current', 'history', 'context'), 'invalid evidence role')
    check_source(item.get('source'))
    occurred(item['source']['accessed_at'], 'accessed_at')
    add_record(work, 'evidence', item)


def eligible(e, request):
    s = e['source']
    if s['access_scope'] == 'snippet':
        return False
    available = s.get('available_at')
    if available and instant(available) > instant(request['as_of']):
        return False
    if request['information_regime'] == 'historical_reconstruction' and not available:
        return False
    # A present-day factual assertion needs a dated original, not an undated page.
    if request['mode'] == 'event' and e['role'] == 'current':
        if not available:
            return False
        observed = s.get('observation_as_of') or available
        age = (instant(request['as_of']) - instant(observed)).total_seconds() / 86400
        if age < 0 or age > request.get('max_current_age_days', 30):
            return False
    return True


def matches(work):
    r = read(work / 'request.json')
    mode = 'event' if r['mode'] == 'event' else 'figure'
    return rank(r, catalogue(mode), mode)


def status(work):
    r = read(work / 'request.json')
    ev = records(work, 'evidence')
    searches = records(work, 'searches')
    done = {s['stage'] for s in searches if s['status'] == 'searched'}
    return {'question': r['question'], 'as_of': r['as_of'],
            'evidence_count': len(ev), 'eligible_evidence_ids': [e['id'] for e in ev if eligible(e, r)],
            'pending_search_stages': [s for s in STAGES if s not in done],
            'reports': len(records(work, 'reports')), 'local_queries': len(records(work, 'local_queries')),
            'execution': 'Host search receipts and reading annotations; no automatic semantic fact verification.'}


def import_analogue(work, cid):
    r = read(work / 'request.json')
    candidates = catalogue('event' if r['mode'] == 'event' else 'figure')
    selected = next((c for c in candidates if c['id'] == cid), None)
    require(selected is not None, 'unknown catalogue id')
    for i, s in enumerate(selected['sources']):
        add_evidence(work, {'id': cid + '-source-' + str(i), 'role': 'history', 'source': s,
                           'observation': s['basis'], 'limitations': '；'.join(selected['transfer_limits']),
                           'upstream_id': s['url'], 'catalogue_id': cid})


def check_research_extensions(a, good):
    """Check authored coverage/transition records, never their semantic truth."""
    specs = {
        'source_coverage': ('question', 'actor_position', 'channel', 'upstream_assessment', 'gap_and_decision_effect'),
        'turning_points': ('target', 'horizon', 'old_state', 'maintenance_conditions', 'candidate_change',
                          'causal_role', 'transition_criterion', 'conditions', 'timeline',
                          'behavior_and_feedback', 'counterfactual', 'nontransition_comparison',
                          'observation_process', 'falsifier', 'decision_effect'),
    }
    for field, keys in specs.items():
        if field not in a:
            continue
        rows = a[field]
        require(isinstance(rows, list) and rows, field + ' must be a nonempty list when supplied')
        seen = set()
        for row in rows:
            require(isinstance(row, dict), field + ' row must be an object')
            require(nonempty(row.get('id')) and row['id'] not in seen, field + ' unique id required')
            seen.add(row['id'])
            for key in keys:
                require(nonempty(row.get(key)), field + ' ' + key + ' required')
            refs = row.get('evidence_ids')
            require(isinstance(refs, list) and all(isinstance(x, str) and x in good for x in refs), field + ' eligible evidence required')
            if field == 'source_coverage':
                require(row.get('status') in ('read', 'located_only', 'unavailable', 'not_searched', 'not_applicable'), 'invalid coverage status')
                if row['status'] == 'read':
                    require(refs, 'read coverage needs eligible evidence')
            else:
                require(row.get('status') in ('unresolved', 'candidate', 'observed_transition', 'reversal'), 'invalid turning point status')
                require(row.get('claim_kind') in ('hypothesis', 'observation'), 'invalid turning point claim kind')
                if row['status'] in ('observed_transition', 'reversal'):
                    require(row['claim_kind'] == 'observation' and refs, 'observed transition needs observational evidence')
                if row['claim_kind'] == 'observation':
                    require(refs, 'observations need evidence')
                require('probability' not in row, 'register numeric forecasts separately')


def validate_analysis(work, a):
    r = read(work / 'request.json')
    ev = {e['id']: e for e in records(work, 'evidence')}
    good = {k for k, e in ev.items() if eligible(e, r)}
    require(isinstance(a, dict), 'analysis must be an object')
    require(a.get('verdict') in ('conditional', 'insufficient_evidence'), 'verdict must be conditional or insufficient_evidence')
    for k in ('answer', 'historical_increment', 'counterevidence_search', 'alternatives', 'uncertainty'):
        require(nonempty(a.get(k)), k + ' required')
    if 'yijing_translation' in a:
        require(nonempty(a['yijing_translation']), 'yijing_translation must be nonempty when supplied; omit when unused')
    texts(a.get('era_differences'), 'era_differences')
    texts(a.get('unknowns'), 'unknowns')
    require(isinstance(a.get('conflicts'), list), 'conflicts list required, empty if none found')
    for c in a['conflicts']:
        for k in ('issue', 'handling'):
            require(nonempty(c.get(k)), 'conflict ' + k + ' required')
        require(isinstance(c.get('evidence_ids'), list) and len(c['evidence_ids']) >= 2 and set(c['evidence_ids']) <= set(ev), 'conflict needs source records')
    require(isinstance(a.get('claims'), list), 'claims list required')
    for c in a['claims']:
        require(c.get('kind') in ('observation', 'source_interpretation', 'hypothesis', 'decision_value'), 'invalid claim kind')
        require(nonempty(c.get('statement')), 'claim statement required')
        require(isinstance(c.get('evidence_ids'), list) and set(c['evidence_ids']) <= good, 'claim references absent or ineligible evidence')
        if c['kind'] in ('observation', 'source_interpretation'):
            require(c['evidence_ids'], 'factual claims require evidence')
    require(isinstance(a.get('dominant_factors'), list), 'dominant_factors list required')
    for f in a['dominant_factors']:
        for k in ('factor', 'mechanism', 'scope', 'falsifier', 'timelag'):
            require(nonempty(f.get(k)), 'factor ' + k + ' required')
        require(isinstance(f.get('evidence_ids'), list) and set(f['evidence_ids']) <= good, 'invalid factor evidence')
    require(isinstance(a.get('actions'), list), 'actions list required')
    for action in a['actions']:
        for k in ('option', 'condition', 'cost', 'reversibility', 'stop_signal'):
            require(nonempty(action.get(k)), 'action ' + k + ' required')
    require(isinstance(a.get('review_signals'), list) and a['review_signals'], 'review signals required')
    for signal in a['review_signals']:
        for k in ('indicator', 'trigger', 'decision_change', 'check_after'):
            require(nonempty(signal.get(k)), 'review ' + k + ' required')
    selected = a.get('selected_analogues')
    require(isinstance(selected, list), 'selected_analogues list required')
    accepted = {c['id']: c for c in matches(work)['candidates']}
    for cid in selected:
        require(cid in accepted, 'selected analogue excluded or unknown: ' + str(cid))
        require(any(e.get('catalogue_id') == cid and k in good for k, e in ev.items()), 'import selected analogue evidence first')
    if not selected:
        require(nonempty(a.get('no_analogue_reason')), 'no_analogue_reason required')
    if a['verdict'] == 'conditional':
        require(not status(work)['pending_search_stages'], 'complete all four searches or use insufficient_evidence')
        require(a['claims'] and a['dominant_factors'] and a['actions'], 'conditional analysis requires claims, factors and options')
        if r['mode'] == 'event':
            used = {eid for c in a['claims'] for eid in c['evidence_ids']}
            require(any(ev[k]['role'] == 'current' for k in good & used), 'recent event needs cited eligible current evidence')
    check_comparisons(a, good, {c['id'] for c in catalogue(r['mode'])})
    check_research_extensions(a, good)
    require('probability' not in a, 'register calibrated numeric forecasts separately')
    return {'eligible_evidence': sorted(good), 'selected': selected,
            'limits': 'Structural validation does not verify source truth, causal identification or forecast skill.'}


def render(snapshot):
    r, a = snapshot['request'], snapshot['analysis']
    out = ['# ' + r['question'], '', '信息截止：' + r['as_of'], '', a['answer'], '',
           '判断状态：' + a['verdict'], '', '## 依据']
    for c in a['claims']:
        out += ['', '- [' + c['kind'] + '] ' + c['statement'] + '（' + ', '.join(c['evidence_ids']) + '）']
    out += ['', '## 主导因素与条件']
    for f in a['dominant_factors']:
        out += ['', '- ' + f['factor'] + '：' + f['mechanism'] + '。范围：' + f['scope'] + '；时滞：' + f['timelag'] + '；反证：' + f['falsifier']]
    for heading, body in [('历史增加的认识', a['historical_increment']), ('时代差异', '\n'.join('- ' + x for x in a['era_differences'])), ('反证与替代解释', a['counterevidence_search'] + '\n\n' + a['alternatives']), ('不确定性', a['uncertainty'] + '\n\n' + '\n'.join('- ' + x for x in a['unknowns']))]:
        out += ['', '## ' + heading, '', body]
    for m in a.get('mechanism_comparisons', []):
        out += ['', '## 机制与条件迁移：' + m['id'], '',
                '目标：' + m['target_outcome'] + '；历史参照：' + str(m['analogue_id']) + '；判断：' + m['decision'],
                '', m['mechanism'], '', '稳定关系假设：' + m['invariant_hypothesis']]
        for x in m['modifiers']:
            out += ['', '- ' + x['variable'] + ' [' + x['status'] + ']：历史 ' + x['source_state'] + '；目标 ' + x['target_state'] + '；影响 ' + x['effect_on_mechanism'] + '；依据 ' + ', '.join(x['source_evidence_ids'] + x['target_evidence_ids'])]
            if x.get('reassessment'):
                out += ['  重新判断：' + x['reassessment']]
        out += ['', '传播与响应：' + m['propagation_vs_response'], '', '阶段切换：' + m['phase_switch'],
                '', '观察过程：' + m['observation_process'], '', '反证：' + m['falsifier'], '', m['conclusion']]
    for field, heading in (('source_coverage', '来源覆盖'), ('turning_points', '候选转折')):
        for row in a.get(field, []):
            out += ['', '## ' + heading + '：' + row['id']]
            for key, value in row.items():
                if key != 'id':
                    out += ['', '- ' + key + '：' + (', '.join(value) if isinstance(value, list) else str(value))]
    if a.get('yijing_translation'):
        out += ['', '## 周易与人性社会', '', a['yijing_translation']]
    out += ['', '## 可行选项']
    for x in a['actions']:
        out += ['', '- ' + x['option'] + '；条件：' + x['condition'] + '；成本：' + x['cost'] + '；可逆性：' + x['reversibility'] + '；停止信号：' + x['stop_signal']]
    out += ['', '## 修订信号']
    for x in a['review_signals']:
        out += ['', '- ' + x['indicator'] + '；触发：' + x['trigger'] + '；调整：' + x['decision_change'] + '；检查时点：' + x['check_after']]
    out += ['', '## 来源与冲突']
    for e in snapshot['evidence']:
        s = e['source']
        out += ['', '- ' + e['id'] + ' — [' + s['locator'] + '](' + s['url'] + ')；阅读范围：' + s['access_scope'] + '；限制：' + e['limitations']]
    for c in a['conflicts']:
        out += ['', '- 冲突：' + c['issue'] + '；处理：' + c['handling']]
    return '\n'.join(out) + '\n'


def finalize(work, analysis):
    validation = validate_analysis(work, analysis)
    snapshot = {'schema_version': 3 if any(k in analysis for k in ('source_coverage', 'turning_points')) else 2, 'created_at': now(), 'request': read(work / 'request.json'),
                'analysis': analysis, 'validation': validation, 'matching': matches(work),
                'searches': records(work, 'searches'), 'evidence': records(work, 'evidence'),
                'local_queries': records(work, 'local_queries')}
    snapshot['content_sha256'] = digest(snapshot)
    name = snapshot['content_sha256'][:16]
    write_new(work / 'reports' / (name + '.json'), snapshot)
    with (work / 'reports' / (name + '.md')).open('x', encoding='utf-8') as f:
        f.write(render(snapshot))
    return {'report': name, 'sha256': snapshot['content_sha256'], 'verdict': analysis['verdict']}


def verify(snapshot):
    body = dict(snapshot)
    claimed = body.pop('content_sha256', None)
    require(claimed == digest(body), 'report hash mismatch')
    return {'verified': True, 'sha256': claimed}


def review(work, item):
    require(nonempty(item.get('report')), 'report required')
    require(re.fullmatch(r'[a-f0-9]{16}', item['report']), 'invalid report id')
    verify(read(work / 'reports' / (item['report'] + '.json')))
    for k in ('observed_change', 'decision_revision', 'remaining_unknowns'):
        require(nonempty(item.get(k)), k + ' required')
    occurred(item.get('reviewed_at'), 'reviewed_at')
    require(isinstance(item.get('evidence_ids'), list) and item['evidence_ids'], 'review evidence required')
    ev = {e['id']: e for e in records(work, 'evidence')}
    require(set(item['evidence_ids']) <= set(ev), 'review evidence missing')
    item = dict(item, evidence_snapshot=[ev[k] for k in item['evidence_ids']])
    item['content_sha256'] = digest(item)
    add_record(work, 'reviews', item)
    return {'review_recorded': item['id']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('init', 'status', 'plan', 'search', 'evidence', 'match', 'import-analogue', 'finalize', 'review', 'verify', 'tags', 'kb-search'))
    p.add_argument('--work', type=Path)
    p.add_argument('--input', type=Path)
    p.add_argument('--id')
    p.add_argument('--query')
    a = p.parse_args()
    try:
        if a.command == 'tags':
            out = {m: {d: sorted({t for c in catalogue(m) for t in c['features'].get(d, [])}) for d in DIMENSIONS[m]} for m in DIMENSIONS}
        elif a.command == 'verify':
            require(a.input, '--input required'); out = verify(read(a.input))
        else:
            require(a.work, '--work required')
            if a.command in ('init', 'search', 'evidence', 'finalize', 'review'):
                require(a.input, '--input required')
                item = read(a.input)
            if a.command == 'init': out = init(a.work, item)
            else:
                check_request(read(a.work / 'request.json'))
                if a.command == 'kb-search':
                    require(nonempty(a.query), '--query required')
                    result = subprocess.run([sys.executable, str(ROOT / 'knowledge-base/scripts/query.py'), 'search', '--q', a.query, '--limit', '10'], capture_output=True, text=True, check=True, timeout=60)
                    out = {'query': a.query, 'queried_at': now(), 'result': json.loads(result.stdout)}
                    write_new(a.work / 'local_queries' / (digest(out)[:16] + '.json'), out)
                elif a.command == 'status': out = status(a.work)
                elif a.command == 'plan': out = read(a.work / 'search-plan.json')
                elif a.command == 'match': out = matches(a.work)
                elif a.command == 'search': add_search(a.work, item); out = status(a.work)
                elif a.command == 'evidence': add_evidence(a.work, item); out = status(a.work)
                elif a.command == 'import-analogue': import_analogue(a.work, a.id); out = status(a.work)
                elif a.command == 'finalize': out = finalize(a.work, item)
                elif a.command == 'review': out = review(a.work, item)
        print(encode(out), end='')
    except (ValueError, TypeError, OSError, KeyError, subprocess.SubprocessError) as exc:
        p.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
