"""Replay saved analyses through actual budget/gating; no new model calls."""
import copy,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.integrated import IntegratedReader,retrieve_packet
from kg_pipeline.io import read,save,dumps

def main():
    source=ROOT/'experiments/runs/20261109T030211818725Z_kiwi_default_regression'
    config=read(source/'config.json');pointer=read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
    graph=read(ROOT/pointer['graph']);new=IntegratedReader(graph)
    spec=importlib.util.spec_from_file_location('kg_pipeline.before_integrated',HERE/'private/before/integrated.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);old=mod.IntegratedReader(graph)
    rows=[]
    def packet(reader,fn,text,bound):
        p,_=fn(reader,text,bound,config['knowledge_character_budget'])
        disputed={u['id'] for u in bound if u['structural_objections'] or u['analysis_issues']}
        kept=[]
        for a in p['verified_scope_knowledge']:
            deps={a['unit_id']}|{i for ids in a.get('relations',{}).values() for i in ids}
            if not deps&disputed:kept.append(a)
        idx={u['id']:u for u in bound}
        actions=[{'action_id':f'A{i+1}',**a,'source_form_literal':idx[a['unit_id']].get('source_form_literal')} for i,a in enumerate(kept)]
        return p,actions
    for d in sorted((source/'private/records').iterdir()):
        if not (d/'bound_analysis.json').exists():
            rows.append({'id':d.name,'status':'no_saved_analysis'});continue
        bound=read(d/'bound_analysis.json');text=read(d/'input.json')['text']
        bp,ba=packet(old,mod.retrieve_packet,text,bound);ap,aa=packet(new,retrieve_packet,text,bound)
        logged=read(d/'selected_knowledge.json') if (d/'selected_knowledge.json').exists() else None
        keys=lambda actions:[(a['unit_id'],a['rule_id']) for a in actions]
        row={'id':d.name,'status':'replayed','old_matches_saved_selection':ba==logged,
            'same_selected_ids':keys(ba)==keys(aa),'before_actions':len(ba),'after_actions':len(aa),
            'before_chars':len(dumps(ba)),'after_chars':len(dumps(aa)),
            'before_budget_omissions':[x for x in bp['delivery_omissions'] if x['reason']=='delivery_character_budget'],
            'after_budget_omissions':[x for x in ap['delivery_omissions'] if x['reason']=='delivery_character_budget']}
        request=read(d/'writer/request.json')
        message=next(m for m in request['messages'] if m['role']=='user')
        writer=json.loads(message['content']);assert writer['knowledge']==logged
        updated=copy.deepcopy(writer);updated['knowledge']=aa
        save(HERE/'private/replayed_writer_payloads'/d.name/'before.json',writer)
        save(HERE/'private/replayed_writer_payloads'/d.name/'after.json',updated)
        row['request_knowledge_roundtrip']=json.loads(dumps(updated))['knowledge']==aa
        rows.append(row)
    good=[r for r in rows if r['status']=='replayed']
    summary={'source_run':source.name,'records':len(rows),'replayed':len(good),
        'missing_analysis':len(rows)-len(good),'before_matches_saved':sum(r['old_matches_saved_selection'] for r in good),
        'unchanged_selection':sum(r['same_selected_ids'] for r in good),
        'before_actions':sum(r['before_actions'] for r in good),'after_actions':sum(r['after_actions'] for r in good),
        'before_chars':sum(r['before_chars'] for r in good),'after_chars':sum(r['after_chars'] for r in good),
        'qwen_calls':0,'warning':'저장된 분석값 고정 재생. 최종 JSON 직렬화 확인이며 서버 전송·번역 재실험 아님.'}
    save(HERE/'private/delivery_replay.json',rows);save(HERE/'delivery_replay_summary.json',summary)
    print(dumps(summary))
    assert all(r['old_matches_saved_selection'] and r['request_knowledge_roundtrip'] for r in good)

if __name__=='__main__':main()
