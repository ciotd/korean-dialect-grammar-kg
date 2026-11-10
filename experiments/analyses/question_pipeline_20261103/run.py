"""Paired diagnostic: frozen manual vs Qwen+Kiwi analysis, same KG/generator."""
import collections,concurrent.futures,copy,datetime,importlib.metadata,json,platform,shutil,sys,time
from pathlib import Path
from adapter import HERE,ROOT,GRAPH,RuntimeReader,adapt,compact_packet,check_output,compact_morph
from contracts import ANALYSIS,GENERATION,ANALYSIS_PROMPT,GENERATION_PROMPT
from kg_pipeline.io import Qwen,read,save,sha,dumps
from kg_runtime.morphology import Morphology
from kg_pipeline.runner import register_run,metrics
from research_management.core import guard_dataset
from research_management.work import WorkStore
from kg_pipeline.validation import validate_schema
SOURCE=ROOT/'experiments/analyses/question_refinement_20261102/private/development.json'
REVIEW=ROOT/'experiments/analyses/question_human_review_20261102/private/review_set.json'

def process_pair(row,morph,client,graph,out,config):
 qid=row['id'];text=row['analysis']['text'];records={}
 for arm in ('model','manual'):
  rid=qid+'_'+arm;folder=out/'private/records'/rid;folder.mkdir(parents=True,exist_ok=False)
  save(folder/'input.json',{'id':rid,'source_case':qid,'text':text,'condition':arm});save(folder/'morphology.json',morph)
  records[arm]={'id':rid,'source_case':qid,'condition':arm,'input_text':text,'output_text':None,'status':'started','stage_seconds':{},'calls':[],'human_evaluation':None}
 mfolder=out/'private/records'/records['model']['id'];raw=None;error=None;t=time.perf_counter()
 try:
  raw=client.call('question_analysis',ANALYSIS_PROMPT,{'text':text,'words':compact_morph(morph)},ANALYSIS,mfolder/'analysis_call',config['analysis_max_tokens'],config['seed'])
  validate_schema(raw,ANALYSIS)
 except Exception as e:error={'error_type':type(e).__name__,'error':str(e)[:300]}
 records['model']['stage_seconds']['analysis']=time.perf_counter()-t
 # Alternate generation-arm order to reduce fixed order effects. No retries.
 order=('manual','model') if int(qid[1:])%2 else ('model','manual')
 for arm in order:
  result=records[arm];folder=out/'private/records'/result['id'];start=time.perf_counter();stage='analysis'
  try:
   if arm=='model':
    if error:raise ValueError('model_analysis_call_failed:'+error['error_type']+':'+error['error'])
    analysis=adapt(raw,morph);result['analysis_ambiguity']=raw['ambiguity']
   else:
    analysis=copy.deepcopy(row['analysis'])
    if qid=='Q15':
     analysis['clauses'][0]['features']['polarity']='negative'
     save(folder/'manual_correction.json',{'field':'polarity','before':'positive','after':'negative','basis':'안 와 explicit negation; corrected in this run only'})
   save(folder/'analysis.json',analysis);reader=RuntimeReader(graph,morph);reader.validate(analysis)
   save(folder/'analysis_checks.json',{'valid_contract':True,'origin':analysis['origin'],'semantic_truth_verified':False})
   stage='retrieval';t=time.perf_counter();retrieval=reader.query(analysis);packet=reader.packet(analysis,retrieval)
   save(folder/'retrieval_raw.json',retrieval);save(folder/'reference_packet_full.json',packet)
   payload=compact_packet(analysis,packet,morph);save(folder/'reference_packet.json',payload)
   result['stage_seconds'][stage]=time.perf_counter()-t
   result.update(rule_ids=[x['rule_id'] for x in payload['actions']],readiness=[c['readiness'] for c in packet['clauses']],
    needs_analysis=[x for c in packet['clauses'] for x in c['needs_analysis']],query_state=[c['state'] for c in retrieval['clauses']],
    feature_values=analysis['clauses'][0]['features'],target=analysis['clauses'][0]['target_text'],
    payload_sha256=sha(dumps(payload).encode()),raw_chars=len(dumps(packet)),packet_chars=len(dumps(payload)))
   if not payload['actions']:
    result.update(status='needs_review',generation_call_skipped=True,reason='No ready action: '+','.join(result['readiness']))
   else:
    stage='generation';t=time.perf_counter()
    gen=client.call('question_generation',GENERATION_PROMPT,payload,GENERATION,folder/'generation_call',config['generation_max_tokens'],config['seed'])
    validate_schema(gen,GENERATION);result['stage_seconds'][stage]=time.perf_counter()-t
    checks=check_output(text,gen['output_text'],payload);save(folder/'generation_checks.json',checks)
    result.update(output_text=gen['output_text'],model_generation_status=gen['status'],reason=gen['reason'],warnings=checks['warnings'],
     status='needs_review' if gen['status']=='needs_review' else 'unchanged' if checks['unchanged'] else 'generated_requires_human_review')
  except Exception as e:result.update(status=stage+'_failed',error_type=type(e).__name__,error=str(e)[:400])
  result['total_seconds']=round(time.perf_counter()-start+result['stage_seconds'].get('analysis',0),4)
  result['calls']=[read(p) for p in sorted(folder.glob('*_call/meta.json'))];save(folder/'result.json',result)
 return [records['manual'],records['model']]

def main():
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');runid=stamp+'_question_paired_development'
 out=ROOT/'experiments/runs'/runid;out.mkdir(parents=True,exist_ok=False);(out/'private').mkdir()
 rows=read(SOURCE);graph=read(GRAPH);model=Qwen(ROOT/'test.py',timeout=90)
 inputrows=[{'id':r['id']+'_'+arm,'source_case':r['id'],'condition':arm,'text':r['analysis']['text']} for r in rows for arm in ('manual','model')]
 inp=out/'private/inputs.jsonl';inp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in inputrows),encoding='utf8')
 config={'phase':'development','dataset_role':'development','metric_contract':'paired_question_diagnostic_v1','model_id':model.model,
  'kg_dataset':graph['version'],'input_count':len(inputrows),'distinct_source_cases':len(rows),'input_sha256':sha(inp.read_bytes()),
  'seed':20261103,'temperature':0,'top_p':1,'enable_thinking':False,'analysis_max_tokens':2048,'generation_max_tokens':1024,'timeout_seconds':90,
  'workers':2,'automatic_retries':0,'conditions':['manual','model'],'question_context':'model receives text+Kiwi only; manual meanings are hypotheses, not uniquely inferable text gold',
  'generation_payload':'same compact fields in both arms; native accepted answers/alternatives never supplied',
  'knowledge_access':'frozen JSON graph via existing edge reader; not live Neo4j','Q16':'duplicate missing-field technical case, not independent linguistic item',
  'manual_corrections':[{'id':'Q15','field':'polarity','from':'positive','to':'negative'}],
  'python':platform.python_version(),'kiwipiepy':importlib.metadata.version('kiwipiepy'),
  'dataset_check':guard_dataset(ROOT,inp,'development'),'model_checkpoint_revision':'not_exposed_by_server','vllm_version':'not_exposed_by_server'}
 save(out/'config.json',config);save(out/'server_models.json',model.models)
 save(out/'analysis.schema.json',ANALYSIS);save(out/'generation.schema.json',GENERATION)
 (out/'analysis_prompt.txt').write_text(ANALYSIS_PROMPT,encoding='utf8');(out/'generation_prompt.txt').write_text(GENERATION_PROMPT,encoding='utf8')
 save(out/'validation_contract.json',{'analysis':'JSON schema + word ID/graph contract + Kiwi agreement','generation':'JSON schema + target/suffix warnings, no output repair','quality':'not scored by model','blocked_outputs':'null, not claimed as copied model output'})
 frozen={str(p):sha(p.read_bytes()) for p in (SOURCE,GRAPH,REVIEW)};save(out/'kg_hashes.json',frozen)
 save(out/'private/manual_source.json',rows);save(out/'private/graph.json',graph)
 paths=list(HERE.glob('*.py'))+[ROOT/'src/kg_pipeline/io.py',ROOT/'src/kg_pipeline/validation.py',ROOT/'src/kg_runtime/morphology.py',ROOT/'experiments/analyses/question_refinement_20261102/query.py',ROOT/'experiments/analyses/question_refinement_20261102/sources.py',ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/semantic_graph.py']
 hashes={}
 for p in paths:
  rel=p.relative_to(ROOT);dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes[str(rel)]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_first_chat_call':True,'code_sha256':sha((out/'code_hashes.json').read_bytes()),'config_sha256':sha((out/'config.json').read_bytes())})
 save(HERE/'private/latest_run.json',{'run_id':runid,'directory':str(out)})
 store=WorkStore(ROOT);task={'id':runid,'title':'질문 KG 모델·수작업 분석 비교 실험','actor':'Qwen + Kiwi','stage':'분석·조회·두 경로 생성','status':'running','done':0,'total':len(rows),'unit':'입력 쌍 (실패 포함)','message':'실험 준비'}
 store.task(task);register_run(ROOT,out);print('RUN '+str(out),flush=True)
 start=time.perf_counter();m=Morphology();morphs={r['id']:m.analyze(r['analysis']['text']) for r in rows};save(out/'private/kiwi_inputs.json',morphs)
 # Distinct connectivity/interface smoke; its output is not used for tuning.
 smoke=m.analyze('물이 차가워?');smoke_dir=out/'private/smoke';smoke_ok=False
 try:
  raw=model.call('question_analysis',ANALYSIS_PROMPT,{'text':smoke['text'],'words':compact_morph(smoke)},ANALYSIS,smoke_dir/'analysis_call',2048,config['seed']);validate_schema(raw,ANALYSIS)
  a=adapt(raw,smoke);reader=RuntimeReader(graph,smoke);q=reader.query(a);p=reader.packet(a,q);payload=compact_packet(a,p,smoke)
  save(smoke_dir/'trace.json',{'analysis':a,'query':q,'packet':p,'payload':payload})
  if payload['actions']:
   gen=model.call('question_generation',GENERATION_PROMPT,payload,GENERATION,smoke_dir/'generation_call',1024,config['seed']);validate_schema(gen,GENERATION)
  smoke_ok=True
 except Exception as e:
  save(out/'preflight_failure.json',{'stage':'smoke','error_type':type(e).__name__,'error':str(e)[:300]})
  task.update(status='failed',message='소규모 연결 시험 실패; 본실험 미실행');store.task(task);register_run(ROOT,out);print('SMOKE_FAILED',type(e).__name__,flush=True);return
 save(out/'preflight.json',{'server_connected':True,'smoke_interface_passed':smoke_ok,'kg_read_only':True})
 results=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  pending={pool.submit(process_pair,r,morphs[r['id']],model,graph,out,config):r['id'] for r in rows}
  while pending:
   done,_=concurrent.futures.wait(pending,timeout=15,return_when=concurrent.futures.FIRST_COMPLETED)
   if not done:store.task(task);print('HEARTBEAT '+str(task['done'])+'/'+str(len(rows)),flush=True)
   for f in done:
    qid=pending.pop(f);pair=f.result();results.extend(pair);task['done']+=1;task['message']=qid+' · '+' / '.join(r['condition']+':'+r['status'] for r in pair);store.task(task)
    print(dumps({'done':task['done'],'total':len(rows),'id':qid,'results':[{k:r.get(k) for k in ('condition','status','output_text','needs_analysis','warnings')} for r in pair]}),flush=True)
 results.sort(key=lambda r:(r['source_case'],r['condition']));save(out/'private/results.json',results)
 summary=metrics(results,time.perf_counter()-start);summary['wall_includes_smoke']=True
 summary['by_condition']={arm:metrics([r for r in results if r['condition']==arm],time.perf_counter()-start) for arm in ('manual','model')}
 summary['smoke_calls']=[read(p) for p in smoke_dir.glob('*_call/meta.json')];summary['total_api_attempts_including_smoke']=summary['api_attempts']+len(summary['smoke_calls'])
 save(out/'metrics.json',summary);save(out/'postflight.json',{'kg_and_input_files_preserved':all(sha(Path(k).read_bytes())==v for k,v in frozen.items()),'all_pairs_recorded':len(results)==32})
 save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
 register_run(ROOT,out);task.update(status='completed',message='16입력×두경로 완료. 원문 유지/보류/실패 구분. 결과 분석 대기.');store.task(task)
 print('COMPLETE '+runid,flush=True)
if __name__=='__main__':main()
