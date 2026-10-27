"""Reproducible current comparison. Never mutate sealed run artifacts."""
import argparse,collections,datetime,json,math,random,statistics,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from kg_pipeline.io import read,save,sha,load_jsonl
from research_management.core import Registry
from kg_runtime.catalog import PROJECTION

def optional(p,default=None):return read(p) if p.is_file() else default
def aggregate(run_id):
    folder=PROJECT/'experiments/runs'/run_id
    rows=read(folder/'private/results.json');records=[];stages=collections.defaultdict(list)
    for r in rows:
        f=folder/'private/records'/r['id'];raw=optional(f/'retrieval_raw.json',{});more=optional(f/'additional_retrieval.json',{})
        candidates={c['candidate_id']:c for c in raw.get('candidates',[])+more.get('candidates',[])}
        item_ids=sorted({x['id'] for x in raw.get('items',[])+more.get('items',[])})
        packet=optional(f/'reference_packet.json',{})
        for k,v in r['stage_seconds'].items():stages[k].append(v)
        records.append({**r,'morphology':optional(f/'morphology.json'),
            'concepts':raw.get('concept_ids',optional(f/'mapping.json',{}).get('selected_concept_ids',[])),
            'modules':raw.get('searched_modules',[]),'item_ids':item_ids,'candidates':list(candidates.values()),
            'query':raw.get('query',raw.get('queries')),'query_parameters':raw.get('query_parameters'),
            'packet':packet if 'candidates' in packet else {'evidence_count':len(packet.get('evidence',[])),
                'selected_evidence':[{'claim':e.get('claim_id'),'atom':e.get('atom_id'),'target':e.get('target_uid'),
                  'role':e.get('role'),'forms':e.get('forms')} for e in packet.get('evidence',[])]},
            'decision':optional(f/'agent_followup_call/parsed.json',optional(f/'agent_call/parsed.json')),
            'plan':optional(f/'transformation_plan.json'),'final_plan':optional(f/'final_plan.json'),
            'generation':optional(f/'generation_call/parsed.json'),'checks':optional(f/'generation_checks.json'),
            'analysis':optional(f/'analysis_call/parsed.json'),'analysis_checks':optional(f/'analysis_checks.json'),
            'artifact_directory':str(f.relative_to(PROJECT)),
            'initial_raw_utf8_bytes':len(json.dumps(raw,ensure_ascii=False,separators=(',',':')).encode()),
            'initial_packet_utf8_bytes':len(json.dumps(packet,ensure_ascii=False,separators=(',',':')).encode()),
            'additional_candidate_gain':len(set(candidates)-{c['candidate_id'] for c in raw.get('candidates',[])}) if more else None})
    return {'run_id':run_id,'config':read(folder/'config.json'),'metrics':read(folder/'metrics.json'),
        'prompts':{n:(folder/n).read_text(encoding='utf8') for n in ('analysis_prompt.txt','generation_prompt.txt')},
        'postflight':read(folder/'postflight.json'),'records':records,
        'all_retrieved_ids':sorted({x for r in records for x in r['item_ids']}),
        'mean_retrieved_items':statistics.mean(len(r['item_ids']) for r in records),
        'error_categories':dict(collections.Counter(r.get('error','').split(':')[0] for r in rows if r['status'].endswith('_failed'))),
        'initial_raw_utf8_bytes':sum(r['initial_raw_utf8_bytes'] for r in records),
        'initial_packet_utf8_bytes':sum(r['initial_packet_utf8_bytes'] for r in records),
        'length_groups':[{'label':label,'records':sum(lo<=len(r['input_text'])<=hi for r in records),
              'failed':sum(lo<=len(r['input_text'])<=hi and r['status'].endswith('_failed') for r in records)}
              for label,lo,hi in [('30자 이하',0,30),('31~80자',31,80),('81자 이상',81,100000)]],
        'stages':{k:{'mean':statistics.mean(v),'median':statistics.median(v),'count':len(v)} for k,v in stages.items()},
        'versions':{'code':read(folder/'code_hashes.json'),'kg':read(folder/'kg_hashes.json')}}

def paired_analysis(left,right):
    a={r['id']:r for r in left['records']};b={r['id']:r for r in right['records']}
    both=[];neither=[];qonly=[];konly=[]
    for key in a:
        av=a[key].get('analysis_valid',False);bv=b[key].get('analysis_valid',False)
        (both if av and bv else qonly if av else konly if bv else neither).append(key)
    n=len(qonly)+len(konly)
    p=min(1,2*sum(math.comb(n,i) for i in range(min(len(qonly),len(konly))+1))/2**n) if n else 1
    # Same payload and prompt except the provided Kiwi tokens; check recorded requests.
    equal=True
    for key in a:
        req=[]
        for run in (left,right):
            f=PROJECT/'experiments/runs'/run['run_id']/'private/records'/key/'analysis_call/request.json'
            x=read(f);u=json.loads(x['messages'][1]['content']);u.pop('kiwi_source_tokens',None)
            x['messages'][1]['content']=json.dumps(u,sort_keys=True,ensure_ascii=False);req.append(x)
        equal=equal and req[0]==req[1]
    transport_excluded=[key for key in a if any(c.get('status')=='failed' for r in (a[key],b[key]) for c in r['calls'])]
    paired_received=[key for key in a if key not in transport_excluded]
    return {'both_valid':both,'neither_valid':neither,'qwen_only_valid':qonly,'kiwi_only_valid':konly,
            'exact_paired_discordance_p':p,'requests_equal_except_kiwi_tokens':equal,
            'both_received_response':{'n':len(paired_received),'excluded':transport_excluded,
                'qwen_valid':sum(a[k].get('analysis_valid',False) for k in paired_received),
                'kiwi_valid':sum(b[k].get('analysis_valid',False) for k in paired_received)},
            'endpoint':'Source-span/structural contract, not linguistic correctness'}

def operational_delta(current,previous):
    out={}
    for name in ('single','multi'):
        new=current[name];old=previous[name];oldrows={r['id']:r for r in old['records']}
        changed_pool=[]
        for r in new['records']:
            before={c['candidate_id'] for c in oldrows[r['id']].get('retrieval',{}).get('candidates',[])}
            after={c['candidate_id'] for c in r['candidates']}
            if before!=after:changed_pool.append({'id':r['id'],'added':sorted(after-before),'removed':sorted(before-after)})
        extra=[r for r in new['records'] if r['additional_candidate_gain'] is not None]
        a,b=old['metrics'],new['metrics']
        out[name]={'previous_run':old['run_id'],'new_run':new['run_id'],
           'token_delta':b['reported_usage']['total_tokens']-a['reported_usage']['total_tokens'],
           'token_reduction_fraction':1-b['reported_usage']['total_tokens']/a['reported_usage']['total_tokens'],
           'call_delta':b['api_attempts']-a['api_attempts'],
           'mean_latency_delta':b['mean_record_seconds']-a['mean_record_seconds'],
           'additional_lookups':len(extra),'lookups_with_new_candidates':sum(r['additional_candidate_gain']>0 for r in extra),
           'changed_candidate_pools':changed_pool,
           'warning':'Multiple changes and different run time; not a single-factor causal estimate.'}
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--regression',required=True);ap.add_argument('--evaluation',required=True);ap.add_argument('--diagnostic',required=True)
    a=ap.parse_args();out=PROJECT/'experiments/analyses/search_execution_20261025/private';out.mkdir(parents=True,exist_ok=True)
    batches={};runs={}
    for name,bid in vars(a).items():
        bp=PROJECT/'experiments/batches'/bid;batches[name]={'protocol':read(bp/'protocol.json'),'resources':read(bp/'resources.json')}
        runs[name]={key:aggregate(rid) for key,rid in batches[name]['protocol']['runs'].items()}
    root=PROJECT/'knowledge/authored'/PROJECTION;runtime=read(root/'runtime.json');provenance=read(root/'provenance.json')
    membership={e['source']:e['target'] for e in runtime['edges'] if e['relation']=='in_module'}
    atoms=[{**n,'module':membership.get(n['id']),'provenance':provenance[n['id']]} for n in runtime['nodes'] if n['type']=='SourceAtom']
    modules=[{**n,'atoms':sum(x['module']==n['id'] for x in atoms),'executable':sum(x['module']==n['id'] and x['properties'].get('executable',False) for x in atoms)} for n in runtime['nodes'] if n['type']=='Module']
    old=read(PROJECT/'experiments/analyses/redesign_20261024/private/comparison.json')
    historical={k:{'run_id':v['run_id'],'metrics':v['metrics'],'records':[{x:r.get(x) for x in ('id','input_text','output_text','status','error','candidate_count','candidate_rules')} for r in v['records']]} for k,v in old['runs'].items()}
    registry=Registry(PROJECT);registry.sync()
    verification=[registry.verify(r['run_id']) for group in runs.values() for r in group.values()]
    data={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':runs,'batches':batches,
        'graph':{'statistics':read(root/'statistics.json'),'modules':modules,'atoms':atoms,'rules':runtime['rules'],
                 'documents':[{'id':n['id'],'title':n['title']} for n in runtime['nodes'] if n['type']=='SourceDocument'],
                 'edges':runtime['edges'],'node_labels':{n['id']:n['title'] for n in runtime['nodes']},
                 'coverage':read(PROJECT/'experiments/validation/runtime_20261025/search_coverage.json')},
        'historical':historical,'first50':old['previous'],'paired_analysis':paired_analysis(runs['diagnostic']['analysis_qwen'],runs['diagnostic']['analysis_kiwi']),
        'operational_delta':operational_delta(runs['regression'],old['runs']),
        'verification':verification,'comparisons':{k:registry.compare(runs[k]['single']['run_id'],runs[k]['multi']['run_id']) for k in ('regression','evaluation')},
        'automated_tests':read(PROJECT/'experiments/validation/runtime_20261025/test_exit.json'),
        'evaluation_manifest':read(PROJECT/'data/derived_private/runtime_unseen_12_20261025/manifest.json'),
        'human_scores':None,'limitations':['No gold mapping or native-speaker scores.','All effect claims limited to observed structural contracts and cost.','Remote checkpoint/load/cache unknown; latency is a single run observation.','New 12 inputs are author-created convenience samples.','No KG-free or text-only retrieval ablation.','17 input-bound operators, not a complete dialect grammar engine.']}
    pages=read(PROJECT/'knowledge/authored/kg_runtime_20261024/private/source_pages.json')
    page=next(p for p in pages if p['doc']=='D02' and p['pdf_page']==203)
    quote=next(line for line in page['text'].splitlines() if line.startswith('해예체 -예'))
    data['source_contradiction_review']={'reviewer':'main_builder_source_comparison','record':'ADVCE006B',
       'source':{'doc':'D02','pdf_page':203,'quote':quote,'page_text_sha256':page['text_sha256']},
       'observation':'해예체 자체가 없다는 모델의 거절 이유는 해당 문헌에 해예체가 명시된 사실과 충돌한다.',
       'limit':'특정 문장에서 해요→해예가 항상 적절하다는 판정이나 자연스러움 점수가 아니다.',
       'decisions':{k:next(r for r in runs['regression'][k]['records'] if r['id']=='ADVCE006B')['decision'] for k in ('single','multi')}}
    save(out/'data.json',data)
    rng=random.Random(20261025);blind=[];key=[]
    for group in ('regression','evaluation'):
        single=runs[group]['single'];multi={r['id']:r for r in runs[group]['multi']['records']}
        for r in single['records']:
            choices=[('single',r['output_text']),('multi',multi[r['id']]['output_text'])];rng.shuffle(choices)
            blind.append({'id':r['id'],'group':group,'input':r['input_text'],'reviewer':None,'choices':[
                {'label':chr(65+i),'output':v,'naturalness_1_to_5':None,'meaning_preserved':None,'grammar_appropriate':None,'comment':''} for i,(_,v) in enumerate(choices)]})
            key.append({'id':r['id'],'group':group,'conditions':{chr(65+i):c for i,(c,_) in enumerate(choices)}})
    save(out/'blind_review.json',blind);save(out/'blind_review_key.json',key)
    for n in ('report.html','report.js','report.css','review.html','review.js'):
        (out/n).write_bytes((PROJECT/'tools/report_assets/search_execution'/n).read_bytes())
    save(out.parent/'delivery_manifest.json',{'runs':{g:{c:r['run_id'] for c,r in rs.items()} for g,rs in runs.items()},
         'files':{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.iterdir() if p.is_file()},
         'run_artifacts_modified':False})
    print(json.dumps({g:{c:r['metrics'] for c,r in rs.items()} for g,rs in runs.items()},ensure_ascii=False))

if __name__=='__main__':main()
