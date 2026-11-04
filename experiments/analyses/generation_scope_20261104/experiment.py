"""Controlled generation-scope comparison. Reuses r7 analysis, graph and Qwen client."""
from pathlib import Path
import sys,json,copy,datetime,time,concurrent.futures,collections,statistics,shutil,importlib.util,random,math
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import Qwen,read,save,sha,dumps
from kg_pipeline.validation import validate_schema
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
from research_management.core import guard_dataset
SOURCE=R/'experiments/runs/20261104T013633051461Z_support_expansion_full50'
BASE_PROMPT=(SOURCE/'generation_prompt.txt').read_text('utf8')
SEEDS=(20261104,20261105);ARMS=('A','B','C')
DEV=[('GS01','오늘 바람이 시원해서 기분이 좋아.'),('GS02','나는 아침에 국수를 먹었어.'),('GS03','동생은 지금 마당에서 자전거를 고쳐.'),('GS04','그 가방은 생각보다 무거워.'),('GS05','저는 어제 신청서를 작성했어요.'),('GS06','이 의자는 오래 앉아 있어도 편해요.'),('GS07','누가 현관에 택배를 놨어?'),('GS08','아버지는 저녁을 드셨어요?'),('GS09','그 상자는 책상 아래에 놓아 주세요.'),('GS10','오늘은 내가 설거지할게.'),('GS11','날씨가 좋네요. 나중에 같이 산책하자.'),('GS12','이분은 새로 오신 기사님이에요. 안내는 제가 할게요.')]
SCOPE='현재 KG가 지원한 actions 위치만 고치고 그 밖의 글자·띄어쓰기·문장부호는 유지한다. 여러 actions가 있으면 한 번에 반영해 전체 문장을 반환한다. actions가 비어 있으면 원문 전체를 그대로 출력하고 status=unchanged로 답한다.'
FORMS='음운 축약·불규칙만 적용하고 제공된 결합형 외의 방언 어미 변이를 만들지 않는다.'
OPEN='KG가 지정한 위치에서는 전달된 규칙을 적용한다. 지정되지 않은 부분 또는 actions가 빈 문장도 네가 학습한 경상도 방언 지식으로 자연스럽게 생성할 수 있다. 문장 전체의 뜻·시제·부정·높임·발화 의도와 인물·사물 정보를 보존한다. 바꿀 필요가 없는 표현은 유지해도 된다. 지식이 없다는 이유만으로 원문 유지를 강제하지 않는다.'
def policy(packet,arm):
 has=bool(packet['actions']);return 'strict' if arm=='A' or (arm=='B' and has) else 'open'
def request_parts(packet,arm,version='v2'):
 p=copy.deepcopy(packet);prompt=BASE_PROMPT
 assert SCOPE in prompt and FORMS in prompt
 if policy(p,arm)=='open':
  prompt=prompt.replace(SCOPE,OPEN).replace(FORMS,'actions에 지정된 위치에서는 음운 축약·불규칙을 적용하되 제공된 결합형 안에서 생성한다. 그 밖의 부분은 학습한 방언 지식을 사용할 수 있다.')
  p['instruction']='Apply KG actions at their specified positions; elsewhere, including empty actions, use learned Gyeongsang dialect while preserving meaning, tense, negation, politeness and speech act.'
  if version=='v2':prompt=prompt.replace('원문 밖의 뜻이나 새로운 방언 규칙은 만들지 않는다.','원문에 없는 뜻은 추가하지 않는다. KG가 지정한 위치에서는 전달된 결합형을 사용하고, 그 밖의 부분은 학습한 방언 지식을 사용할 수 있다.')
 return prompt,p
def stamp():return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
def input_lines(rows):return ''.join(json.dumps({'id':r['id'],'text':r['text']},ensure_ascii=False)+'\n' for r in rows)
def validate_packet(p):
 cursor=0;ids=[]
 for a in sorted(p['actions'],key=lambda x:x['span']):
  i,j=a['span'];assert 0<=i<j<=len(p['text']) and i>=cursor and p['text'][i:j]==a['target'];cursor=j;ids.append(a['target_id'])
 assert len(ids)==len(set(ids))
def dependency_check():
 rows=[]
 for k,v in read(SOURCE/'code_hashes.json').items():
  current=sha((R/k).read_bytes());allowed=False
  if current!=v:
   old=(SOURCE/'code_snapshot'/k).read_text('utf8');new=(R/k).read_text('utf8')
   allowed=Path(k)==Path('experiments/analyses/boundary_qwen_20261103/run.py') and new.replace(",'unit_key':'analysis_and_generation_per_input'",'')==old
  assert current==v or allowed,'unreviewed_dependency_change:'+k
  rows.append({'path':k,'source_sha256':v,'current_sha256':current,'equal':current==v,'allowed_progress_only_difference':allowed})
 return rows
def get_runtime():
 sys.path.insert(0,str(R/'experiments/analyses/support_expansion_20261104'))
 sp=importlib.util.spec_from_file_location('scope_reused_support',R/'experiments/analyses/support_expansion_20261104/run.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def frozen_files(out):
 paths=set([H/'experiment.py',H/'PLAN.md',H/'test_experiment.py',R/'src/kg_pipeline/io.py',R/'src/kg_pipeline/validation.py'])
 paths.update(R/p for p in read(SOURCE/'code_hashes.json'))
 hashes={}
 for p in sorted(paths):
  dest=out/'code_snapshot'/p.relative_to(R);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes[str(p.relative_to(R))]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes)
def finish(out,metrics):
 save(out/'metrics.json',metrics)
 save(out/'postflight.json',{'code_unchanged':all(sha((R/k).read_bytes())==v for k,v in read(out/'code_hashes.json').items()),'source_unchanged':all(sha((SOURCE/k).read_bytes())==v for k,v in read(SOURCE/'artifact_hashes.json').items())})
 save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
 register_run(R,out)
def prepare_dev(client):
 deps=dependency_check();m=get_runtime();rt=m.rt;analyzer=m.parent.Morphology();graph=read(SOURCE/'private/graph.json');assert read(rt.bridge.GRAPH)==graph
 out=R/'experiments/runs'/(stamp()+'_scope_shared_dev_analysis');out.mkdir(parents=True)
 rows=[{'id':i,'text':t} for i,t in DEV];inp=out/'private/inputs.jsonl';inp.parent.mkdir();inp.write_text(input_lines(rows),'utf8')
 check=guard_dataset(R,inp,'development');save(out/'config.json',{'phase':'development','dataset_role':'development','model_id':client.model,'input_count':len(rows),'input_sha256':sha(inp.read_bytes()),'kg_dataset':graph['version'],'purpose':'shared analysis and retrieval only; no generation','data_check':check,'automatic_retries':0})
 frozen_files(out);save(out/'dependency_check.json',deps);save(out/'private/graph.json',graph);save(out/'server_models.json',client.models);(out/'analysis_prompt.txt').write_text(rt.PROMPT,'utf8');register_run(R,out)
 store=WorkStore(R);task={'id':out.name,'title':'새 개발12문장 분석·조회 1회 공유','actor':'Qwen + 기존 r7','stage':'공유 분석','status':'running','done':0,'total':12,'unit':'문장','unit_key':'scope_shared_analysis'};store.task(task)
 results=[]
 for row in rows:
  d=out/'private/records'/row['id'];d.mkdir(parents=True);morph=analyzer.analyze(row['text']);save(d/'morphology.json',morph);actions=[];support=[];target_results=[]
  for target in rt.base.sentence_targets(morph):
   uid=target['uid'];local=target['morph'];td=d/'targets'/uid;td.mkdir(parents=True);save(td/'target.json',target)
   trr={'target_id':uid,'status':'started'}
   try:
    schema,user=rt.schema_and_payload(graph,local,uid,row['text']);raw=client.call('boundary_analysis',rt.PROMPT,user,schema,td/'analysis_call',3072,20261103);validate_schema(raw,schema)
    a,tr=rt.analyze_response(graph,raw,local,uid);save(td/'analysis.json',a);save(td/'trace.json',tr)
    p=tr['packet']['clauses'][0];q=tr['retrieval']['clauses'][0];trr.update(status='retrieved',readiness=p['readiness'],needs_analysis=p['needs_analysis'])
    if p['readiness']=='ready_for_generation_trial':
     _,enhanced=rt.generation_payload(a,tr,local);save(td/'enhanced.json',enhanced);act=copy.deepcopy(enhanced['actions'][0]);act.update(span=target['original_span'],target_id=uid,features=a['clauses'][0]['features'])
     act['condition_checks']=[{k:c[k] for k in ('condition_id','feature','observed','allowed','state','basis','evidence_ids','interpretation_evidence_ids','decision_ids') if k in c} for c in q['eligible'][0]['checks']]
     actions.append(act)
   except Exception as e:trr.update(status='analysis_failed',readiness='not_delivered',error_type=type(e).__name__,error=str(e)[:180])
   save(td/'result.json',trr);target_results.append(trr)
   if not any(x['target_id']==uid for x in actions):support.append({'target_id':uid,'text':row['text'][slice(*target['original_span'])],'state':trr['readiness'],'reasons':trr.get('needs_analysis',[])})
   if trr['status']=='analysis_failed':break
  allowed=('target_id','target','span','source_morphs','stem','nominal','prefinals','source_final','rule_id','meaning','forms','composition','preserve','features','condition_checks')
  packet={'text':row['text'],'actions':[{k:a[k] for k in allowed if k in a} for a in actions],'unsupported_or_unresolved':support,'instruction':'Apply only these verified-scope actions; unsupported is not linguistically forbidden.'}
  for act in packet['actions']:act['forms']=[f for f in act['forms'] if f.get('selected_combining_form')];act['structure_evidence']=m.select_evidence(graph,act)
  save(d/'generation_packet.json',packet);save(d/'actions_internal.json',actions);result={'id':row['id'],'input_text':row['text'],'output_text':None,'status':'analysis_only','targets':target_results};save(d/'result.json',result);results.append(result)
  task.update(done=len(results),message=row['id']+' 조회 완료');store.task(task);print('DEV_ANALYSIS',len(results),12,flush=True)
  if any(t['status']=='analysis_failed' for t in target_results):break
 failed=sum(t['status']=='analysis_failed' for r in results for t in r['targets'])
 if failed:save(out/'failure.json',{'reason':'shared_analysis_error_stop','unattempted_input_ids':[r['id'] for r in rows[len(results):]],'generation_started':False})
 save(out/'private/results.json',results);calls=[read(p) for p in (out/'private/records').rglob('meta.json')];finish(out,{'records':len(results),'planned_records':12,'analysis_calls':len(calls),'generation_calls':0,'api_attempts':len(calls),'valid_output_records':0,'analysis_failed_targets':failed,'reported_usage':{k:sum((x.get('usage') or {}).get(k,0) or 0 for x in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')}})
 failed=sum(t['status']=='analysis_failed' for r in results for t in r['targets'])
 task.update(status='failed' if failed else 'completed',message='공유 분석 오류: 생성 비교 중단' if failed else '공유 분석 완료. 생성은 별도 세조건.');store.task(task);save(H/'private/latest_dev_analysis.json',{'directory':str(out)})
 if failed:raise RuntimeError('shared_analysis_errors_no_generation:'+str(failed))
 return out
def checks(row,text):
 from importlib.util import spec_from_file_location,module_from_spec
 if not isinstance(text,str):return {'changed':None,'outside_original_actions':None,'suffix_contracts':[]}
 a=row['packet']['actions'];source=row['text'];pieces=[];outside=False
 if a:
  import re
  pattern='^';cursor=0
  for x in sorted(a,key=lambda x:x['span']):
   i,j=x['span'];assert source[i:j]==x['target'];pattern+=re.escape(source[cursor:i])+'(.*?)';cursor=j
  match=re.fullmatch(pattern+re.escape(source[cursor:])+'$',text,re.DOTALL);outside=match is None;pieces=list(match.groups()) if match else []
 else:outside=text!=source
 suffix=[]
 for k,x in enumerate(sorted(a,key=lambda x:x['span'])):
  if x['rule_id'] in ('SEM_DECL_HAEYE_EO','SEM_SUP_POLITE_Q_EO') and x['target'].endswith('요'):
   expected=x['target'][:-1]+'예';observed=pieces[k] if pieces else None
   suffix.append({'target_id':x['target_id'],'target':x['target'],'expected_structure':expected,'observed':observed,'match':observed==expected if observed is not None else None,'interpretation':'literal known composition diagnostic, not naturalness'})
 return {'changed':text!=source,'outside_original_actions':outside,'suffix_contracts':suffix}
def run(cohort):
 client=Qwen(R/'test.py',timeout=90)
 src=SOURCE if cohort=='regression' else prepare_dev(client)
 rows=[{'id':r['id'],'text':r['input_text'],'packet':read(src/'private/records'/r['id']/'generation_packet.json')} for r in read(src/'private/results.json')]
 for r in rows:
  validate_packet(r['packet'])
  for arm in ARMS:request_parts(r['packet'],arm)
 schema=read(SOURCE/'private/records/DEV002/generation_call/request.json')['response_format']['json_schema']['schema']
 batch=stamp();outdirs={};results=collections.defaultdict(list)
 for arm in ARMS:
  out=R/'experiments/runs'/(batch+'_scope_'+cohort+'_'+arm);out.mkdir();outdirs[arm]=out
  inp=out/'private/inputs.jsonl';inp.parent.mkdir();expanded=[{'id':r['id']+'__r'+str(rep),'text':r['text'],'source_id':r['id'],'repeat':rep} for rep in (1,2) for r in rows];inp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in expanded),'utf8')
  save(out/'config.json',{'phase':cohort,'dataset_role':cohort,'metric_contract':'generation_scope_diagnostic_v1','generation_policy_version':'v2','input_count':len(expanded),'unique_inputs':len(rows),'input_sha256':sha(inp.read_bytes()),'model_id':client.model,'kg_dataset':'semantic_grammar_20261104_r7','source_run':src.name,'source_results_sha256':sha((src/'private/results.json').read_bytes()),'arm':arm,'seeds':SEEDS,'temperature':0,'top_p':1,'enable_thinking':False,'max_tokens':2048,'workers':2,'analysis_calls':0,'automatic_retries':0,'final_writer':'Qwen','reference_answers_in_request':False,'data_check':guard_dataset(R,inp,cohort),'paired_request_identity':'A=B with actions; B=C without actions; independently sampled control calls'})
  save(out/'private/shared_cases.json',rows);save(out/'private/graph.json',read(SOURCE/'private/graph.json'));save(out/'response_schema.json',schema);save(out/'server_models.json',client.models);frozen_files(out)
  save(out/'freeze.json',{'before_first_call':True,'input_sha256':sha(inp.read_bytes()),'shared_packets_sha256':sha(dumps(rows).encode()),'plan_sha256':sha((H/'PLAN.md').read_bytes())});register_run(R,out)
 save(H/'private'/('latest_'+cohort+'.json'),{a:str(d) for a,d in outdirs.items()})
 jobs=[]
 for rep,seed in enumerate(SEEDS,1):
  for i,row in enumerate(rows):
   order=list(ARMS);shift=(i+rep)%3;order=order[shift:]+order[:shift];jobs.extend((a,row,rep,seed) for a in order)
 save(H/'private'/('schedule_'+batch+'.json'),[{'arm':a,'id':r['id'],'repeat':rep,'seed':seed} for a,r,rep,seed in jobs])
 store=WorkStore(R);task={'id':batch+'_scope_'+cohort,'title':'생성 범위 A/B/C 비교 · '+cohort,'actor':'Qwen','stage':'동일 지식·세 범위·두 반복','status':'running','done':0,'total':len(jobs),'unit':'호출','unit_key':'scope_generation','message':'원문 유지 강제와 전체 문장 생성 비교'};store.task(task);start=time.perf_counter()
 def execute(job):
  arm,row,rep,seed=job;out=outdirs[arm]/'private/records'/(row['id']+'__r'+str(rep));out.mkdir(parents=True);prompt,p=request_parts(row['packet'],arm);save(out/'generation_packet.json',p)
  result={'id':out.name,'source_id':row['id'],'repeat':rep,'input_text':row['text'],'output_text':None,'action_count':len(p['actions']),'effective_policy':policy(p,arm),'status':'started'}
  try:
   raw=client.call('dialect_generation',prompt,p,schema,out/'generation_call',2048,seed);validate_schema(raw,schema);text=raw['output_text'];result.update(output_text=text,model_status=raw['status'],reason=raw['reason'],status='unchanged' if text==row['text'] else 'generated_requires_human_review')
  except Exception as e:result.update(status='generation_failed',error_type=type(e).__name__,error=str(e)[:180])
  try:result['diagnostic']=checks(row,result['output_text'])
  except Exception as exc:result['diagnostic']={'changed':None if result['output_text'] is None else result['output_text']!=row['text'],'outside_original_actions':None,'suffix_contracts':[]};result['diagnostic_error']=type(exc).__name__
  save(out/'result.json',result);return arm,result
 # Bounded batches keep failures from submitting the whole experiment to a dead server.
 stop=False;consecutive=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for offset in range(0,len(jobs),2):
   for f in concurrent.futures.as_completed([pool.submit(execute,j) for j in jobs[offset:offset+2]]):
    arm,res=f.result();results[arm].append(res);consecutive=consecutive+1 if res['status']=='generation_failed' else 0
    done=sum(map(len,results.values()));failed=sum(r['status']=='generation_failed' for rs in results.values() for r in rs)
    task.update(done=done,message=arm+' '+res['id']+' '+res['status']);store.task(task);print(json.dumps({'done':done,'total':len(jobs),'arm':arm,'id':res['id'],'eta_seconds':round((time.perf_counter()-start)/done*(len(jobs)-done))},ensure_ascii=False),flush=True)
    if res.get('diagnostic_error') or consecutive>=5 or (done>=10 and failed/done>.2):stop=True
   if stop:break
 wall=time.perf_counter()-start
 for arm,out in outdirs.items():
  rs=sorted(results[arm],key=lambda x:(x['source_id'],x['repeat']));save(out/'private/results.json',rs);calls=[read(p) for p in (out/'private/records').rglob('meta.json')];times=[c['seconds'] for c in calls]
  metrics={'records':len(rs),'planned_records':len(rows)*2,'unique_inputs':len(rows),'valid_output_records':sum(isinstance(r['output_text'],str) for r in rs),'changed_records':sum(r['diagnostic']['changed'] is True for r in rs),'api_attempts':len(calls),'analysis_calls':0,'generation_calls':len(calls),'failures':sum(r['status']=='generation_failed' for r in rs),'stopped_early':stop,'wall_seconds_shared_batch':round(wall,3),'call_latency_median_seconds':statistics.median(times) if times else None,'call_latency_p95_seconds':sorted(times)[max(0,int(len(times)*.95)-1)] if times else None,'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},'naturalness':'not_evaluated'}
  if stop:save(out/'failure.json',{'reason':'predeclared_failure_stop','completed_records':len(rs),'planned_records':len(rows)*2})
  metrics['planned_unique_inputs']=len(rows);metrics['observed_unique_inputs']=len({r['source_id'] for r in rs});metrics['model_status_counts']=dict(collections.Counter(r.get('model_status','no_valid_response') for r in rs));metrics['call_latency_p95_seconds']=sorted(times)[max(0,math.ceil(len(times)*.95)-1)] if times else None;metrics['p95_definition']='nearest_rank_ceil';finish(out,metrics);print(arm,json.dumps(metrics,ensure_ascii=False),flush=True)
 task.update(status='failed' if stop else 'completed',message='중단 조건 도달' if stop else '비교 완료. 변경 수는 자연스러움 아님.');store.task(task)
 if stop:raise SystemExit('Experiment stopped: inspect saved failures, no automatic retries')
if __name__=='__main__':run(sys.argv[1])
