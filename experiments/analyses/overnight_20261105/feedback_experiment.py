"""Paired follow-up diagnostic; no reference-answer access, no output replacement."""
from pathlib import Path
import sys,json,datetime,time,shutil,collections,statistics
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path[:0]=[str(R/'src'),str(R/'experiments/analyses/generation_scope_20261104')]
from kg_pipeline.io import Qwen,read,save,sha,dumps
from kg_pipeline.validation import validate_schema
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
from repair_feedback import build_feedback,retry_payload
OLD=R/'experiments/analyses/generation_scope_20261104/private/refinement/20261104T083517Z'
DEADLINE=datetime.datetime(2026,11,4,23,0,tzinfo=datetime.timezone.utc)

def main():
 graph=read(OLD/'graph.json');selected=[x for x in read(OLD/'feedback_preview_v2.json') if x['feedback']['status']=='feedback_available'];assert len(selected)==6
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=R/'experiments/runs'/(stamp+'_paired_error_feedback');out.mkdir(parents=True)
 client=Qwen(R/'test.py',timeout=90);save(out/'server_models.json',client.models)
 jobs=[]
 for i,row in enumerate(selected):
  req=read(Path(row['request']));packet=json.loads(req['messages'][1]['content']);output=row['feedback']['original_output'];fb=build_feedback(graph,packet,output);assert fb==row['feedback']
  for arm in (('neutral','specific') if i%2==0 else ('specific','neutral')):
   jobs.append({'id':row['id']+'__r'+str(row['repeat'])+'__'+arm,'source_id':row['id'],'repeat':row['repeat'],'arm':arm,'input_text':packet['text'],'packet':packet,'first_output':output,'payload':retry_payload(graph,packet,output,fb,arm),'source_request':row['request'],'seed':req['seed'],'system':req['messages'][0]['content']+'\n이번 요청은 수정 요청이다. original_request 안의 text와 actions가 원래 입력과 KG 정보다. previous_output을 검토하고, failed_checks가 있으면 참고하여 문장 전체를 다시 생성한다.','schema':req['response_format']['json_schema']['schema']})
 save(out/'private/jobs.json',jobs);save(out/'private/graph.json',graph)
 config={'phase':'diagnostic','dataset_role':'regression','input_count':12,'unique_inputs':3,'first_outputs':6,'arms':['neutral','specific'],'model_id':client.model,'kg_dataset':graph.get('version'),'temperature':0,'top_p':1,'enable_thinking':False,'max_tokens':2048,'automatic_retries':0,'followup_calls_per_first_output_per_arm':1,'metric_contract':'single_action_surface_contract_not_naturalness','source_checkpoint':'42dfc8f','difference':'failed_checks only; unequal token counts','reference_answers_in_request':False,'final_writer':'Qwen'}
 save(out/'config.json',config);save(out/'freeze.json',{'before_first_call':True,'jobs_sha256':sha(dumps(jobs).encode()),'graph_sha256':sha(dumps(graph).encode()),'deadline_utc':DEADLINE.isoformat()})
 codes=[H/'feedback_experiment.py',H/'PLAN.md',R/'src/kg_pipeline/io.py',R/'experiments/analyses/generation_scope_20261104/repair_feedback.py']
 hashes={}
 for p in codes:
  q=out/'code_snapshot'/p.relative_to(R);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);hashes[str(p.relative_to(R))]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);register_run(R,out)
 save(H/'private/latest_feedback.json',{'directory':str(out)})
 store=WorkStore(R);task={'id':out.name,'title':'① 같은 실패 출력: 중립 재검토 vs 구체 오류 피드백','actor':'Qwen','stage':'생성 비교','status':'running','done':0,'total':12,'unit':'호출','unit_key':'feedback_pair'};store.task(task)
 results=[];start=time.perf_counter();consecutive=0
 for job in jobs:
  if datetime.datetime.now(datetime.timezone.utc)>=DEADLINE:break
  folder=out/'private/records'/job['id'];folder.mkdir(parents=True);save(folder/'input.json',job)
  result={k:job[k] for k in ('id','source_id','repeat','arm','input_text','first_output')};result.update(output_text=None,status='started')
  try:
   raw=client.call('feedback_generation',job['system'],job['payload'],job['schema'],folder/'generation_call',2048,job['seed']);validate_schema(raw,job['schema']);result.update(output_text=raw['output_text'],model_status=raw['status'],status='generated_requires_human_review',diagnostic=build_feedback(graph,job['packet'],raw['output_text']));consecutive=0
  except Exception as e:result.update(status='generation_failed',error_type=type(e).__name__,error=str(e)[:200]);consecutive+=1
  save(folder/'result.json',result);results.append(result);save(out/'private/results.json',results)
  task.update(done=len(results),message=job['id']);store.task(task);print(json.dumps({'done':len(results),'total':12,'id':job['id'],'output':result['output_text'],'check':result.get('diagnostic',{}).get('status'),'eta_seconds':round((time.perf_counter()-start)/len(results)*(12-len(results)))},ensure_ascii=False),flush=True)
  if consecutive>=3:break
 calls=[read(p) for p in (out/'private/records').rglob('meta.json')];byarm={}
 for arm in ('neutral','specific'):
  rows=[x for x in results if x['arm']==arm];byarm[arm]={'responses':len(rows),'contract_satisfied':sum(x.get('diagnostic',{}).get('status')=='declared_contract_satisfied' for x in rows),'check_counts':dict(collections.Counter(x.get('diagnostic',{}).get('status','generation_failed') for x in rows))}
 metrics={'records':len(results),'planned_records':12,'api_attempts':len(calls),'generation_calls':len(calls),'analysis_calls':0,'valid_output_records':sum(x['output_text'] is not None for x in results),'arms':byarm,'naturalness':'not_evaluated','reported_usage':{k:sum((x.get('usage') or {}).get(k,0) or 0 for x in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},'wall_seconds':time.perf_counter()-start}
 save(out/'metrics.json',metrics);save(out/'postflight.json',{'code_unchanged':all(sha((R/p).read_bytes())==h for p,h in hashes.items()),'completed_planned_calls':len(results)==12});save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(R,out)
 task.update(status='completed' if len(results)==12 else 'failed',message='비교 완료. 품질 평가와 구별.');store.task(task);print(json.dumps(metrics,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
