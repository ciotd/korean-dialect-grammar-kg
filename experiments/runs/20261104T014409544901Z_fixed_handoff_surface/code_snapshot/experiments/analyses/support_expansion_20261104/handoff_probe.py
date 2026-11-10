"""Paired generation-only diagnostic: fixed saved analysis, positions and KG rules.

Control repeats the actual packet. Surface-preserving handoff removes bookkeeping
and explains how to keep an already-inflected source. Qwen writes both outputs.
No completed dialect target, reference answer or composer result is supplied.
"""
from pathlib import Path
import concurrent.futures,collections,datetime,json,shutil,time,importlib.util
import runtime as rt
from kg_pipeline.io import Qwen,read,save,sha
from kg_pipeline.validation import validate_schema
from kg_runtime.morphology import Morphology
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
H=Path(__file__).resolve().parent;R=H.parents[2]
s=importlib.util.spec_from_file_location('probe_boundary_runner',R/'experiments/analyses/boundary_qwen_20261103/run.py');parent=importlib.util.module_from_spec(s);s.loader.exec_module(parent);parent.rt=rt
SURFACE_PROMPT=rt.GENERATION_PROMPT+'''
이번에는 이미 활용된 원문의 형태를 최대한 이용한다. 어간과 선어말 목록은 보존 확인용이지 모든 어절을 처음부터 다시 만들라는 뜻이 아니다.
KG composition이 해체+예 결합인 경우, 원문의 아/어요·네요·지요 활용에서 마지막 요를 예로 바꾸면 해체 부분과 과거·높임 형태가 보존된다. 새 어를 덧붙이지 않는다. 이 방법을 명사 뒤 라예 또는 나/노/가/고 규칙으로 확대하지 않는다.
그 밖의 규칙은 전달된 composition과 forms로 결합하되, 원문의 과거·높임 선어말을 없애지 않는다. 앞에서 설명한 보존 조건은 그대로 지킨다.
'''
def lean(packet):
 p={'text':packet['text'],'actions':[],'unsupported_or_unresolved':packet['unsupported_or_unresolved'],'instruction':packet['instruction']}
 for a in packet['actions']:
  b={k:a[k] for k in ('target_id','target','span','source_morphs','stem','nominal','prefinals','source_final','rule_id','meaning','forms','composition','preserve') if k in a}
  b['speech_act']=a['features'].get('speech_act');p['actions'].append(b)
 return p
def main():
 source=Path(read(H/'private/latest_full50.json')['directory']);original=read(source/'private/results.json');rows=[]
 for r in original:
  d=source/'private/records'/r['id'];packet=read(d/'generation_packet.json')
  if packet['actions']:rows.append((r,packet,read(d/'actions_internal.json')))
 assert rows and len(rows)==sum(r['supported_targets']>0 for r in original)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');client=Qwen(R/'test.py',timeout=90);analyzer=Morphology();runs={};outcomes=collections.defaultdict(list);start=time.perf_counter()
 code=Path(__file__);code_hash=sha(code.read_bytes());source_config=read(source/'config.json')
 for arm,prompt in [('control',rt.GENERATION_PROMPT),('surface',SURFACE_PROMPT)]:
  d=R/'experiments/runs'/(stamp+'_fixed_handoff_'+arm);d.mkdir(parents=True,exist_ok=False);runs[arm]=d
  inp=d/'private/inputs.jsonl';inp.parent.mkdir();inp.write_text(''.join(json.dumps({'id':r['id'],'text':r['input_text']},ensure_ascii=False)+'\n' for r,_,_ in rows),'utf8')
  config={**source_config,'metric_contract':'fixed_action_generation_v1','phase':'regression_diagnostic','dataset_role':'regression_subset','source_run':source.name,'input_count':len(rows),'input_sha256':sha(inp.read_bytes()),'arm':arm,'analysis_calls':0,'analysis_policy':'reuse exact source records','selection':'all source records with at least one ready action','comparison':'paired diagnostic; representation and guidance changed together, not individually attributed','model_id':client.model}
  save(d/'config.json',config);save(d/'server_models.json',client.models);save(d/'private/graph.json',read(source/'private/graph.json'));save(d/'source_hashes.json',{'results':sha((source/'private/results.json').read_bytes()),'source_code_hashes':read(source/'code_hashes.json')})
  shutil.copytree(source/'code_snapshot',d/'code_snapshot');rel=code.relative_to(R);dest=d/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(code,dest);hashes=read(source/'code_hashes.json');hashes[str(rel)]=code_hash;save(d/'code_hashes.json',hashes)
  (d/'generation_prompt.txt').write_text(prompt,'utf8');save(d/'freeze.json',{'before_first_chat_call':True,'input_sha256':sha(inp.read_bytes()),'graph_sha256':sha((d/'private/graph.json').read_bytes()),'prompt_sha256':sha(prompt.encode()),'code_sha256':code_hash});register_run(R,d)
 save(H/'private/latest_handoff.json',{a:str(d) for a,d in runs.items()})
 store=WorkStore(R);task={'id':stamp+'_handoff','title':'동일 분석·규칙, 전달 방식 비교','actor':'Qwen / 조건 고정','stage':'기존 전달 vs 활용형 보존 안내','status':'running','done':0,'total':len(rows)*2,'unit':'생성 호출','message':'정답 미전달·조합기 대체 없음'};store.task(task)
 def execute(arm,row,packet,actions):
  d=runs[arm]/'private/records'/row['id'];d.mkdir(parents=True);p=packet if arm=='control' else lean(packet)
  assert [(a['target_id'],a['rule_id'],a['forms'],a['composition']) for a in p['actions']]==[(a['target_id'],a['rule_id'],a['forms'],a['composition']) for a in packet['actions']]
  save(d/'generation_packet.json',p);save(d/'actions_internal.json',actions);save(d/'input.json',{'id':row['id'],'text':row['input_text']});t=time.perf_counter()
  r={'id':row['id'],'input_text':row['input_text'],'output_text':None,'arm':arm,'targets':row['targets'],'supported_targets':len(actions),'output_origin':'qwen_full_sentence','status':'generation_started'}
  try:
   raw=client.call('dialect_generation',rt.GENERATION_PROMPT if arm=='control' else SURFACE_PROMPT,p,rt.GENERATION_SCHEMA,d/'generation_call',2048,20261103);validate_schema(raw,rt.GENERATION_SCHEMA);r.update(parent.inspect_generated(row['input_text'],raw,actions,analyzer));r['status']='completed_with_warnings' if r['checks']['warnings'] else 'completed'
  except Exception as exc:r.update(status='generation_failed',error_type=type(exc).__name__,error=str(exc)[:160])
  r['seconds']=round(time.perf_counter()-t,3);save(d/'result.json',r);return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures=[]
  for i,(r,p,a) in enumerate(rows):
   for arm in (['control','surface'] if i%2==0 else ['surface','control']):futures.append(pool.submit(execute,arm,r,p,a))
  for future in concurrent.futures.as_completed(futures):
   r=future.result();outcomes[r['arm']].append(r);task.update(done=sum(map(len,outcomes.values())),message=r['arm']+' '+r['id']);store.task(task);print(json.dumps({'done':task['done'],'total':task['total'],'arm':r['arm'],'id':r['id'],'status':r['status']},ensure_ascii=False),flush=True)
 elapsed=round(time.perf_counter()-start,3)
 for arm,d in runs.items():
  results=sorted(outcomes[arm],key=lambda r:next(i for i,(row,_,_) in enumerate(rows) if row['id']==r['id']));save(d/'private/results.json',results);calls=[read(p) for p in (d/'private/records').rglob('meta.json')]
  metrics={'records':len(results),'valid_output_records':sum(r['output_text'] is not None for r in results),'api_attempts':len(calls),'analysis_calls':0,'generation_calls':len(calls),'changed_records':sum(r['output_text'] is not None and r['output_text']!=r['input_text'] for r in results),'record_status_counts':dict(collections.Counter(r['status'] for r in results)),'warning_counts':dict(collections.Counter(w for r in results for w in r.get('checks',{}).get('warnings',[]))),'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},'paired_wall_seconds':elapsed,'record_seconds_sum':sum(r['seconds'] for r in results),'naturalness_evaluation':'not_scored'}
  save(d/'metrics.json',metrics);save(d/'postflight.json',{'code_unchanged':sha(code.read_bytes())==code_hash,'inputs_unchanged':sha((d/'private/inputs.jsonl').read_bytes())==read(d/'config.json')['input_sha256'],'source_results_unchanged':sha((source/'private/results.json').read_bytes())==read(d/'source_hashes.json')['results'],'all_fixed_actions':True});save(d/'artifact_hashes.json',{str(p.relative_to(d)):sha(p.read_bytes()) for p in d.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(R,d);print(arm,json.dumps(metrics,ensure_ascii=False))
 task.update(status='completed',done=task['total'],message='동일 위치·규칙 비교 완료. 자연스러움 점수 아님');store.task(task)
if __name__=='__main__':main()
