"""Verify completed experiment artifacts and separate failure/hold observations."""
import collections,hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save

def main():
    active=read(BASE/'private/active_run.json');summary=read(BASE/'private/summary.json')
    assert summary['complete'],'Evaluate the completed batch first'
    cases=read(BASE/'private/cases.json');assert len(cases)==50 and len({c['id'] for c in cases})==50
    resources=read(Path(active['root'])/'resources.json');files=0;failures=[];holds=[];repairs=[];runs={}
    for arm,run_id in active['runs'].items():
        folder=ROOT/'experiments/runs'/run_id
        post=read(folder/'postflight.json');assert all(post.values())
        for rel,h in read(folder/'artifact_hashes.json').items():
            assert hashlib.sha256((folder/rel).read_bytes()).hexdigest()==h,(arm,rel)
            files+=1
        rows=read(folder/'private/results.json');assert len(rows)==50
        assert {r['id'] for r in rows}=={c['id'] for c in cases}
        counts=collections.Counter();unchanged_reasons=collections.Counter()
        for c in cases:
            r=c['results']['new_'+arm]
            assert r['output']==next(x for x in rows if x['id']==c['id'])['output_text']
            if r['error']:failures.append({'id':c['id'],'arm':arm,'error':r['error']})
            for e in r['edits']:
                if e['issues']:
                    holds.append({'id':c['id'],'arm':arm,'before':e['before'],'after':e['after'],'outcome':e['outcome'],'issues':e['issues'],'cards':e.get('rule_ids',[])})
                    counts.update(i['code'] for i in e['issues'])
                if any(x['kind']=='scoped_surface_tail' for x in e.get('repairs',[])):
                    repairs.append({'id':c['id'],'arm':arm,'before':e['before'],'raw':e['proposed_after'],'after':e['after'],'outcome':e['outcome']})
            if r['output']==c['input']:
                unchanged_reasons['with_held_edit' if any(e['issues'] for e in r['edits']) else 'no_held_edit']+=1
        runs[arm]={'postflight':post,'result_count':len(rows),'issue_occurrences':dict(counts),'unchanged_groups':dict(unchanged_reasons)}
    assert sum(summary['conditions']['new_'+a]['calls'] for a in active['runs'])==resources['physical_api_attempts']
    assert sum(summary['conditions']['new_'+a]['tokens'] for a in active['runs'])==resources['physical_total_tokens']
    assert summary['verified_requests']==98
    assert summary['scope_violations']==0
    v={'artifact_files_verified':files,'runs':runs,'requests_verified':98,'total_result_records':100,'physical_costs_match':True,
       'failures':failures,'scope_repairs':repairs,'hold_observations':holds,
       'interpretation':'Issue counts are observed software decisions, not validated linguistic diagnoses. Naturalness not scored.'}
    save(BASE/'private/verification.json',v)
    print(json.dumps({k:v[k] for k in ('artifact_files_verified','requests_verified','total_result_records','physical_costs_match','runs','failures','scope_repairs')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
