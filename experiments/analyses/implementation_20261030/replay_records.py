"""Offline audit of all old records. Adapted legacy targets are NOT new model predictions."""
import collections
import json
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[2];sys.path.insert(0,str(PROJECT/'src'))
sys.path.insert(0,str(PROJECT/'local/python'))
from kg_runtime import edit_contract as ec
from kg_pipeline.io import read,save
from research_management.work import WorkStore

def adapt(old,morph,cards,analysis,input_id):
    by={c['id']:c for c in cards};edits=[];gaps=[];derivations=[]
    for i,e in enumerate(old):
        bindings=[];word=next((w for w in morph['words'] if w['uid']==e.get('word_id')),None)
        for cid in e.get('rule_ids',[]):
            if cid not in by:gaps.append({'edit_id':f'E{i+1}','card_id':cid,'reason':'missing_card'});continue
            c=by[cid];component='particle' if c.get('module')=='M04' or cid.startswith('GS_PART_') else 'construction' if any(' ' in x for x in c['forms']) or cid.startswith(('GS_CONNECT','GS_HAM_AUX')) else 'ending'
            matches=[j for j,f in enumerate(c['forms']) if ec.form_match(e.get('after',''),f,component)=='literal_match']
            index=0 if len(c['forms'])==1 else matches[0] if len(matches)==1 else None
            if index is None:gaps.append({'edit_id':f'E{i+1}','card_id':cid,'reason':'target_not_recorded_or_ambiguous'});continue
            tags=[t.split('-')[0] for _,t in (word or {}).get('morphs',[])]
            allowed=[t for sense in ec.nested_values(c.get('when',{}),'particle_sense') for t in ec.INTERPRETATION['particle_tags'].get(sense,[])]
            indices=[j for j,t in enumerate(tags) if (t in allowed if allowed else t.startswith('J'))] if component=='particle' else [j for j,t in enumerate(tags) if t in ('EF','EC','ETM','ETN')]
            if not indices:gaps.append({'edit_id':f'E{i+1}','card_id':cid,'reason':'no_bound_source_morpheme'});continue
            bindings.append({'card_id':cid,'form_index':index,'component':component,'source_word_id':word['uid'],'morph_index':indices[-1]})
            derivations.append({'edit_id':f'E{i+1}','card_id':cid,'index':index,'method':'sole_catalog_form' if len(c['forms'])==1 else 'unique_literal_output_match'})
        edits.append(dict(edit_id=f'E{i+1}',word_ids=[e.get('word_id','')],bindings=bindings,depends_on=[],action='needs_review' if any(g['edit_id']==f'E{i+1}' for g in gaps) else 'apply',
            instruction=e.get('instruction',''),after=e.get('after',''),reason=e.get('reason','')))
    return {'request_id':ec.context(morph,cards,analysis,input_id)['request_id'],'edits':edits,'reason':'과거 결과의 오프라인 재검사. 신규 모델 출력 아님'},gaps,derivations

def main():
    import datetime
    global replay_task
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    replay_task='offline-replay-'+stamp
    book=read(PROJECT/'experiments/analyses/full_review_20261029/private/casebook.json')['cases'];rows=[];store=WorkStore(PROJECT)
    previous=BASE/'private/replay.json'
    if previous.exists() and not (BASE/'private/replays/initial_legacy_audit.json').exists():save(BASE/'private/replays/initial_legacy_audit.json',read(previous))
    for n,case in enumerate(book,1):
        arms={}
        for arm,a in case['arms'].items():
            path=PROJECT/a['source_record_dir'];morph=read(path/'morphology.json');packet=read(path/'reference_packet.json')
            final=path/'final_plan.json'
            old=(read(final) if final.exists() else a.get('draft') or {}).get('edits',[])
            if not final.exists() and a.get('worker_response'):
                answers={x.get('word_id'):x.get('after','') for x in a['worker_response'].get('edits',[])}
                old=[dict(e,after=answers.get(e.get('word_id'),e.get('after',''))) for e in old]
            value,gaps,derivations=adapt(old,morph,packet['cards'],packet.get('grammar'),case['id'])
            item={'old_status':a.get('status'),'old_output':a.get('output'),'old_error':a.get('error'),
                'source':str(path.relative_to(PROJECT)),'adaptation_gaps':gaps,'target_derivations':derivations,
                'new_qwen_calls':0,'dependent_groups':'not_recorded_in_old_output','old_edit_count':len(old),
                'adaptation_status':'inferred_with_gaps' if gaps else 'inferred_targets' if old else 'empty_plan' if not a.get('error') else 'no_usable_plan'}
            if a.get('error') and not old:
                item.update(replay_status='not_auditable_no_plan',replayed_output=None);arms[arm]=item;continue
            try:
                plan=ec.bind_plan(value,morph,packet['cards'],analysis=packet.get('grammar'),input_id=case['id'])
                item.update(plan=plan,replayed_output=ec.assemble(morph['text'],plan),replay_status=plan['status'])
            except Exception as exc:item.update(replay_status='contract_rejected',error=str(exc))
            # A legacy missing binding is missing evidence, never permission inferred from an omitted card.
            if gaps:item['interpretation_limit']='Some target forms were never recorded. This is an audit, not a new v2 execution.'
            arms[arm]=item
        rows.append({'id':case['id'],'input':case['input'],'arms':arms})
        store.task(dict(id=replay_task,title='기존 50문장 재검사',actor='코드 검사',stage='기존 기록에 새 검사 적용',status='running' if n<len(book) else 'completed',
            done=n,total=len(book),unit='입력',unit_key='offline-record-input',message='각 입력의 Single/Multi 기존 기록을 확인. 새 Qwen 호출 없음.'))
    reasons=collections.Counter(i['code'] for r in rows for a in r['arms'].values() for e in a.get('plan',{}).get('edits',[]) for i in e['issues'])
    summary={'inputs':len(rows),'records':sum(len(r['arms']) for r in rows),'status_counts':dict(collections.Counter(a['replay_status'] for r in rows for a in r['arms'].values())),
        'original_execution_status_counts':dict(collections.Counter(a['old_status'] for r in rows for a in r['arms'].values())),
        'original_failed_records':sum(bool(a['old_error']) for r in rows for a in r['arms'].values()),
        'adaptation_status_counts':dict(collections.Counter(a['adaptation_status'] for r in rows for a in r['arms'].values())),
        'audit_status_by_original_execution':{status:dict(collections.Counter(a['replay_status'] for r in rows for a in r['arms'].values() if a['old_status']==status)) for status in {a['old_status'] for r in rows for a in r['arms'].values()}},
        'reason_counts':dict(reasons),'records_with_adaptation_gaps':sum(bool(a['adaptation_gaps']) for r in rows for a in r['arms'].values()),
        'repairs':sum(len(e['repairs']) for r in rows for a in r['arms'].values() for e in a.get('plan',{}).get('edits',[])),
        'new_qwen_calls':0,'quality_improvement':None,'scope':'offline legacy output audit; inferred target binding and unknown dependencies; not a v2 performance experiment'}
    save(BASE/f'private/replays/{stamp}.json',{'summary':summary,'rows':rows})
    save(BASE/'private/replay.json',{'summary':summary,'rows':rows,'run_id':stamp});print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
