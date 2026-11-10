"""Replay all previously saved decisions with new shared checks, without model calls."""
import importlib.util,json,sys,time,hashlib,collections,datetime as dt,shutil
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[2];P=B/'private';sys.path[:0]=[str(R/'local/python'),str(R/'src')]
from kg_pipeline.io import read,save
from research_management.work import WorkStore
spec=importlib.util.spec_from_file_location('replay_engine',R/'experiments/analyses/contract_alignment_20261030/replay.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)

def main():
 tag=dt.datetime.now(dt.timezone.utc).strftime('%H%M%S%f');task_id='controlled-replay-20261031-'+tag
 archive=P/'replay_revisions'/tag;archive.mkdir(parents=True,exist_ok=False)
 for name in ('replay_cases.json','replay_summary.json','replay_source_hashes.json'):
  if (P/name).exists():shutil.copy2(P/name,archive/name)
 code={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (R/'src/kg_runtime').glob('*.py')}
 a=engine.read(R/'experiments/analyses/register_connective_20261030/private/active_run.json');rows=[];started=time.perf_counter();done=0
 data=[json.loads(x) for x in (R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl').read_text('utf8').splitlines()]
 for item in data:
  row={'id':item['id'],'input':item['text'],'arms':{}}
  for arm,run in a['runs'].items():
   f=R/'experiments/runs'/run/'private/records'/item['id'];old=engine.read(f/'result.json');m=engine.read(f/'morphology.json');p=engine.read(f/'reference_packet.json')
   assert item['text']==old['input_text']==m['text']==p['input']
   replay=engine.replay(f,arm,'contract_only',m,p,p['grammar'],old)
   before=engine.read(f/'final_plan.json') if (f/'final_plan.json').exists() else None
   oldedit={e['edit_id']:e for e in (before or {}).get('edits',[])}
   changes=[]
   for e in (replay.get('final_plan') or replay.get('planner_plan') or {}).get('edits',[]):
    olde=oldedit.get(e['edit_id']);newcodes=sorted({x['code'] for x in e['issues']});oldcodes=sorted({x['code'] for x in (olde or {}).get('issues',[])})
    if olde and (e['outcome']!=olde['outcome'] or newcodes!=oldcodes):changes.append({'edit_id':e['edit_id'],'before':e['before'],'after':e['after'],'old_outcome':olde['outcome'],'new_outcome':e['outcome'],'old_codes':oldcodes,'new_codes':newcodes,'cards':e['rule_ids']})
   row['arms'][arm]={'old_output':old['output_text'],'old_status':old['status'],'replay':replay,'edit_changes':changes}
   done+=1
  rows.append(row)
  WorkStore(R).task({'id':task_id,'title':'기존 100개 기록의 판정 비교','actor':'프로그램','stage':'오프라인 재검증','status':'running','done':done,'total':100,'unit':'기록','unit_key':'saved_record','message':item['id']+' · 새 Qwen 호출 없음'})
 summary={'inputs':50,'records':100,'new_model_calls':0,'new_queries':0,'seconds':time.perf_counter()-started,'arms':{}}
 for arm in a['runs']:
  vs=[r['arms'][arm] for r in rows];summary['arms'][arm]={'replayed_outputs':sum(v['replay']['output'] is not None for v in vs),
   'output_changes':[r['id'] for r in rows if r['arms'][arm]['replay']['output'] is not None and r['arms'][arm]['replay']['output']!=r['arms'][arm]['old_output']],
   'edited_judgment_changes':sum(len(v['edit_changes']) for v in vs),'unavailable':dict(collections.Counter(v['replay'].get('reason') for v in vs if v['replay']['output'] is None))}
 for rel,h in engine.HASHES.items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h
 for rel,h in code.items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h
 save(P/'replay_code_hashes.json',code)
 for rel in code:
  dest=P/'replay_code_snapshot'/Path(rel).name;shutil.copy2(R/rel,dest) if dest.parent.exists() else (dest.parent.mkdir(parents=True),shutil.copy2(R/rel,dest))
 save(P/'replay_cases.json',rows);save(P/'replay_summary.json',summary);save(P/'replay_source_hashes.json',engine.HASHES)
 WorkStore(R).task({'id':task_id,'title':'기존 100개 기록의 판정 비교','actor':'프로그램','stage':'오프라인 재검증','status':'completed','done':100,'total':100,'unit':'기록','unit_key':'saved_record','message':'원본 보존 확인. 새 모델 응답이 필요한 경우는 미확인으로 남김.'})
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
