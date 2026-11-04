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
from research_management.live import BatchProgress
from .morphology import Morphology,compact_morph
from .cards import CardGraph,VERSION,DATASET
from .card_content import CardContent
from . import card_pipeline as cp
from .analysis_alignment import reconcile_analysis,VERSION as ALIGNMENT_VERSION
from .compatibility import select_compatible,guidance,VERSION as COMPATIBILITY_VERSION

def prepare(project,inputs,condition,client,batch,phase,generation_card_version=None):
    out=project/'experiments/runs'/f'{batch}_cards_{condition}_{phase}'
    out.mkdir(parents=True,exist_ok=False);(out/'private').mkdir()
    shutil.copy2(inputs,out/'private/inputs.jsonl')
    config={'version':'cards_compatible_v1','compatibility':COMPATIBILITY_VERSION,'analysis_alignment':ALIGNMENT_VERSION,'request_schema_policy':'request_local_ID_enum_and_bounded_explanations','edit_contract':cp.CONTRACT_VERSION,'architecture':condition,'phase':phase,'dataset_role':'development' if phase=='smoke' else 'regression',
        'batch_id':batch,'model_id':client.model,'input_sha256':sha(inputs.read_bytes()),'input_count':len(load_jsonl(inputs)),
        'kg_dataset':DATASET,'runtime_projection':VERSION,'seed':20261028,'temperature':0,'top_p':1,'enable_thinking':False,
        'workers':2,'automatic_retries':0,'analysis_max_tokens':9000,'generation_max_tokens':6000,'cards_limit':48,
        'metric_contract':'shared_analysis_cards_v2','evaluation_protocol':'paired_edit_contract_20261030',
        'scope':'data_driven_grammar_plans','analysis_policy':'once_per_input_reused_identically_for_both_arms',
        'cost_policy':'per-arm includes shared analysis once; multi skips worker when no applicable planned edit; unequal calls are recorded, not equal-work inference',
        'model_checkpoint_revision':'not_exposed','gpu':'not_exposed','python':platform.python_version(),
        'kiwipiepy':'0.23.1','test_exposure':'Original50 regression, not unseen evaluation; no native gold'}
    if generation_card_version:
        CardContent(project,generation_card_version)
        config.update(generation_card_version=generation_card_version,selection_card_version=VERSION,
            content_projection='after unchanged v2 selection; same IDs/order/forms',
            test_exposure='regression inputs; approved references exist separately; new-output human quality evaluation pending')
    save(out/'config.json',config);save(out/'server_models.json',client.models)
    hashes={}
    for package in ('kg_runtime','kg_pipeline','research_management'):
        for f in sorted(f for f in (project/'src'/package).iterdir() if f.suffix in ('.py','.json')):
            rel=f'{package}/{f.name}';target=out/'code_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(f,target);hashes[rel]=sha(f.read_bytes())
    save(out/'code_hashes.json',hashes)
    kg_files=[project/'knowledge/authored'/VERSION/'cards.json',project/'knowledge/authored'/DATASET/'graph/nodes.jsonl',project/'knowledge/authored'/DATASET/'graph/edges.jsonl']
    if generation_card_version and generation_card_version!=VERSION:
        kg_files += [project/'knowledge/authored'/generation_card_version/name for name in ('cards.json','provenance.json','manifest.json')]
    save(out/'kg_hashes.json',{str(f.relative_to(project)):sha(f.read_bytes()) for f in kg_files})
    save(out/'analysis.schema.json',cp.ANALYSIS);save(out/'planning.schema.json',cp.DECISION);save(out/'generation.schema.json',cp.DECISION if condition=='single' else cp.WORKER)
    save(out/'validation_contract.json',{'analysis':'anchored_ids_and_actual_concepts','generation':cp.CONTRACT_VERSION,'quality':'human_pending'})
    (out/'analysis_prompt.txt').write_text(cp.ANALYSIS_PROMPT,encoding='utf8')
    (out/'generation_prompt.txt').write_text(cp.SINGLE if condition=='single' else cp.PLANNER+'\n\n'+cp.GENERATOR,encoding='utf8')
    save(out/'freeze.json',{'time':dt.datetime.now(dt.timezone.utc).isoformat(),'config_sha256':sha((out/'config.json').read_bytes()),'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes())})
    register_run(project,out);return out

def shared_analysis(record,morph,client,graph,folder,content=None):
    folder.mkdir(parents=True,exist_ok=False);save(folder/'input.json',record);save(folder/'morphology.json',morph)
    start=time.perf_counter();stage='analysis';value={'ok':False,'stage_seconds':{}}
    try:
        t=time.perf_counter()
        analysis=client.call('analysis',cp.ANALYSIS_PROMPT,{'text':record['text'],'words':compact_morph(morph),
            'concepts':graph.data['concepts']},cp.ANALYSIS,folder/'analysis_call',9000,20261028)
        aligned=cp.validate_analysis(analysis,morph,graph.concepts)
        analysis,analysis_review=reconcile_analysis(analysis,morph,graph.concepts)
        aligned=cp.validate_analysis(analysis,morph,graph.concepts,aligned=True)
        save(folder/'aligned_analysis.json',analysis);save(folder/'analysis_alignment.json',analysis_review)
        save(folder/'analysis_checks.json',{'valid':True,'aligned_units':aligned,'semantic_accuracy':'human_pending'})
        value['stage_seconds'][stage]=time.perf_counter()-t;stage='retrieval';t=time.perf_counter()
        retrieval=graph.retrieve(morph,analysis);save(folder/'retrieval_raw.json',retrieval)
        save(folder/'mapping.json',{'selected_concept_ids':retrieval['concept_ids'],'origin':'Kiwi_routes_union_Qwen_functions','paths':retrieval['paths']})
        save(folder/'selection_audit.json',{'ranking':retrieval['ranking'],'selected_count':len(retrieval['cards']),'retrieved_count':len(retrieval['retrieved_ids'])})
        delivered=retrieval['cards']
        if content is not None:
            delivered,projection=content.project_cards(delivered)
            save(folder/'generation_projection.json',projection)
        # Real query results only. No fabricated node IDs or lookup by gold translation.
        all_cards=[graph.by[cid] for cid in retrieval['retrieved_ids']] if hasattr(graph,'by') else retrieval['cards']
        if content is not None:all_cards,_=content.project_cards(all_cards)
        delivered,compatibility=select_compatible(all_cards,delivered,analysis,morph)
        save(folder/'compatibility_selection.json',compatibility)
        save(folder/'selection_audit.json',{'initial_ranking':retrieval['ranking'],'initial_selected_ids':[c['id'] for c in retrieval['cards']],
            'selected_count':len(delivered),'selected_ids':[c['id'] for c in delivered],'retrieved_count':len(retrieval['retrieved_ids']),
            'final_selection':'register_connective_compatibility_from_same_query'})
        if content is not None:
            source_by={c['id']:c for c in ([graph.by[cid] for cid in retrieval['retrieved_ids']] if hasattr(graph,'by') else retrieval['cards'])}
            _,projection=content.project_cards([source_by[c['id']] for c in delivered])
            save(folder/'generation_projection.json',projection)
        payload={'input':record['text'],'words':compact_morph(morph),'grammar':analysis,'analysis_review':analysis_review,'cards':delivered,
                 'candidate_guidance':guidance(delivered,analysis,morph),
                 'contract_context':cp.context(morph,delivered,analysis,record['id'])}
        save(folder/'reference_packet.json',payload)
        value['stage_seconds'][stage]=time.perf_counter()-t;value.update(ok=True)
    except Exception as exc:value.update(error_type=type(exc).__name__,error=str(exc)[:500],failed_stage=stage)
    value['seconds']=time.perf_counter()-start;save(folder/'shared.json',value);return value

def generate(record,condition,client,shared,out):
    folder=out/'private/records'/record['id'];shutil.copytree(shared,folder)
    info=read(folder/'shared.json');start=time.perf_counter();stage='planning'
    r={'id':record['id'],'input_text':record['text'],'output_text':None,'status':'started','condition':condition,
        'stage_seconds':info['stage_seconds'],'human_evaluation':None,'selected_rules':[],'kg_queries':1 if info['ok'] else 0,'generation_call_skipped':False}
    try:
        if not info['ok']:
            stage=info['failed_stage'];raise ValueError(info['error'])
        morph=read(folder/'morphology.json');payload=read(folder/'reference_packet.json')
        retrieval=read(folder/'retrieval_raw.json');t=time.perf_counter()
        schema=cp.request_schema(cp.DECISION,'request_id',payload['contract_context']['request_id'])
        decision=client.call('agent',cp.SINGLE if condition=='single' else cp.PLANNER,payload,schema,folder/'agent_call',6000,20261028)
        cp.validate_schema(decision,schema)
        plan=cp.bind_plan(decision,morph,payload['cards'],realize=condition=='single',analysis=payload['grammar'],input_id=record['id']);save(folder/'transformation_plan.json',plan)
        r['stage_seconds'][stage]=time.perf_counter()-t
        stage='generation';t=time.perf_counter()
        if condition=='multi' and any(e['action']=='apply' and not e['issues'] for e in plan['edits']):
            used={i for e in plan['edits'] for i in e['rule_ids']}
            schema=cp.request_schema(cp.WORKER,'plan_id',plan['plan_id'])
            answer=client.call('generation',cp.GENERATOR,dict(payload,cards=[c for c in payload['cards'] if c['id'] in used],plan=plan),schema,folder/'generation_call',6000,20261028)
            cp.validate_schema(answer,schema)
            final=cp.realize_plan(plan,answer,morph,payload['cards'],analysis=payload['grammar'],input_id=record['id'])
        elif condition=='multi':
            r['generation_call_skipped']=True
            answer={'plan_id':plan['plan_id'],'reason':'실행할 수정 없음: 추가 호출 생략',
                'edits':[{'edit_id':e['edit_id'],'action':e['action'] if e['action']!='apply' else 'needs_review','after':e['before'],'reason':e['reason']} for e in plan['edits']]}
            final=cp.realize_plan(plan,answer,morph,payload['cards'],analysis=payload['grammar'],input_id=record['id'])
            save(folder/'generation_call/parsed.json',{'response':answer,'origin':'program_skip_no_applicable_edits'})
        else:
            final=plan;save(folder/'generation_call/parsed.json',{'edits':final['edits'],'origin':'single_agent_same_call'})
        save(folder/'final_plan.json',final);output=cp.assemble(record['text'],final)
        save(folder/'generation_checks.json',{'anchor_ids_valid':True,'source_spans_bound':True,'rule_ids_retrieved':True,
             'outside_edit_spans_preserved':True,'assembly':'versioned_bounded_edits','contract':cp.CONTRACT_VERSION,
             'status':final['status'],'held_edits':final['held_edit_count'],
             'meaning_inside_edits':'human_pending','naturalness':'human_pending'})
        r['stage_seconds'][stage]=time.perf_counter()-t
        r.update(status=final['status'],output_text=output,
            edit_count=final['applied_edit_count'],held_edit_count=final['held_edit_count'],
            held_by_model=final['held_by_model'],held_by_program=final['held_by_program'],
            selected_rules=sorted({i for e in final['edits'] for i in e['rule_ids']}),
            applied_rules=sorted({i for e in final['edits'] if e['outcome']=='applied' for i in e['rule_ids']}),
            reference_count=sum(bool(c['forms']) for c in payload['cards']),packet_chars=len(dumps(payload)),raw_chars=len(dumps(retrieval)),
            retrieved_items=len(retrieval['retrieved_ids']),selected_card_count=len(payload['cards']),reason=final['reason'])
        if r['generation_call_skipped']:
            r['held_by_model']=sum(e['action']=='needs_review' for e in plan['edits'])
            r['held_by_program']=sum(bool(e['issues']) for e in final['edits'])
    except Exception as exc:r.update(status=stage+'_failed',error_type=type(exc).__name__,error=str(exc)[:500])
    r['incremental_generation_seconds']=round(time.perf_counter()-start,4)
    r['total_seconds']=round(info['seconds']+r['incremental_generation_seconds'],4)
    r['shared_analysis_seconds']=info['seconds']
    r['calls']=[read(p) for p in sorted(folder.glob('*_call/meta.json'))]
    save(folder/'result.json',r);return r

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--credentials',type=Path,required=True);p.add_argument('--qwen-config',type=Path,required=True)
    p.add_argument('--generation-card-version',default=None,help='Explicit same-ID content version; v2 selection remains unchanged')
    p.add_argument('--phase',choices=['smoke','regression'],required=True);a=p.parse_args(argv)
    guard_dataset(a.project,a.inputs,'development' if a.phase=='smoke' else 'regression')
    records=load_jsonl(a.inputs)
    import re
    if not records or len({r['id'] for r in records})!=len(records) or any(not re.fullmatch('[A-Za-z0-9_-]+',r['id']) for r in records):raise ValueError('invalid_inputs')
    content=CardContent(a.project,a.generation_card_version) if a.generation_card_version else None
    client=Qwen(a.qwen_config);graph=CardGraph(a.project,Neo4j(a.credentials));analyzer=Morphology()
    morphs={r['id']:analyzer.analyze(r['text']) for r in records}
    batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');root=a.project/'experiments/batches'/batch
    outs={c:prepare(a.project,a.inputs,c,client,batch,a.phase,a.generation_card_version) for c in ('single','multi')}
    save(root/'protocol.json',{'batch_id':batch,'runs':{c:o.name for c,o in outs.items()},'shared_analysis':True,'phase':a.phase,
        'order':'analysis barrier, then input-wise rotating single/multi, workers2','wall_note':'shared remote server; per-record latency excludes queue/preflight/Kiwi warmup'})
    print('BATCH '+str(root),flush=True);started=time.perf_counter()
    with BatchProgress(a.project,batch,len(records)) as progress:
        progress.start('analysis')
        with cf.ThreadPoolExecutor(max_workers=2) as pool:
            fs={pool.submit(shared_analysis,r,morphs[r['id']],client,graph,root/'private/shared'/r['id'],content):r['id'] for r in records}
            for f in cf.as_completed(fs):
                ok=f.result()['ok'];print(dumps({'analysis':fs[f],'ok':ok}),flush=True)
                progress.completed_item('analysis',fs[f],'완료' if ok else '분석 실패')
        results={c:[] for c in outs}
        progress.start('single');progress.start('multi')
        with cf.ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[]
            for i,r in enumerate(records):
                for c in (('single','multi') if i%2==0 else ('multi','single')):jobs.append(pool.submit(generate,r,c,client,root/'private/shared'/r['id'],outs[c]))
            for i,f in enumerate(cf.as_completed(jobs),1):
                r=f.result();results[r['condition']].append(r);print(dumps({'done':i,'id':r['id'],'arm':r['condition'],'status':r['status'],'edits':r.get('edit_count')}),flush=True)
                progress.completed_item(r['condition'],r['id'],r['status'])
        wall=time.perf_counter()-started
        progress.start('finalize')
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
        progress.completed_item('finalize',batch,'결과·해시·자원 기록 저장 완료')

if __name__=='__main__':main()
