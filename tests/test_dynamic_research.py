"""Synthetic contract tests; fixtures are not historical or decision evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analogue_matcher import rank
from search_plan import plan


def request():
    return {'as_of': '2026-10-09T12:00:00+08:00',
            'features': {'mechanisms': ['supply-shock'], 'constraints': ['limited-buffer']},
            'conditions': {'network': 'connected'}}


def candidate():
    return {'id': 'synthetic-a', 'title': 'Synthetic structure',
            'features': {'mechanisms': ['supply-shock'], 'constraints': ['limited-buffer']},
            'required_conditions': {'network': 'connected'},
            'transfer_limits': ['Institutional comparability has not been established'],
            'sources': [{'url': 'https://example.org/fixture', 'locator': 'fixture section',
                         'basis': 'Synthetic test annotation, not a historical assertion',
                         'access_scope': 'excerpt', 'available_at': '2026-10-01T00:00:00Z',
                         'accessed_at': '2026-10-09T02:00:00Z'}]}


class ResearchTests(unittest.TestCase):
    def test_structural_match_is_explained(self):
        r = rank(request(), [candidate()], 'event')['candidates'][0]
        self.assertEqual(r['rank_score'], 1)
        self.assertEqual(r['matches']['mechanisms'], ['supply-shock'])
        self.assertNotIn('probability', r)

    def test_different_structure_abstains(self):
        c = candidate(); c['features'] = {'mechanisms': ['different']}
        self.assertEqual(rank(request(), [c], 'event')['status'], 'no_analogue')

    def test_necessary_condition_conflict_excludes(self):
        c = candidate(); c['required_conditions']['network'] = 'isolated'
        r = rank(request(), [c], 'event')
        self.assertFalse(r['candidates'])
        self.assertIn('condition_conflict:network', r['excluded'][0]['reasons'])

    def test_unknown_condition_is_not_a_match(self):
        q = request(); q['conditions'] = {}
        r = rank(q, [candidate()], 'event')['candidates'][0]
        self.assertEqual(r['status'], 'provisional')
        self.assertEqual(r['unknown_conditions'], ['network'])

    def test_future_source_cannot_enter_ranking(self):
        c = candidate(); c['sources'][0]['available_at'] = '2026-10-10T00:00:00Z'
        r = rank(request(), [c], 'event')
        self.assertIn('source_after_cutoff', r['excluded'][0]['reasons'])

    def test_unknown_availability_is_provisional(self):
        c = candidate(); c['sources'][0]['available_at'] = None
        self.assertEqual(rank(request(), [c], 'event')['candidates'][0]['status'], 'provisional')

    def test_snippet_is_not_read_evidence(self):
        c = candidate(); c['sources'][0]['access_scope'] = 'snippet'
        self.assertEqual(rank(request(), [c], 'event')['status'], 'no_analogue')

    def test_outcome_and_fame_do_not_change_score(self):
        c = candidate(); a = rank(request(), [c], 'event')['candidates'][0]['rank_score']
        c.update(outcome='success', fame=999999)
        self.assertEqual(rank(request(), [c], 'event')['candidates'][0]['rank_score'], a)

    def test_empty_and_duplicate_input_rejected(self):
        q = request(); q['features'] = {}
        with self.assertRaises(ValueError): rank(q, [], 'event')
        with self.assertRaises(ValueError): rank(request(), [candidate(), candidate()], 'event')

    def test_personal_decision_episode(self):
        q = request(); q['features'] = {'decision_types': ['exit'], 'reversibility': ['partial']}
        c = candidate(); c['features'] = copy.deepcopy(q['features'])
        self.assertEqual(rank(q, [c], 'figure')['candidates'][0]['rank_score'], 1)
        with self.assertRaises(ValueError): rank(q, [c], 'event')

    def test_search_plan_does_not_claim_execution(self):
        p = plan('公开研究主题', 'event', ['health'], request()['as_of'])
        self.assertEqual(p['execution_status'], 'plan_only_not_searched')
        self.assertEqual(len(p['stages']), 4)
        self.assertTrue(any(s['id'] == 'who-don' for s in p['source_routes']))
        with self.assertRaises(ValueError): plan('x', 'event', [], '2026-10-09')

    def test_event_cli_runs_and_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            q, c = Path(tmp)/'q.json', Path(tmp)/'c.json'
            q.write_text(json.dumps(request())); c.write_text(json.dumps([candidate()]))
            command = [sys.executable, str(ROOT/'scripts/event_matcher.py'), '--request', str(q), '--candidates', str(c)]
            r = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)['status'], 'candidates_found')
            c.write_text('{}')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == '__main__': unittest.main()
