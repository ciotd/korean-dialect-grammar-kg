"""Offline fixed-choice replay. Never creates a Qwen client or performs KG queries.

Only old VALID IDs are rebound to the changed contract hash. Old invalid IDs and
missing outputs stay failures. References are joined AFTER replay for viewing.
"""
import copy,hashlib,json,shutil,sys,time
from collections import Counter
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];P=BASE/'private'
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime import card_pipeline as cp
from kg_runtime.analysis_alignment import reconcile_analysis
from research_management.work import WorkStore
HASHES={}
def read(p):
    data=p.read_bytes();HASHES[str(p.relative_to(ROOT))]=hashlib.sha256(data).hexdigest();return json.loads(data)
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def progress(done,message):
    WorkStore(ROOT).task(dict(id='contract-alignment-20261030',title='문장 분석·수정 작업 연결 보완',actor='Codex 총괄',stage='saved_record_replay',status='running',done=done,total=100,unit='기존 처리 기록',message=message))

def replay(folder,arm,mode,morph,packet,aligned,oldresult):
    result={'output':None,'status':'unavailable','old_error':oldresult.get('error'),'rebindings':[],
            'fixed_saved_model_choices':True,'new_model_calls':0,'new_KG_queries':0}
    rawpath=folder/'agent_call/parsed.json'
    if packet is None or not rawpath.exists():
        result['reason']='no_saved_downstream' if packet is None else 'no_complete_saved_model_response'
        return result
    decision=read(rawpath)
    if decision.get('request_id')!=packet['contract_context']['request_id']:
        result.update(reason='original_stale_request_not_repaired');return result
    analysis=aligned if mode=='aligned_analysis' else packet['grammar']
    decision=copy.deepcopy(decision)
    new_id=cp.context(morph,packet['cards'],analysis,folder.name)['request_id']
    result['rebindings'].append({'field':'request_id','old':decision['request_id'],'new':new_id,'basis':'old_matches_original_saved_packet'})
    decision['request_id']=new_id
    try:
        plan=cp.bind_plan(decision,morph,packet['cards'],realize=arm=='single',analysis=analysis,input_id=folder.name)
        result['planner_plan']=plan
        if arm=='single':final=plan
        else:
            gp=folder/'generation_call/parsed.json';oldplanpath=folder/'transformation_plan.json'
            if not gp.exists() or not oldplanpath.exists():
                result.update(reason='no_saved_worker_response');return result
            raw=read(gp);oldplan=read(oldplanpath)
            generated_skip=raw.get('origin')=='program_skip_no_applicable_edits'
            answer=raw['response'] if generated_skip else raw
            if answer.get('plan_id')!=oldplan['plan_id']:
                result.update(reason='original_stale_worker_not_repaired');return result
            newly_applicable=any(e['action']=='apply' and not e['issues'] for e in plan['edits'])
            if generated_skip and newly_applicable:
                result.update(reason='previous_program_skip_needs_new_worker');return result
            answer=copy.deepcopy(answer)
            result['rebindings'].append({'field':'plan_id','old':answer['plan_id'],'new':plan['plan_id'],'basis':'old_matches_original_saved_plan'})
            answer['plan_id']=plan['plan_id']
            final=cp.realize_plan(plan,answer,morph,packet['cards'],analysis=analysis,input_id=folder.name)
            result['worker_origin']='old_program_skip' if generated_skip else 'saved_Qwen_worker_response'
        result.update(output=cp.assemble(morph['text'],final),status=final['status'],reason=None,final_plan=final)
    except Exception as exc:result.update(reason='replay_validation_error',error=f'{type(exc).__name__}:{exc}')
    return result

def main():
    start=time.perf_counter();active=read(ROOT/'experiments/analyses/scoped_repair_20261030/private/active_run.json')
    catalog=read(ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json')
    concepts={c['id']:c for c in catalog['concepts']} if isinstance(catalog['concepts'],list) else catalog['concepts']
    inputs=ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
    data=inputs.read_bytes();HASHES[str(inputs.relative_to(ROOT))]=hashlib.sha256(data).hexdigest()
    records=[json.loads(x) for x in data.decode('utf8').splitlines()];rows=[];count=0
    for record in records:
        row={'id':record['id'],'input':record['text'],'arms':{}}
        for arm,runid in active['runs'].items():
            folder=ROOT/'experiments/runs'/runid/'private/records'/record['id']
            old=read(folder/'result.json');morph=read(folder/'morphology.json');raw=read(folder/'analysis_call/parsed.json')
            assert old['input_text']==record['text']==morph['text']
            packet=read(folder/'reference_packet.json') if (folder/'reference_packet.json').exists() else None
            if packet is not None:assert packet['grammar']==raw
            cp.validate_analysis(raw,morph,concepts)
            aligned,review=reconcile_analysis(raw,morph,concepts);cp.validate_analysis(aligned,morph,concepts,aligned=True)
            item={'record':str(folder.relative_to(ROOT)),'baseline':{'output':old['output_text'],'status':old['status'],'error':old.get('error')},
                'raw_analysis':raw,'effective_analysis':aligned,'alignment_review':review,'source_words':morph['words'],'analysis_validation':'passed'}
            for mode in ('contract_only','aligned_analysis'):
                item[mode]=replay(folder,arm,mode,morph,packet,aligned,old)
                item[mode]['output_differs_from_old']=item[mode]['output']!=old['output_text']
            row['arms'][arm]=item
            count+=1;progress(count,f"{record['id']} {arm}: 저장 응답 재검증. 새 Qwen 호출 없음.")
            print(f'{count}/100 {record["id"]} {arm}',flush=True)
        assert row['arms']['single']['effective_analysis']==row['arms']['multi']['effective_analysis']
        rows.append(row)
    # Read approved references only for the report, never to influence replay.
    refpath=ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl'
    data=refpath.read_bytes();HASHES[str(refpath.relative_to(ROOT))]=hashlib.sha256(data).hexdigest()
    refs={r['id']:r for r in map(json.loads,data.decode('utf8').splitlines())}
    for row in rows:
        assert refs[row['id']]['input']==row['input'];row['reference']=refs[row['id']]['reference']
    summary={'inputs':len(rows),'saved_records':count,'new_model_calls':0,'new_KG_queries':0,'modes':{},
             'analysis_changed_input_ids':[r['id'] for r in rows if r['arms']['single']['raw_analysis']['units']!=r['arms']['single']['effective_analysis']['units']],
             'analysis_changes':dict(Counter(c['field'] for r in rows for c in r['arms']['single']['alignment_review']['changes'])),
             'unverified_features':dict(Counter(c['function'] for r in rows for c in r['arms']['single']['alignment_review']['unverified_functions'])),
             'source_conflicts':[{'id':r['id'],**c} for r in rows for c in r['arms']['single']['alignment_review']['source_conflicts']],
             'seconds':time.perf_counter()-start,'quality_metrics':None,'fixed_cards_and_model_choices':True}
    for mode in ('baseline','contract_only','aligned_analysis'):
        summary['modes'][mode]={}
        for arm in active['runs']:
            values=[r['arms'][arm][mode] for r in rows]
            summary['modes'][mode][arm]={'changed':sum(v['output'] is not None and v['output']!=r['input'] for r,v in zip(rows,values)),
                'unchanged':sum(v['output']==r['input'] for r,v in zip(rows,values)),
                'unavailable':sum(v['output'] is None for v in values),
                'unavailable_reasons':dict(Counter(v.get('reason') or v.get('error') for v in values if v['output'] is None))}
    for rel,h in HASHES.items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
    save(P/'cases.json',rows);save(P/'summary.json',summary);save(P/'input_hashes.json',HASHES)
    codes={}
    for package in ('kg_runtime','kg_pipeline'):
        for f in (ROOT/'src'/package).glob('*'):
            if f.suffix not in ('.py','.json'):continue
            dest=P/'code_snapshot'/package/f.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
            codes[str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
    save(P/'code_hashes.json',codes)
    save(P/'protocol.json',dict(source_runs=active['runs'],new_model_calls=0,new_KG_queries=0,
        meaning='fixed-choice software replay, not new translation experiment',
        controls=['same input','same saved Kiwi','same delivered cards','same selected bindings and Qwen proposed surfaces'],
        interventions=['edit contract only','edit contract plus source-aligned analysis'],
        limitations=['cannot measure changed retrieval or Qwen choices','no replacement for missing/truncated responses','ID rebinding only after old equality validation','reference consulted only after execution','outputs not independent quality evaluation']))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
