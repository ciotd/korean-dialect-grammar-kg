"""Reapply the corrected checker/composer to frozen Qwen answers. Zero network calls."""
import sys,json,importlib.util,datetime,time,collections,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'experiments/analyses/research_loop_20261103'))
import run as runner
s=importlib.util.spec_from_file_location('checked_runtime',H/'runtime.py');rt=importlib.util.module_from_spec(s);s.loader.exec_module(rt)
from kg_pipeline.io import read,save,sha
from kg_runtime.morphology import Morphology
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
PARENT=R/'experiments/runs/20261103T093451123726Z_research_loop_followup50'
class FrozenAnalysis:
 def __init__(self):self.count=0
 def call(self,stage,prompt,user,schema,out,max_tokens,seed):
  td=PARENT/'private/records'/out.parents[2].name/'targets'/out.parent.name
  req=read(td/'analysis_call/request.json')
  assert stage=='scoped_analysis' and req['messages'][0]['content']==prompt
  assert json.loads(req['messages'][1]['content'])==user and req['response_format']['json_schema']['schema']==schema
  raw=read(td/'analysis_call/parsed.json');self.count+=1
  save(out.parent/'analysis_reused.json',{'origin':'frozen_qwen_answer','original_call':str(td/'analysis_call'),'request_sha256':sha((td/'analysis_call/request.json').read_bytes()),'parsed_sha256':sha((td/'analysis_call/parsed.json').read_bytes()),'new_api_call':False,'parsed':raw})
  return raw
def main():
 for name in ('PROMPT','schema_and_payload','analyze_response','generation_payload','preservation_check'):setattr(runner,name,getattr(rt,name))
 runid=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_condition_checked_replay50';out=R/'experiments/runs'/runid;out.mkdir(parents=True,exist_ok=False)
 config=read(PARENT/'config.json');config.update(kg_dataset='semantic_grammar_20261103_r4',analysis_mode='frozen_answer_replay',source_run=PARENT.name,new_model_calls=0,comparison='same 62 Qwen answers; corrected multiple-boundary guard; provenance-only graph r4')
 graph=read(rt.bridge.GRAPH);morphs=read(PARENT/'private/morphs.json');rows=[json.loads(l) for l in (PARENT/'private/inputs.jsonl').read_text('utf8').splitlines() if l]
 save(out/'config.json',config);save(out/'private/graph.json',graph);save(out/'private/morphs.json',morphs);shutil.copy2(PARENT/'private/inputs.jsonl',out/'private/inputs.jsonl')
 save(out/'server_models.json',read(PARENT/'server_models.json'))
 deps=[H/'runtime.py',H/'replay_checked.py',H/'test_runtime.py',H/'refine_provenance.py']+[R/p for p in read(PARENT/'code_hashes.json') if R/p not in (H/'runtime.py',H/'test_runtime.py')]
 hashes={}
 for p in deps:
  rel=p.relative_to(R);d=out/'code_snapshot'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);hashes[str(rel)]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_replay':True,'graph_sha256':sha(rt.bridge.GRAPH.read_bytes()),'input_sha256':sha((out/'private/inputs.jsonl').read_bytes()),'source_manifest_sha256':sha((PARENT/'artifact_hashes.json').read_bytes())})
 store=WorkStore(R);task={'id':runid,'title':'保存済み分析の検査補正','actor':'코드 + Kiwi / 새 Qwen 호출 없음','stage':'저장한 분석 재검사','status':'running','done':0,'total':50,'unit':'입력','message':'같은 모델 답변으로 검사 누락 수정 효과만 확인'}
 task['title']='저장된 Qwen 답변 50건 재검사';store.task(task);register_run(R,out)
 client=FrozenAnalysis();analyzer=Morphology();start=time.perf_counter();results=[]
 for row in rows:
  results.append(runner.execute(row,morphs[row['id']],graph,client,out,config,analyzer));task['done']=len(results);store.task(task)
 save(out/'private/results.json',results);ts=[t for r in results for t in r['targets']]
 metrics={'records':len(results),'api_attempts':0,'analysis_calls':0,'analysis_reused':client.count,'generation_calls':0,'changed_records':sum(r['input_text']!=r['output_text'] for r in results),'actual_generated_outputs':sum(r['generated_targets'] for r in results),'generation_failures':sum(g['status']=='failed' for t in ts for g in t['generation'].values()),'target_count':len(ts),'target_status_counts':dict(collections.Counter(t['status'] for t in ts)),'readiness_counts':dict(collections.Counter(t.get('readiness','not_retrieved') for t in ts)),'wall_seconds':round(time.perf_counter()-start,3),'reported_usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0},'naturalness_evaluation':'not_performed','human_evaluation':'pending'}
 save(out/'metrics.json',metrics);save(out/'postflight.json',{'graph_unchanged':sha(rt.bridge.GRAPH.read_bytes())==read(out/'freeze.json')['graph_sha256'],'loaded_graph_matches_snapshot':graph==read(out/'private/graph.json'),'code_unchanged':all(sha((R/p).read_bytes())==h for p,h in hashes.items()),'inputs_unchanged':sha((out/'private/inputs.jsonl').read_bytes())==config['input_sha256'],'source_count':len(rows),'result_count':len(results)})
 save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(R,out)
 task.update(status='completed',message='검사 누락 보완 후 재집계. 새 모델 호출 아님.');store.task(task)
 save(H/'private/latest_checked.json',{'run_id':runid,'directory':str(out)});print(json.dumps({'run_id':runid,**metrics},ensure_ascii=False))
if __name__=='__main__':main()
