"""Replay exactly the saved analysis and KG packet. Only composition handoff changes."""
import concurrent.futures,datetime,json,shutil,time,threading
from pipeline import *
from kg_pipeline.io import Qwen,read,save,sha,load_jsonl
from kg_pipeline.runner import register_run
from kg_runtime.morphology import Morphology
from research_management.work import WorkStore
LOCK=threading.Lock()
def main():
 source=Path(read(HERE/'private/latest_dev.json')['directory'])
 rows=load_jsonl(source/'private/inputs.jsonl');old=read(source/'private/results.json');client=Qwen(ROOT/'test.py',timeout=90);morphology=Morphology()
 runid=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_research_loop_composition_replay'
 out=ROOT/'experiments/runs'/runid;out.mkdir(parents=True,exist_ok=False);(out/'private').mkdir()
 shutil.copy2(source/'private/inputs.jsonl',out/'private/inputs.jsonl')
 config=read(source/'config.json');config.update(metric_contract='composition_replay_v1',source_run=source.name,analysis_calls=0,
  comparison='fixed previous analysis and exact KG packet; Korean component payload and output schema changed together',arms=['components'],paired_generation=False,input_count=32)
 save(out/'config.json',config);save(out/'server_models.json',client.models)
 (out/'prompt.txt').write_text(COMPOSE_PROMPT,'utf8');save(out/'schema.json',COMPOSE_SCHEMA)
 snapshot={}
 for file in (HERE/'pipeline.py',HERE/'replay.py'):
  dest=out/'code_snapshot'/file.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest);snapshot[str(file.relative_to(ROOT))]=sha(file.read_bytes())
 save(out/'code_hashes.json',snapshot);save(out/'freeze.json',{'before_first_chat_call':True,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'source_artifact_manifest_sha256':sha((source/'artifact_hashes.json').read_bytes()),'graph_sha256':sha(bridge.GRAPH.read_bytes())})
 save(HERE/'private/latest_replay.json',{'run_id':runid,'directory':str(out)})
 store=WorkStore(ROOT);task={'id':runid,'title':'같은 분석·같은 규칙으로 조합 지시만 재검사','actor':'Qwen','stage':'생성 전달 수정','status':'running','done':0,'total':32,'unit':'입력','message':'원문 정답 없이 실제 부품만 전달'};store.task(task)
 def execute(r):
  folder=out/'private/records'/r['id'];folder.mkdir(parents=True,exist_ok=False);save(folder/'input.json',{'id':r['id'],'text':r['input_text']})
  result={'id':r['id'],'input_text':r['input_text'],'output_text':r['input_text'],'status':'no_ready_target','source_run':source.name,'targets':[]}
  for t in r['targets']:
   if t.get('readiness')!='ready_for_generation_trial':continue
   olddir=source/'private/records'/r['id']/'targets'/t['target_id'];payload=read(olddir/'enhanced.json')
   td=folder/'targets'/t['target_id'];td.mkdir(parents=True)
   for name in ('analysis.json','trace.json','enhanced.json'):shutil.copy2(olddir/name,td/name)
   save(td/'source_link.json',{'source':str(olddir),'enhanced_sha256':sha((olddir/'enhanced.json').read_bytes())})
   try:
    resp=client.call('generation_components',COMPOSE_PROMPT,compose_payload(payload),COMPOSE_SCHEMA,td/'components_call',256,20261103);validate_schema(resp,COMPOSE_SCHEMA)
    result['status']='needs_review'
    if resp['replacement']:
     output=apply_piece(payload['text'],payload['actions'][0],resp['replacement'])
     with LOCK:checks=preservation_check(morphology,output,payload)
     result.update(output_text=output,status='generated',checks=checks)
    result['targets'].append({'target_id':t['target_id'],'rules':t['rules'],'status':result['status'],'response':resp})
   except Exception as e:result.update(status='failed',error_type=type(e).__name__,error=str(e)[:200])
  save(folder/'result.json',result);return result
 start=time.perf_counter();results=[];register_run(ROOT,out);print('RUN '+runid,flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for f in concurrent.futures.as_completed([pool.submit(execute,r) for r in old]):
   r=f.result();results.append(r);task.update(done=len(results),message=r['id']+' '+r['status']);store.task(task)
   print(json.dumps({'done':len(results),'total':32,'id':r['id'],'status':r['status'],'output':r['output_text']},ensure_ascii=False),flush=True)
 results.sort(key=lambda r:next(i for i,x in enumerate(rows) if x['id']==r['id']));save(out/'private/results.json',results)
 calls=[read(p) for p in (out/'private/records').rglob('meta.json')]
 metrics={'records':32,'analysis_calls':0,'generation_calls':len(calls),'api_attempts':len(calls),'actual_generated_outputs':sum(r['status']=='generated' for r in results),
  'valid_output_records':sum(r['status']=='generated' for r in results),'surface_warning_records':sum(bool(r.get('checks',{}).get('warnings')) for r in results),
  'wall_seconds':round(time.perf_counter()-start,3),'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},'naturalness_evaluation':'not_performed'}
 save(out/'metrics.json',metrics);save(out/'postflight.json',{'source_manifest_unchanged':sha((source/'artifact_hashes.json').read_bytes())==read(out/'freeze.json')['source_artifact_manifest_sha256'],'graph_unchanged':sha(bridge.GRAPH.read_bytes())==read(out/'freeze.json')['graph_sha256']})
 register_run(ROOT,out);save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
 task.update(status='completed',done=32,message='고정 분석·조회 재사용 생성 검사 완료');store.task(task);print(json.dumps(metrics,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
