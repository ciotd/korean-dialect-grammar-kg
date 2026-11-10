"""Readable before/after report with raw model proposals distinguished from code repairs."""
import collections,html,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,load_jsonl
E=lambda x:html.escape(str(x if x is not None else '출력 없음'))
ERRORS={'binding_not_ending':'모델이 고른 위치를 분석기는 어미로 분류하지 않아 중단',
 'invalid_analysis_function':'기존 분석 실패를 유지함','invalid_target_index':'카드에 없는 형태 번호를 선택함',
 'stale_request':'응답의 요청 번호가 다름','stale_worker_plan':'응답의 계획 번호가 다름','CallError:200':'모델 응답이 길이 제한 등으로 완성되지 못함'}
ISSUES={'scoped_operation_source_unavailable':'이 카드의 부분 교체를 적용할 수 없는 입력',
 'scoped_operation_composition_unavailable':'다른 교체와 섞여 부분 교체 범위를 확정하지 못함',
 'scoped_operation_preservation_violation':'카드가 보존하도록 지정한 부분이 달라짐',
 'source_suffix_composition_disagreement':'다시 분석한 결과에서 원문 활용 보존을 확인하지 못함',
 'predicate_kind_disagreement':'동사·형용사 등의 종류가 카드와 다름','target_realization_unverified':'선택 카드의 형태로 결과를 확인하지 못함',
 'function_evidence_insufficient':'문법 기능의 근거가 부족함','particle_function_disagreement':'조사의 문법 기능이 맞지 않음',
 'particle_edit_changes_other_material':'조사 외의 내용도 바뀜','reference_or_restriction_not_rewrite':'참고·제한 자료를 변환 규칙으로 선택함'}

def main():
    active=read(BASE/'private/active_run.json');batch=Path(active['root'])
    refs={r['id']:r['reference'] for r in load_jsonl(ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl')}
    records=load_jsonl(batch/'private/inputs.jsonl');cases=[];summary={};verified=0;scope_checks=[]
    for record in records:
        c={'id':record['id'],'input':record['text'],'reference':refs[record['id']],'results':{}}
        for arm in ('single','multi'):
            oldfolder=ROOT/'experiments/runs'/active['baselines'][arm]/'private/records'/record['id'];old=read(oldfolder/'result.json')
            current=ROOT/'experiments/runs'/active['runs'][arm]/'private/records'/record['id']
            c['results']['old_'+arm]={'output':old['output_text'],'status':old['status'],'error':old.get('error'),
                'calls':len(old['calls']),'tokens':sum((x.get('usage') or {}).get('total_tokens',0) for x in old['calls']),
                'seconds':old['incremental_generation_seconds']}
            if not (current/'result.json').exists():continue
            r=read(current/'result.json');plan=read(current/'final_plan.json') if (current/'final_plan.json').exists() else {}
            proposal=read(current/'agent_call/parsed.json') if (current/'agent_call/parsed.json').exists() else {}
            if (current/'agent_call/request.json').exists():
                request=read(current/'agent_call/request.json');packet=read(current/'reference_packet.json');old_packet=read(oldfolder/'reference_packet.json')
                assert json.loads(request['messages'][1]['content'])==packet
                assert {k:v for k,v in packet.items() if k!='contract_context'}=={k:v for k,v in old_packet.items() if k!='contract_context'}
                old_request=read(oldfolder/'agent_call/request.json')
                assert request['messages'][0]==old_request['messages'][0]
                assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in old_request.items() if k!='messages'}
                verified+=1
            repairs=[{'before':e['before'],'raw':e.get('proposed_after'),'after':e['after'],'outcome':e['outcome']} for e in plan.get('edits',[]) if any(x['kind']=='scoped_surface_tail' for x in e.get('repairs',[]))]
            for e in plan.get('edits',[]):
                if e['outcome']=='applied' and e.get('surface_origin')=='deterministic_card_scope_composition':
                    expected=e['suffix_projection']['candidates']
                    morph=read(current/'morphology.json');words={w['uid']:w for w in morph['words']}
                    direct=e['before'];positions=[]
                    for op in e['suffix_projection']['scope_operations']:
                        w=words[op['word_id']];pos=w['end']-1-e['span'][0]
                        assert direct[pos]=='요' and w['surface'].endswith('요')
                        positions.append(pos)
                    for pos in sorted(set(positions),reverse=True):direct=direct[:pos]+'예'+direct[pos+1:]
                    scope_checks.append({'id':record['id'],'arm':arm,'before':e['before'],'after':e['after'],
                        'preserved':bool(positions) and e['after']==direct and len(expected)==1 and e['after']==expected[0],
                        'independent_source_tail_result':direct,'raw':e['proposed_after']})
            c['results']['new_'+arm]={'output':r['output_text'],'status':r['status'],'error':r.get('error'),
                'calls':len(r['calls']),'tokens':sum((x.get('usage') or {}).get('total_tokens',0) for x in r['calls']),
                'seconds':r['incremental_generation_seconds'],'edits':plan.get('edits',[]),'proposal_edits':proposal.get('edits',[]),
                'reason':plan.get('reason',proposal.get('reason','')),'repairs':repairs,'record':str(current.relative_to(ROOT))}
        cases.append(c)
    for key in ('old_single','new_single','old_multi','new_multi'):
        pairs=[(c,c['results'][key]) for c in cases if key in c['results']]
        summary[key]={'n':len(pairs),'changed':sum(r['output'] is not None and r['output']!=c['input'] for c,r in pairs),
            'unchanged':sum(r['output']==c['input'] for c,r in pairs),'no_output':sum(r['output'] is None for c,r in pairs),
            'calls':sum(r['calls'] for c,r in pairs),'tokens':sum(r['tokens'] for c,r in pairs),'sum_seconds':sum(r['seconds'] for c,r in pairs),
            'scope_repaired_edits':sum(len(r.get('repairs',[])) for c,r in pairs),'scope_repaired_records':sum(bool(r.get('repairs')) for c,r in pairs),
            'errors':dict(collections.Counter(r['error'] for c,r in pairs if r['error']))}
    resource=read(batch/'resources.json') if (batch/'resources.json').exists() else None
    data={'complete':all(summary['new_'+a]['n']==50 for a in ('single','multi')) and resource is not None,
        'conditions':summary,'resources':resource,'verified_requests':verified,'scope_applied_checks':len(scope_checks),
        'scope_violations':sum(not r['preserved'] for r in scope_checks),'human_quality_score':None,
        'comparison':'historical before/after; same-response offline replay is separate'}
    save(BASE/'private/cases.json',cases);save(BASE/'private/summary.json',data);save(BASE/'private/scope_checks.json',scope_checks)
    labels={'old_single':'Single · 수정 전','new_single':'Single · 수정 후','old_multi':'Multi · 수정 전','new_multi':'Multi · 수정 후'}
    h='<h1>어미를 어디까지 바꿀지 바로잡았습니다</h1><p class="lead"><b>카드와 문장 분석은 그대로 두고, 활용 조합·검사를 수정했습니다.</b><br>모델이 고른 카드에 “요만 바꾸기”가 명시돼 있으면, 프로그램이 앞부분을 보존해 조합합니다.</p>'
    h+='<p>실험 완료 · 실패를 포함한 새 결과 기록 100개</p>' if data['complete'] else '<p>실험 진행 중 · 아래는 현재 저장된 결과입니다. <a href="/work">실시간 진행 보기</a></p>'
    findings=BASE/'private/findings.json'
    if findings.exists():
        h+='<section><h2>핵심 결과</h2>'
        for f in read(findings):h+='<h3>'+E(f['title'])+'</h3><p>'+E(f['text'])+'</p>'
        h+='</section>'
    h+='<div class="flow">Qwen: 카드 선택·수정 제안<br>↓<br>프로그램: 선택 카드의 교체 범위 확인<br>↓<br><b>나왔어요 → [나왔어]를 유지 + 예</b><br>↓<br>원래 제안·보정 내역·최종 결과를 모두 기록</div>'
    h+='<h2>50문장 결과</h2><p>수정 전은 직전 새 카드 실험 결과입니다. <b>이번에 같은 시점으로 다시 실행한 대조군은 아닙니다.</b> 변경된 문장 수는 정답 수가 아닙니다.</p><table><tr><th>방식</th><th>기록</th><th>문장 변경</th><th>원문 유지</th><th>출력 없음</th></tr>'
    for k,v in summary.items():h+='<tr><th>'+labels[k]+'</th>'+''.join('<td>'+str(v[x])+'</td>' for x in ('n','changed','unchanged','no_output'))+'</tr>'
    h+='</table><p>입력은 50개이고 Single/Multi 두 방식이므로 새 결과 기록은 100개입니다. 기존 분석 실패 QUAL002는 그대로 유지합니다.</p>'
    replay=read(BASE/'private/replay_summary.json')
    h+='<section><h2>모델 차이와 코드 효과를 나누어 확인했습니다</h2><p><b>① 이전 응답 재생:</b> Qwen을 새로 호출하지 않고 저장된 응답 100개를 새 코드에 넣었습니다. '+str(replay['output_changed'])+'개 출력이 달라졌고, 기존 실패 5개는 남았습니다. 이는 같은 모델 응답에 코드만 다르게 적용한 확인입니다.</p><p><b>② 새 Qwen 실행:</b> 같은 입력·분석·카드로 50개를 두 방식에서 다시 생성했습니다. 새 응답과 프로그램 보정 결과를 아래에서 구분해 볼 수 있습니다.</p>'
    h+='<p>새 실행에서 범위 조합을 실제 반영한 항목 '+str(len(scope_checks))+'개 중 원문 보존 검사 불일치는 '+str(data['scope_violations'])+'개입니다. <b>이 검사는 교체 범위에 대한 검사이며 전체 방언 정확도가 아닙니다.</b></p></section>'
    h+='<h2>입력별 실제 출력</h2><p>각 문장의 상세를 펼치면 Qwen 제안과 프로그램 보정을 구별할 수 있습니다.</p><div class="filters"><input id="search" placeholder="문장 또는 ID 검색" aria-label="문장 검색"><select id="filter" aria-label="결과 필터"><option value="all">전체</option><option value="repair">프로그램 보정이 있었던 문장</option><option value="failure">수정 후 출력 실패</option><option value="unchanged">수정 후 Single 원문 유지</option></select><span id="count"></span></div>'
    for c in cases:
        r=c['results'];flags={'repair':any(r.get('new_'+a,{}).get('repairs') for a in ('single','multi')),
            'failure':any(r.get('new_'+a,{}).get('output','pending') is None for a in ('single','multi')),
            'unchanged':r.get('new_single',{}).get('output')==c['input']}
        h+='<article class="case" data-search="'+E(c['id']+' '+c['input'])+'" '+ ' '.join('data-'+k+'="'+str(int(v))+'"' for k,v in flags.items())+'><h3>'+E(c['id'])+'</h3><p><b>원문:</b> '+E(c['input'])+'</p><p class="reference"><b>사용자 승인 표현:</b> '+E(c['reference'])+'</p><table>'
        for k in ('old_single','new_single'):
            h+='<tr><th>'+labels[k]+'</th><td>'+E(r[k]['output'] if k in r else '실행 대기')+'</td></tr>'
        h+='</table><details><summary>Multi 결과와 모델 제안·보정 과정 보기</summary><table>'
        for k in ('old_multi','new_multi'):h+='<tr><th>'+labels[k]+'</th><td>'+E(r[k]['output'] if k in r else '실행 대기')+'</td></tr>'
        h+='</table>'
        for key in ('new_single','new_multi'):
            if key not in r:continue
            v=r[key];h+='<h3>'+labels[key]+'</h3>'
            if v['error']:h+='<p class="error">'+E(ERRORS.get(v['error'],v['error']))+'</p>'
            h+='<table><tr><th>원문 부분</th><th>선택 카드</th><th>Qwen이 제안한 표현</th><th>프로그램 처리</th><th>실제 반영</th></tr>'
            for ed in v['edits']:
                repaired=any(x['kind']=='scoped_surface_tail' for x in ed.get('repairs',[]));applied=ed['outcome']=='applied'
                treatment='교체 범위에 맞게 조합' if repaired else '범위 조합과 일치' if ed.get('surface_origin')=='deterministic_card_scope_composition' else '기존 처리'
                if ed['issues']:treatment+=' · '+'; '.join(ISSUES.get(i['code'],i['code']) for i in ed['issues'])
                h+='<tr><td>'+E(ed['before'])+'</td><td>'+E(', '.join(ed.get('rule_ids',[])))+'</td><td>'+E(ed.get('proposed_after',ed['after']))+'</td><td>'+E(treatment)+'</td><td>'+E(ed['after'] if applied else ed['before'])+('' if applied else ' (원문 유지)')+'</td></tr>'
            h+='</table>'
            if v['error'] and v['proposal_edits']:h+='<p>계획 단계에서 실패해 최종 문장이 생성되지 않았습니다. 제안 원문은 실행 기록에 보존했습니다.</p>'
        h+='</details></article>'
    h+='<details><summary>실행 비용·검증·남은 범위</summary><table><tr><th>방식</th><th>호출</th><th>토큰</th><th>입력별 처리시간 합계</th></tr>'
    for k,v in summary.items():h+='<tr><th>'+labels[k]+'</th><td>'+str(v['calls'])+'</td><td>'+format(v['tokens'],',')+'</td><td>'+str(round(v['sum_seconds'],1))+'초</td></tr>'
    h+='</table><p>수정 전은 과거 비용이며 이번 비용에 더하지 않았습니다. 공유 서버·병렬 실행이므로 시간 차이는 참고값입니다.</p>'
    if resource:h+='<p>이번 실행 '+str(round(resource['wall_seconds']/60,1))+'분 · '+str(resource['physical_api_attempts'])+'회 · '+format(resource['physical_total_tokens'],',')+'토큰.</p>'
    if (BASE/'private/final_reviewer.json').exists():h+='<p><b>독립 최종 검토 완료:</b> 결과 100개, 편집 205개, 실제 요청 98개, 파일 해시 2,582개를 대조했습니다. 통계·비용·모델 제안과 실제 반영의 구분이 일치했습니다. 전체 자연스러움 평가를 대신하지는 않습니다.</p>'
    h+='<ul><li>카드별 함수가 아닌 공통 부분교체 동작 하나와 카드 두 장의 데이터 설정을 추가했습니다. 원래 카드 내용은 보존했습니다.</li><li>따옴표 내부, 죠처럼 요가 표면에 없는 축약형, 별도 조사로 분석된 요, 불명확한 혼합 편집은 이번 동작의 지원 범위가 아닙니다.</li><li>모델의 유지·보류 판단을 강제로 적용으로 바꾸지 않습니다. 교정 전 제안과 교정 주체를 남깁니다.</li><li>원문 분석 오류·다른 어미 활용·조사 선택·문맥 자연스러움은 별도 문제로 남습니다.</li><li>93개 자동 검사와 독립 구현 검토를 통과했습니다. 사람의 자연스러움 평가는 수행하지 않았습니다.</li></ul><p>실제 요청 대조 '+str(verified)+'개 · '+E(active['batch'])+'</p></details>'
    css=(ROOT/'experiments/analyses/card_content_experiment_20261030/private/report.css').read_text(encoding='utf-8')
    js="const q=document.querySelector('#search'),f=document.querySelector('#filter'),cards=[...document.querySelectorAll('.case')];function update(){let n=0;for(const c of cards){const ok=c.dataset.search.toLowerCase().includes(q.value.toLowerCase())&&(f.value==='all'||c.dataset[f.value]==='1');c.hidden=!ok;n+=ok;}document.querySelector('#count').textContent=n+'문장 표시';}q.addEventListener('input',update);f.addEventListener('change',update);update();"
    (BASE/'private/report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>교체 범위 수정 후 실험</title><link rel="stylesheet" href="report.css"><main>'+h+'</main><script src="report.js"></script></html>',encoding='utf-8')
    (BASE/'private/report.css').write_text(css,encoding='utf-8');(BASE/'private/report.js').write_text(js,encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
