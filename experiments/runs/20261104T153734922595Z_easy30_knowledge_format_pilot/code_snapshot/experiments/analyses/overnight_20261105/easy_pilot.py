"""Three-arm developmental pilot: external knowledge and serialization, not retrieval superiority."""
from pathlib import Path
import sys,json,copy,datetime,time,collections,itertools,shutil
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path[:0]=[str(H),str(R/'src')]
import candidate_runtime as rt
from paired_kg import packet_from_targets,DEADLINE
from kg_pipeline.io import Qwen,read,save,sha,dumps
from kg_pipeline.validation import validate_schema
from kg_pipeline.runner import register_run
from kg_runtime.morphology import Morphology
from research_management.work import WorkStore
from research_management.core import guard_dataset
SYSTEM='한국어 표준어를 자연스러운 경상도 방언으로 바꾸세요. 원문의 사건, 시제, 부정, 질문·요청·약속 등의 기능, 주체 높임과 상대 높임을 유지하세요. 입력 분석은 참고 정보이며 틀릴 수 있습니다. 문법 참고 정보가 있으면 원문의 조건에 맞는 정보를 활용하세요. 정보가 없거나 해당하지 않는 부분은 알고 있는 방언 지식을 활용해도 됩니다. 문장을 생략하거나 새 사건을 추가하지 말고 전체 문장을 생성하세요. 지정된 JSON 형식으로만 답하세요.'

def leaves(value,path=()):
 if isinstance(value,dict) and value:
  for k,v in value.items():yield from leaves(v,path+(k,))
 elif isinstance(value,list) and value:
  for i,v in enumerate(value):yield from leaves(v,path+(i,))
 else:yield list(path),value

def render(value):return '\n'.join(json.dumps(p,ensure_ascii=False)+' = '+json.dumps(v,ensure_ascii=False) for p,v in leaves(value))
def restore(text):
 records=[(json.loads(line.split(' = ',1)[0]),json.loads(line.split(' = ',1)[1])) for line in text.splitlines()]
 def build(prefix):
  exact=[v for p,v in records if p==prefix]
  if exact:return exact[0]
  paths=[p for p,v in records if p[:len(prefix)]==prefix];keys=list(dict.fromkeys(p[len(prefix)] for p in paths))
  if isinstance(keys[0],int):return [build(prefix+[i]) for i in sorted(keys)]
  return {k:build(prefix+[k]) for k in keys}
 return build([])

def payloads(text,traces,packet):
 common={'text':text,'analysis':[{'target_id':t['target']['uid'],'span':t['target']['original_span'],'observed_morphology':t['analysis']['clauses'][0]['morphology'],'features':t['analysis']['clauses'][0]['features']} for t in traces]}
 knowledge={k:copy.deepcopy(v) for k,v in packet.items() if k not in ('text','instruction')}
 assert 'expected_surface' not in dumps(knowledge)
 j=dumps(knowledge);t=render(knowledge);assert restore(t)==knowledge
 p={a:{**copy.deepcopy(common),'grammar_reference':v} for a,v in [('N',''),('T',t),('J',j)]}
 assert all({k:v for k,v in p[a].items() if k!='grammar_reference'}==common for a in p)
 return p,{'knowledge_sha256':sha(j.encode()),'leaf_count':len(list(leaves(knowledge))),'roundtrip_equal':True,'characters':{'T':len(t),'J':len(j)},'common_sha256':sha(dumps(common).encode())}

def wire_content(payload):
 common={k:v for k,v in payload.items() if k!='grammar_reference'}
 return dumps(common)+'\n\n문법 참고 정보:\n'+payload['grammar_reference']

def observed(text,analyzer):
 ts=analyzer.analyze(text)['tokens']
 return {'past_ep':sum(t['base_tag']=='EP' and t['form'] in ('았','었','였') for t in ts),'honorific_si':sum(t['base_tag']=='EP' and t['form'] in ('시','으시') for t in ts),'negative_morphemes':sum(t['form'] in ('안','못','않','아니','말') and t['base_tag'] in ('MAG','VX','VCN') for t in ts),'lexical_gyesi':sum(t['form']=='계시' and t['base_tag'] in ('VX','VV') for t in ts),'observational_warning_only':True}

def main():
 graph=read(rt.GRAPH);rows=[json.loads(l) for l in (H/'private/easy30.jsonl').read_text('utf8').splitlines() if l.strip()];stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=R/'experiments/runs'/(stamp+'_easy30_knowledge_format_pilot');out.mkdir(parents=True);inp=out/'private/inputs.jsonl';inp.parent.mkdir();shutil.copy2(H/'private/easy30.jsonl',inp)
 guard=guard_dataset(R,inp,'development');analyzer=Morphology();counts={r['id']:len(rt.base.sentence_targets(analyzer.analyze(r['text']))) for r in rows};assert sum(counts.values())==30,'unplanned_analysis_budget';save(out/'preflight.json',{'target_counts':counts,'maximum_analysis_calls':30,'maximum_generation_calls':90});client=Qwen(R/'test.py',timeout=90);save(out/'config.json',{'phase':'development','dataset_role':'reviewer_authored_controlled_pilot_not_independent','model_id':client.model,'kg_dataset':'semantic_grammar_20261105_r10_candidate','input_count':30,'arms':['N','T','J'],'arm_meanings':{'N':'no_external_grammar','T':'lossless_flat_path_value_text','J':'nested_json_same_knowledge'},'temperature':0,'top_p':1,'seed':20261103,'max_generation_tokens':2048,'enable_thinking':False,'automatic_retries':0,'final_writer':'Qwen','forced_copy_when_no_knowledge':False,'reference_answers_in_request':False,'system_prompt_sha256':sha(SYSTEM.encode()),'data_check':guard,'input_sha256':sha(inp.read_bytes()),'naturalness':'not_evaluated','known_delivery_defects':['EZ01','EZ21'],'metric_contract':'output_observations_not_accuracy'})
 deps={Path(__file__),H/'PILOT_PLAN.md',H/'test_pilot.py'};deps.update(R/p for p in read(Path(read(H/'private/latest_past_development.json')['directory'])/'code_hashes.json'))
 hashes={}
 for p in deps:
  rel=p.relative_to(R);dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes[str(rel)]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'private/graph.json',graph);save(out/'server_models.json',client.models);save(out/'freeze.json',{'before_first_call':True,'graph_sha256':sha(rt.GRAPH.read_bytes()),'inputs_sha256':sha(inp.read_bytes()),'system_prompt':SYSTEM});save(H/'private/latest_pilot.json',{'directory':str(out)});register_run(R,out)
 task={'id':out.name,'title':'⑥ 쉬운30 개발파일럿: 지식 유무·전달 형식','actor':'Kiwi + Qwen + KG','stage':'development_pilot','status':'running','done':0,'total':30,'unit':'입력','unit_key':'easy_pilot'};store=WorkStore(R);store.task(task);results=[];start=time.perf_counter();af=0;ac=0;fails=collections.Counter();consecutive=collections.Counter();attempts=collections.Counter();stop_reason=None
 for i,row in enumerate(rows):
  if datetime.datetime.now(datetime.timezone.utc)>=DEADLINE:stop_reason='deadline';break
  d=out/'private/records'/row['id'];d.mkdir(parents=True);m=analyzer.analyze(row['text']);save(d/'morphology.json',m);targets=rt.base.sentence_targets(m);raws=[]
  try:
   for target in targets:
    schema,user=rt.schema_and_payload(graph,target['morph'],target['uid'],row['text']);raw=client.call('boundary_analysis',rt.PROMPT,user,schema,d/'analysis'/target['uid'],3072,20261103);validate_schema(raw,schema);raws.append(raw)
   packet,traces,internal=packet_from_targets(row['text'],targets,raws,graph);save(d/'packet.json',packet);save(d/'traces.json',traces);ps,proof=payloads(row['text'],traces,packet);save(d/'information_equality.json',proof);save(d/'payloads.json',ps);wire={a:wire_content(p) for a,p in ps.items()};assert restore(wire['T'].split('\n\n문법 참고 정보:\n',1)[1])==json.loads(wire['J'].split('\n\n문법 참고 정보:\n',1)[1]);save(d/'wire_contents.json',wire);before=observed(row['text'],analyzer);ac=0
  except Exception as e:
   af+=1;ac+=1;results.append({'id':row['id'],'source_id':row['id'],'arm':'shared_analysis','status':'analysis_or_query_failed','error':type(e).__name__+':'+str(e)[:200]});save(d/'failure.json',results[-1]);task.update(done=i+1,message=row['id']+' 분석 실패');store.task(task)
   if ac>=5 or (i>=9 and af/(i+1)>.2):stop_reason='analysis_failure_threshold';break
   continue
  order=['N','T','J'][i%3:]+['N','T','J'][:i%3];save(d/'call_order.json',order)
  for arm in order:
   ad=d/arm;result={'id':row['id']+'__'+arm,'source_id':row['id'],'arm':arm,'input_text':row['text'],'output_text':None,'supported_targets':len(packet['actions']),'rule_ids':[a['rule_id'] for a in packet['actions']],'known_delivery_defect':row['known_delivery_defect']};attempts[arm]+=1
   try:
    response=client.call('dialect_generation',SYSTEM,wire_content(ps[arm]),rt.GENERATION_SCHEMA,ad/'generation_call',2048,20261103);validate_schema(response,rt.GENERATION_SCHEMA);result.update(status='generated_requires_human_review',output_text=response['output_text'],model_status=response['status']);consecutive[arm]=0
   except Exception as e:result.update(status='generation_failed',error=type(e).__name__+':'+str(e)[:200]);fails[arm]+=1;consecutive[arm]+=1
   if result['output_text'] is not None:
    try:
     after=observed(result['output_text'],analyzer);result.update(observed_before=before,observed_after=after,observed_count_decreased=[k for k in ('past_ep','honorific_si','negative_morphemes','lexical_gyesi') if before[k]>after[k]],unchanged=result['output_text']==row['text'])
    except Exception as e:result['diagnostic_error']=type(e).__name__
   save(ad/'result.json',result);results.append(result);print(json.dumps({'id':row['id'],'arm':arm,'output':result['output_text'],'status':result['status']},ensure_ascii=False),flush=True)
  save(out/'private/results.json',results);task.update(done=i+1,message=row['id']);store.task(task)
  if any(consecutive[a]>=5 or (attempts[a]>=10 and fails[a]/attempts[a]>.2) for a in order):stop_reason='generation_failure_threshold';break
 save(out/'private/results.json',results);calls=[read(p) for p in (out/'private/records').rglob('meta.json')];metrics={'planned_inputs':30,'completed_inputs':task['done'],'records':len(results),'api_attempts':len(calls),'analysis_calls':sum(c['stage']=='boundary_analysis' for c in calls),'generation_calls':sum(c['stage']=='dialect_generation' for c in calls),'analysis_failures':af,'generation_failures':dict(fails),'arm_counts':dict(collections.Counter(r['arm'] for r in results)),'unchanged_counts':{a:sum(r['arm']==a and r.get('unchanged',False) for r in results) for a in ['N','T','J']},'past_count_decrease_warnings':{a:sum(r['arm']==a and 'past_ep' in r.get('observed_count_decreased',[]) for r in results) for a in ['N','T','J']},'naturalness':'not_evaluated','stop_reason':stop_reason,'wall_seconds':time.perf_counter()-start,'reported_usage':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')}}
 save(out/'metrics.json',metrics);save(out/'postflight.json',{'code_unchanged':all(sha((R/p).read_bytes())==h for p,h in hashes.items()),'graph_unchanged':sha(rt.GRAPH.read_bytes())==read(out/'freeze.json')['graph_sha256']});save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(R,out);task.update(status='completed' if task['done']==30 else 'failed',message='완료' if not stop_reason else stop_reason);store.task(task);print(json.dumps(metrics,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
