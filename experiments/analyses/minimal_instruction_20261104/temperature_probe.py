"""Three-arm, repeated instruction ablation; no analysis rerun or gold delivery."""
from pathlib import Path
import sys,json,copy,collections,datetime,time,concurrent.futures,shutil,random
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import read,save,sha
from temperature_transport import TemperatureQwen as Qwen
from kg_pipeline.validation import validate_schema
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
SOURCE=R/'experiments/runs/20261104T013633051461Z_support_expansion_full50'
RULES={'SEM_DECL_HAEYE_EO','SEM_SUP_POLITE_Q_EO'}
SHORT='''지정된 위치의 글자만 수정하는 작업을 수행한다. actions의 instruction을 그대로 따른다. 그 밖의 글자·띄어쓰기·문장부호는 보존한다. 최종 문장 전체를 output_text에 적는다. 변경했으면 status=generated, 그대로면 unchanged, 수행할 수 없으면 needs_review. reason은 짧게 적는다. JSON만 출력한다.'''
INSTRUCTION="이 target 어절의 맨 끝 '요' 한 글자만 '예'로 바꾼다. 그 앞의 모든 글자와 지정 위치 밖의 원문은 그대로 유지한다."
def cases():
 rows=[]
 for row in read(SOURCE/'private/results.json'):
  packet=read(SOURCE/'private/records'/row['id']/'generation_packet.json')
  for a in packet['actions']:
   if a['rule_id'] not in RULES:continue
   i,j=a['span'];assert row['input_text'][i:j]==a['target'] and a['target'].endswith('요')
   rows.append({'id':row['id']+'__'+a['target_id'],'source_id':row['id'],'target_id':a['target_id'],'text':row['input_text'],'action':a})
 assert len(rows)==9;return rows
def payload(row,arm):
 a={k:copy.deepcopy(row['action'][k]) for k in ('target_id','target','span')};a['instruction']=INSTRUCTION
 if arm=='C':a={**copy.deepcopy(row['action']),**a}
 return {'text':row['text'],'actions':[a]}
def evaluate(row,text):
 i,j=row['action']['span'];expected=row['text'][:j-1]+'예'+row['text'][j:]
 if not isinstance(text,str):return {'instruction_match':False,'category':'no_valid_output'}
 return {'instruction_match':text==expected,'category':'exact_instruction_followed' if text==expected else 'unchanged' if text==row['text'] else 'instruction_violation'}
def main():
 rows=cases();source_prompt=(SOURCE/'generation_prompt.txt').read_text('utf8');schema=read(SOURCE/'private/records'/rows[0]['source_id']/'generation_call/request.json')['response_format']['json_schema']['schema'];prompts={'T0':source_prompt,'T7':source_prompt}
 assert all(payload(r,'A')==payload(r,'B') for r in rows)
 client=Qwen(R/'test.py',timeout=90);stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');outdirs={};results=collections.defaultdict(list)
 for arm in prompts:
  d=R/'experiments/runs'/(stamp+'_temperature_only_'+arm);d.mkdir(parents=True);outdirs[arm]=d
  inp=d/'private/inputs.jsonl';inp.parent.mkdir();expanded=[{'id':r['id']+'__r'+str(rep),'source_id':r['id'],'repeat':rep,'text':r['text']} for rep in (1,2,3) for r in rows];inp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in expanded),'utf8')
  save(d/'config.json',{'phase':'regression_diagnostic','dataset_role':'regression_subset','metric_contract':'literal_suffix_instruction_v1','input_count':27,'unique_positions':9,'repeats':3,'input_sha256':sha(inp.read_bytes()),'model_id':client.model,'kg_dataset':'semantic_grammar_20261104_r7','source_run':SOURCE.name,'source_results_sha256':sha((SOURCE/'private/results.json').read_bytes()),'arm':arm,'temperature':0 if arm=='T0' else 0.7,'top_p':1,'seeds':[20261104,20261105,20261106],'enable_thinking':False,'workers':2,'max_tokens':2048,'analysis_calls':0,'automatic_retries':0,'final_writer':'Qwen','reference_answers_in_request':False,'comparison':'T0/T7 same C messages/schema/settings except temperature; paired seeds across three repetitions','data_check':{'records':27,'unique_positions':9,'source_records':50,'role':'regression_positions_repeated_not_new_independent_dataset'}})
  save(d/'server_models.json',client.models);save(d/'private/cases.json',rows);(d/'generation_prompt.txt').write_text(prompts[arm],'utf8');save(d/'response_schema.json',schema)
  files=[H/'temperature_probe.py',H/'temperature_transport.py',H/'TEMPERATURE_PLAN.md',H/'private/server_launch_20261104.json',R/'src/kg_pipeline/io.py',R/'src/kg_pipeline/validation.py'];hashes={}
  for f in files:
   rel=f.relative_to(R);target=d/'code_snapshot'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target);hashes[str(rel)]=sha(f.read_bytes())
  save(d/'code_hashes.json',hashes);save(d/'freeze.json',{'before_first_call':True,'input_sha256':sha(inp.read_bytes()),'prompt_sha256':sha(prompts[arm].encode())});register_run(R,d)
 save(H/'private/latest_temperature.json',{a:str(d) for a,d in outdirs.items()});task={'id':stamp+'_minimal_instruction','title':'동일KG·동일지시 temperature 단독 비교','actor':'Qwen','stage':'9위치 × 2조건 × 3seed','status':'running','done':0,'total':54,'unit':'호출','unit_key':'single_generation','message':'문법 선택 고정·완성 답안 미전달'};store=WorkStore(R);store.task(task);start=time.perf_counter()
 def execute(arm,row,rep):
  id=row['id']+'__r'+str(rep);d=outdirs[arm]/'private/records'/id;d.mkdir(parents=True);p=payload(row,'C');save(d/'generation_packet.json',p);save(d/'input.json',{'id':id,'text':row['text']});r={'id':id,'source_id':row['id'],'repeat':rep,'input_text':row['text'],'output_text':None,'status':'started'}
  try:
   raw=client.call('dialect_generation',prompts[arm],p,schema,d/'generation_call',2048,20261103+rep,temperature=0 if arm=='T0' else 0.7);validate_schema(raw,schema);r.update(output_text=raw['output_text'],model_status=raw['status'],status='completed')
  except Exception as exc:r.update(status='generation_failed',error_type=type(exc).__name__,error=str(exc)[:180])
  r['diagnostic']=evaluate(row,r['output_text']);save(d/'result.json',r);return arm,r
 jobs=[]
 for rep in (1,2,3):
  for i,row in enumerate(rows):
   order=['T0','T7'];shift=(rep+i)%2;order=order[shift:]+order[:shift]
   jobs.extend((a,row,rep) for a in order)
 save(H/'private'/('schedule_'+stamp+'.json'),[{'arm':a,'source_id':r['id'],'repeat':n} for a,r,n in jobs])
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  fs=[pool.submit(execute,*job) for job in jobs]
  for f in concurrent.futures.as_completed(fs):
   arm,r=f.result();results[arm].append(r);done=sum(map(len,results.values()));task.update(done=done,message=arm+' '+r['id']+' '+r['diagnostic']['category']);store.task(task);print(json.dumps({'done':done,'total':54,'arm':arm,'id':r['id'],'match':r['diagnostic']['instruction_match'],'eta_seconds':round((time.perf_counter()-start)/done*(54-done))},ensure_ascii=False),flush=True)
 for arm,d in outdirs.items():
  rs=sorted(results[arm],key=lambda r:(r['source_id'],r['repeat']));save(d/'private/results.json',rs);calls=[read(p) for p in (d/'private/records').rglob('meta.json')]
  metrics={'records':len(rs),'unique_positions':9,'repeats':3,'valid_output_records':sum(isinstance(r['output_text'],str) for r in rs),'api_attempts':len(calls),'analysis_calls':0,'generation_calls':len(calls),'instruction_matches':sum(r['diagnostic']['instruction_match'] for r in rs),'category_counts':dict(collections.Counter(r['diagnostic']['category'] for r in rs)),'wall_seconds_shared_batch':round(time.perf_counter()-start,3),'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},'naturalness':'not_evaluated'}
  save(d/'metrics.json',metrics);hashes=read(d/'code_hashes.json');save(d/'postflight.json',{'code_unchanged':all(sha((R/f).read_bytes())==v for f,v in hashes.items()),'source_unchanged':sha((SOURCE/'private/results.json').read_bytes())==read(d/'config.json')['source_results_sha256'],'input_unchanged':sha((d/'private/inputs.jsonl').read_bytes())==read(d/'config.json')['input_sha256']});save(d/'artifact_hashes.json',{str(p.relative_to(d)):sha(p.read_bytes()) for p in d.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(R,d);print(arm,json.dumps(metrics,ensure_ascii=False))
 task.update(done=54,status='completed',message='온도 단독 비교 완료. 자연스러움 평가 아님.');store.task(task)
if __name__=='__main__':main()
