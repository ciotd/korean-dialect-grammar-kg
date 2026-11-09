"""Inventory existing artifacts only. Does not validate or modify grammar knowledge."""
from pathlib import Path
from collections import Counter
import json,hashlib
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
def read(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
latest=read('knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
graph=read(latest['graph']);nodes={n['id']:n for n in graph['nodes']}
rules={i for i,n in nodes.items() if n['type']=='SemanticRule'}
modules=[];assigned=set()
for n in sorted((n for n in graph['nodes'] if n['type']=='Module'),key=lambda x:x['id']):
    r=sorted({e['source'] for e in graph['edges'] if e['target']==n['id'] and e['relation']=='IN_MODULE' and e['source'] in rules})
    assigned.update(r);modules.append({'id':n['id'],'title':n['title'],'direct_rule_ids':r,'direct_rule_count':len(r),'scope':'Direct IN_MODULE edges only; not semantic coverage or complete indirect membership'})
coverage=read('experiments/analyses/integrated_grammar_20261106/coverage_r2.json')
packages=coverage['packages']
run='experiments/runs/20261109T030211818725Z_kiwi_default_regression'
config=read(run+'/config.json');metrics=read(run+'/metrics.json')
codes=read(run+'/code_hashes.json')
eligible=set();delivered=set();used=set();request_count=0;request_matches=[];memo_cases=[]
for d in sorted((ROOT/run/'private/records').iterdir()):
    if (d/'retrieval.json').exists():
        for unit in json.loads((d/'retrieval.json').read_text(encoding='utf-8')):
            eligible.update(x['rule_id'] for x in unit.get('eligible',[]))
    if not (d/'selected_knowledge.json').exists():continue
    selected=json.loads((d/'selected_knowledge.json').read_text(encoding='utf-8'))
    action_rules={x['action_id']:x['rule_id'] for x in selected}
    delivered.update(action_rules.values())
    if (d/'writer/parsed.json').exists():
        parsed=json.loads((d/'writer/parsed.json').read_text(encoding='utf-8'))
        used.update(action_rules[a] for a in parsed.get('used_action_ids',[]) if a in action_rules)
    if (d/'writer/request.json').exists():
        req=json.loads((d/'writer/request.json').read_text(encoding='utf-8'))
        payload=json.loads(req['messages'][1]['content']);request_count+=1
        request_matches.append(payload['knowledge']==selected)
        for x in selected:
            txt=json.dumps(x,ensure_ascii=False)
            if '리드 판단 필요' in txt or 'D07 p24' in txt:
                memo_cases.append({'record':d.name,'rule_id':x['rule_id'],'field':'limitations','contains_review_note':'리드 판단 필요' in txt,'contains_page_reference':'D07 p24' in txt})
overview={
 'date':'2026-11-09','scope':'Stage 1: existing artifact inventory; no new Qwen, KG edits or full grammar validation',
 'graph':{'path':latest['graph'],'version':latest['version'],'sha256':sha(ROOT/latest['graph']),'nodes':len(nodes),'edges':len(graph['edges']),'types':dict(Counter(n['type'] for n in graph['nodes'])),'matches_latest_run':sha(ROOT/latest['graph'])==config['graph_sha256']},
 'modules':modules,'rules_without_direct_module_edge':sorted(rules-assigned),
 'work_packages':packages,'package_count':len(packages),'packages_marked_complete':sum(x['whole_package_complete'] for x in packages),
 'package_table_caveat':'2026-11-06 additional44 mapping; new_rule_ids exclude prior12 rules; zero here does not imply no current implementation.',
 'prior_rule_ids':sorted(r for r in rules if not r.startswith('INT_')),
 'latest_run':{'id':Path(run).name,'metrics':metrics,'config_without_secrets':{k:config.get(k) for k in ['model_id','temperature','top_p','seed','graph_sha256','knowledge_character_budget','enable_thinking']}},
 'runtime_code_match':{'checked':len(codes),'changed':[p for p,h in codes.items() if sha(ROOT/p)!=h]},
 'saved_run_rule_stages':{'eligible_unique':len(eligible),'delivered_unique':len(delivered),'reported_used_unique':len(used),'no_eligible_observation':sorted(rules-eligible),'writer_requests':request_count,'knowledge_equals_selected':all(request_matches),'caveat':'Eligibility is not all retrieval; reported use is not correct realization. This is one exposed regression run, not grammar coverage.'},
 'verified_mixed_note_examples':memo_cases,
 'source_hashes':{p:sha(ROOT/p) for p in ['experiments/analyses/integrated_grammar_20261106/coverage_r2.json',run+'/config.json',run+'/metrics.json',run+'/code_hashes.json']}
}
(BASE/'overview.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'graph':overview['graph'],'packages':len(packages),'completed_labels':overview['packages_marked_complete'],'rules_without_direct_module_edge':overview['rules_without_direct_module_edge'],'runtime':overview['runtime_code_match']},ensure_ascii=False,indent=2))
