"""Derive visual report + immutable blind assignments from sealed experiment runs."""
import argparse
import collections
import hashlib
import itertools
import secrets
import shutil
import statistics
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,sha,load_jsonl
from kg_runtime.cards import VERSION

OLD={'single':'20261025T085653301020Z_runtime_single_regression','multi':'20261025T085653584686Z_runtime_multi_regression'}
FUNCTION_KO={'declarative':'평서','polar_question':'판정 의문','wh_question':'의문사 의문','request':'요청·명령','propositive':'청유','prohibition':'금지',
 'conditional':'조건','causal':'원인','quotation':'인용','intention':'의지·약속','conjecture':'추측','retrospective':'회상','negation':'부정','relative':'관형절','progressive':'진행','contrast':'대조·양보','particle':'조사','other':'기타'}

def diagnosis():
    rows=[]
    def add(ids,phenomenon,cause,cards,sources,interpretation):
        for i in ids.split():rows.append(dict(id=i,phenomenon=phenomenon,cause=cause,cards=cards,sources=sources,interpretation=interpretation))
    add('DEV002 DEV007 NEW009','일반 평서 · 과거',
        '기존 17개 코드에는 반말 일반 평서 어미의 수정 연산이 없다.', ['GS_END_DECL_HRA_09'], 'D02 PDF 109쪽',
        '-다는 표준형으로도 기록된다. 샀어→샀다 같은 변화가 가능하다고 해도 고유한 방언 개선의 증거는 아니다. 부정·관형절은 별도로 보존해야 한다.')
    add('DEV005','형용사 평서','질문·청유·지 종결 등 기존 연산에 해당하지 않는다.', ['GS_END_DECL_HRA_09','GS_ENDRULE_I_DEO'], 'D02 PDF 109·91쪽',
        '형용사 자료가 존재하지만 하이소체 형태를 반말에 바로 적용하면 대우 수준이 달라진다. 변환하지 않는 선택도 가능하다.')
    add('DEV011 NEW004 ADVCE001A ADVCE001B','공손한 판정 의문 · 현재/과거',
        '기존 나/노 연산은 polite이면 제외하고, 예 연산은 나요를 허용 목록에 넣지 않았다.',
        ['GS_ENDRULE_Q_POLAR_V','GS_ENDRULE_YO_COMPOSE','GS_END_Q_HI_01'], 'D02 PDF 145·203·213·119쪽',
        '의문 어미 및 공손한 계열은 존재한다. 그러나 나/노, 요/예, 격식적인 니껴를 무조건 합치거나 교체할 수는 없다. 시제·대우 유지와 조합 검토가 필요하다.')
    add('DEV020','금지 · -지 마','기존 요청 연산은 세요만 처리한다. -지 말다를 위한 후보 생성은 없다.',
        ['GS_HAM_NEG_MAL'], 'D07 PDF 21~22쪽',
        '문헌은 -지 말다가 표준어와 같다고 기록한다. 금지 표현 자체가 바뀌지 않았다는 이유만으로 실패라고 할 수 없다.')
    add('DEV029','경험·회상 · -더라','기존 17개 목록에 회상 종결 연산이 없다.',
        ['GS_ENDRULE_RA_RETR'], 'D02 PDF 198쪽',
        '더+라/래 관련 지식은 있다. -더라의 회상 의미를 없애지 않고 활용할 수 있는지 판단해야 한다.')
    add('NEW008','부정 계사 · 아니야','기존 계사 연산은 질문 또는 공손한 종결에만 적용된다.',
        ['GS_FEATURE_COP','GS_ENDRULE_RA_COP'], 'D02 PDF 42·50·74·145·198쪽',
        '이다와 아니다의 구별이 필요하다. 긍정 계사 규칙을 부정 계사에 그대로 확대하면 안 된다. 부정 계사의 직접 대응은 별도 보완 대상이다.')
    add('ADVCE003A ADVCE003B','-까요: 의향 질문 / 추측 질문',
        '기존 공손한 예 연산에 까요가 포함되지 않았다.', ['GS_END_Q_YO_14','GS_END_Q_HAE_09'], 'D02 PDF 213·208쪽',
        '같은 -까요라도 제가 닫을까요는 행동 의향, 저절로 닫힐까요는 사건의 추측이다. 목록 존재만으로 같은 새 어미를 강제할 수 없다.')
    add('ADVCE008A ADVCE008B','화자 약속 · -ㄹ게요, 관형절 시제 대비',
        '기존 17개 목록에 약속 -끼 변환이 없고, 예 연산도 게요를 처리하지 않는다.',
        ['GS_ENDRULE_KKI_PROM','GS_ENDRULE_YO_COMPOSE','GS_HAM_ADN'], 'D02 PDF 201·203쪽; D07 PDF 21쪽',
        '-끼는 모음으로 끝나는 동사 어간과 결합하며 -ㄹ게에 대응한다고 문헌에 나온다. 공손한 합성형은 추가 조합 판단이고, 읽는/읽던의 차이는 보존해야 한다.')
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',required=True);a=p.parse_args()
    project=ROOT;batch=project/'experiments/batches'/a.batch;protocol=read(batch/'protocol.json')
    out=project/'experiments/analyses/grammar_cards_20261028/private';out.mkdir(parents=True,exist_ok=True)
    if (out/'blind_review.json').exists() and read(out/'report_manifest.json')['batch']!=a.batch:raise ValueError('blind_assignments_already_exist_for_other_batch')
    runs={**{f'old_{k}':project/'experiments/runs'/v for k,v in OLD.items()},**{k:project/'experiments/runs'/v for k,v in protocol['runs'].items()}}
    rows={k:read(v/'private/results.json') for k,v in runs.items()};by={k:{r['id']:r for r in rs} for k,rs in rows.items()}
    source=read(project/'knowledge/authored'/VERSION/'cards.json');cards={c['id']:c for c in source['cards']}
    graphroot=project/'knowledge/authored'/source['source_dataset']/'graph'
    graphnodes={n['id']:n for n in load_jsonl(graphroot/'nodes.jsonl')}
    graphedges={e['id']:e for e in load_jsonl(graphroot/'edges.jsonl')}
    diagnoses=diagnosis()
    actual_empty={r['id'] for r in rows['old_single'] if r.get('candidate_count')==0}
    assert {r['id'] for r in diagnoses}==actual_empty
    assert all(by['old_multi'][i].get('candidate_count')==0 for i in actual_empty)
    for d in diagnoses:
        assert all(i in cards for i in d['cards'])
        d.update(input=by['single'][d['id']]['input_text'],single=by['single'][d['id']]['output_text'],multi=by['multi'][d['id']]['output_text'])
    diagnoses.sort(key=lambda d:list(by['single']).index(d['id']))
    traces=[]
    for r in rows['single']:
        i=r['id'];folder=runs['single']/'private/records'/i
        morph=read(folder/'morphology.json');words={w['uid']:w for w in morph['words']}
        analysis=read(folder/'analysis_call/parsed.json') if (folder/'analysis_call/parsed.json').exists() else {'units':[]}
        retrieval=read(folder/'retrieval_raw.json') if (folder/'retrieval_raw.json').exists() else {'cards':[],'retrieved_ids':[],'paths':[]}
        units=[dict(u,surface=words.get(u['word_id'],{}).get('surface',u['word_id']),functions=[FUNCTION_KO.get(f,f) for f in u['functions']]) for u in analysis.get('units',[])]
        used=set(r.get('selected_rules',[]))
        path=next((p for p in retrieval['paths'] if p['rule_id'] in used),next(iter(retrieval['paths']),None))
        trace={'id':i,'input':r['input_text'],'analysis':units,'cards':retrieval['cards'],'retrieved':len(retrieval['retrieved_ids']),
            'path':f"{path['concept_id']} → {path['via']} → {path['rule_id']}" if path else '분석 또는 조회 단계 실패'}
        if path:
            nodeids=list(dict.fromkeys([path['concept_id'],path['via'],path['rule_id']]))
            trace['network']={'nodes':[{'id':k,'title':graphnodes[k]['title'],'type':graphnodes[k]['type']} for k in nodeids],
                'edges':[{k:graphedges[e][k] for k in ('id','source','target','relation')} for e in path['edge_ids']]}
        else:trace['network']={'nodes':[],'edges':[]}
        for c in ('single','multi'):
            final=runs[c]/'private/records'/i/'final_plan.json';rr=by[c][i]
            plan=read(final) if final.exists() else {'edits':[]}
            trace[c]={'edits':plan['edits'],'output':rr['output_text'],'error':rr.get('error'),'reason':rr.get('reason')}
        traces.append(trace)
    metrics=[]
    for k,label in [('old_single','이전 Single'),('old_multi','이전 Multi'),('single','새 Single'),('multi','새 Multi')]:
        metrics.append(dict(read(runs[k]/'metrics.json'),label=label,run=runs[k].name))
    checks=read(out/'validation_notes.json') if (out/'validation_notes.json').exists() else []
    data={'stats':read(project/'knowledge/authored'/VERSION/'statistics.json'),'diagnosis':diagnoses,'metrics':metrics,
        'records':traces,'batch':read(batch/'resources.json'),'example_card':cards['GS_ENDRULE_KKI_PROM'],'checks':checks,
        'errors':[{'arm':c,'id':r['id'],'error':r.get('error',r['status'])} for c in ('single','multi') for r in rows[c] if r['status'].endswith('_failed')]}
    old_ids={r['id'] for r in read(project/'knowledge/authored/kg_runtime_20261025/runtime.json')['rules']}
    changed_cards={c:{i for t in traces for e in t[c]['edits'] if e['before']!=e['after'] for i in e['rule_ids']} for c in ('single','multi')}
    data['coverage']={c:{'used_card_ids':sorted(changed_cards[c]),
        'beyond_old17':sorted(changed_cards[c]-old_ids),
        'old_zero15_changed':sum(by[c][i]['output_text'] is not None and by[c][i]['output_text']!=by[c][i]['input_text'] for i in actual_empty)} for c in ('single','multi')}
    common=[i for i in by['single'] if all(by[c][i]['output_text'] is not None for c in ('single','multi'))]
    data['paired_latency']={'n':len(common),'input_ids':common,
        'mean_seconds':{c:round(statistics.mean(by[c][i]['total_seconds'] for i in common),3) if common else None for c in ('single','multi')},
        'note':'both completed structurally, not a naturalness-qualified subset; full-denominator cost still reported'}
    campaign=[]
    for b in sorted((project/'experiments/batches').glob('20261028*')):
        if not (b/'protocol.json').exists():continue
        pr=read(b/'protocol.json')
        if not all('_cards_' in r for r in pr.get('runs',{}).values()):continue
        requests=list((b/'private/shared').glob('*/analysis_call/request.json'))
        for rid in pr['runs'].values():
            requests += [x for x in (project/'experiments/runs'/rid/'private/records').glob('*/*_call/request.json') if x.parent.name!='analysis_call']
        metas=[read(x.with_name('meta.json')) for x in requests if x.with_name('meta.json').exists()]
        campaign.append({'batch':b.name,'phase':pr.get('phase'),'published_final':b.name==a.batch,
            'attempted_calls':len(requests),'reported_tokens':sum((m.get('usage') or {}).get('total_tokens',0) for m in metas),
            'calls_without_usage':len(requests)-sum(bool(m.get('usage')) for m in metas)})
    data['campaign']=campaign
    data['composition_probe']=read(out/'composition_probe.json') if (out/'composition_probe.json').exists() else []
    meanings={'after_not_single_word':'생성 결과가 한 어절 형식을 지키지 못함',
        'unretrieved_rule_reference':'전달하지 않은 카드 ID를 계획에서 사용함',
        'worker_plan_mismatch':'Worker가 계획된 어절 목록을 그대로 처리하지 못함',
        'invalid_edit_anchor':'중복되거나 원문에 없는 어절 ID 사용',
        'invalid_analysis_concept_id':'KG에 없는 개념 ID 사용'}
    for e in data['errors']:
        e['raw_error']=e['error'];e['error']=meanings.get(e['error'],e['error'])
        folder=runs[e['arm']]/'private/records'/e['id']
        for m in folder.glob('*_call/meta.json'):
            meta=read(m)
            if meta.get('finish_reason')=='length':
                response=read(m.with_name('response.json'));text=response['choices'][0]['message'].get('content') or ''
                tail=len(text)-len(text.rstrip());e['trailing_whitespace_characters']=tail
                e['error']=f'응답이 출력 한도에 도달해 완료되지 않음 (끝부분 공백 {tail:,}자)'
        for t in traces:
            if t['id']==e['id']:t[e['arm']]['error']=e['error']
    save(out/'campaign_costs.json',{'batches':campaign,'note':'No duplicate shared-analysis charges. Missing usage is unknown, not zero. Separate one-call analysis probe retained in analysis_probe/meta.json.'})
    save(out/'data.json',data);save(out/'diagnosis_15.json',diagnoses)
    if not (out/'blind_review.json').exists():
        permutations=list(itertools.permutations(('old_single','single','multi')));rng=secrets.SystemRandom();rng.shuffle(permutations)
        tasks=[];key={}
        for index,r in enumerate(rows['single']):
            order=permutations[index%6];answers=[]
            for slot,c in zip('ABC',order):
                bid=secrets.token_hex(12);answers.append({'blind_id':bid,'slot':slot,'output':by[c][r['id']]['output_text']})
                key[bid]={'condition':c,'run_id':runs[c].name,'input_id':r['id'],'slot':slot}
            tasks.append({'id':r['id'],'input':r['input_text'],'answers':answers})
        save(out/'blind_review.json',tasks);save(out/'blind_key.json',key)
        save(out/'evaluation_protocol.json',{'conditions':3,'assignment':'balanced six permutations, randomly ordered; stable once written',
             'purpose':'old Single vs new Single vs new Multi; linguistic ratings paired by input',
             'primary':'native naturalness 1..5','secondary':'meaning/tense/honorific preserved|changed|unclear',
             'unrated':'missing, not zero','no_output':'not scored; report coverage separately','rater':'user, not AI',
             'limitations':['original50 regression','one rater cannot represent all Gyeongsang speakers','historical vs new confounds multiple changes']})
    for f in (project/'src/research_management/web/cards').iterdir():shutil.copy2(f,out/f.name)
    # Reproducibility of identical analysis and evidence supplied to each arm.
    equal={i:all(sha((runs['single']/'private/records'/i/f).read_bytes())==sha((runs['multi']/'private/records'/i/f).read_bytes())
        for f in ('morphology.json','analysis_call/parsed.json','reference_packet.json') if (runs['single']/'private/records'/i/f).exists()) for i in by['single']}
    manifest={'batch':a.batch,'runs':{k:v.name for k,v in runs.items()},'shared_payload_identical':equal,
        'source_artifact_hashes':{k:sha((v/'artifact_hashes.json').read_bytes()) for k,v in runs.items()},
        'cards_sha256':sha((project/'knowledge/authored'/VERSION/'cards.json').read_bytes()),'native_ratings_present':False}
    save(out/'report_manifest.json',manifest)
    nav=project/'experiments/management/report_navigation.json';links=read(nav)
    for title,name,summary in [('11 · 문법 카드 기반 재실험','report.html','15건 대조·Qwen 기능 분석·Single/Multi 실제 비교'),('12 · 방식을 가린 사람 평가','review.html','이전 Single·새 Single·새 Multi의 자연스러움 및 의미 보존 평가')]:
        url='http://127.0.0.1:8766/reports/grammar-cards/'+name
        if not any(x['url']==url for x in links):links.append({'title':title,'url':url,'summary':summary})
    save(nav,links)
    lines=['[문법 카드 기반 KG 실험 핵심 결과]',
        '17개 규칙을 모두 통과하는 구조가 아니라, 17개 안에서만 수정 후보를 만들던 구조였다.',
        f"카드 {data['stats']['card_count']}개 / 공통 개념 {data['stats']['concept_count']}개 / 12개 모듈. 새 실행기에는 규칙별 Python 연산자 제한 없음.",
        f'두 방식의 분석·조회 전달 자료 동일: {sum(equal.values())}/{len(equal)}',
        '방식 | 실행 검사 통과 | 변경 | 실패 | 호출 | 토큰 | 평균 초 (실패 포함)']
    for m in metrics:lines.append(f"{m['label']} | {m['valid_output_records']}/50 | {m['changed_records']} | {50-m['valid_output_records']} | {m['api_attempts']} | {m['reported_usage']['total_tokens']:,} | {m['mean_record_seconds']}")
    for c in ('single','multi'):lines.append(f"{c}: 이전 후보 0인 15건 중 변경 {data['coverage'][c]['old_zero15_changed']}건, 이전 17개 밖 사용 카드 {len(data['coverage'][c]['beyond_old17'])}종 (품질 점수 아님)")
    lines+=['사람 평가는 아직 미실시. 자연스러움·정확도를 위 실행 수치로 대체하지 않음.',
        '확인된 문제: 문법 기능 오분류 / 조건 해석과 활용 조합 오류 / 일부 응답의 공백 반복.',
        '보고서: http://127.0.0.1:8766/reports/grammar-cards/report.html',
        '사람 평가: http://127.0.0.1:8766/reports/grammar-cards/review.html']
    (out/'terminal_summary.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('\n'.join(lines))

if __name__=='__main__':main()
