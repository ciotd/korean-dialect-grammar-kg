"""Isolate reference selection on frozen analyses: zero model calls."""
import collections
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,dumps
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline.reference_delivery import select_references
HERE=Path(__file__).resolve().parent

def main():
    summaries=[]
    for run in sorted((ROOT/'experiments/runs').glob('*_integrated_grammar_*')):
        if not (run/'metrics.json').exists() or read(run/'config.json')['phase'] not in ('development','regression'):continue
        reader=IntegratedReader(read(run/'private/graph.json'))
        out=HERE/'private/reference_replay'/run.name;counts=collections.Counter();cases=[]
        for r in read(run/'private/results.json'):
            rd=run/'private/records'/r['id']
            if not (rd/'generation_packet.json').exists():continue
            packet=read(rd/'generation_packet.json');units=read(rd/'bound_analysis.json');traces=read(rd/'retrieval.json')
            refs,omitted=select_references(reader,units,traces,packet['verified_scope_knowledge'])
            counts.update(o['reason'] for o in omitted)
            after={**packet,'related_unprocessed_sources':refs,
                   'delivery_omissions':[o for o in packet['delivery_omissions'] if 'rule_id' in o]+omitted,
                   'reference_delivery_policy':'source_side_and_unit_kind_v1'}
            assert after['verified_scope_knowledge']==packet['verified_scope_knowledge']
            save(out/(r['id']+'.json'),after)
            cases.append({'id':r['id'],'before_count':len(packet['related_unprocessed_sources']),'after_count':len(refs),
                          'before_chars':len(dumps(packet['related_unprocessed_sources'])),'after_chars':len(dumps(refs)),
                          'same_refined_rules':True})
        summaries.append({'run_id':run.name,'cases':cases,'exclusion_counts':dict(counts),
                          'before_reference_count':sum(c['before_count'] for c in cases),
                          'after_reference_count':sum(c['after_count'] for c in cases),
                          'before_chars':sum(c['before_chars'] for c in cases),
                          'after_chars':sum(c['after_chars'] for c in cases),
                          'model_calls':0,'quality_effect':'not_measured'})
    save(HERE/'private/reference_replay_summary.json',summaries)
    print(dumps([{k:v for k,v in s.items() if k!='cases'} for s in summaries]))

if __name__=='__main__':main()
