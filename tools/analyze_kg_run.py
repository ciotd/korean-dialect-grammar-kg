"""Post-run diagnostics. Does not change prompts, pipeline code, or recorded outputs."""
from pathlib import Path
import argparse,collections,statistics,json,hashlib

def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run
    def read(p):return json.loads(p.read_text(encoding='utf-8'))
    def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    results=read(run/'private/results.json');config=read(run/'config.json')
    out=run.parent.parent/'analyses'/(run.name+'_diagnostics');out.mkdir(parents=True,exist_ok=False)
    issues=[];rejections=collections.Counter();used_claims=collections.Counter();refs_claims=collections.Counter();docs=collections.Counter()
    stages=collections.defaultdict(list);total_units=0;mapped_units=0;distinct_concepts=set();uncertainty_inputs=[]
    for r in results:
        base=run/'private/records'/r['id']
        for stage,seconds in r['stage_seconds'].items():stages[stage].append(seconds)
        if r.get('error'):
            prefix=r['error'].split(':')[0];issues.append({'id':r['id'],'stage':r['status'].removesuffix('_failed'),'category':prefix,'detail':r['error']})
        if (base/'mapping.json').exists():
            m=read(base/'mapping.json');an=read(base/'analysis_call/parsed.json');total_units+=len(an['units'])
            mapped_units+=len({c['unit_id'] for c in m['candidates']});distinct_concepts.update(m['selected_concept_ids'])
            if an['uncertainties']:uncertainty_inputs.append(r['id'])
        if (base/'selection_audit.json').exists():
            audit=read(base/'selection_audit.json')
            for d in audit['decisions']:
                for c in d['conditions']:
                    if not c['matched']:rejections[c['condition']]+=1
        if (base/'reference_packet.json').exists():
            packet=read(base/'reference_packet.json');byid={e['evidence_id']:e for e in packet['evidence']}
            for e in packet['evidence']:
                if e['role']=='realization_reference':refs_claims[e['claim_id']]+=1;docs[e['source']['document_id']]+=1
            if r['status']=='generated_requires_human_review':
                generated=read(base/'generation_call/parsed.json')
                for edit in generated['edits']:
                    for eid in edit['evidence_ids']:used_claims[byid[eid]['claim_id']]+=1
    def describe(v):
        sv=sorted(v);return {'n':len(v),'mean_seconds':round(statistics.mean(v),3),'median_seconds':round(statistics.median(v),3),'p95_nearest_rank_seconds':round(sv[max(0,__import__('math').ceil(.95*len(v))-1)],3)}
    report={'run_id':run.name,'pipeline_version':config['version'],'results_sha256':digest(run/'private/results.json'),
      'metrics_sha256':digest(run/'metrics.json'),'script_sha256':digest(Path(__file__)),
      'input_count':len(results),'error_categories':dict(collections.Counter(x['category'] for x in issues)),
      'issues':issues,'distinct_actual_concept_ids':sorted(distinct_concepts),'analysis_units_in_records_reaching_mapping':total_units,
      'units_with_at_least_one_concept':mapped_units,'inputs_with_qwen_uncertainties':uncertainty_inputs,
      'references_by_claim':dict(refs_claims),'references_by_document':dict(docs),'cited_claims_in_changed_outputs':dict(used_claims),
      'records_with_reference_but_unchanged':[r['id'] for r in results if r.get('reference_count',0)>0 and r['status']=='unchanged'],
      'records_without_realization_reference':[r['id'] for r in results if 'reference_count' in r and r['reference_count']==0],
      'stage_seconds_completed_stages_only':{k:describe(v) for k,v in stages.items()},
      'failed_condition_occurrences':dict(rejections.most_common()),
      'interpretation':'Descriptive process diagnostics only; no accuracy/naturalness/gold labels; failed conditions can mean mismatch or unresolved input, not a false source claim.'}
    (out/'diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'out':str(out),'errors':report['error_categories'],'distinct_concepts':len(distinct_concepts),'references_by_claim':dict(refs_claims),'used_claims':dict(used_claims)},ensure_ascii=False))
if __name__=='__main__':main()
