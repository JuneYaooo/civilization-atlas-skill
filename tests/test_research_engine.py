"""Research workflow tests: evidence gates, abstention, immutable reports and distribution data."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import research_engine as e
from analogue_matcher import rank


def request():
    return dict(question='Synthetic research task', target='defined outcome', geography='synthetic region',
                horizon='one month', goal='avoid irreversible loss', as_of='2026-10-09T02:00:00Z',
                mode='event', information_regime='current', topics=['health'],
                features={'mechanisms':['capacity-feedback']}, conditions={'transmission_route':'contact'})


def evidence():
    return dict(id='synthetic-source', role='current', observation='Synthetic fact, not a real event',
                limitations='Test fixture only', upstream_id='synthetic',
                source=dict(url='https://example.org/fixture',locator='fixture',basis='synthetic',
                            access_method='synthetic_test',access_scope='excerpt',
                            available_at='2026-10-08T00:00:00Z',accessed_at='2026-10-09T01:00:00Z'))


def comparison():
    return dict(id='synthetic-mechanism', analogue_id=None, target_outcome='defined outcome',
                mechanism='capacity changes feasible action', invariant_hypothesis='not established historically',
                modifiers=[dict(variable='available capacity',source_state='No historical source selected',
                target_state='Unknown',effect_on_mechanism='May limit response',status='unknown',
                source_evidence_ids=[],target_evidence_ids=[])],
                propagation_vs_response='Response delay and coverage unknown',phase_switch='Reassess on capacity change',
                observation_process='Distinguish reporting from state change',falsifier='Capacity does not constrain action',
                decision='conditional',conclusion='Collect target evidence before acting')


def analysis():
    return dict(mechanism_comparisons=[comparison()],verdict='conditional', answer='Synthetic conditional answer',
                claims=[dict(kind='observation',statement='Test only',evidence_ids=['synthetic-source'])],
                dominant_factors=[dict(factor='capacity',mechanism='test link',scope='test',timelag='unknown',falsifier='test fails',evidence_ids=['synthetic-source'])],
                selected_analogues=[], no_analogue_reason='Not established',historical_increment='None established',
                era_differences=['Institutions differ'],counterevidence_search='Synthetic search',alternatives='Alternative hypothesis',
                conflicts=[],uncertainty='Not quantified',unknowns=['Effect size'],yijing_translation='Not applicable to test',
                actions=[dict(option='gather evidence',condition='uncertainty',cost='time',reversibility='high',stop_signal='enough evidence')],
                review_signals=[dict(indicator='new evidence',trigger='contradiction',decision_change='revise',check_after='next research session')])


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.work=Path(self.tmp.name)/'work'
        e.init(self.work, request())
    def tearDown(self): self.tmp.cleanup()
    def complete(self):
        e.add_evidence(self.work,evidence())
        for stage in e.STAGES:
            e.add_search(self.work,dict(id=stage,stage=stage,query='synthetic',provider='fixture',searched_at='2026-10-09T01:00:00Z',status='searched',result_urls=[],outcome='No results; synthetic test'))
    def test_plan_is_not_execution(self):
        self.assertEqual(len(e.status(self.work)['pending_search_stages']),4)
        with self.assertRaises(ValueError):e.finalize(self.work,analysis())
    def test_incomplete_research_can_abstain(self):
        a=analysis();a.update(verdict='insufficient_evidence',claims=[],dominant_factors=[],actions=[])
        out=e.finalize(self.work,a)
        self.assertEqual(out['verdict'],'insufficient_evidence')
    def test_complete_freeze_and_tamper_detection(self):
        self.complete();out=e.finalize(self.work,analysis())
        frozen=e.read(self.work/'reports'/(out['report']+'.json'))
        self.assertTrue(e.verify(frozen)['verified'])
        frozen['analysis']['answer']='modified'
        with self.assertRaises(ValueError):e.verify(frozen)
    def test_yijing_optional_and_only_rendered_when_supplied(self):
        self.complete();a=analysis();a.pop('yijing_translation')
        out=e.finalize(self.work,a)
        report=e.read(self.work/'reports'/(out['report']+'.json'))
        self.assertNotIn('周易',e.render(report))
        a['yijing_translation']='Interpret incentives and trust under different social positions.'
        out=e.finalize(self.work,a)
        report=e.read(self.work/'reports'/(out['report']+'.json'))
        self.assertIn(a['yijing_translation'],e.render(report))
        for invalid in ('', None, {}):
            a['yijing_translation']=invalid
            with self.assertRaises(ValueError):e.finalize(self.work,a)

    def test_ineligible_current_sources(self):
        for change in ({'access_scope':'snippet'},{'available_at':None},{'available_at':'2026-10-10T00:00:00Z'},{'available_at':'2020-01-01T00:00:00Z'}):
            item=evidence();item['source'].update(change)
            self.assertFalse(e.eligible(item,request()))
    def test_historical_unknown_vintage_excluded(self):
        r=request();r['information_regime']='historical_reconstruction'
        item=evidence();item['role']='history';item['source']['available_at']=None
        self.assertFalse(e.eligible(item,r))
    def test_missing_citation_rejected(self):
        self.complete();a=analysis();a['claims'][0]['evidence_ids']=['missing']
        with self.assertRaises(ValueError):e.finalize(self.work,a)
    def test_unavailable_search_not_completed(self):
        self.complete()
        (self.work/'searches/facts.json').unlink()
        e.add_search(self.work,dict(id='unavailable',stage='facts',query='test',provider='none',searched_at='2026-10-09T01:00:00Z',status='unavailable',result_urls=[],outcome='No tool'))
        with self.assertRaises(ValueError):e.finalize(self.work,analysis())
    def test_records_never_overwrite(self):
        e.add_evidence(self.work,evidence())
        with self.assertRaises(FileExistsError):e.add_evidence(self.work,evidence())
        bad=evidence();bad['id']='../escape'
        with self.assertRaises(ValueError):e.add_evidence(self.work,bad)
    def test_condition_conflict_blocks_selected_analogue(self):
        self.complete();a=analysis();a['selected_analogues']=['covid-2020']
        with self.assertRaises(ValueError):e.finalize(self.work,a)
    def test_review_preserves_original(self):
        self.complete();out=e.finalize(self.work,analysis());p=self.work/'reports'/(out['report']+'.json');before=p.read_bytes()
        e.review(self.work,dict(id='review-one',report=out['report'],reviewed_at='2026-10-10T00:00:00Z',observed_change='Test update',decision_revision='Test revision',remaining_unknowns='Unknown',evidence_ids=['synthetic-source']))
        self.assertEqual(before,p.read_bytes())
    def test_catalogues_are_sourced_and_rankable(self):
        for mode,count in [('event',8),('figure',16)]:
            cat=e.catalogue(mode);self.assertEqual(len(cat),count)
            for c in cat:
                for s in c['sources']:e.check_source(s)
                self.assertTrue(c['transfer_limits']);self.assertTrue(c['open_questions'])
                r=request();r['features']=c['features'];r['conditions']=c['required_conditions']
                self.assertEqual(rank(r,[c],mode)['candidates'][0]['id'],c['id'])
    def test_installed_default_matcher(self):
        q=self.work/'request.json'
        result=subprocess.run([sys.executable,str(ROOT/'scripts/event_matcher.py'),'--request',str(q)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['candidates'])
    def test_missing_comparison_blocked(self):
        self.complete();a=analysis();a.pop('mechanism_comparisons')
        with self.assertRaises(ValueError):e.finalize(self.work,a)
    def test_unknown_cannot_be_upgraded_to_transfer(self):
        from mechanism_transfer import check_comparisons
        a=analysis();a['selected_analogues']=['fixture']
        c=a['mechanism_comparisons'][0];c.update(analogue_id='fixture',decision='transfer')
        with self.assertRaises(ValueError):check_comparisons(a,{'synthetic-source'},{'fixture'})
    def test_broken_condition_requires_reject(self):
        self.complete();a=analysis();m=a['mechanism_comparisons'][0]['modifiers'][0]
        m.update(status='broken',target_evidence_ids=['synthetic-source'])
        with self.assertRaises(ValueError):e.finalize(self.work,a)
    def test_changed_requires_reassessment_and_target_evidence(self):
        self.complete();a=analysis();m=a['mechanism_comparisons'][0]['modifiers'][0]
        m.update(status='changed',target_evidence_ids=['synthetic-source'])
        with self.assertRaises(ValueError):e.finalize(self.work,a)
        m['reassessment']='Target parameter must be remeasured'
        out=e.finalize(self.work,a)
        snap=e.read(self.work/'reports'/(out['report']+'.json'))
        self.assertEqual(snap['schema_version'],2)
        self.assertIn(m['reassessment'],e.render(snap))
        m['target_evidence_ids']=['absent']
        with self.assertRaises(ValueError):e.finalize(self.work,a)
    def test_selected_analogue_needs_own_comparison(self):
        from mechanism_transfer import check_comparisons
        a=analysis();a['selected_analogues']=['fixture']
        with self.assertRaises(ValueError):check_comparisons(a,{'synthetic-source'},{'fixture'})
    def test_rejected_path_can_coexist_with_current_hypothesis(self):
        from mechanism_transfer import check_comparisons
        a=analysis();row=copy.deepcopy(a['mechanism_comparisons'][0])
        row.update(id='rejected',analogue_id='fixture',decision='reject')
        row['modifiers'][0].update(status='broken',source_evidence_ids=['synthetic-source'],target_evidence_ids=['synthetic-source'])
        a['mechanism_comparisons'].append(row)
        check_comparisons(a,{'synthetic-source'},{'fixture'})

    def test_source_credentials_and_unverified_conflicts_rejected(self):
        item=evidence();item['source']['url']='file:///tmp/fixture'
        with self.assertRaises(ValueError):e.add_evidence(self.work,item)
        self.complete();a=analysis();a['conflicts']=[dict(issue='test',handling='pending',evidence_ids=['missing','synthetic-source'])]
        with self.assertRaises(ValueError):e.finalize(self.work,a)

if __name__=='__main__':unittest.main()
