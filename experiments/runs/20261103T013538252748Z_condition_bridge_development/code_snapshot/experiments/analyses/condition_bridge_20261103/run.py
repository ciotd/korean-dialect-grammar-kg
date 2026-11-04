"""Frozen paired analysis/retrieval experiment. Never calls generation."""
import collections
import concurrent.futures
import datetime
import json
import platform
import shutil
import time
from pathlib import Path
from bridge import HERE,ROOT,PRIOR,GRAPH,PROMPT,contract,payload,assemble,trace
from adapter import RuntimeReader,adapt,compact_morph
from contracts import ANALYSIS,ANALYSIS_PROMPT
from kg_pipeline.io import Qwen,read,save,sha,dumps
from kg_pipeline.validation import validate_schema
from kg_pipeline.runner import register_run
from research_management.core import guard_dataset
from research_management.work import WorkStore

def execute(row,arm,morph,graph,client,out,config):
 rid=row['id']+'_'+arm;folder=out/'private/records'/rid;folder.mkdir(parents=True,exist_ok=False)
 result={'id':rid,'source_case':row['id'],'group':row['group'],'condition':arm,'input_text':row['text'],
  'output_text':None,'status':'started','calls':[],'stage_seconds':{},'human_evaluation':None,
  'generation_call_skipped':True,'generation_reason':'analysis_retrieval_only_experiment'}
 save(folder/'input.json',{'id':rid,'text':row['text'],'condition':arm});save(folder/'morphology.json',morph)
 stage='analysis';start=time.perf_counter()
 try:
  schema=ANALYSIS if arm=='baseline' else contract(graph)[0]
  user={'text':row['text'],'words':compact_morph(morph)} if arm=='baseline' else payload(graph,morph)
  raw=client.call('question_analysis',ANALYSIS_PROMPT if arm=='baseline' else PROMPT,user,schema,
    folder/'analysis_call',config['analysis_max_tokens'],config['seed'])
  validate_schema(raw,schema);result['analysis_response_valid']=True
  result['stage_seconds']['analysis']=time.perf_counter()-start
  stage='binding';a=adapt(raw,morph) if arm=='baseline' else assemble(graph,raw,morph)
  save(folder/'analysis.json',a);result.update(feature_values=a['clauses'][0]['features'],target=a['clauses'][0]['target_text'])
  stage='retrieval'
  if arm=='bridge':
   t=trace(graph,a,morph);q=t['retrieval'];packet=t['packet'];save(folder/'condition_trace.json',t)
  else:
   reader=RuntimeReader(graph,morph);q=reader.query(a);packet=reader.packet(a,q)
  save(folder/'retrieval_raw.json',q);save(folder/'reference_packet.json',packet)
  result.update(status='retrieval_completed',query_state=q['clauses'][0]['state'],readiness=packet['clauses'][0]['readiness'],
    eligible_rule_ids=[x['rule_id'] for x in q['clauses'][0]['eligible']],
    unresolved_rule_ids=[x['rule_id'] for x in q['clauses'][0]['unresolved']],
    scope_failures=q['clauses'][0]['scope_failures'],needs_analysis=packet['clauses'][0]['needs_analysis'])
 except Exception as exc:
  result.update(status=stage+'_failed',error_type=type(exc).__name__,error=str(exc)[:250])
 result['total_seconds']=round(time.perf_counter()-start,4)
 result['calls']=[read(p) for p in folder.glob('*_call/meta.json')]
 save(folder/'result.json',result)
 return result

def main():
 prepared=read(HERE/'private/preparation.json')
 if not all(sha(Path(p).read_bytes())==h for p,h in prepared['files'].items()):raise ValueError('prepared_inputs_changed')
 rows=read(HERE/'private/cases.json');morphs=read(HERE/'private/kiwi_inputs.json');graph=read(GRAPH)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');runid=stamp+'_condition_bridge_development'
 out=ROOT/'experiments/runs'/runid;out.mkdir(parents=True,exist_ok=False)
 client=Qwen(ROOT/'test.py',timeout=90)
 inputs=[{'id':r['id']+'_'+arm,'source_case':r['id'],'condition':arm,'text':r['text']} for r in rows for arm in ('baseline','bridge')]
 inp=out/'private/inputs.jsonl';inp.parent.mkdir();inp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in inputs),encoding='utf-8')
 config={'phase':'development','dataset_role':'development','metric_contract':'analysis_condition_bridge_v1',
  'model_id':client.model,'kg_dataset':graph['version'],'input_count':len(inputs),'source_cases':32,'unique_source_texts':31,
  'input_sha256':sha(inp.read_bytes()),'seed':20261103,'temperature':0,'top_p':1,'enable_thinking':False,
  'analysis_max_tokens':2048,'generation_calls':0,'automatic_retries':0,'workers':2,'timeout_seconds':90,
  'arms':['baseline','bridge'],'comparison':'same server, seed, token cap, Kiwi and KG; multiple interface changes as a package, not an isolated causal ablation',
  'reference_policy':'builder references; Q13 Q15 Q16 diagnostic-only. References never provided to Qwen.',
  'data_check':guard_dataset(ROOT,inp,'development'),'python':platform.python_version(),
  'model_checkpoint_revision':'not_exposed_by_server','knowledge_access':'frozen graph JSON, no live Neo4j'}
 save(out/'config.json',config);save(out/'server_models.json',client.models)
 save(out/'analysis.schema.json',contract(graph)[0]);save(out/'baseline_analysis.schema.json',ANALYSIS)
 (out/'analysis_prompt.txt').write_text(PROMPT,encoding='utf-8');(out/'baseline_analysis_prompt.txt').write_text(ANALYSIS_PROMPT,encoding='utf-8')
 for name in ('cases.json','kiwi_inputs.json','condition_inventory.json','preparation.json','preparation_v1.json','cases_v1.json'):
  save(out/'private'/name,read(HERE/'private'/name))
 save(out/'private/graph.json',graph);save(out/'kg_hashes.json',prepared['files'])
 dependencies=list(HERE.glob('*.py'))+list(PRIOR.glob('*.py'))+[
  ROOT/'experiments/analyses/question_refinement_20261102/query.py',ROOT/'experiments/analyses/question_refinement_20261102/sources.py',
  ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/semantic_graph.py',ROOT/'src/kg_pipeline/io.py',
  ROOT/'src/kg_pipeline/validation.py',ROOT/'src/kg_runtime/morphology.py']
 hashes={}
 for p in dependencies:
  rel=p.relative_to(ROOT);dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes[str(rel)]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'before_first_chat_call':True,'config_sha256':sha((out/'config.json').read_bytes()),'code_manifest_sha256':sha((out/'code_hashes.json').read_bytes())})
 save(HERE/'private/latest_run.json',{'run_id':runid,'directory':str(out)})
 store=WorkStore(ROOT);task={'id':runid,'title':'분석·KG 조건 연결 비교 32건×2방식','actor':'Qwen + Kiwi','stage':'분석·조회 비교',
  'status':'running','done':0,'total':64,'unit':'분석 호출','message':'생성 호출 없음. 실행 조건 동결 완료.'}
 store.task(task);register_run(ROOT,out);print('RUN '+runid,flush=True)
 # Frozen batch, no response-dependent changes. Alternate order for the paired arms.
 jobs=[(r,arm) for i,r in enumerate(rows) for arm in (('baseline','bridge') if i%2==0 else ('bridge','baseline'))]
 results=[];start=time.perf_counter()
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  pending={pool.submit(execute,r,arm,morphs[r['id']],graph,client,out,config):(r['id'],arm) for r,arm in jobs}
  while pending:
   done,_=concurrent.futures.wait(pending,timeout=15,return_when=concurrent.futures.FIRST_COMPLETED)
   if not done:
    task['message']='서버 응답 대기';store.task(task);print('WAIT '+str(task['done'])+'/64',flush=True)
   for f in done:
    pending.pop(f);result=f.result();results.append(result);task['done']+=1
    elapsed=time.perf_counter()-start;eta=round(elapsed/task['done']*(64-task['done']))
    task.update(message=result['id']+' '+result['status'],estimated_remaining_seconds=eta)
    store.task(task);print(dumps({'done':task['done'],'total':64,'eta_seconds':eta,'id':result['id'],'status':result['status'],'query':result.get('query_state')}),flush=True)
 results.sort(key=lambda r:(r['source_case'],r['condition']));save(out/'private/results.json',results)
 calls=[c for r in results for c in r['calls']]
 metric={'records':64,'api_attempts':len(calls),'generation_calls':0,'actual_generated_outputs':0,'valid_output_records':0,
  'analysis_failures':sum(r['status']=='analysis_failed' for r in results),'status_counts':dict(collections.Counter(r['status'] for r in results)),
  'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},
  'wall_seconds':round(time.perf_counter()-start,3),'quality_evaluation':'not performed; no translations generated'}
 save(out/'metrics.json',metric)
 save(out/'postflight.json',{'inputs_and_graph_preserved':all(sha(Path(p).read_bytes())==h for p,h in prepared['files'].items()),'records':len(results),'generation_requests':len(list((out/'private').rglob('generation_call/request.json')))})
 save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
 register_run(ROOT,out);task.update(status='completed',done=64,estimated_remaining_seconds=0,message='比較 호출 완료. 분모·오류 분석 진행.');store.task(task)
 print('COMPLETE '+runid,flush=True)

if __name__=='__main__':main()
