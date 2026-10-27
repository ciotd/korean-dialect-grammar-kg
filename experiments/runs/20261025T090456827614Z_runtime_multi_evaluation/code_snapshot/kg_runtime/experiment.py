import argparse
import concurrent.futures
import datetime as dt
import json
import os
import platform
import shutil
import time
import traceback
from pathlib import Path
from kg_pipeline.io import Qwen,Neo4j,load_jsonl,save,sha,dumps,read
from kg_pipeline.runner import metrics,register_run
from kg_pipeline.retrieval import load_catalog,retrieve
from kg_pipeline.mapping import map_concepts
from kg_pipeline.selection import select_evidence
from kg_pipeline.validation import validate_analysis,validate_schema
from kg_pipeline.contracts import ANALYSIS,ANALYSIS_PROMPT
from . import __version__
from .morphology import Morphology,compact_morph
from .graph import DATASET,GraphTool,compact_candidates,compact_context,make_plan,apply_plan
from .catalog import PROJECTION
from .prompts import DECISION,WORKER,SINGLE,PLANNER,GENERATOR

def run_record(record,condition,client,graph,analyzer,catalog,out,seed):
    folder=out/'private/records'/record['id'];folder.mkdir(parents=True,exist_ok=False)
    save(folder/'input.json',record);start=time.perf_counter();cpu=time.process_time();stage='morphology'
    r={'id':record['id'],'input_text':record['text'],'output_text':None,'status':'started','stage_seconds':{},'calls':[],
       'condition':condition,'human_evaluation':None,'kg_queries':0,'selected_rules':[]}
    try:
        t=time.perf_counter();m=analyzer.analyze(record['text']);save(folder/'morphology.json',m);r['stage_seconds'][stage]=time.perf_counter()-t
        if condition in ('analysis_kiwi','analysis_qwen'):
            stage='analysis';t=time.perf_counter()
            payload={'input_id':record['id'],'text':record['text'],
                'alignment_instruction':'anchor.surface는 반드시 원문 그대로 복사한다. 형태소의 표제형을 원문 구간으로 쓰지 않는다. 형태 분석 참고 정보가 제공되더라도 원문 구간과 절 범위를 직접 확인한다.'}
            if condition=='analysis_kiwi':payload['kiwi_source_tokens']=m['tokens']
            value=client.call('analysis',ANALYSIS_PROMPT,payload,ANALYSIS,folder/'analysis_call',12000,seed)
            check=validate_analysis(value,record['text'],record['id'],ANALYSIS);save(folder/'analysis_checks.json',check)
            r['stage_seconds'][stage]=time.perf_counter()-t;stage='mapping';mapping=map_concepts(value,catalog);save(folder/'mapping.json',mapping)
            stage='retrieval';t=time.perf_counter();raw=retrieve(graph.neo,mapping,DATASET,1501);save(folder/'retrieval_raw.json',raw);r['kg_queries']=2 if mapping['selected_concept_ids'] else 0
            r['stage_seconds'][stage]=time.perf_counter()-t;stage='selection';packet,audit=select_evidence(raw,value,mapping);save(folder/'reference_packet.json',packet);save(folder/'selection_audit.json',audit)
            r.update(status='analysis_completed',analysis_valid=True,reference_count=sum(x['role']=='realization_reference' for x in packet['evidence']),
                     analysis_warnings=check['warnings'],packet_chars=len(dumps(packet)),raw_chars=len(dumps(raw)))
        else:
            stage='retrieval';t=time.perf_counter();retrieval=graph.retrieve(m,analyzer);r['kg_queries']+=1
            r.update(retrieved_items=retrieval.get('retrieved_item_count',0),non_executable_items=retrieval.get('non_executable_count',0))
            save(folder/'retrieval_raw.json',retrieval);save(folder/'mapping.json',{'selected_concept_ids':retrieval['concept_ids'],'paths':retrieval['paths'],'origin':'Kiwi_POS_and_ending_routes'})
            r['stage_seconds'][stage]=time.perf_counter()-t
            stage='planning';t=time.perf_counter();payload={'input':record['text'],'words':compact_morph(m),'candidates':compact_candidates(retrieval),
              'source_conditions':compact_context(retrieval),'unsearched_modules':graph.remaining_modules(retrieval)}
            save(folder/'reference_packet.json',payload)
            prompt=SINGLE if condition=='single' else PLANNER
            decision=client.call('agent',prompt,payload,DECISION,folder/'agent_call',4000,seed)
            validate_schema(decision,DECISION)
            if decision['action']=='lookup':
                requested=decision['lookup_concepts']
                allowed={x['id'] for x in payload['unsearched_modules']}
                if not requested or not set(requested)<=allowed:raise ValueError('invalid_or_redundant_lookup_request')
                more=graph.retrieve(m,analyzer,requested);r['kg_queries']+=1;save(folder/'additional_retrieval.json',more)
                by={c['candidate_id']:c for c in retrieval['candidates']+more['candidates']};retrieval['candidates']=list(by.values())
                retrieval['items']=list({x['id']:x for x in retrieval.get('items',[])+more.get('items',[])}.values())
                payload.update(candidates=compact_candidates(retrieval),source_conditions=compact_context(retrieval),previous_action=decision,unsearched_modules=[],remaining_lookups=0)
                decision=client.call('agent_followup',prompt+'\n추가 조회를 이미 완료했다. 이제 finish로 답한다.',payload,DECISION,folder/'agent_followup_call',4000,seed)
                validate_schema(decision,DECISION)
                if decision['action']!='finish':raise ValueError('lookup_budget_exhausted')
            plan=make_plan(decision['selected_candidate_ids'],retrieval,record['text']);save(folder/'transformation_plan.json',plan)
            r['stage_seconds'][stage]=time.perf_counter()-t;stage='generation';t=time.perf_counter()
            if condition=='multi':
                instructions=[{'id':e['candidate_id'],'word':e['target_uid'],'span':e['span'],'from':e['before'],'to':e['after'],'when':e['condition']} for e in plan['edits']]
                answer=client.call('generation',GENERATOR,{'input':record['text'],'words':compact_morph(m),'plan':instructions},WORKER,folder/'generation_call',4000,seed)
                validate_schema(answer,WORKER)
                if not set(answer['applied_candidate_ids'])<=set(decision['selected_candidate_ids']):raise ValueError('worker_added_unplanned_edit')
                final_plan=make_plan(answer['applied_candidate_ids'],retrieval,record['text'])
            else:
                answer={'applied_candidate_ids':decision['selected_candidate_ids'],'output_text':decision['output_text'],'reason':decision['reason']};final_plan=plan
                save(folder/'generation_call/parsed.json',answer)
            expected=apply_plan(record['text'],final_plan)
            save(folder/'final_plan.json',final_plan)
            save(folder/'generation_checks.json',{'edits_exactly_reconstruct_output':answer['output_text']==expected,
                'linguistic_correctness':'not_verified','edit_count':len(final_plan['edits']),
                'expected_output_from_plan':expected,'model_output':answer['output_text'],
                'meaning_check_scope':'Only unchanged spans and declared edits checked; meaning inside edits and naturalness need human review.'})
            if answer['output_text']!=expected:raise ValueError('output_differs_from_authorized_edits')
            r['stage_seconds'][stage]=time.perf_counter()-t
            r.update(status='generated_requires_human_review' if expected!=record['text'] else 'unchanged',output_text=expected,
                     edit_count=len(final_plan['edits']),selected_rules=[x['rule_id'] for x in final_plan['edits']],
                     reference_count=len(retrieval['candidates']),packet_chars=len(dumps(payload)),raw_chars=len(dumps(retrieval)),
                     candidate_rules=sorted({x['rule_id'] for x in retrieval['candidates']}),candidate_count=len(retrieval['candidates']),
                     omitted_by_worker=len(plan['edits'])-len(final_plan['edits']),reason=answer['reason'])
    except Exception as exc:
        r.update(status=stage+'_failed',error_type=type(exc).__name__,error=str(exc)[:700])
        if 't' in locals():r['stage_seconds'][stage]=time.perf_counter()-t
        (folder/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
    r['total_seconds']=round(time.perf_counter()-start,4)
    r['process_cpu_seconds_window']=round(time.process_time()-cpu,4)
    r['calls']=[read(p) for p in sorted(folder.glob('*_call/meta.json'))]
    save(folder/'result.json',r);return r

def prepare_run(project,inputs,condition,client,batch_id,workers,phase):
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=project/'experiments/runs'/f'{stamp}_runtime_{condition}_{phase}'
    out.mkdir(parents=True,exist_ok=False);(out/'private').mkdir();shutil.copy2(inputs,out/'private/inputs.jsonl')
    config={'version':__version__,'phase':phase,'dataset_role':{'regression':'regression','evaluation':'evaluation','smoke':'development'}[phase],
      'architecture':condition,'batch_id':batch_id,'model_id':client.model,'input_sha256':sha(inputs.read_bytes()),'input_count':len(load_jsonl(inputs)),
      'kg_dataset':DATASET,'runtime_projection':PROJECTION,'seed':20261023,'temperature':0,'top_p':1,'workers':workers,
      'enable_thinking':False,'analysis_max_tokens':12000,'generation_max_tokens':4000,'automatic_retries':0,
      'metric_contract':'analysis_diagnostic_v1' if condition in ('analysis_kiwi','analysis_qwen') else 'runtime_plan_execution_v1',
      'evaluation_protocol':'controlled_runtime_no_gold_20261025','model_checkpoint_revision':'not_exposed_by_server','gpu':'not_exposed_by_server',
      'resource_note':'Local CPU/RSS observed; shared remote GPU memory/load unknown. No GPU efficiency claim.',
      'scope':'analysis_diagnostic' if condition in ('analysis_kiwi','analysis_qwen') else 'source_compiled_transformation',
      'test_exposure':'Original50 is regression; new evaluation inputs are author-created and frozen before any calls, not native-speaker gold.',
      'kiwipiepy':'0.23.1','kiwipiepy_model':'0.23.0','python':platform.python_version()}
    save(out/'config.json',config);save(out/'server_models.json',client.models)
    codehash={}
    for package in ('kg_runtime','kg_pipeline'):
        for f in (project/'src'/package).glob('*.py'):
            rel=package+'/'+f.name;target=out/'code_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target);codehash[rel]=sha(f.read_bytes())
    save(out/'code_hashes.json',codehash)
    save(out/'validation_contract.json',{'plan_validator':codehash['kg_runtime/graph.py'],'schemas':sha(dumps([DECISION,WORKER]).encode()),'analysis_validator':codehash['kg_pipeline/validation.py']})
    save(out/'kg_hashes.json',{'runtime.json':sha((project/'knowledge/authored'/PROJECTION/'runtime.json').read_bytes()),
                             'provenance.json':sha((project/'knowledge/authored'/PROJECTION/'provenance.json').read_bytes()),
                             **{n:sha((project/'knowledge/authored'/DATASET/'graph'/n).read_bytes()) for n in ('nodes.jsonl','edges.jsonl')}})
    save(out/'analysis.schema.json',ANALYSIS if condition in ('analysis_kiwi','analysis_qwen') else DECISION);save(out/'generation.schema.json',WORKER)
    (out/'analysis_prompt.txt').write_text(ANALYSIS_PROMPT if condition in ('analysis_kiwi','analysis_qwen') else SINGLE if condition=='single' else PLANNER,encoding='utf8')
    (out/'generation_prompt.txt').write_text(GENERATOR if condition=='multi' else 'Single Agent returns final output in the decision call.',encoding='utf8')
    save(out/'freeze.json',{'time_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes()),'config_sha256':sha((out/'config.json').read_bytes())})
    register_run(project,out);return out

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--credentials',type=Path,required=True);p.add_argument('--qwen-config',type=Path,required=True)
    p.add_argument('--conditions',nargs='+',choices=['analysis_qwen','analysis_kiwi','single','multi'],default=['single','multi']);p.add_argument('--phase',choices=['smoke','regression','evaluation'],required=True)
    p.add_argument('--workers',type=int,default=2);a=p.parse_args(argv)
    if len(set(a.conditions))!=len(a.conditions):raise ValueError('duplicate_conditions')
    if not 1<=a.workers<=4:raise ValueError('workers must be 1..4')
    records=load_jsonl(a.inputs)
    if not records or len({r['id'] for r in records})!=len(records):raise ValueError('invalid_input_ids')
    import re
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+',r['id']) for r in records):raise ValueError('invalid_input_id')
    from research_management.core import guard_dataset
    guard_dataset(a.project,a.inputs,{'regression':'regression','evaluation':'evaluation','smoke':'development'}[a.phase])
    client=Qwen(a.qwen_config);neo=Neo4j(a.credentials);catalog=load_catalog(neo,a.project/'knowledge/authored'/DATASET,DATASET)
    graph=GraphTool(a.project,neo);analyzer=Morphology();analyzer.analyze('형태 분석 준비.')
    batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    outs={c:prepare_run(a.project,a.inputs,c,client,batch,a.workers,a.phase) for c in a.conditions}
    jobs=[]
    for i,r in enumerate(records):
        order=a.conditions[i%len(a.conditions):]+a.conditions[:i%len(a.conditions)]
        jobs.extend((r,c) for c in order)
    protocol={'batch_id':batch,'job_order':[(r['id'],c) for r,c in jobs],'order':'input-wise rotating condition order','workers':a.workers,'runs':{k:v.name for k,v in outs.items()},'model_calls_planned_min':sum(2 if c=='multi' else 1 for _,c in jobs)}
    batchpath=a.project/'experiments/batches'/batch;save(batchpath/'protocol.json',protocol)
    print(dumps(protocol),flush=True);start=time.perf_counter();cpu=time.process_time();results={c:[] for c in a.conditions}
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        fs=[pool.submit(run_record,r,c,client,graph,analyzer,catalog,outs[c],20261023) for r,c in jobs]
        for i,f in enumerate(concurrent.futures.as_completed(fs),1):
            r=f.result();results[r['condition']].append(r);print(dumps({'done':i,'of':len(jobs),'id':r['id'],'condition':r['condition'],'status':r['status'],'edits':r.get('edit_count')}),flush=True)
    wall=time.perf_counter()-start
    for condition,out in outs.items():
        rows=sorted(results[condition],key=lambda x:next(i for i,r in enumerate(records) if r['id']==x['id']))
        save(out/'private/results.json',rows);m=metrics(rows,wall)
        m.update(wall_seconds=None,shared_batch_wall_seconds=round(wall,3),analysis_valid_records=sum(r.get('analysis_valid',False) for r in rows),
                 kg_query_count=sum(r['kg_queries'] for r in rows),selected_rule_ids=sorted({k for r in rows for k in r['selected_rules']}),
                 wall_note='Shared interleaved batch: compare per-record latency; no isolated per-condition wall time.',
                 rule_accuracy=None,meaning_preservation=None,naturalness=None)
        save(out/'metrics.json',m)
        save(out/'postflight.json',{'input_unchanged':sha(a.inputs.read_bytes())==read(out/'config.json')['input_sha256'],
          'code_unchanged':all(sha((a.project/'src'/rel).read_bytes())==h for rel,h in read(out/'code_hashes.json').items()),
          'kg_unchanged':all(sha((a.project/'knowledge/authored'/DATASET/'graph'/n).read_bytes())==h for n,h in read(out/'kg_hashes.json').items() if n in ('nodes.jsonl','edges.jsonl')),
          'runtime_unchanged':all(sha((a.project/'knowledge/authored'/PROJECTION/n).read_bytes())==read(out/'kg_hashes.json')[n] for n in ('runtime.json','provenance.json'))})
        save(out/'private/human_review.json',[{'id':r['id'],'input':r['input_text'],'output':r['output_text'],'naturalness':None,'meaning_preserved':None,'rule_correctness':None,'reviewer':None} for r in rows])
        save(out/'artifact_hashes.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in out.rglob('*') if f.is_file() and f.name!='artifact_hashes.json'})
        register_run(a.project,out);print('COMPLETE '+out.name+' '+dumps(m),flush=True)
    save(batchpath/'resources.json',{'batch_wall_seconds':wall,'local_process_cpu_seconds':time.process_time()-cpu,'local_peak_working_set_bytes':peak_memory(),'remote_gpu_memory_bytes':None,'remote_gpu_utilization':None})

def peak_memory():
    if os.name!='nt':return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(x,ctypes.c_size_t) for x in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    c=Counters();c.cb=ctypes.sizeof(c)
    kernel=ctypes.windll.kernel32;kernel.GetCurrentProcess.restype=wintypes.HANDLE
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    if ctypes.windll.psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb):return c.PeakWorkingSetSize
    return None

if __name__=='__main__':main()
