"""Three independent delivery conditions on 50 frozen analyses, paired by architecture."""
import argparse,concurrent.futures as cf,copy,datetime as dt,importlib.util,json,shutil,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[2];P=B/'private';sys.path[:0]=[str(R/'local/python'),str(R/'src')]
from kg_pipeline.io import Qwen,read,save,sha,load_jsonl
from kg_pipeline.runner import metrics,register_run
from kg_runtime import card_experiment as ce,card_pipeline as cp
from kg_runtime.compatibility import guidance
from kg_runtime.delivery_aids import VARIANTS,PROMPTS,prepare as augment
from research_management.core import guard_dataset
INPUTS=R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
SOURCE='20261030T085346443103Z'
CONDITIONS=[(v,a) for v in VARIANTS for a in ('single','multi')]
# Reuse the heartbeat and event storage implementation; no model call on import.
sp=importlib.util.spec_from_file_location('previous_progress',R/'experiments/analyses/card_content_experiment_20261030/run.py')
old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old)

def check(plan):
 for rel,h in plan['hashes'].items():assert sha((R/rel).read_bytes())==h,rel

def prepared():
 guard_dataset(R,INPUTS,'regression');records=load_jsonl(INPUTS);assert len(records)==50
 rows=[];hashes={str(INPUTS.relative_to(R)):sha(INPUTS.read_bytes())}
 for rec in records:
  src=R/'experiments/batches'/SOURCE/'private/shared'/rec['id']
  packet=read(src/'reference_packet.json');m=read(src/'morphology.json');assert read(src/'shared.json')['ok']
  assert rec['text']==packet['input']==m['text']
  packet['contract_context']=cp.context(m,packet['cards'],packet['grammar'],rec['id'])
  packet['candidate_guidance']=guidance(packet['cards'],packet['grammar'],m)
  for variant in VARIANTS:
   effective=augment(packet,m,variant)
   assert [c['id'] for c in effective['cards']]==[c['id'] for c in packet['cards']]
  for f in src.rglob('*'):
   if f.is_file():hashes[str(f.relative_to(R))]=sha(f.read_bytes())
  rows.append({'id':rec['id'],'source':str(src.relative_to(R)),'cards':[c['id'] for c in packet['cards']],
               'base_packet_sha256':sha(json.dumps(packet,ensure_ascii=False,sort_keys=True).encode())})
 plan={'source_batch':SOURCE,'input_count':50,'conditions':[v+'_'+a for v,a in CONDITIONS],'new_analysis_calls':0,'new_KG_queries':0,
       'rows':rows,'hashes':hashes,'runner_sha256':sha(Path(__file__).read_bytes()),
       'intervention':'shared check fix in all arms; explanation OR composition independently added; never combined',
       'limitations':'single run per condition, not unseen evaluation; no new-output human naturalness labels',
       'approved_references':'not read by this runner or delivery aids'}
 check(plan);return plan

def execute(plan):
 # Preflight before creating run directories; never pretend a models failure is generation.
 c=Qwen(R/'test.py');assert c.model=='Qwen3.8-27B','unexpected_model'
 batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_delivery'
 root=R/'experiments/batches'/batch;root.mkdir(parents=True,exist_ok=False);save(root/'protocol.json',plan)
 outs={}
 for v,a in CONDITIONS:
  out=ce.prepare(R,INPUTS,a,c,batch+'_'+v,'regression','kg_cards_20261030_v3');outs[v,a]=out
  cfg=read(out/'config.json');cfg.update(experiment_family='controlled_delivery_v1',intervention=v,
   analysis_policy='frozen_saved_analysis_no_new_calls',cost_policy='new generation only; cached analysis excluded',
   selection_policy='frozen previous delivered IDs/order; no re-retrieval or reselection',source_batch=SOURCE,
   content_projection='unchanged saved v3 cards; optional separate delivery aids',evaluation_protocol='controlled_delivery_v1')
  save(out/'config.json',cfg);shutil.copy2(__file__,out/'intervention_runner.py');save(out/'private/protocol.json',plan)
  (out/'agent_prompt.txt').write_text((cp.SINGLE if a=='single' else cp.PLANNER)+PROMPTS[v],encoding='utf8')
  (out/'worker_prompt.txt').write_text(cp.GENERATOR+PROMPTS[v],encoding='utf8')
  save(out/'freeze.json',{'config_sha256':sha((out/'config.json').read_bytes()),'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes()),'runner_sha256':plan['runner_sha256']})
  register_run(R,out)
 for row in plan['rows']:
  dst=root/'private/shared'/row['id'];shutil.copytree(R/row['source'],dst)
  packet=read(dst/'reference_packet.json');m=read(dst/'morphology.json')
  packet['contract_context']=cp.context(m,packet['cards'],packet['grammar'],row['id'])
  packet['candidate_guidance']=guidance(packet['cards'],packet['grammar'],m)
  assert sha(json.dumps(packet,ensure_ascii=False,sort_keys=True).encode())==row['base_packet_sha256']
  save(dst/'reference_packet.json',packet);save(dst/'reuse.json',{'source':row['source'],'old_analysis_call_not_new':True})
 save(P/'active_run.json',{'batch':batch,'root':str(root),'runs':{v+'_'+a:o.name for (v,a),o in outs.items()}})
 results={k:[] for k in outs};records=load_jsonl(INPUTS);started=time.perf_counter()
 def job(rec,v,a):
  r=ce.generate(rec,a,c,root/'private/shared'/rec['id'],outs[v,a],delivery_variant=v)
  r.update(intervention=v,analysis_reused=True,kg_queries=0,reused_analysis_seconds=r['shared_analysis_seconds'],shared_analysis_seconds=0,total_seconds=r['incremental_generation_seconds'])
  r['stage_seconds']={k:x for k,x in r['stage_seconds'].items() if k not in ('analysis','retrieval')}
  r['calls']=[x for x in r['calls'] if x['stage']!='analysis'];save(outs[v,a]/'private/records'/rec['id']/'result.json',r)
  return v,a,r
 progress=old.Progress(batch,301);progress.data.update(title='조건 통일 후 설명·조합 도움 분리 비교',stage='50문장 × 3조건 × Single/Multi',message='동일한 기존 분석·카드·모델 설정. 실패도 처리 수에 포함.')
 print('BATCH '+batch,flush=True)
 with progress:
  with cf.ThreadPoolExecutor(max_workers=2) as pool:
   jobs=[]
   for i,rec in enumerate(records):
    for v,a in CONDITIONS[i%6:]+CONDITIONS[:i%6]:jobs.append(pool.submit(job,rec,v,a))
   for f in cf.as_completed(jobs):
    v,a,r=f.result();results[v,a].append(r);message=f'{r["id"]} {v}/{a}: {r["status"]}';print(message,flush=True);progress.done(message)
  wall=time.perf_counter()-started;check(plan);order={r['id']:i for i,r in enumerate(records)};calls=[]
  for (v,a),out in outs.items():
   rows=sorted(results[v,a],key=lambda x:order[x['id']]);save(out/'private/results.json',rows)
   m=metrics(rows,wall);m.update(wall_seconds=None,shared_batch_wall_seconds=wall,cost_note='new generation only; cached analysis excluded',evaluation_note='counts not linguistic accuracy; regression');save(out/'metrics.json',m)
   post={'input_unchanged':sha(INPUTS.read_bytes())==read(out/'config.json')['input_sha256'],
    'code_unchanged':all(sha((R/'src'/rel).read_bytes())==h for rel,h in read(out/'code_hashes.json').items()),
    'kg_unchanged':all(sha((R/rel).read_bytes())==h for rel,h in read(out/'kg_hashes.json').items()),'source_preserved':True}
   save(out/'postflight.json',post);assert all(post.values())
   save(out/'artifact_hashes.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in out.rglob('*') if f.is_file() and f.name!='artifact_hashes.json'})
   calls.extend(x for r in rows for x in r['calls']);register_run(R,out)
  save(root/'resources.json',{'physical_api_attempts':len(calls),'physical_total_tokens':sum((x.get('usage') or {}).get('total_tokens',0) for x in calls),'wall_seconds':wall,'new_analysis_calls':0,'new_retrieval_queries':0})
  progress.done('300개 처리 결과·실패·코드·설정·해시 보존 완료')
 print('COMPLETE '+batch,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args();plan=prepared()
 save(P/'prepared_plan.json',plan);print('Prepared: 50 inputs x 6 arms; no references read.',flush=True)
 if args.execute:execute(plan)
