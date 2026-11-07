"""Three bounded writer-only diagnostics from immutable recorded inputs."""
import argparse,datetime as dt,json,sys,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tools')]
from kg_pipeline.io import Qwen,read,save,sha
from kg_pipeline.multi_agent import validate_review,repair_issues,feedback_request,revision_contract,check_writer,check_feedback
from kg_pipeline.runner import register_run
from run_qwen_multi import GuardedClient

def run(args):
 source=Path(args.source).resolve();end=dt.datetime.fromisoformat(args.deadline)
 if end.tzinfo is None or end<=dt.datetime.now(dt.timezone.utc):raise ValueError('Future timezone-aware deadline required')
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'experiments/runs'/(stamp+'_feedback_route_probe');(out/'private').mkdir(parents=True)
 config=read(source/'config.json');save(out/'config.json',{'program_id':'feedback_route_probe_20261107','input_count':3,'source_run':source.name,'max_calls':3,'seed':config['seed'],'model_id':config['model_id'],'deadline':args.deadline,'reference_answers_in_request':False,'dataset_role':'development_exposed','negative_control_bypasses_normal_filter':True,'pipeline_effect_comparison':False})
 source_rows={r['id']:r for r in read(source/'private/results.json')};results=[];start=time.perf_counter()
 save(out/'code_hashes.json',{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [Path(__file__),ROOT/'src/kg_pipeline/multi_agent.py',ROOT/'src/kg_pipeline/io.py',ROOT/'tools/run_qwen_multi.py']})
 for p in [Path(__file__),ROOT/'src/kg_pipeline/multi_agent.py',ROOT/'src/kg_pipeline/io.py',ROOT/'tools/run_qwen_multi.py']:
  dest=out/'code_snapshot'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 register_run(ROOT,out)
 try:
  transport=Qwen(ROOT/'test.py',model=config['model_id'],timeout=120);client=GuardedClient(transport,end,3,1)
  for identifier,mode in [('MULTI_DEV02','qualified_feedback'),('MULTI_DEV04','negative_unfiltered_feedback'),('MULTI_DEV05','qualified_feedback')]:
   client.begin_input();rd=out/'private/records'/identifier;prior=source/'private/records'/identifier
   row=source_rows[identifier];text=row['input_text'];record={'id':identifier,'input_text':text,'mode':mode,'output_text':None,'status':'started'}
   try:
    request=read(prior/'writer/request.json');payload=json.loads(request['messages'][1]['content']);draft=read(prior/'writer/parsed.json');review=read(prior/'reviewer/parsed.json')
    checked=validate_review(review,text,draft);issues=repair_issues(checked)
    if mode=='negative_unfiltered_feedback':issues=review['issues'][:1]
    if not issues:raise ValueError('No candidate feedback: do not synthesize any')
    feedback=feedback_request(issues);actions=read(prior/'selected_knowledge.json');clauses=payload['analysis']['clauses']
    save(rd/'fixed_materials.json',{'original_payload':payload,'draft':draft,'raw_review':review,'normal_filter':checked,'feedback':feedback,'source_hashes':{name:sha((prior/name).read_bytes()) for name in ['writer/request.json','writer/parsed.json','reviewer/parsed.json','selected_knowledge.json']}})
    record['draft_text']=draft['output_text'];record['feedback_issues']=feedback['issues']
    result=client.call('feedback_route_writer',request['messages'][0]['content'],{**payload,'previous_draft':draft,'review':feedback},revision_contract(actions,clauses,feedback),rd/'revision',4096,config['seed'])
    check_writer(result,actions,clauses);check_feedback(result,feedback)
    record.update(output_text=result['output_text'],feedback_decisions=result['feedback_decisions'],status='generated_requires_human_review')
   except Exception as exc:record.update(status='failed',error_type=type(exc).__name__)
   save(rd/'result.json',record);results.append(record);save(out/'private/results.json',results);print(identifier,record['status'],flush=True)
 finally:
  metas=[read(p) for p in (out/'private/records').rglob('meta.json')]
  save(out/'metrics.json',{'records':len(results),'api_attempts':len(metas),'valid_output_records':sum(r['status']=='generated_requires_human_review' for r in results),'reported_usage':{k:sum((m.get('usage') or {}).get(k,0) or 0 for m in metas) for k in ['prompt_tokens','completion_tokens','total_tokens']},'calls_without_usage':sum(not m.get('usage') for m in metas),'wall_seconds':time.perf_counter()-start,'naturalness':None,'automatic_retries':0})
  hashes=read(out/'code_hashes.json');save(out/'postflight.json',{'code_unchanged':all(sha((ROOT/p).read_bytes())==h for p,h in hashes.items())})
  save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file()});register_run(ROOT,out)
 print(out,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true',required=True);p.add_argument('--source',required=True);p.add_argument('--deadline',required=True);run(p.parse_args())
