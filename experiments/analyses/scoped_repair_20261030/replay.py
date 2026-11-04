"""Replay saved v3 decisions through new code; no new Qwen calls or changed old files."""
import copy,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_pipeline.io import read,save,sha
from kg_runtime import card_pipeline as cp

def main():
    active=read(ROOT/'experiments/analyses/card_content_experiment_20261030/private/active_run.json');results=[]
    for arm in ('single','multi'):
        source=ROOT/'experiments/runs'/active['runs']['v3_'+arm]
        for old in read(source/'private/results.json'):
            folder=source/'private/records'/old['id'];out=BASE/'private/replay'/arm/old['id'];out.mkdir(parents=True,exist_ok=True)
            row={'id':old['id'],'arm':arm,'source_run':source.name,'old_output':old['output_text'],'old_status':old['status'],
                'new_output':None,'new_status':None,'raw_response_changed':False,'rebound_identifiers':['request_id','plan_id'],
                'origin':'offline replay with saved model responses, not a fresh generation experiment'}
            response=folder/'agent_call/parsed.json'
            if not response.exists():
                row.update(new_status='source_response_unavailable',source_error=old.get('error'));results.append(row);continue
            payload=read(folder/'reference_packet.json');morph=read(folder/'morphology.json');raw=read(response);v=copy.deepcopy(raw)
            row['source_response_sha256']=sha(response.read_bytes())
            v['request_id']=cp.context(morph,payload['cards'],payload['grammar'],old['id'])['request_id']
            try:
                plan=cp.bind_plan(v,morph,payload['cards'],realize=arm=='single',analysis=payload['grammar'],input_id=old['id'])
                if arm=='multi':
                    worker=folder/'generation_call/parsed.json'
                    if not worker.exists():raise ValueError('source_worker_response_unavailable')
                    answer=read(worker);answer=copy.deepcopy(answer.get('response',answer));answer['plan_id']=plan['plan_id']
                    plan=cp.realize_plan(plan,answer,morph,payload['cards'],analysis=payload['grammar'],input_id=old['id'])
                row.update(new_output=cp.assemble(old['input_text'],plan),new_status=plan['status'],
                    scope_repaired=[{'before':e['before'],'proposed':e['proposed_after'],'after':e['after'],'outcome':e['outcome']} for e in plan['edits'] if any(r['kind']=='scoped_surface_tail' for r in e['repairs'])],
                    scope_held=[{'before':e['before'],'issues':e['issues']} for e in plan['edits'] if any(i['code'].startswith('scoped_') for i in e['issues'])])
                save(out/'new_plan.json',plan)
            except Exception as exc:row.update(new_status='replay_failed',error=str(exc))
            save(out/'result.json',row);results.append(row)
    summary={'source':active['batch'],'new_model_calls':0,'records':len(results),
        'output_changed':sum(r['old_output'] is not None and r['new_output'] is not None and r['old_output']!=r['new_output'] for r in results),
        'scope_repaired_edits':sum(len(r.get('scope_repaired',[])) for r in results),
        'scope_held_edits':sum(len(r.get('scope_held',[])) for r in results),
        'unavailable_or_failed':[{'id':r['id'],'arm':r['arm'],'status':r['new_status'],'error':r.get('error',r.get('source_error'))} for r in results if r['new_output'] is None],
        'interpretation':'Identifiers rebound to new contract. Same saved model text decisions; no claim of model improvement or native quality.'}
    save(BASE/'private/replay_results.json',results);save(BASE/'private/replay_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
