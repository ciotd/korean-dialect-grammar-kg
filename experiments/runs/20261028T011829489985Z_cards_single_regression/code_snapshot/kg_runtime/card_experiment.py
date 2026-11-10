"""Paired experiment with byte-identical shared analysis/retrieval for both arms."""
import argparse
import concurrent.futures as cf
import datetime as dt
import platform
import shutil
import time
from pathlib import Path
from kg_pipeline.io import Qwen,Neo4j,load_jsonl,save,read,dumps,sha
from kg_pipeline.runner import metrics,register_run
from research_management.core import guard_dataset
from .morphology import Morphology,compact_morph
from .cards import CardGraph,VERSION,DATASET
from . import card_pipeline as cp

def prepare(project,inputs,condition,client,batch,phase):
    out=project/'experiments/runs'/f'{batch}_cards_{condition}_{phase}'
    out.mkdir(parents=True,exist_ok=False);(out/'private').mkdir()
    shutil.copy2(inputs,out/'private/inputs.jsonl')
    config={'version':'cards_v1','architecture':condition,'phase':phase,'dataset_role':'development' if phase=='smoke' else 'regression',
        'batch_id':batch,'model_id':client.model,'input_sha256':sha(inputs.read_bytes()),'input_count':len(load_jsonl(inputs)),
        'kg_dataset':DATASET,'runtime_projection':VERSION,'seed':20261028,'temperature':0,'top_p':1,'enable_thinking':False,
        'workers':2,'automatic_retries':0,'analysis_max_tokens':9000,'generation_max_tokens':6000,'cards_limit':48,
        'metric_contract':'shared_analysis_cards_v1','evaluation_protocol':'paired_shared_analysis_20261028',
        'scope':'data_driven_grammar_plans','analysis_policy':'once_per_input_reused_identically_for_both_arms',
        'cost_policy':'per-arm production cost includes one shared analysis; physical batch counts it only once',
        'model_checkpoint_revision':'not_exposed','gpu':'not_exposed','python':platform.python_version(),
        'kiwipiepy':'0.23.1','test_exposure':'Original50 regression, not unseen evaluation; no native gold'}
    save(out/'config.json',config);save(out/'server_models.json',client.models)
    hashes={}
    for package in ('kg_runtime','kg_pipeline','research_management'):
        for f in (project/'src'/package).glob('*.py'):
            rel=f'{package}/{f.name}';target=out/'code_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(f,target);hashes[rel]=sha(f.read_bytes())
    save(out/'code_hashes.json',hashes)
    save(out/'kg_hashes.json',{str(f.relative_to(project)):sha(f.read_bytes()) for f in
        [project/'knowledge/authored'/VERSION/'cards.json',project/'knowledge/authored'/DATASET/'graph/nodes.jsonl',project/'knowledge/authored'/DATASET/'graph/edges.jsonl']})
    save(out/'analysis.schema.json',cp.ANALYSIS);save(out/'generation.schema.json',cp.DECISION if condition=='single' else cp.WORKER)
    save(out/'validation_contract.json',{'analysis':'anchored_ids_and_actual_concepts','generation':'word_spans_rule_refs_and_nonoverlap','quality':'human_pending'})
    (out/'analysis_prompt.txt').write_text(cp.ANALYSIS_PROMPT,encoding='utf8')
    (out/'generation_prompt.txt').write_text(cp.SINGLE if condition=='single' else cp.PLANNER+'\n\n'+cp.GENERATOR,encoding='utf8')
    save(out/'freeze.json',{'time':dt.datetime.now(dt.timezone.utc).isoformat(),'config_sha256':sha((out/'config.json').read_bytes()),'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes())})
    register_run(project,out);return out

def shared_analysis(record,morph,client,graph,folder):
    folder.mkdir(parents=True,exist_ok=False);save(folder/'input.json',record);save(folder/'morphology.json',morph)
    start=time.perf_counter();stage='analysis';value={'ok':False,'stage_seconds':{}}
    try:
        t=time.perf_counter()
        analysis=client.call('analysis',cp.ANALYSIS_PROMPT,{'text':record['text'],'words':compact_morph(morph),
            'concepts':graph.data['concepts']},cp.ANALYSIS,folder/'analysis_call',9000,20261028)
        aligned=cp.validate_analysis(analysis,morph,graph.concepts)
        save(folder/'analysis_checks.json',{'valid':True,'aligned_units':aligned,'semantic_accuracy':'human_pending'})
        value['stage_seconds'][stage]=time.perf_counter()-t;stage='retrieval';t=time.perf_counter()
        retrieval=graph.retrieve(morph,analysis);save(folder/'retrieval_raw.json',retrieval)
        save(folder/'mapping.json',{'selected_concept_ids':retrieval['concept_ids'],'origin':'Kiwi_routes_union_Qwen_functions','paths':retrieval['paths']})
        save(folder/'selection_audit.json',{'ranking':retrieval['ranking'],'selected_count':len(retrieval['cards']),'retrieved_count':len(retrieval['retrieved_ids'])})
        payload={'input':record['text'],'words':compact_morph(morph),'grammar':analysis,'cards':retrieval['cards']}
        save(folder/'reference_packet.json',payload)
        value['stage_seconds'][stage]=time.perf_counter()-t;value.update(ok=True)
    except Exception as exc:value.update(error_type=type(exc).__name__,error=str(exc)[:500],failed_stage=stage)
    value['seconds']=time.perf_counter()-start;save(folder/'shared.json',value);return value

def generate(record,condition,client,shared,out):
    folder=out/'private/records'/record['id'];shutil.copytree(shared,folder)
    info=read(folder/'shared.json');start=time.perf_counter();stage='planning'
    r={'id':record['id'],'input_text':record['text'],'output_text':None,'status':'started','condition':condition,
        'stage_seconds':info['stage_seconds'],'human_evaluation':None,'selected_rules':[],'kg_queries':1 if info['ok'] else 0}
    try:
        if not info['ok']:
            stage=info['failed_stage'];raise ValueError(info['error'])
        morph=read(folder/'morphology.json');payload=read(folder/'reference_packet.json')
        retrieval=read(folder/'retrieval_raw.json');t=time.perf_counter()
        decision=client.call('agent',cp.SINGLE if condition=='single' else cp.PLANNER,payload,cp.DECISION,folder/'agent_call',6000,20261028)
        plan=cp.bind_plan(decision,morph,payload['cards'],realize=condition=='single');save(folder/'transformation_plan.json',plan)
        r['stage_seconds'][stage]=time.perf_counter()-t
        stage='generation';t=time.perf_counter()
        if condition=='multi':
            used={i for e in plan['edits'] for i in e['rule_ids']}
            answer=client.call('generation',cp.GENERATOR,dict(payload,cards=[c for c in payload['cards'] if c['id'] in used],plan=plan),
                cp.WORKER,folder/'generation_call',6000,20261028)
            final=cp.realize_plan(plan,answer,morph,payload['cards'])
        else:
            final=plan;save(folder/'generation_call/parsed.json',{'edits':final['edits'],'origin':'single_agent_same_call'})
        save(folder/'final_plan.json',final);output=cp.assemble(record['text'],final)
        save(folder/'generation_checks.json',{'anchor_ids_valid':True,'source_spans_bound':True,'rule_ids_retrieved':True,
             'outside_edit_spans_preserved':True,'assembly':'deterministic_splicing_of_Qwen_realized_words',
             'meaning_inside_edits':'human_pending','naturalness':'human_pending'})
        r['stage_seconds'][stage]=time.perf_counter()-t
        r.update(status='unchanged' if output==record['text'] else 'generated_requires_human_review',output_text=output,
            edit_count=sum(e['before']!=e['after'] for e in final['edits']),selected_rules=sorted({i for e in final['edits'] for i in e['rule_ids']}),
            reference_count=sum(bool(c['forms']) for c in payload['cards']),packet_chars=len(dumps(payload)),raw_chars=len(dumps(retrieval)),
            retrieved_items=len(retrieval['retrieved_ids']),selected_card_count=len(payload['cards']),reason=final['reason'])
    except Exception as exc:r.update(status=stage+'_failed',error_type=type(exc).__name__,error=str(exc)[:500])
    r['incremental_generation_seconds']=round(time.perf_counter()-start,4)
    r['total_seconds']=round(info['seconds']+r['incremental_generation_seconds'],4)
    r['shared_analysis_seconds']=info['seconds']
    r['calls']=[read(p) for p in sorted(folder.glob('*_call/meta.json'))]
    save(folder/'result.json',r);return r

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--credentials',type=Path,required=True);p.add_argument('--qwen-config',type=Path,required=True)
    p.add_argument('--phase',choices=['smoke','regression'],required=True);a=p.parse_args(argv)
    guard_dataset(a.project,a.inputs,'development' if a.phase=='smoke' else 'regression')
    records=load_jsonl(a.inputs)
    import re
    if not records or len({r['id'] for r in records})!=len(records) or any(not re.fullmatch('[A-Za-z0-9_-]+',r['id']) for r in records):raise ValueError('invalid_inputs')
    client=Qwen(a.qwen_config);graph=CardGraph(a.project,Neo4j(a.credentials));analyzer=Morphology()
    morphs={r['id']:analyzer.analyze(r['text']) for r in records}
    batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');root=a.project/'experiments/batches'/batch
    outs={c:prepare(a.project,a.inputs,c,client,batch,a.phase) for c in ('single','multi')}
    save(root/'protocol.json',{'batch_id':batch,'runs':{c:o.name for c,o in outs.items()},'shared_analysis':True,'phase':a.phase,
        'order':'analysis barrier, then input-wise rotating single/multi, workers2','wall_note':'shared remote server; per-record latency excludes queue/preflight/Kiwi warmup'})
    print('BATCH '+str(root),flush=True);started=time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        fs={pool.submit(shared_analysis,r,morphs[r['id']],client,graph,root/'private/shared'/r['id']):r['id'] for r in records}
        for f in cf.as_completed(fs):print(dumps({'analysis':fs[f],'ok':f.result()['ok']}),flush=True)
    results={c:[] for c in outs}
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[]
        for i,r in enumerate(records):
            for c in (('single','multi') if i%2==0 else ('multi','single')):jobs.append(pool.submit(generate,r,c,client,root/'private/shared'/r['id'],outs[c]))
        for i,f in enumerate(cf.as_completed(jobs),1):
            r=f.result();results[r['condition']].append(r);print(dumps({'done':i,'id':r['id'],'arm':r['condition'],'status':r['status'],'edits':r.get('edit_count')}),flush=True)
    wall=time.perf_counter()-started
    order={r['id']:i for i,r in enumerate(records)}
    for c,out in outs.items():
        rows=sorted(results[c],key=lambda r:order[r['id']]);save(out/'private/results.json',rows)
        m=metrics(rows,wall);m.update(wall_seconds=None,shared_batch_wall_seconds=wall,
            selected_rule_ids=sorted({i for r in rows for i in r['selected_rules']}),
            cost_note='Production-equivalent per-arm costs include shared analysis once. Do not sum both arms as physical batch cost.')
        save(out/'metrics.json',m)
        save(out/'postflight.json',{'input_unchanged':sha(a.inputs.read_bytes())==read(out/'config.json')['input_sha256'],
            'code_unchanged':all(sha((a.project/'src'/rel).read_bytes())==h for rel,h in read(out/'code_hashes.json').items()),
            'kg_unchanged':all(sha((a.project/rel).read_bytes())==h for rel,h in read(out/'kg_hashes.json').items())})
        save(out/'artifact_hashes.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in out.rglob('*') if f.is_file() and f.name!='artifact_hashes.json'})
        register_run(a.project,out);print('COMPLETE '+out.name+' '+dumps(m),flush=True)
    calls=[read(p) for p in (root/'private/shared').glob('*/analysis_call/meta.json')]
    calls += [read(p) for out in outs.values() for p in (out/'private/records').glob('*/*_call/meta.json') if p.parent.name!='analysis_call']
    save(root/'resources.json',{'wall_seconds':wall,'physical_api_attempts':len(calls),
        'physical_total_tokens':sum((c.get('usage') or {}).get('total_tokens',0) for c in calls),
        'remote_gpu_usage':None,'currency_cost':None,'analysis_shared_once':True})

if __name__=='__main__':main()
