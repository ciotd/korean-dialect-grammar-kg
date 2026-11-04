"""Approved composition-only comparison, using saved Qwen analysis and KG paths."""
import datetime,json,time,shutil,importlib.metadata
from composer import compose
from pipeline import *
from kg_runtime.morphology import Morphology
from kg_pipeline.io import read,save,sha
from kg_pipeline.runner import register_run
from research_management.work import WorkStore

def main():
 start=time.perf_counter();analyzer=Morphology();startup=time.perf_counter()-start
 dev=Path(read(HERE/'private/latest_dev.json')['directory']);full=Path(read(HERE/'private/latest_full50.json')['directory'])
 baseline=Path(read(HERE/'private/latest_replay.json')['directory']);bm={r['id']:r for r in read(baseline/'private/results.json')}
 jobs=[]
 for group,src in [('dev',dev),('full50',full)]:
  for r in read(src/'private/results.json'):
   for t in r['targets']:
    if t.get('readiness')!='ready_for_generation_trial':continue
    jobs.append((group,src,r,t))
 if len(jobs)!=30:raise ValueError('approved_cohort_not_27_plus_3')
 runid=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_kiwi_composition_fixed30';out=ROOT/'experiments/runs'/runid;out.mkdir(parents=True,exist_ok=False);(out/'private').mkdir()
 rows=[{'id':group+'_'+r['id']+'_'+t['target_id'],'text':r['input_text'],'source_case':r['id'],'group':group} for group,src,r,t in jobs]
 inputs=out/'private/inputs.jsonl';inputs.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),'utf8')
 config={'phase':'diagnostic','dataset_role':'development_and_regression_subset','metric_contract':'kiwi_fixed_composition_v1','input_count':30,'input_sha256':sha(inputs.read_bytes()),
  'model_id':'Kiwi.join '+importlib.metadata.version('kiwipiepy'),'analysis_model':'saved Qwen analysis; no new call',
  'kg_dataset':read(bridge.GRAPH)['version'],'generator':'Kiwi.join(lm_search=False); integrated copula uses selected KG form directly',
  'source_runs':[dev.name,full.name],'baseline_run':baseline.name,'analysis_calls':0,'generation_model_calls':0,'lm_search':False,
  'comparison':'same frozen analysis, selected usage, original morphs and combining form; replace surface realization implementation only',
  'limitation':'27 development targets plus3 full50 targets; selection conditional on prior readiness, not full50 translation performance'}
 save(out/'config.json',config);save(out/'private/graph.json',read(bridge.GRAPH));hashes={}
 dependencies=[HERE/'composer.py',HERE/'compose_run.py',HERE/'test_composer.py',HERE/'pipeline.py',ROOT/'src/kg_runtime/morphology.py']
 for p in dependencies:
  rel=p.relative_to(ROOT);dst=out/'code_snapshot'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst);hashes[str(rel)]=sha(p.read_bytes())
 save(out/'code_hashes.json',hashes);save(out/'freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_composition':True,
  'source_manifests':{str(p/'artifact_hashes.json'):sha((p/'artifact_hashes.json').read_bytes()) for p in (dev,full,baseline)},'graph_sha256':sha(bridge.GRAPH.read_bytes())})
 save(HERE/'private/latest_composer.json',{'run_id':runid,'directory':str(out)})
 store=WorkStore(ROOT);task={'id':runid,'title':'Qwen과 활용 조합기 비교: 같은30위치','actor':'Kiwi·기존KG','stage':'고정분석·조회 재사용','status':'running','done':0,'total':30,'unit':'위치','message':'새 모델호출0. 문장정답표 없음.'};store.task(task)
 results=[];loop=time.perf_counter()
 for i,(group,src,r,t) in enumerate(jobs):
  row=rows[i];folder=out/'private/records'/row['id'];folder.mkdir(parents=True)
  source=src/'private/records'/r['id']/'targets'/t['target_id'];payload=read(source/'enhanced.json');action=payload['actions'][0]
  save(folder/'input.json',row);proof={}
  for name in ('analysis.json','trace.json','enhanced.json'):
   shutil.copy2(source/name,folder/name);proof[name]=sha((source/name).read_bytes())
  save(folder/'source_link.json',{'source':str(source),'hashes':proof})
  record={'id':row['id'],'source_case':r['id'],'source_run':src.name,'group':group,'target_id':t['target_id'],'input_text':r['input_text'],
   'output_text':None,'status':'started','rules':t['rules'],'human_evaluation':None,'source_packet_hash':proof['enhanced.json'],
   'qwen_output_text':bm[r['id']]['output_text'] if group=='dev' else r['output_text']}
  try:
   tick=time.perf_counter();piece,operation=compose(analyzer.kiwi,action);record['composition_seconds']=time.perf_counter()-tick
   local=apply_piece(payload['text'],action,piece);checks=preservation_check(analyzer,local,payload)
   span=t['span'];global_action={'span':span,'target':r['input_text'][span[0]:span[1]]}
   if global_action['target']!=action['target']:raise ValueError('source_target_mismatch')
   output=apply_piece(r['input_text'],global_action,piece)
   save(folder/'composition.json',operation)
   record.update(status='generated_requires_human_review',output_text=output,replacement=piece,checks=checks,changed=output!=r['input_text'])
  except Exception as exc:record.update(status='composition_failed',error_type=type(exc).__name__,error=str(exc))
  save(folder/'result.json',record);results.append(record);task.update(done=i+1,message=r['id']+' '+record['status']);store.task(task)
 save(out/'private/results.json',results)
 metrics={'records':30,'api_attempts':0,'analysis_calls':0,'generation_model_calls':0,'valid_output_records':sum(r['status']=='generated_requires_human_review' for r in results),
  'changed_records':sum(r.get('changed',False) for r in results),'status_counts':dict(__import__('collections').Counter(r['status'] for r in results)),
  'surface_warning_records':sum(bool(r.get('checks',{}).get('warnings')) for r in results),'reported_usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0},
  'wall_seconds':round(time.perf_counter()-loop,6),'kiwi_startup_seconds':round(startup,6),'composition_seconds_sum':sum(r.get('composition_seconds',0) for r in results),
  'naturalness_evaluation':'not_performed','valid_count_meaning':'candidate emitted for human review; not translation accuracy'}
 save(out/'metrics.json',metrics);f=read(out/'freeze.json');save(out/'postflight.json',{'source_manifests_unchanged':all(sha(Path(p).read_bytes())==h for p,h in f['source_manifests'].items()),
  'source_packet_copies_match':all(all(sha((out/'private/records'/r['id']/name).read_bytes())==h for name,h in read(out/'private/records'/r['id']/'source_link.json')['hashes'].items()) for r in results),
  'code_unchanged':all(sha((ROOT/p).read_bytes())==h for p,h in hashes.items()),'graph_unchanged':sha(bridge.GRAPH.read_bytes())==f['graph_sha256']})
 save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'});register_run(ROOT,out)
 task.update(status='completed',done=30,message='같은30위치 조합 비교 완료. 자연스러움은 미평가.');store.task(task)
 print(json.dumps({'run_id':runid,'metrics':metrics,'comparisons':[{'id':r['id'],'qwen':r['qwen_output_text'],'composer':r['output_text'],'warnings':r.get('checks',{}).get('warnings')} for r in results]},ensure_ascii=False))
if __name__=='__main__':main()
