"""One frozen experiment per command; no response-dependent retries or tuning."""
import collections,concurrent.futures,datetime,json,platform,shutil,threading,time,sys
from pipeline import *
from kg_runtime.morphology import Morphology
from kg_runtime.realization import compose
from kg_pipeline.io import Qwen,read,save,sha,load_jsonl
from kg_pipeline.runner import register_run
from research_management.core import guard_dataset
from research_management.work import WorkStore
LOCK=threading.Lock()

def execute(row,morph,graph,client,out,config,analyzer):
 folder=out/'private/records'/row['id'];folder.mkdir(parents=True,exist_ok=False)
 save(folder/'input.json',row);save(folder/'morphology.json',morph)
 result={'id':row['id'],'input_text':row['text'],'output_text':row['text'],'status':'started','targets':[], 'human_evaluation':None}
 start=time.perf_counter();patches=[]
 for target in sentence_targets(morph):
  uid=target['uid'];local=target['morph'];td=folder/'targets'/uid;td.mkdir(parents=True)
  save(td/'target.json',target);r={'target_id':uid,'span':target['original_span'],'status':'started','generation':{}}
  stage='analysis'
  try:
   schema,user=schema_and_payload(graph,local,uid,row['text'])
   raw=client.call('scoped_analysis',PROMPT,user,schema,td/'analysis_call',2048,20261103)
   validate_schema(raw,schema);stage='binding';a,tr=analyze_response(graph,raw,local,uid)
   save(td/'analysis.json',a);save(td/'trace.json',tr)
   p=tr['packet']['clauses'][0];q=tr['retrieval']['clauses'][0]
   r.update(features=a['clauses'][0]['features'],readiness=p['readiness'],query_state=q['state'],
    segmentation_state='unresolved' if a.get('adapter_diagnostics') else 'simple_sentence',projection_state='projected',
    rules=[c['rule_id'] for c in p['choices']],scope_failures=q['scope_failures'],needs_analysis=p['needs_analysis'],status='retrieved')
   if p['readiness']=='ready_for_generation_trial':
    compact,enhanced=generation_payload(a,tr,local);save(td/'compact.json',compact);save(td/'enhanced.json',enhanced)
    arms=('composer',) if config.get('realizer')=='kiwi' else (('whole','piece') if config['paired_generation'] else ('piece',))
    if config['paired_generation'] and row['id'][-1:] in ('2','4','6','8','0'):arms=tuple(reversed(arms))
    for arm in arms:
     gr={'status':'started'}
     try:
      if arm=='composer':
       with LOCK:piece,operation=compose(analyzer.kiwi,enhanced['actions'][0])
       resp={'replacement':piece,'status':'generated','operation':operation,'origin':'deterministic_Kiwi_composition'}
       save(td/'composition.json',resp)
      else:
       resp=client.call('generation_'+arm,GENERATION_PROMPT if arm=='whole' else COMPOSE_PROMPT,
        compact if arm=='whole' else compose_payload(enhanced),GENERATION if arm=='whole' else COMPOSE_SCHEMA,td/(arm+'_call'),768,20261103)
       validate_schema(resp,GENERATION if arm=='whole' else COMPOSE_SCHEMA)
       if arm=='piece':resp=dict(resp,status='generated' if resp['replacement'] else 'needs_review')
      gr.update(model_response=resp,status=resp['status'])
      if resp['status']=='generated':
       output=resp['output_text'] if arm=='whole' else apply_piece(local['text'],enhanced['actions'][0],resp['replacement'])
       with LOCK:check=preservation_check(analyzer,output,enhanced)
       gr.update(output_text=output,checks=check)
       if arm in ('piece','composer'):patches.append((target['original_span'],resp['replacement']))
     except Exception as e:gr.update(status='failed',error_type=type(e).__name__,error=str(e)[:200])
     r['generation'][arm]=gr
    r['status']='generation_attempted'
  except Exception as e:
   unsupported=stage=='binding' and str(e) in ('unsupported_predicate_morphology','unsupported_derivational_base','multiple_derivational_predicates','missing_or_multiple_final_endings')
   r.update(status='projection_unsupported' if unsupported else stage+'_failed',projection_state='unsupported' if unsupported else 'unknown',error_type=type(e).__name__,error=str(e)[:200])
  result['targets'].append(r);save(td/'result.json',r)
 # Right-to-left patches have original offsets, never the shifted output offsets.
 last=len(row['text'])+1
 for (i,j),piece in sorted(patches,reverse=True):
  if j>last:raise ValueError('overlapping_target_patches')
  result['output_text']=result['output_text'][:i]+piece+result['output_text'][j:];last=i
 failures=[r for r in result['targets'] if r['status'].endswith('_failed') or any(g['status']=='failed' for g in r['generation'].values())]
 result.update(status='completed_with_stage_errors' if failures else 'completed',generated_targets=len(patches),
  unchanged=result['output_text']==row['text'],target_count=len(result['targets']),seconds=round(time.perf_counter()-start,3),
  output_status='partial_supported_conversion' if patches else ('generation_failed_or_deferred' if any(t.get('readiness')=='ready_for_generation_trial' for t in result['targets']) else 'no_ready_target'),
  quality_evaluation='not_scored; preservation checks are not naturalness')
 save(folder/'result.json',result);return result

def main(mode):
 global PROMPT,schema_and_payload,analyze_response
 if mode.startswith('scoped'):
  import importlib.util
  spec=importlib.util.spec_from_file_location('scope_runtime',ROOT/'experiments/analyses/grammar_expansion_20261103/scope_runtime.py');runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
  PROMPT=runtime.PROMPT;schema_and_payload=runtime.schema_and_payload;analyze_response=runtime.analyze_response
 graph=read(bridge.GRAPH);analyzer=Morphology();realizer='kiwi' if mode.startswith(('composer','scoped')) else 'qwen'
 dataset_mode='dev' if mode in ('dev','composer32') else 'full50'
 if dataset_mode=='dev':
  prior=read(ROOT/'experiments/analyses/condition_bridge_20261103/private/cases.json')
  rows=[{'id':r['id'],'text':r['text']} for r in prior]
  morphs=read(ROOT/'experiments/analyses/condition_bridge_20261103/private/kiwi_inputs.json')
 else:
  rows=load_jsonl(ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl')
  rows=[{'id':r['id'],'text':r['text']} for r in rows]
  morphs={r['id']:analyzer.analyze(r['text']) for r in rows}
 client=Qwen(ROOT/'test.py',timeout=90)
 runid=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_research_loop_'+mode
 out=ROOT/'experiments/runs'/runid;out.mkdir(parents=True,exist_ok=False)
 inp=out/'private/inputs.jsonl';inp.parent.mkdir();inp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),'utf8')
 config={'phase':'development' if dataset_mode=='dev' else 'regression','dataset_role':'development' if dataset_mode=='dev' else 'regression',
  'metric_contract':'research_loop_target_preservation_v2','model_id':client.model,'kg_dataset':graph['version'],
  'input_count':len(rows),'input_sha256':sha(inp.read_bytes()),'paired_generation':dataset_mode=='dev' and realizer=='qwen','realizer':realizer,
  'arms':['composer'] if realizer=='kiwi' else (['whole','piece'] if dataset_mode=='dev' else ['piece']),'seed':20261103,'temperature':0,'top_p':1,'enable_thinking':False,
  'analysis_max_tokens':2048,'generation_max_tokens':0 if realizer=='kiwi' else 768,'workers':2,'automatic_retries':0,
  'scope_adapter':'v3_model_boundary_links' if mode.startswith('scoped') else 'v2_global_boundary_guard','comparison':'paired generation uses same observed analysis and selected graph usage; prompt and output contract change together',
  'analysis_comparison':'previous bridge run is historical, not simultaneous controlled causal evidence',
  'graph_access':'frozen JSON using real graph edges; no live Neo4j writes','reference_policy':'no reference sentences or manually mapped input IDs in model requests',
  'data_check':guard_dataset(ROOT,inp,'development' if dataset_mode=='dev' else 'regression'),'python':platform.python_version(),
  'quality_metrics':'not available; no naturalness/accuracy claims','server_revision':'not_exposed'}
 save(out/'config.json',config);save(out/'server_models.json',client.models);save(out/'private/graph.json',graph)
 save(out/'private/morphs.json',morphs)
 (out/'analysis_prompt.txt').write_text(PROMPT,'utf8');(out/'whole_prompt.txt').write_text(GENERATION_PROMPT,'utf8');(out/'piece_prompt.txt').write_text(COMPOSE_PROMPT,'utf8')
 dependencies=[HERE/'pipeline.py',HERE/'run.py',HERE/'test_pipeline.py',Path(bridge.__file__),
  ROOT/'experiments/analyses/question_pipeline_20261103/adapter.py',ROOT/'experiments/analyses/question_pipeline_20261103/contracts.py',
  ROOT/'experiments/analyses/question_refinement_20261102/query.py',ROOT/'experiments/analyses/question_refinement_20261102/sources.py',
  ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/semantic_graph.py',ROOT/'src/kg_pipeline/io.py',ROOT/'src/kg_pipeline/validation.py',ROOT/'src/kg_runtime/morphology.py',ROOT/'src/kg_runtime/realization.py',ROOT/'experiments/analyses/grammar_expansion_20261103/scope_runtime.py']
 hashes={}
 for path in dependencies:
  rel=path.relative_to(ROOT);dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);hashes[str(rel)]=sha(path.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'freeze.json',{'before_first_chat_call':True,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'input_sha256':sha(inp.read_bytes()),'graph_sha256':sha(bridge.GRAPH.read_bytes()),'config_sha256':sha((out/'config.json').read_bytes())})
 save(HERE/('private/latest_'+mode+'.json'),{'run_id':runid,'directory':str(out)})
 store=WorkStore(ROOT);task={'id':runid,'title':'개발 32건 분석·조회·생성 비교' if dataset_mode=='dev' else '기존 50건 지원범위·오류 진단',
  'actor':'Qwen + Kiwi','stage':'분석 → 조건 조회 → 생성','status':'running','done':0,'total':len(rows),'unit':'입력','message':'동결 후 실행. 정확도 평가 아님.'}
 store.task(task);register_run(ROOT,out);print('RUN '+runid,flush=True)
 start=time.perf_counter();results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  fs={pool.submit(execute,r,morphs[r['id']],graph,client,out,config,analyzer):r for r in rows}
  while fs:
   done,_=concurrent.futures.wait(fs,timeout=15,return_when=concurrent.futures.FIRST_COMPLETED)
   if not done:print('WAIT '+str(len(results))+'/'+str(len(rows)),flush=True)
   for f in done:
    row=fs.pop(f)
    try:r=f.result()
    except Exception as e:
     r={'id':row['id'],'input_text':row['text'],'output_text':None,'status':'runner_failed','error_type':type(e).__name__,'error':str(e)[:200],'targets':[]}
     save(out/'private/records'/row['id']/'result.json',r)
    results.append(r);task.update(done=len(results),message=r['id']+' / 바뀐 위치 '+str(r.get('generated_targets',0)));store.task(task)
    print(json.dumps({'done':len(results),'total':len(rows),'id':r['id'],'status':r['status'],'generated':r.get('generated_targets',0),'eta_seconds':round((time.perf_counter()-start)/len(results)*(len(rows)-len(results)))},ensure_ascii=False),flush=True)
 results.sort(key=lambda r:next(i for i,x in enumerate(rows) if x['id']==r['id']));save(out/'private/results.json',results)
 calls=[read(p) for p in (out/'private/records').rglob('meta.json')];ts=[t for r in results for t in r.get('targets',[])]
 metrics={'records':len(results),'api_attempts':len(calls),'analysis_calls':sum(c['stage']=='scoped_analysis' for c in calls),
  'generation_calls':sum(c['stage'].startswith('generation_') for c in calls),'generated_records':sum(r.get('generated_targets',0)>0 for r in results),
  'actual_generated_outputs':sum(bool(g.get('output_text')) for t in ts for g in t['generation'].values()),
  'output_records_with_patch':sum(r.get('generated_targets',0)>0 for r in results),
  'changed_records':sum(r.get('output_text') is not None and r.get('output_text')!=r.get('input_text') for r in results),
  'generation_failures':sum(g['status']=='failed' for t in ts for g in t['generation'].values()),'target_count':len(ts),
  'target_status_counts':dict(collections.Counter(t['status'] for t in ts)),
  'readiness_counts':dict(collections.Counter(t.get('readiness','not_retrieved') for t in ts)),
  'wall_seconds':round(time.perf_counter()-start,3),'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},
  'naturalness_evaluation':'not_performed','human_evaluation':'pending'}
 save(out/'metrics.json',metrics);save(out/'postflight.json',{'graph_unchanged':sha(bridge.GRAPH.read_bytes())==read(out/'freeze.json')['graph_sha256'],
  'loaded_graph_matches_snapshot':graph==read(out/'private/graph.json'),'code_unchanged':all(sha((ROOT/p).read_bytes())==h for p,h in hashes.items()),'inputs_unchanged':sha(inp.read_bytes())==config['input_sha256'],'source_count':len(rows),'result_count':len(results)})
 save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
 register_run(ROOT,out)
 task.update(status='completed',done=len(rows),message='실행 완료. 미지원과 오류·자연스러움은 별도 해석.');store.task(task)
 print(json.dumps(metrics,ensure_ascii=False),flush=True)
if __name__=='__main__':main(sys.argv[1])
