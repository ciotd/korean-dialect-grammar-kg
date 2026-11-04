"""Qwen analysis -> actual KG -> one Qwen full-output call per input."""
import collections,concurrent.futures,datetime,json,platform,shutil,sys,time,threading,re
from pathlib import Path
import runtime as rt
R=rt.ROOT;H=Path(__file__).resolve().parent
from kg_pipeline.io import Qwen,read,save,sha,load_jsonl
from kg_pipeline.validation import validate_schema
from kg_runtime.morphology import Morphology
from kg_runtime.realization import compose
from kg_pipeline.runner import register_run
from research_management.core import guard_dataset
from research_management.work import WorkStore
LOCK=threading.Lock()
DEV=[('B01','동생이 문을 열어놓고 쉬어요.'),('B02','기온이 높아지는 날에는 물을 자주 마셔요.'),('B03','수업에서 읽어 본 이야기가 생각나요.'),('B04','이 책 읽어봤어?'),('B05','작년에 사 온 모자를 써 봤어?'),('B06','가게에 가보니까 벌써 닫았네요.'),('B07','누가 왔는지 알아?'),('B08','선생님이 적으시고 계셨어요.'),('B09','이것을 고쳐놓으면 편하거든요.'),('B10','시간이 없으니까 빨리 가.'),('B11','마당이 환해지는 모습을 봤어요.'),('B12','아버지가 주무시고 있어?')]

def generation_check(text,output,actions,analyzer):
 if not actions:return {'warnings':[] if text==output else ['changed_without_supported_action'],'pieces':[],'quality':'not_evaluated'}
 ordered=sorted(actions,key=lambda a:a['span']);cursor=0;pattern='^'
 for a in ordered:
  i,j=a['span']
  if i<cursor or text[i:j]!=a['target']:raise ValueError('invalid_action_alignment')
  pattern+=re.escape(text[cursor:i])+'(.*?)';cursor=j
 pattern+=re.escape(text[cursor:])+'$';m=re.fullmatch(pattern,output,re.DOTALL)
 if not m:return {'warnings':['outside_supported_spans_changed'],'pieces':[],'quality':'not_evaluated'}
 pieces=[];warnings=[]
 for a,piece in zip(ordered,m.groups()):
  # Reuse the existing preservation inspector on one recorded action at a time.
  local_a=copy_action(a);i,j=a['span'];p={'text':text,'actions':[local_a]}
  with LOCK:check=rt.preservation_check(analyzer,text[:i]+piece+text[j:],p)
  if a.get('expected_surface') is not None and piece!=a['expected_surface']:check['warnings'].append('documented_surface_structure_mismatch')
  if not piece:check['warnings'].append('empty_replacement')
  pieces.append({'target_id':a['target_id'],'replacement':piece,'warnings':check['warnings']});warnings.extend(check['warnings'])
 return {'warnings':sorted(set(warnings)),'pieces':pieces,'quality':'surface_diagnostics_not_human_evaluation'}
def copy_action(a):return json.loads(json.dumps(a,ensure_ascii=False))

def inspect_generated(text,response,actions,analyzer):
 # A diagnostic failure must never erase a valid Qwen response.
 output=response['output_text']
 try:check=generation_check(text,output,actions,analyzer)
 except Exception as e:check={'warnings':['validation_failed'],'error_type':type(e).__name__,'error':str(e)[:200],'pieces':[]}
 if response['status']!='needs_review' and (response['status']=='unchanged')!=(output==text):check['warnings'].append('reported_status_text_disagree')
 if response['status']=='needs_review':check['warnings'].append('model_needs_review')
 return {'output_text':output,'model_status':response['status'],'unchanged':output==text,'checks':check}

def execute(row,morph,graph,client,out,analyzer):
 folder=out/'private/records'/row['id'];folder.mkdir(parents=True,exist_ok=False);save(folder/'input.json',row);save(folder/'morphology.json',morph)
 start=time.perf_counter();targets=[];actions=[];support=[]
 for target in rt.base.sentence_targets(morph):
  uid=target['uid'];local=target['morph'];td=folder/'targets'/uid;td.mkdir(parents=True);save(td/'target.json',target)
  t={'target_id':uid,'span':target['original_span'],'status':'analysis_started'}
  try:
   schema,user=rt.schema_and_payload(graph,local,uid,row['text'])
   raw=client.call('boundary_analysis',rt.PROMPT,user,schema,td/'analysis_call',3072,20261103);validate_schema(raw,schema)
   a,tr=rt.analyze_response(graph,raw,local,uid);save(td/'analysis.json',a);save(td/'trace.json',tr)
   p=tr['packet']['clauses'][0];q=tr['retrieval']['clauses'][0]
   t.update(status='retrieved',readiness=p['readiness'],query_state=q['state'],needs_analysis=p['needs_analysis'],features=a['clauses'][0]['features'],rules=[x['rule_id'] for x in p['choices']])
   if p['readiness']=='ready_for_generation_trial':
    _,enhanced=rt.generation_payload(a,tr,local);save(td/'enhanced.json',enhanced)
    action=copy_action(enhanced['actions'][0]);action.update(span=target['original_span'],target_id=uid,features=a['clauses'][0]['features'])
    action['condition_checks']=[{'condition_id':c['condition_id'],'feature':c['feature'],'observed':c['observed'],'allowed':c['allowed'],'state':c['state']} for c in q['eligible'][0]['checks']]
    # This comparison is never given to Qwen or substituted into its output.
    try:
     with LOCK:piece,operation=compose(analyzer.kiwi,enhanced['actions'][0])
     save(td/'composer_comparison.json',{'piece':piece,'operation':operation,'used_as_final_output':False,'sent_to_qwen':False})
    except Exception as e:save(td/'composer_comparison.json',{'error_type':type(e).__name__,'error':str(e)[:150],'used_as_final_output':False})
    actions.append(action)
  except Exception as e:t.update(status='analysis_or_query_failed',readiness='not_delivered',error_type=type(e).__name__,error=str(e)[:200])
  targets.append(t);save(td/'result.json',t)
  if not any(a['target_id']==uid for a in actions):support.append({'target_id':uid,'text':row['text'][slice(*target['original_span'])],'state':t.get('readiness',t['status']),'reasons':t.get('needs_analysis',[])})
 allowed=('target_id','target','span','source_morphs','stem','nominal','prefinals','source_final','rule_id','meaning','forms','composition','preserve','features','condition_checks')
 packet={'text':row['text'],'actions':[{k:a[k] for k in allowed if k in a} for a in actions],'unsupported_or_unresolved':support,'instruction':'Apply only these verified-scope actions; unsupported is not linguistically forbidden.'}
 nodes={n['id']:n for n in graph['nodes']}
 for action in packet['actions']:
  action['forms']=[f for f in action['forms'] if f.get('selected_combining_form')]
  action['structure_evidence']=[{'evidence_id':e['target'],'quote':nodes[e['target']]['properties']['quote']} for e in graph['edges'] if e['source']==action['rule_id'] and e['relation']=='SUPPORTED_BY' and e['target']=='EV_DECL_STRUCTURE']
 save(folder/'generation_packet.json',packet);save(folder/'actions_internal.json',actions)
 result={'id':row['id'],'input_text':row['text'],'output_text':None,'status':'generation_started','targets':targets,'target_count':len(targets),'supported_targets':len(actions),'output_origin':'qwen_full_sentence','human_evaluation':None}
 try:
  response=client.call('dialect_generation',rt.GENERATION_PROMPT,packet,rt.GENERATION_SCHEMA,folder/'generation_call',2048,20261103);validate_schema(response,rt.GENERATION_SCHEMA)
  result.update(inspect_generated(row['text'],response,actions,analyzer))
  result['status']='completed_with_stage_errors' if any(t['status']=='analysis_or_query_failed' for t in targets) else 'completed_with_warnings' if result['checks']['warnings'] else 'completed'
 except Exception as e:result.update(status='generation_failed',error_type=type(e).__name__,error=str(e)[:200])
 result['seconds']=round(time.perf_counter()-start,3);save(folder/'result.json',result);return result

def main(mode):
 if mode not in ('dev','full50'):raise ValueError('mode')
 graph=read(rt.bridge.GRAPH);analyzer=Morphology()
 rows=[{'id':i,'text':t} for i,t in DEV] if mode=='dev' else [{'id':r['id'],'text':r['text']} for r in load_jsonl(R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl')]
 morphs={r['id']:analyzer.analyze(r['text']) for r in rows};client=Qwen(R/'test.py',timeout=90)
 id=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_boundary_qwen_'+mode;out=R/'experiments/runs'/id;out.mkdir(parents=True,exist_ok=False)
 inp=out/'private/inputs.jsonl';inp.parent.mkdir();inp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),'utf8')
 config={'phase':'development' if mode=='dev' else 'regression','dataset_role':'development' if mode=='dev' else 'regression','metric_contract':'qwen_full_sentence_boundary_v1','model_id':client.model,'kg_dataset':graph['version'],'input_count':len(rows),'input_sha256':sha(inp.read_bytes()),'realizer':'qwen_full_sentence','composer_role':'offline_comparison_only','seed':20261103,'temperature':0,'top_p':1,'enable_thinking':False,'workers':2,'automatic_retries':0,'analysis_max_tokens':3072,'generation_max_tokens':2048,'graph_access':'frozen JSON graph; real edges; no Neo4j write','source_reference_policy':'no gold sentences or source sentence IDs in generation','comparison':'historical descriptive comparison; analysis and final generation both changed','python':platform.python_version(),'server_revision':'not_exposed','data_check':guard_dataset(R,inp,'development' if mode=='dev' else 'regression')}
 save(out/'config.json',config);save(out/'server_models.json',client.models);save(out/'private/graph.json',graph);save(out/'private/morphs.json',morphs)
 (out/'analysis_prompt.txt').write_text(rt.PROMPT,'utf8');(out/'generation_prompt.txt').write_text(rt.GENERATION_PROMPT,'utf8')
 prev=read(R/'experiments/runs/20261103T094439414985Z_condition_checked_replay50/code_hashes.json')
 deps=set([H/'runtime.py',H/'run.py',H/'test_runtime.py']+[R/p for p in prev]);hashes={}
 for p in deps:
  rel=p.relative_to(R);d=out/'code_snapshot'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);hashes[str(rel)]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'freeze.json',{'before_first_chat_call':True,'graph_sha256':sha(rt.bridge.GRAPH.read_bytes()),'config_sha256':sha((out/'config.json').read_bytes()),'input_sha256':sha(inp.read_bytes())})
 save(H/('private/latest_'+mode+'.json'),{'run_id':id,'directory':str(out)})
 store=WorkStore(R);task={'id':id,'title':'개별 경계 분석 → KG → Qwen 최종 생성','actor':'Qwen + KG / Kiwi 보조','stage':'분석·조회·Qwen 생성','status':'running','done':0,'total':len(rows),'unit':'입력','message':'모델 최종 출력은 자동 대체하지 않음'};store.task(task);register_run(R,out)
 print('RUN '+id,flush=True);start=time.perf_counter();results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(execute,r,morphs[r['id']],graph,client,out,analyzer):r for r in rows}
  for future in concurrent.futures.as_completed(futures):
   row=futures[future]
   try:res=future.result()
   except Exception as e:
    res={'id':row['id'],'input_text':row['text'],'output_text':None,'status':'runner_failed','error_type':type(e).__name__,'error':str(e)[:200],'targets':[]};save(out/'private/records'/row['id']/'result.json',res)
   results.append(res);task.update(done=len(results),message=row['id']+' '+res['status']);store.task(task)
   print(json.dumps({'done':len(results),'total':len(rows),'id':row['id'],'status':res['status'],'eta_seconds':round((time.perf_counter()-start)/len(results)*(len(rows)-len(results)))},ensure_ascii=False),flush=True)
 results.sort(key=lambda r:next(i for i,x in enumerate(rows) if x['id']==r['id']));save(out/'private/results.json',results)
 calls=[read(p) for p in (out/'private/records').rglob('meta.json')];targets=[t for r in results for t in r['targets']]
 metrics={'records':len(results),'api_attempts':len(calls),'analysis_calls':sum(c['stage']=='boundary_analysis' for c in calls),'generation_calls':sum(c['stage']=='dialect_generation' for c in calls),'valid_output_records':sum(isinstance(r.get('output_text'),str) for r in results),'changed_records':sum(r.get('output_text') is not None and r['output_text']!=r['input_text'] for r in results),'target_count':len(targets),'readiness_counts':dict(collections.Counter(t.get('readiness','not_retrieved') for t in targets)),'target_status_counts':dict(collections.Counter(t['status'] for t in targets)),'record_status_counts':dict(collections.Counter(r['status'] for r in results)),'warning_counts':dict(collections.Counter(w for r in results for w in r.get('checks',{}).get('warnings',[]))),'wall_seconds':round(time.perf_counter()-start,3),'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},'human_evaluation':'not_performed','naturalness_evaluation':'not_scored'}
 save(out/'metrics.json',metrics);save(out/'postflight.json',{'graph_unchanged':sha(rt.bridge.GRAPH.read_bytes())==read(out/'freeze.json')['graph_sha256'],'code_unchanged':all(sha((R/p).read_bytes())==h for p,h in hashes.items()),'inputs_unchanged':sha(inp.read_bytes())==config['input_sha256'],'source_count':len(rows),'result_count':len(results)})
 save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(R,out);task.update(status='completed',message='Qwen 최종 출력과 단계별 기록 저장. 자연스러움 미평가.');store.task(task)
 print(json.dumps(metrics,ensure_ascii=False),flush=True)
if __name__=='__main__':main(sys.argv[1])
