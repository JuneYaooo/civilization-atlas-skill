"""Validate explicit transfer assumptions, not causal truth or prediction accuracy."""


def check_comparisons(analysis, eligible, catalogue_ids):
    rows = analysis.get('mechanism_comparisons')
    required = analysis['verdict'] == 'conditional' or bool(analysis['selected_analogues'])
    if rows is None and not required:
        return
    if not isinstance(rows, list) or (required and not rows):
        raise ValueError('mechanism_comparisons required for conditional judgments or selected analogues')
    selected = set(analysis['selected_analogues'])
    covered = set()
    ids = set()
    def text(value, label):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(label + ' must be nonempty')
    def refs(values, label, needed=False):
        if not isinstance(values, list) or any(not isinstance(v, str) or v not in eligible for v in values) or (needed and not values):
            raise ValueError(label + ' needs eligible evidence')
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('mechanism comparison must be an object')
        for key in ('id', 'target_outcome', 'mechanism', 'invariant_hypothesis', 'propagation_vs_response', 'phase_switch', 'observation_process', 'falsifier', 'conclusion'):
            text(row.get(key), key)
        if row['id'] in ids:
            raise ValueError('duplicate mechanism comparison id')
        ids.add(row['id'])
        cid = row.get('analogue_id')
        if 'analogue_id' not in row or (cid is not None and (not isinstance(cid, str) or cid not in catalogue_ids)):
            raise ValueError('analogue_id must be a catalogue id or explicit null')
        decision = row.get('decision')
        if decision not in ('transfer', 'conditional', 'reject'):
            raise ValueError('invalid transfer decision')
        if cid is None and decision == 'transfer':
            raise ValueError('cannot certify historical transfer without a historical analogue')
        modifiers = row.get('modifiers')
        if not isinstance(modifiers, list) or not modifiers:
            raise ValueError('identify decision-relevant modifiers')
        for m in modifiers:
            if not isinstance(m, dict):
                raise ValueError('modifier must be an object')
            for key in ('variable', 'source_state', 'target_state', 'effect_on_mechanism'):
                text(m.get(key), key)
            state = m.get('status')
            if state not in ('preserved', 'changed', 'unknown', 'broken'):
                raise ValueError('invalid modifier status')
            known = state != 'unknown'
            refs(m.get('source_evidence_ids'), 'source state', known and cid is not None)
            refs(m.get('target_evidence_ids'), 'target state', known)
            if state == 'unknown' and decision == 'transfer':
                raise ValueError('unknown modifier prevents unconditional transfer')
            if state == 'broken' and decision != 'reject':
                raise ValueError('broken necessary condition requires rejecting this mechanism')
            if state == 'changed':
                text(m.get('reassessment'), 'changed conditions require target reassessment')
        if cid is not None and decision != 'reject':
            if cid not in selected:
                raise ValueError('usable historical mechanism must name a selected analogue')
            covered.add(cid)
    if not selected <= covered:
        raise ValueError('every selected analogue needs a non-rejected mechanism comparison')
    if analysis['verdict'] == 'conditional' and not any(r['decision'] != 'reject' for r in rows):
        raise ValueError('conditional judgment needs a remaining mechanism, or abstain')
