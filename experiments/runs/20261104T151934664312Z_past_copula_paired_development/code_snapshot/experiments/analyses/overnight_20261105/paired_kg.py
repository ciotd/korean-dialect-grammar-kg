"""Freeze shared analysis; compare r7 and one candidate KG with the existing writer."""
from pathlib import Path
import sys,importlib.util,copy,datetime,time,collections,shutil,json
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path[:0]=[str(H),str(R/'src')]
import candidate_runtime as rt
from kg_pipeline.io import Qwen,read,save,sha,dumps
from kg_pipeline.validation import validate_schema
from kg_pipeline.runner import register_run
from kg_runtime.morphology import Morphology
from research_management.work import WorkStore
from research_management.core import guard_dataset
DEADLINE=datetime.datetime(2026,11,4,23,tzinfo=datetime.timezone.utc)
DEV=[('CP01','작년에는 이곳이 도서관이었어요.'),('CP02','그때 제 직업은 요리사였어요.'),('CP03','방금 들린 소리는 경보였어요.'),('CP04','그 사람은 당시 신입 직원이었어요.'),('CP05','그건 제 실수가 아니었어요.'),('CP06','오늘 모임은 공식 행사가 아니었어요.'),('CP07','저 건물은 처음부터 창고가 아니었어요.'),('CP08','그때는 쉬는 시간이 아니었어요.'),('CP09','지금은 쉬는 시간이에요.'),('CP10','이건 제 우산이 아니에요.'),('CP11','어제 그분이 당직 의사였어요?'),('CP12','할아버지는 예전에 교장 선생님이셨어요.'),('CP13','저는 어제 물건을 정리했어요.'),('CP14','오늘 공기가 차가워요.'),('CP15','문을 조용히 닫아 주세요.'),('CP16','그 사람은 신입 직원이었어.')]

def packet_from_targets(text,targets,raws,graph):
 actions=[];support=[];traces=[]
 for target,raw in zip(targets,raws):
  uid=target['uid'];local=target['morph'];a,tr=rt.analyze_response(graph,raw,local,uid);p=tr['packet']['clauses'][0];q=tr['retrieval']['clauses'][0]
  traces.append({'target':target,'analysis':a,'trace':tr})
  if p['readiness']=='ready_for_generation_trial':
   _,en=rt.generation_payload(a,tr,local);act=copy.deepcopy(en['actions'][0]);act.update(span=target['original_span'],target_id=uid,features=a['clauses'][0]['features']);act['condition_checks']=[{k:c[k] for k in ('condition_id','feature','observed','allowed','state','basis','evidence_ids','interpretation_evidence_ids','decision_ids') if k in c} for c in q['eligible'][0]['checks']];actions.append(act)
  else:support.append({'target_id':uid,'text':text[slice(*target['original_span'])],'state':p['readiness'],'reasons':p['needs_analysis']})
 fields=('target_id','target','span','source_morphs','stem','nominal','prefinals','source_final','rule_id','meaning','forms','composition','preserve','features','condition_checks')
 packet={'text':text,'actions':[{k:a[k] for k in fields if k in a} for a in actions],'unsupported_or_unresolved':support,'instruction':'Apply only these verified-scope actions; unsupported is not linguistically forbidden.'}
 ns={n['id']:n for n in graph['nodes']}
 for a in packet['actions']:
  a['forms']=[f for f in a['forms'] if f.get('selected_combining_form')]
  rp=ns[a['rule_id']]['properties'];evs=rp.get('delivery_evidence_ids') if a['rule_id'].startswith('SEM_SUP_') else ['EV_DECL_STRUCTURE'] if any(e['source']==a['rule_id'] and e['relation']=='SUPPORTED_BY' and e['target']=='EV_DECL_STRUCTURE' for e in graph['edges']) else []
  a['structure_evidence']=[{'evidence_id':eid,'quote':ns[eid]['properties']['quote'],'document_id':ns[eid]['properties'].get('document_id'),'pdf_page':ns[eid]['properties'].get('pdf_page'),'role':'primary' if eid in rp.get('primary_evidence_ids',[]) else 'supporting','source_family':ns[eid]['properties'].get('source_family')} for eid in evs]
 return packet,traces,actions

def finish(out,results,start,planned):
 save(out/'private/results.json',results);calls=[read(p) for p in (out/'private/records').rglob('meta.json')]
 metrics={'records':len(results),'planned_inputs':planned,'api_attempts':len(calls),'analysis_calls':sum(c['stage']=='boundary_analysis' for c in calls),'generation_calls':sum(c['stage']=='dialect_generation' for c in calls),'valid_output_records':sum(isinstance(x.get('output_text'),str) for x in results),'arm_counts':dict(collections.Counter(x['arm'] for x in results)),'failure_count':sum(x['status']=='failed' for x in results),'naturalness':'not_evaluated','wall_seconds':time.perf_counter()-start,'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')}}
 save(out/'metrics.json',metrics);save(out/'postflight.json',{'code_unchanged':all(sha((R/p).read_bytes())==h for p,h in read(out/'code_hashes.json').items()),'graph_unchanged':{arm:sha(Path(p).read_bytes())==read(out/'freeze.json')['graph_hashes'][arm] for arm,p in read(out/'config.json')['graph_paths'].items()}});save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(R,out);print(json.dumps(metrics,ensure_ascii=False),flush=True)

def main(mode='development'):
 graphs={'r7':read(R/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json'),'r10':read(rt.GRAPH)}
 rows=[{'id':i,'text':t} for i,t in DEV] if mode=='development' else [json.loads(l) for l in (R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl').read_text('utf8').splitlines() if l.strip()]
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=R/'experiments/runs'/(stamp+'_past_copula_paired_'+mode);out.mkdir(parents=True);(out/'private').mkdir();inp=out/'private/inputs.jsonl';inp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
 guard=guard_dataset(R,inp,mode);analyzer=Morphology();client=Qwen(R/'test.py',timeout=90)
 paths={'r7':str(R/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json'),'r10':str(rt.GRAPH)}
 save(out/'config.json',{'phase':mode,'dataset_role':mode,'input_count':len(rows),'model_id':client.model,'kg_dataset':'r7_vs_r10_shared_analysis','graph_paths':paths,'final_writer':'Qwen','arms':['r7','r10'],'analysis_shared':True,'automatic_retries':0,'seed':20261103,'temperature':0,'top_p':1,'enable_thinking':False,'reference_answers_in_request':False,'data_check':guard,'input_sha256':sha(inp.read_bytes()),'metric_contract':'paired_kg_support_and_generation_not_human_quality'})
 save(out/'server_models.json',client.models)
 for arm,g in graphs.items():save(out/'private'/('graph_'+arm+'.json'),g)
 deps={H/'paired_kg.py',H/'candidate_runtime.py',H/'build_past_graph.py',H/'PLAN.md',H/'test_candidate.py',R/'src/kg_pipeline/io.py',R/'experiments/analyses/generation_scope_20261104/repair_feedback.py',R/'src/kg_pipeline/validation.py',R/'src/kg_pipeline/runner.py'}
 deps.update(R/p for p in read(R/'experiments/runs/20261104T013633051461Z_support_expansion_full50/code_hashes.json'))
 hashes={}
 for p in deps:
  rel=p.relative_to(R);dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes[str(rel)]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'freeze.json',{'before_first_call':True,'graph_hashes':{a:sha(Path(p).read_bytes()) for a,p in paths.items()},'inputs_sha256':sha(inp.read_bytes())});save(H/'private'/('latest_past_'+mode+'.json'),{'directory':str(out)});register_run(R,out)
 task={'id':out.name,'title':'② 과거·부정 계사 KG 전후 비교','actor':'Kiwi + Qwen + KG','stage':mode,'status':'running','done':0,'total':len(rows),'unit':'입력','unit_key':'paired_past_kg'};store=WorkStore(R);store.task(task);results=[];start=time.perf_counter();failed_inputs=0;consecutive_failures=0
 for i,row in enumerate(rows):
  if datetime.datetime.now(datetime.timezone.utc)>=DEADLINE:break
  rd=out/'private/records'/row['id'];rd.mkdir();morph=analyzer.analyze(row['text']);save(rd/'morphology.json',morph);targets=rt.base.sentence_targets(morph);raws=[]
  try:
   for target in targets:
    schema,user=rt.schema_and_payload(graphs['r10'],target['morph'],target['uid'],row['text']);s0,u0=rt.schema_and_payload(graphs['r7'],target['morph'],target['uid'],row['text']);assert schema==s0 and user==u0,'analysis_contract_changed_between_graphs'
    raw=client.call('boundary_analysis',rt.PROMPT,user,schema,rd/'analysis'/target['uid'],3072,20261103);validate_schema(raw,schema);raws.append(raw)
  except Exception as e:
   failed_inputs+=1;results.append({'id':row['id'],'arm':'shared_analysis','input_text':row['text'],'output_text':None,'status':'failed','error':type(e).__name__+':'+str(e)[:160]});save(rd/'failure.json',results[-1]);save(out/'private/results.json',results);consecutive_failures+=1;task.update(done=i+1,message=row['id']+' analysis failed');store.task(task)
   if consecutive_failures>=5 or (i>=9 and failed_inputs/(i+1)>.2):break
   continue
  consecutive_failures=0
  for arm in (('r7','r10') if i%2==0 else ('r10','r7')):
   ad=rd/arm;ad.mkdir();result={'id':row['id']+'__'+arm,'source_id':row['id'],'arm':arm,'input_text':row['text'],'output_text':None,'status':'started'}
   try:
    packet,traces,internal=packet_from_targets(row['text'],targets,raws,graphs[arm]);save(ad/'generation_packet.json',packet);save(ad/'traces.json',traces);save(ad/'actions_internal.json',internal)
    response=client.call('dialect_generation',rt.GENERATION_PROMPT,packet,rt.GENERATION_SCHEMA,ad/'generation_call',2048,20261103);validate_schema(response,rt.GENERATION_SCHEMA)
    result.update(status='generated_requires_human_review',output_text=response['output_text'],model_status=response['status'],rule_ids=[a['rule_id'] for a in packet['actions']],supported_targets=len(packet['actions']),target_count=len(targets),readiness=[t['trace']['packet']['clauses'][0]['readiness'] for t in traces])
    # Read-only declared contract inspector, never rewrite output.
    from importlib.util import spec_from_file_location,module_from_spec
    s=spec_from_file_location('offline_fb',R/'experiments/analyses/generation_scope_20261104/repair_feedback.py');fb=module_from_spec(s);s.loader.exec_module(fb);result['diagnostic']=fb.build_feedback(graphs[arm],packet,response['output_text'])
   except Exception as e:result.update(status='failed',error=type(e).__name__+':'+str(e)[:180])
   save(ad/'result.json',result);results.append(result);print(json.dumps({'id':row['id'],'arm':arm,'output':result['output_text'],'rules':result.get('rule_ids',[]),'status':result['status']},ensure_ascii=False),flush=True)
  save(out/'private/results.json',results);task.update(done=i+1,message=row['id']);store.task(task)
  if i>=9 and sum(x['status']=='failed' for x in results)/len(results)>.2:break
 finish(out,results,start,len(rows));task.update(status='completed' if task['done']==len(rows) else 'failed',message='공유 분석·KG 전후 비교 기록 완료');store.task(task)

if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'development')
