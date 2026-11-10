"""Isolate reference selection on frozen analyses: zero model calls."""
import collections
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,dumps,load_jsonl
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline.reference_delivery import select_references
HERE=Path(__file__).resolve().parent
RUN_IDS=['20261106T051728566435Z_integrated_grammar_development',
         '20261106T052943610843Z_integrated_grammar_regression']

def replay_inventory(run):
    rows=load_jsonl(run/'private/inputs.jsonl')
    results={r['id']:r for r in read(run/'private/results.json')}
    for row in rows:
        rid=row['id'];result=results.get(rid)
        packet=run/'private/records'/rid/'generation_packet.json'
        yield {'id':rid,'source_result_status':result.get('status') if result else None,
               'replay_status':'missing_result' if result is None else 'missing_packet' if not packet.exists() else 'replayed'}

def main():
    summaries=[]
    for run_id in RUN_IDS:
        run=ROOT/'experiments/runs'/run_id
        if not (run/'metrics.json').exists():
            summaries.append({'run_id':run_id,'status':'pending','cases':[]});continue
        reader=IntegratedReader(read(run/'private/graph.json'))
        out=HERE/'private/reference_replay'/run.name;counts=collections.Counter();cases=[]
        for r in replay_inventory(run):
            rd=run/'private/records'/r['id']
            if r['replay_status']!='replayed':cases.append(r);continue
            packet=read(rd/'generation_packet.json');units=read(rd/'bound_analysis.json');traces=read(rd/'retrieval.json')
            refs,omitted=select_references(reader,units,traces,packet['verified_scope_knowledge'])
            counts.update(o['reason'] for o in omitted)
            after={**packet,'related_unprocessed_sources':refs,
                   'delivery_omissions':[o for o in packet['delivery_omissions'] if 'rule_id' in o]+omitted,
                   'reference_delivery_policy':'source_side_and_unit_kind_v1'}
            assert after['verified_scope_knowledge']==packet['verified_scope_knowledge']
            save(out/(r['id']+'.json'),after)
            cases.append({**r,'before_count':len(packet['related_unprocessed_sources']),'after_count':len(refs),
                          'before_chars':len(dumps(packet['related_unprocessed_sources'])),'after_chars':len(dumps(refs)),
                          'same_refined_rules':True})
        summaries.append({'run_id':run.name,'status':'completed','cases':cases,'exclusion_counts':dict(counts),
                          'planned_inputs':len(cases),'replayed_inputs':sum(c['replay_status']=='replayed' for c in cases),
                          'skipped_inputs':[c for c in cases if c['replay_status']!='replayed'],
                          'before_reference_count':sum(c.get('before_count',0) for c in cases),
                          'after_reference_count':sum(c.get('after_count',0) for c in cases),
                          'before_chars':sum(c.get('before_chars',0) for c in cases),
                          'after_chars':sum(c.get('after_chars',0) for c in cases),
                          'model_calls':0,'quality_effect':'not_measured'})
    save(HERE/'private/reference_replay_summary.json',summaries)
    print(dumps([{k:v for k,v in s.items() if k!='cases'} for s in summaries]))

if __name__=='__main__':main()
