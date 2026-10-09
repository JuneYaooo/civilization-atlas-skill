#!/usr/bin/env python3
"""Replay frozen evidence workflows offline; does not repeat live web retrieval."""
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import research_engine as engine


def main():
    outcomes=[]
    for name in ('event','personal'):
        snapshot=engine.read(Path(__file__).parent/(name+'.json'))
        engine.verify(snapshot)
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)/name
            engine.init(work,snapshot['request'])
            for item in snapshot['searches']:engine.add_search(work,item)
            for item in snapshot['evidence']:engine.add_evidence(work,item)
            if snapshot['schema_version'] == 1 and not snapshot['analysis'].get('mechanism_comparisons'):
                try:
                    engine.validate_analysis(work,snapshot['analysis'])
                except ValueError as exc:
                    if 'mechanism_comparisons' not in str(exc):
                        raise
                else:
                    raise AssertionError('legacy analysis silently accepted as current protocol')
                outcomes.append({'mode':name,'original_hash_verified':True,
                                 'pipeline_replayed':False,'upgrade_required':'mechanism_comparisons',
                                 'live_search_repeated':False})
                continue
            checked=engine.validate_analysis(work,snapshot['analysis'])
            for query in snapshot.get('local_queries',[]):
                engine.write_new(work/'local_queries'/(engine.digest(query)[:16]+'.json'),query)
            result=engine.finalize(work,snapshot['analysis'])
            engine.verify(engine.read(work/'reports'/(result['report']+'.json')))
            # Demonstrate rejection of source-after-cutoff, not just a happy-path report.
            good=next(item for item in snapshot['evidence'] if item['role']=='current') if name=='event' else None
            if good:
                import copy
                changed=copy.deepcopy(good)
                changed['source']['available_at']='2099-01-01T00:00:00Z'
                if engine.eligible(changed,snapshot['request']):raise AssertionError('future source accepted')
            outcomes.append({'mode':name,'original_hash_verified':True,'pipeline_replayed':True,
                             'eligible_evidence_count':len(checked['eligible_evidence']),
                             'live_search_repeated':False})
    print(json.dumps(outcomes,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
