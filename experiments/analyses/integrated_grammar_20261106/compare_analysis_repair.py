"""Paired development diagnosis; no automatic naturalness score."""
import collections
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,sha,dumps
HERE=Path(__file__).resolve().parent

def structural(run,rid):
    rd=run/'private/records'/rid
    if not (rd/'bound_analysis.json').exists():return {'analysis_available':False}
    us=read(rd/'bound_analysis.json');raw=read(rd/'analysis/parsed.json')
    return {'analysis_available':True,'units':len(us),
            'proposed_relations':sum(len(u.get('relations',[])) for u in raw['units']),
            'valid_relations':sum(sum(len(v) for v in u['relations'].values()) for u in us),
            'relation_issues':sum(len(u['relation_issues']) for u in us),
            'null_features':sum(v is None for u in us for v in u['features'].values()),
            'rule_instances':sum(len(t['eligible']) for t in read(rd/'retrieval.json')),
            'unresolved_instances':sum(len(t['unresolved']) for t in read(rd/'retrieval.json'))}

def main():
    candidates=[p for p in (ROOT/'experiments/runs').glob('*_integrated_grammar_repair') if (p/'metrics.json').exists()]
    if not candidates:print('No completed repair run');return
    after=sorted(candidates)[-1];manifest=read(HERE/'private/analysis_repair_manifest.json');before=ROOT/'experiments/runs'/manifest['baseline']
    old={r['id']:r for r in read(before/'private/results.json')};new={r['id']:r for r in read(after/'private/results.json')}
    bcfg=read(before/'config.json');acfg=read(after/'config.json')
    control={'same_graph':bcfg['graph_sha256']==acfg['graph_sha256'],
             'same_generation_prompt':(before/'generation_prompt.txt').read_bytes()==(after/'generation_prompt.txt').read_bytes(),
             'same_core_code':(before/'code_hashes.json').exists() and read(before/'code_hashes.json')['src/kg_pipeline/integrated.py']==read(after/'code_hashes.json')['src/kg_pipeline/integrated.py'],
             'same_seed':bcfg['seed']==acfg['seed'],
             'same_character_budget':bcfg['knowledge_character_budget']==acfg['knowledge_character_budget'],
             'same_selected_inputs':all(old[i]['input_text']==new[i]['input_text'] for i in manifest['ids'] if i in new),
             'unchanged_schemas':all((before/'private/records'/i/'analysis.schema.json').read_bytes()==(after/'private/records'/i/'analysis.schema.json').read_bytes() for i in new)}
    rows=[];totals={'before':collections.Counter(),'after':collections.Counter()}
    for rid in manifest['ids']:
        if rid not in new:
            rows.append({'id':rid,'attempted':False});continue
        b=structural(before,rid);a=structural(after,rid)
        for name,data in [('before',b),('after',a)]:
            for k,v in data.items():
                if type(v)is int:totals[name][k]+=v
        rows.append({'id':rid,'attempted':True,'before':b,'after':a,
                     'before_output':old[rid].get('output_text'),'after_output':new[rid].get('output_text'),
                     'added_rules':sorted(set(new[rid].get('rule_ids',[]))-set(old[rid].get('rule_ids',[]))),
                     'removed_rules':sorted(set(old[rid].get('rule_ids',[]))-set(new[rid].get('rule_ids',[])))})
    checks=[]
    for c in read(HERE/'private/analysis_repair_checks.json')['checks']:
        outcomes={}
        for name,run in [('before',before),('after',after)]:
            p=run/'private/records'/c['id']/'bound_analysis.json'
            us=[u for u in read(p) if u['kind']==c['kind'] and u['text']==c['text']] if p.exists() else []
            actual=[u['features'].get(c['feature']) for u in us]
            outcomes[name]={'actual':actual,'matches':bool(actual) and all(v in c['expected'] for v in actual)}
        checks.append({**c,**outcomes})
    save(HERE/'private/analysis_repair_comparison.json',{'baseline':before.name,'candidate':after.name,
         'controls':control,'paired_inputs':len(new),'aggregate_structural':{k:dict(v) for k,v in totals.items()},
         'checks':checks,'cases':rows,'quality_effect':'not_independently_evaluated',
         'limits':'18 exposed development inputs; definitions changed as a bundle; no repeat-variance estimate.'})
    print(dumps({'controls':control,'checks_before':sum(x['before']['matches'] for x in checks),
                'checks_after':sum(x['after']['matches'] for x in checks),'check_count':len(checks),
                'structural':{k:dict(v) for k,v in totals.items()}}))

if __name__=='__main__':main()
