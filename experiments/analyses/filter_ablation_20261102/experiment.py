"""Selection-policy ablation using frozen analysis and actual stored graph retrieval.

Production code/cards and previous runs are read-only. No reference translations
are loaded into preparation or model calls. Both arms reuse the existing multi
planner/worker and downstream checks without modifications.
"""
import argparse,copy,datetime as dt,sys,time,threading,shutil,platform,json
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
H=Path(__file__).resolve().parent;R=H.parents[2];P=H/'private'
sys.path[:0]=[str(R/'local/python'),str(R/'src')]
from kg_pipeline.io import read,save,sha,dumps,load_jsonl,Qwen
from kg_pipeline.runner import register_run
from kg_runtime import card_pipeline as cp
from kg_runtime.card_experiment import generate
from kg_runtime.compatibility import select_compatible,guidance
from kg_runtime.cards import select_cards
from kg_runtime.card_content import CardContent
from research_management.work import WorkStore
SOURCE=R/'experiments/batches/20261030T085346443103Z/private/shared'
INPUT=R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
ARMS=('filtered','unfiltered');TASK='filter-ablation-20261102'

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(x):return sha(dumps(x).encode())
def task(stage,status='running',done=None,total=None,message=''):
 d=dict(id=TASK,title='50문장 카드 선별 사용·우회 비교',actor='Codex 총괄',stage=stage,status=status,message=message)
 if total is not None:d.update(done=done,total=total,unit='조건별 처리',unit_key=stage)
 WorkStore(R).task(d)

def packets(row,catalog):
 folder=SOURCE/row['id'];raw=read(folder/'retrieval_raw.json');m=read(folder/'morphology.json');a=read(folder/'reference_packet.json')
 assert row['text']==a['input']==m['text']
 ids=raw['retrieved_ids'];assert len(set(ids))==len(ids)
 assert set(ids)=={p['rule_id'] for p in raw['paths']}
 all_cards=[copy.deepcopy(catalog.by[i]) for i in sorted(ids)]
 assert all(c==catalog.by[c['id']] for c in a['cards'])
 # Replay CURRENT existing selection code on the same frozen query universe.
 # Historical selected packets are not used as newly measured controls.
 ranked,_=select_cards([catalog.base[i] for i in sorted(ids)],a['grammar'],m)
 original,_=catalog.project_cards(ranked)
 rebuilt,_=select_compatible(all_cards,original,a['grammar'],m)
 a['cards']=rebuilt;a['candidate_guidance']=guidance(rebuilt,a['grammar'],m)
 # Both arms use CURRENT identical downstream contract; stored packet predates
 # later contract changes. Retain old packet in source snapshot, not its stale ID.
 a['contract_context']=cp.context(m,a['cards'],a['grammar'],row['id'])
 b=copy.deepcopy(a);b['cards']=all_cards;b['candidate_guidance']=[]
 b['contract_context']=cp.context(m,all_cards,b['grammar'],row['id'])
 for key in a:
  if key not in ('cards','candidate_guidance','contract_context'):assert a[key]==b[key]
 for key in ('contract','input_id','user_restrictions'):assert a['contract_context'][key]==b['contract_context'][key]
 assert {c['id'] for c in a['cards']} <= set(ids)
 # request_id is a deterministic payload signature and necessarily differs.
 return m,raw,{'filtered':a,'unfiltered':b}

def source_hashes():
 files=[INPUT,H/'experiment.py',H/'test_experiment.py']
 for package in ('kg_runtime','kg_pipeline','research_management'):
  files+=list((R/'src'/package).glob('*.py'))+list((R/'src'/package).glob('*.json'))
 for v in ('kg_cards_20261028_v2','kg_cards_20261030_v3'):
  files+=list((R/'knowledge/authored'/v).glob('*.json'))
 for row in load_jsonl(INPUT):
  files += [SOURCE/row['id']/f for f in ('retrieval_raw.json','reference_packet.json','morphology.json','shared.json')]
 return {str(f.relative_to(R)):sha(f.read_bytes()) for f in files if f.exists()}

def prepare():
 task('조건 구성',message='저장된 실제 조회 결과로 A/B 구성. Qwen 호출 및 카드 수정 없음.')
 rows=load_jsonl(INPUT);assert len(rows)==len({r['id'] for r in rows})==50
 catalog=CardContent(R,'kg_cards_20261030_v3');stats=[]
 for row in rows:
  morph,raw,arms=packets(row,catalog)
  for arm,payload in arms.items():
   f=P/'prepared'/arm/row['id']
   save(f/'reference_packet.json',payload);save(f/'morphology.json',morph);save(f/'retrieval_raw.json',raw)
   save(f/'shared.json',{'ok':True,'stage_seconds':{},'seconds':0,'analysis_retrieval_reused':True,'source':str((SOURCE/row['id']).relative_to(R))})
   stats.append({'id':row['id'],'arm':arm,'cards':len(payload['cards']),'guidance_count':len(payload['candidate_guidance']),'payload_chars':len(dumps(payload)),'payload_sha256':digest(payload),'retrieval_sha256':digest(raw),'morphology_sha256':digest(morph),'analysis_sha256':digest(payload['grammar'])})
 save(P/'preparation.json',stats);save(P/'source_hashes.json',source_hashes())
 protocol={'version':'filter_ablation_v1','date':now(),'inputs':50,'arms':list(ARMS),'architecture':'multi','repeats':1,'seed':20261028,'workers':2,'max_completion_tokens':6000,'automatic_retries':0,'max_calls':200,
 'question':'Does removing the pre-planner card selection policy improve selection and generation?',
 'treatment':'all IDs from the SAME stored actual query; remove initial top48 rank, per-word top3 compatibility selection, and program candidate guidance; deterministic ID order; no token truncation',
 'control':'current existing ranking/compatibility/guidance code replayed on frozen actual query; context rebuilt using current identical contract; new planning and generation, not historical output',
 'fixed':'source, morphology, grammar, actual query/results, card version/content, planner/worker prompts, seed/sampling, downstream checks and repairs',
 'retained':'intrinsic candidate/reference/restriction roles and existing user restrictions; post-planning and post-generation linguistic checks',
 'derived_changes':'card_usage and request_id follow different card pools; worker plan/card subset follow Qwen choices; this is bundled policy ablation, not isolated filter-vs-length-vs-order causality',
 'evidence':'stored graph paths preserve actual Concept IDs and relations; no new graph query or analysis calls',
 'references':'not loaded during prepare/run; user-approved references used only in post-run display',
 'test_role':'exposed regression/diagnostic set, not held-out generalization; one repeat cannot establish stochastic reliability',
 'failure_policy':'no truncation/retry/tuning during run; retain context overflow and malformed replies as failures, not unchanged successes; stop batch on service unavailability',
 'cost_scope':'new planning and generation only; excludes reused analysis and retrieval',
 'approval':{'channel':'chat','quote':'진행','preceding_scope':'기존 선별 사용/선별 우회, 전체50, Qwen 직접 선택, 카드내용과 후단검사 유지'}}
 save(P/'protocol.json',protocol)
 print(dumps({'records':len(stats),'by_arm':{a:{'cards_min':min(s['cards'] for s in stats if s['arm']==a),'cards_max':max(s['cards'] for s in stats if s['arm']==a),'chars_min':min(s['payload_chars'] for s in stats if s['arm']==a),'chars_max':max(s['payload_chars'] for s in stats if s['arm']==a)} for a in ARMS}}),flush=True)
 return rows

class Progress:
 def __init__(self):
  self.done=0;self.lock=threading.Lock();self.stop=threading.Event();self.publish();self.thread=threading.Thread(target=self.beat,daemon=True);self.thread.start()
 def publish(self):task('Qwen 비교 실행',done=self.done,total=100,message='두 조건을 입력별 교차 실행. 완료 수는 성공률이 아니며 원시 선택·생성·후단 검사를 분리 저장합니다.')
 def beat(self):
  while not self.stop.wait(15):
   with self.lock:self.publish()
 def tick(self,r):
  with self.lock:self.done+=1;self.publish();print(dumps({'done':self.done,'id':r['id'],'arm':r['arm'],'status':r['status'],'calls':r['physical_calls']}),flush=True)
 def close(self):self.stop.set();self.thread.join()

def inspect_result(r,folder):
 rec=folder/'private/records'/r['id'];decision=read(rec/'agent_call/parsed.json') if (rec/'agent_call/parsed.json').exists() else None
 r['planner_selected_bindings']=[{'edit_id':e['edit_id'],'action':e['action'],'word_ids':e['word_ids'],'bindings':e['bindings']} for e in (decision or {}).get('edits',[])]
 r['raw_selected_rules']=sorted({b['card_id'] for e in (decision or {}).get('edits',[]) for b in e['bindings']})
 r['edit_trace']=[]
 plan=read(rec/'transformation_plan.json') if (rec/'transformation_plan.json').exists() else None
 final=read(rec/'final_plan.json') if (rec/'final_plan.json').exists() else None
 worker=read(rec/'generation_call/parsed.json') if (rec/'generation_call/parsed.json').exists() else {}
 actual_worker=worker if 'origin' not in worker else {}
 raw_by={e['edit_id']:e for e in actual_worker.get('edits',[])}
 r['preworker_held_edits']=[{'edit_id':e['edit_id'],'bindings':e['bindings'],'issues':e['issues'],'outcome':e['outcome']} for e in (plan or {}).get('edits',[]) if e['outcome']=='needs_review']
 for e in (final or {}).get('edits',[]):
  w=raw_by.get(e['edit_id'],{})
  r['edit_trace'].append({'edit_id':e['edit_id'],'bindings':e['bindings'],'word_ids':e['word_ids'],'before':e['before'],'raw':w.get('after'),'raw_action':w.get('action'),'raw_reason':w.get('reason'),'after':e['after'],'outcome':e['outcome'],'issues':e['issues'],'repairs':e.get('repairs',[])})
 r['physical_calls']=len(list(rec.glob('*_call/meta.json')))
 r['quality_accuracy']=None;r['analysis_reused']=True
 r['failed_call_details']=[m for m in r['calls'] if m.get('status')=='failed']
 save(rec/'result.json',r);return r

def run(rows):
 assert source_hashes()==read(P/'source_hashes.json'),'source_changed_since_prepare'
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');root=P/stamp;root.mkdir(parents=True,exist_ok=False)
 freeze=read(P/'source_hashes.json');save(root/'freeze.json',freeze);shutil.copytree(P/'prepared',root/'prepared')
 for rel in freeze:
  dest=root/'snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,dest)
 save(root/'protocol.json',read(P/'protocol.json'))
 try:client=Qwen(R/'test.py',timeout=240)
 except Exception as e:
  save(root/'connection_failure.json',{'type':type(e).__name__,'http_status':getattr(e,'code',None),'at':now()});task('Qwen 연결 실패',status='waiting',message='모델 목록 조회 실패. 입력·조건은 보존했으며 생성 호출 없음.');raise
 save(root/'server_models.json',client.models)
 print('MODEL '+client.model+' '+dumps({'max_model_len':[m.get('max_model_len') for m in client.models['data']]}),flush=True)
 outs={};results={a:[] for a in ARMS}
 for a in ARMS:
  out=R/'experiments/runs'/f'{stamp}_filter_ablation_{a}';out.mkdir(parents=True,exist_ok=False);outs[a]=out
  cfg={'version':'filter_ablation_v1','architecture':'multi','phase':'diagnostic','dataset_role':'regression','batch_id':stamp,'arm':a,'model_id':client.model,'input_count':50,'input_sha256':sha(INPUT.read_bytes()),'model_checkpoint_revision':'not_exposed','python':platform.python_version(),'seed':20261028,'temperature':0,'top_p':1,'enable_thinking':False,'workers':2,'automatic_retries':0,'generation_max_tokens':6000,'metric_contract':'filter_ablation_mechanical_v1','evaluation_protocol':'same_saved_analysis_query_policy_ablation','cost_scope':'new planning/generation only','kg_dataset':catalog_dataset(),'test_exposure':'regression user-approved references not transmitted','selection':'original' if a=='filtered' else 'all_retrieved_no_guidance'}
  save(out/'config.json',cfg);save(out/'server_models.json',client.models);save(out/'freeze.json',freeze)
  save(out/'code_hashes.json',{k:v for k,v in freeze.items() if '/src/' in '/'+k.replace('\\','/') or k.endswith('experiment.py') or k.endswith('test_experiment.py')})
  save(out/'kg_hashes.json',{k:v for k,v in freeze.items() if k.startswith('knowledge')})
  save(out/'protocol.json',read(root/'protocol.json'));save(out/'validation_contract.json',{'contract':cp.CONTRACT_VERSION,'downstream_unchanged':True,'quality':'human_pending'})
  save(out/'planning.schema.json',cp.DECISION);save(out/'generation.schema.json',cp.WORKER)
  (out/'planner_prompt.txt').write_text(cp.PLANNER,encoding='utf8');(out/'generation_prompt.txt').write_text(cp.GENERATOR,encoding='utf8')
  (out/'private').mkdir();shutil.copy2(INPUT,out/'private/inputs.jsonl')
 save(P/'latest.json',{'root':str(root.relative_to(R)),'runs':{a:p.name for a,p in outs.items()},'state':'running'})
 progress=Progress();started=time.perf_counter();unavailable=threading.Event()
 def pair(row,index):
  output=[]
  for a in (ARMS if index%2==0 else tuple(reversed(ARMS))):
   if unavailable.is_set():
    r={'id':row['id'],'arm':a,'input_text':row['text'],'output_text':None,'status':'not_run_service_unavailable','physical_calls':0,'calls':[],'quality_accuracy':None,'incremental_generation_seconds':0}
    save(outs[a]/'private/records'/row['id']/'result.json',r)
   else:
    r=generate(row,'multi',client,root/'prepared'/a/row['id'],outs[a]);r['arm']=a;r=inspect_result(r,outs[a])
    if any(m.get('http_status') in (401,403,429,502,503,504) or m.get('error_type') in ('URLError','TimeoutError') for m in r['failed_call_details']):unavailable.set()
   progress.tick(r);output.append(r)
  return output
 try:
  # First pair is part of the fixed dataset, not a tuning pilot. Do not change prompts after it.
  for res in pair(rows[0],0):results[res['arm']].append(res)
  with ThreadPoolExecutor(max_workers=2) as pool:
   fs=[pool.submit(pair,r,i) for i,r in enumerate(rows[1:],1)]
   for fut in as_completed(fs):
    for res in fut.result():results[res['arm']].append(res)
 finally:progress.close()
 wall=time.perf_counter()-started;order={r['id']:i for i,r in enumerate(rows)};unchanged=source_hashes()==freeze
 summary={'wall_seconds':wall,'source_unchanged':unchanged,'quality_accuracy':None,'arms':{},'service_unavailable':unavailable.is_set()}
 for a,out in outs.items():
  rr=sorted(results[a],key=lambda x:order[x['id']]);assert len(rr)==50
  save(out/'private/results.json',rr)
  calls=[m for r in rr for m in r['calls']];usage=Counter()
  for m in calls:usage.update({k:v for k,v in (m.get('usage') or {}).items() if isinstance(v,(int,float))})
  metrics={'records':50,'valid_output_records':sum(r.get('output_text') is not None for r in rr),'changed_records':sum(r.get('output_text') is not None and r['output_text']!=r['input_text'] for r in rr),'status_counts':dict(Counter(r['status'] for r in rr)),'api_attempts':len(calls),'reported_usage':dict(usage),'calls_with_usage':sum(bool(m.get('usage')) for m in calls),'calls_without_usage':sum(not m.get('usage') for m in calls),'summed_api_seconds':sum(m.get('seconds',0) for m in calls),'summed_record_seconds':sum(r['incremental_generation_seconds'] for r in rr),'wall_seconds':None,'shared_batch_wall_seconds':wall,'quality_accuracy':None,'naturalness':'human_pending','held_by_model':sum(r.get('held_by_model',0) for r in rr),'held_by_program':sum(r.get('held_by_program',0) for r in rr),'repair_events':sum(len(e['repairs']) for r in rr for e in r.get('edit_trace',[]))}
  summary['arms'][a]=metrics;save(out/'metrics.json',metrics);save(out/'postflight.json',{'source_unchanged':unchanged})
  save(out/'artifact_hashes.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in out.rglob('*') if f.is_file() and f.name!='artifact_hashes.json'})
  register_run(R,out)
 save(root/'summary.json',summary);save(root/'results.json',[r for a in ARMS for r in results[a]])
 save(P/'latest.json',{'root':str(root.relative_to(R)),'runs':{a:p.name for a,p in outs.items()},'state':'completed_with_service_failure' if unavailable.is_set() else 'completed','finished_at':now()})
 task('결과 대조',message='100개 조건별 처리 기록 저장. 새로운 출력·차단·실패와 비용을 대조합니다.')
 print(dumps(summary),flush=True)

def catalog_dataset():return read(R/'knowledge/authored/kg_cards_20261030_v3/cards.json')['source_dataset']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);a=p.parse_args()
 if a.action=='prepare':prepare()
 else:run(load_jsonl(INPUT))
