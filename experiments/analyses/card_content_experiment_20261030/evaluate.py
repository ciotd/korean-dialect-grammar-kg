"""Rebuild comparison from saved requests and outputs; no model calls."""
import collections,html,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,load_jsonl,sha

LABELS={'v2_single':'Single · 이전 카드','v3_single':'Single · 새 카드','v2_multi':'Multi · 이전 카드','v3_multi':'Multi · 새 카드'}
FRIENDLY={'binding_not_ending':'어미로 지정한 위치가 형태소 분석에서는 조사 등 다른 종류로 분류됨',
 'invalid_target_index':'카드에 없는 형태 번호를 선택함','stale_worker_plan':'생성 응답의 계획 번호가 요청과 다름',
 'stale_request':'응답의 요청 번호가 현재 요청과 다름','CallError:200':'응답을 정상 완료하지 못함. 길이 제한 등 원본 응답 확인 필요',
 'invalid_analysis_function':'기존 문법 분석에 허용되지 않은 기능 이름이 있어 분석 단계에서 중단됨'}
ISSUES={'function_evidence_insufficient':'분석에서 이 문법 기능을 확인하지 못함','predicate_kind_disagreement':'동사·형용사 등 종류가 카드 조건과 맞지 않음',
 'target_realization_unverified':'만든 표현을 선택한 카드 형태로 확인하지 못함','particle_edit_changes_other_material':'조사만 바꿔야 하는데 다른 부분도 바뀜',
 'reference_or_restriction_not_rewrite':'참고·제한 설명을 변환 규칙처럼 사용함','user_restricted_conversion':'사용자가 금지한 변환',
 'tense_not_preserved':'원문 시제를 유지하지 못함','subject_honorific_not_preserved':'주체 높임을 유지하지 못함',
 'unknown_condition':'필요한 조건이 확인되지 않음','source_suffix_composition_disagreement':'만든 표현을 다시 분석했을 때 원문 어휘·시제 등의 보존을 확인하지 못함',
 'particle_function_disagreement':'선택한 조사의 문법 기능이 원문 분석과 맞지 않음','function_not_supported':'선택한 문법 기능을 입력 분석이 뒷받침하지 않음',
 'dependency_group_not_applied':'함께 바뀌어야 할 다른 수정이 보류되어 같이 보류함','unlicensed_word_expansion':'허용된 범위를 넘어 단어 수가 늘어남',
 'new_unjoined_jamo':'완성된 글자 대신 분리된 자모가 생김','subject_honorific_disagreement':'주체 높임 정보가 맞지 않음'}
E=lambda x:html.escape(str(x if x is not None else '출력 없음'))

def main():
    active=read(BASE/'private/active_run.json');plan=read(BASE/'private/plan.json');batch=Path(active['root'])
    refs={r['id']:r['reference'] for r in load_jsonl(ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl')}
    original={r['id']:r for r in load_jsonl(batch/'private/inputs.jsonl')}
    carddata=read(ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json')['cards']
    by={c['id']:c for c in carddata};directional={c['id'] for c in carddata if 'rewrite' in c}
    cases=[];verified_requests=0;verified_pairs=0;preservation=[]
    for row in plan['rows']:
        case={'id':row['id'],'input':original[row['id']]['text'],'reference':refs[row['id']],
            'source_delivery':row['origin'],'analysis_ok':row['analysis_ok'],'directional_delivered':row.get('revised_directional_ids',[]),'results':{}}
        for key,run in active['runs'].items():
            folder=ROOT/'experiments/runs'/run/'private/records'/row['id'];rp=folder/'result.json'
            if not rp.exists():continue
            r=read(rp);final=read(folder/'final_plan.json') if (folder/'final_plan.json').exists() else {}
            proposed=read(folder/'agent_call/parsed.json') if (folder/'agent_call/parsed.json').exists() else {}
            if (folder/'agent_call/request.json').exists():
                req=read(folder/'agent_call/request.json');packet=read(folder/'reference_packet.json')
                assert json.loads(req['messages'][1]['content'])==packet
                assert [c['id'] for c in packet['cards']]==row['selected_ids']
                if key.startswith('v3'):assert all(c==by[c['id']] for c in packet['cards'])
                verified_requests+=1
            selected={b['card_id'] for ed in proposed.get('edits',[]) for b in ed.get('bindings',[])}
            apply_selected={b['card_id'] for ed in proposed.get('edits',[]) if ed.get('action')=='apply' for b in ed.get('bindings',[])}
            error_label=FRIENDLY.get(r.get('error'),r.get('error'))
            if any(c.get('finish_reason')=='length' for c in r['calls']):error_label='모델 응답이 최대 길이에 도달해 끝까지 완성되지 않음'
            case['results'][key]={'output':r['output_text'],'status':r['status'],'error':r.get('error'),'error_label':error_label,
                'changed':r['output_text'] is not None and r['output_text']!=case['input'],
                'exact_reference_match':r['output_text']==case['reference'],'selected':sorted(selected),
                'directional_selected':sorted(directional&selected),'directional_apply_proposed':sorted(directional&apply_selected),
                'directional_applied':sorted(directional&set(r.get('applied_rules',[]))),
                'applied':r.get('applied_rules',[]),'edits':final.get('edits',[]),'proposed_edits':proposed.get('edits',[]),
                'reason':final.get('reason',proposed.get('reason','')),'seconds':r['incremental_generation_seconds'],
                'calls':len(r['calls']),'tokens':sum((c.get('usage') or {}).get('total_tokens',0) for c in r['calls']),
                'calls_without_usage':sum(not c.get('usage') for c in r['calls']),
                'held_by_model':r.get('held_by_model',0),'held_by_program':r.get('held_by_program',0),'record':str(folder.relative_to(ROOT))}
            if key.startswith('v3'):
                for ed in final.get('edits',[]):
                    bindings=ed.get('bindings',[])
                    if ed.get('outcome')=='applied' and len(bindings)==1 and bindings[0]['card_id'] in ('GS_END_DECL_YE_01','GS_ENDRULE_YO_COMPOSE') and ed['before'].endswith('요'):
                        expected=ed['before'][:-1]+'예'
                        preservation.append({'id':row['id'],'condition':key,'card_id':bindings[0]['card_id'],'before':ed['before'],
                            'actual':ed['after'],'literal_operation_expected':expected,'instruction_followed':ed['after']==expected,
                            'check_scope':'literal 요-only replacement stated on v3 card, not overall dialect naturalness'})
        if row['analysis_ok']:
            for arm in ('single','multi'):
                if not all('v'+n+'_'+arm in case['results'] for n in ('2','3')):continue
                folders=[ROOT/'experiments/runs'/active['runs']['v'+n+'_'+arm]/'private/records'/row['id'] for n in ('2','3')]
                for name in ('input.json','morphology.json','analysis_call/parsed.json','retrieval_raw.json'):
                    assert (folders[0]/name).read_bytes()==(folders[1]/name).read_bytes()
                a,b=[read(f/'reference_packet.json') for f in folders]
                assert [c['id'] for c in a['cards']]==[c['id'] for c in b['cards']]
                assert [c['forms'] for c in a['cards']]==[c['forms'] for c in b['cards']]
                assert {k:v for k,v in a.items() if k not in ('cards','contract_context')}=={k:v for k,v in b.items() if k not in ('cards','contract_context')}
                ra,rb=[read(f/'agent_call/request.json') for f in folders]
                assert ra['messages'][0]==rb['messages'][0]
                assert {k:v for k,v in ra.items() if k!='messages'}=={k:v for k,v in rb.items() if k!='messages'}
                verified_pairs+=1
        cases.append(case)
    summary={}
    for key in LABELS:
        rows=[c['results'][key] for c in cases if key in c['results']]
        summary[key]={'n':len(rows),'changed':sum(r['changed'] for r in rows),
            'unchanged':sum(r['output'] is not None and not r['changed'] for r in rows),'no_output':sum(r['output'] is None for r in rows),
            'directional_selected':sum(bool(r['directional_selected']) for r in rows),
            'directional_apply_proposed':sum(bool(r['directional_apply_proposed']) for r in rows),
            'directional_applied':sum(bool(r['directional_applied']) for r in rows),
            'exact_reference_match':sum(r['exact_reference_match'] for r in rows),
            'physical_calls':sum(r['calls'] for r in rows),'tokens':sum(r['tokens'] for r in rows),
            'calls_without_usage':sum(r['calls_without_usage'] for r in rows),
            'held_by_model':sum(r['held_by_model'] for r in rows),'held_by_program':sum(r['held_by_program'] for r in rows),
            'sum_generation_seconds':sum(r['seconds'] for r in rows),
            'errors':dict(collections.Counter(r['error'] for r in rows if r['error'])),
            'issues':dict(collections.Counter(i.get('code',str(i)) if isinstance(i,dict) else i for r in rows for ed in r['edits'] for i in ed.get('issues',[])))}
    paired={}
    for arm in ('single','multi'):
        pairs=[c for c in cases if all(v+'_'+arm in c['results'] for v in ('v2','v3'))]
        paired[arm]={'n':len(pairs),'different_output':sum(c['results']['v2_'+arm]['output']!=c['results']['v3_'+arm]['output'] for c in pairs),
            'both_no_output':sum(all(c['results'][v+'_'+arm]['output'] is None for v in ('v2','v3')) for c in pairs)}
    resources=read(batch/'resources.json') if (batch/'resources.json').exists() else None
    data={'complete':all(v['n']==50 for v in summary.values()) and resources is not None,'conditions':summary,'paired':paired,
        'verified_requests':verified_requests,'verified_pairs':verified_pairs,'resources':resources,'human_naturalness_score':None,
        'note':'Changed output and exact reference match are not naturalness accuracy; repeated exposed regression inputs.'}
    save(BASE/'private/cases.json',cases);save(BASE/'private/summary.json',data);save(BASE/'private/preservation_diagnostic.json',preservation)
    h='<h1>카드 내용을 고치면 출력이 좋아질까?</h1><p class="lead">같은 문장, 같은 분석, 같은 카드 목록을 주고 <b>카드 설명만 이전 버전과 새 버전으로 바꿨습니다.</b></p>'
    h+='<p>'+('실험 완료 · 50문장 × 4조건' if data['complete'] else '실험 진행 중 · 저장된 결과만 표시')+' · <a href="/work">실시간 진행 보기</a></p>'
    findings=BASE/'private/findings.json'
    if findings.exists():
        h+='<section><h2>결론부터 보기</h2>'
        for f in read(findings):h+='<article><h3>'+E(f['title'])+'</h3><p>'+E(f['text'])+'</p><small>'+E(f.get('evidence',''))+'</small></article>'
        h+='</section>'
    h+='<div class="flow">고정한 50개 입력·분석·카드 목록<br>↓<br><b>이전 카드 ↔ 새 카드</b><br>↓<br>Single: 한 번에 수정 / Multi: 수정 계획 → 문장 생성<br>↓<br>실제 출력과 막힌 지점 비교</div>'
    h+='<h2>전체 결과</h2><p><b>바뀐 문장 수는 정답 수가 아닙니다.</b> 원문 유지에는 모델의 유지 판단과 검사에서 수정이 막힌 경우가 함께 포함됩니다.</p><table><thead><tr><th>실행 방식</th><th>처리</th><th>문장이 바뀜</th><th>원문 유지</th><th>출력 없음</th></tr></thead><tbody>'
    for k,v in summary.items():h+='<tr><th>'+LABELS[k]+'</th>'+''.join('<td>'+str(v[x])+'</td>' for x in ('n','changed','unchanged','no_output'))+'</tr>'
    h+='</tbody></table><p>분석에 실패했던 QUAL002 1건은 모든 조건에서 실패로 유지했습니다. 나머지 49건에서 생성 모델을 실행했습니다.</p>'
    diagnostic=BASE/'private/diagnostic_checks.json'
    if diagnostic.exists():
        h+='<section><h2>실패 원인을 실제로 확인한 예</h2><p>카드는 <b>“끝의 요만 예로 바꾸고 앞부분은 유지”</b>라고 지시했습니다. 그러나 모델과 활용 조합 코드는 <b>어요 전체를 예로 바꿨습니다.</b></p><table><tr><th>원문</th><th>카드 지시를 그대로 따르면</th><th>Qwen 실제 결과</th><th>현재 검사</th></tr>'
        for item in read(diagnostic):
            for c in item['changes']:h+='<tr><td>'+E(c['input'])+'</td><td>'+E(c['card_instruction_expected'])+'</td><td>'+E(c['model_output'])+'</td><td>두 표현을 모두 통과시킴</td></tr>'
        h+='</table><p><b>확인된 문제:</b> 카드의 “어를 남긴다”는 설명을 실제 조합·검사가 지키게 만들지 못했습니다. 카드 내용을 더 길게 쓰는 것만으로 해결되지 않는 부분입니다.</p>'
        if preservation:
            h+='<p>현재 저장된 새 카드 결과에서 이 두 카드로 실제 반영된 “요로 끝나는 수정 항목” '+str(len(preservation))+'개를 확인했고, 그중 '+str(sum(not x['instruction_followed'] for x in preservation))+'개가 “요만 교체” 지시와 달랐습니다. 동일 입력의 Single/Multi는 별도 항목이며, 자연스러움 점수가 아닙니다.</p>'
        h+='<small>“카드 지시를 그대로 따르면” 열은 Codex가 요 한 글자만 바꿔 만든 오프라인 확인용 후보입니다. 추가 Qwen 출력이나 사람의 자연스러움 평가 결과가 아닙니다. 실제 실험 출력은 수정하지 않았습니다.</small></section>'
    h+='<details><summary>바꾼 10개 카드가 실제로 사용됐나?</summary><p>이전 카드와 새 카드에서 같은 10개 ID를 추적합니다. 선택에는 유지·보류 판단도 포함되므로 “바꾸겠다고 선택”과 “실제 반영”을 구분했습니다.</p><table><tr><th>방식</th><th>판단에 사용</th><th>바꾸겠다고 선택</th><th>최종 반영</th></tr>'
    for k,v in summary.items():h+='<tr><th>'+LABELS[k]+'</th>'+''.join('<td>'+str(v[x])+'</td>' for x in ('directional_selected','directional_apply_proposed','directional_applied'))+'</tr>'
    h+='</table><p>각 수치는 해당 카드가 하나 이상 사용된 문장 수입니다. 적용됐어도 활용이 틀리거나 부자연스러울 수 있습니다.</p></details>'
    h+='<details><summary>어디서 수정이 멈췄나?</summary><p>아래는 입력 문장 수가 아니라 각 문장 안의 수정 항목 수입니다. 한 문장에 여러 항목이 있을 수 있습니다.</p><table><tr><th>방식</th><th>모델이 보류</th><th>프로그램 검사에서 보류</th></tr>'
    for k,v in summary.items():h+='<tr><th>'+LABELS[k]+'</th><td>'+str(v['held_by_model'])+'</td><td>'+str(v['held_by_program'])+'</td></tr>'
    h+='</table>'
    for k,v in summary.items():
        if v['errors'] or v['issues']:
            h+='<h3>'+LABELS[k]+'</h3><ul>'
            for err,n in v['errors'].items():h+='<li>출력 중단 '+str(n)+'건: '+E(FRIENDLY.get(err,err))+'</li>'
            for err,n in sorted(v['issues'].items(),key=lambda x:-x[1])[:5]:h+='<li>수정 보류 지적 '+str(n)+'회: '+E(ISSUES.get(err,err))+'</li>'
            h+='</ul>'
    h+='</details>'
    h+='<h2>50문장 나란히 보기</h2><p>먼저 Single 결과를 보세요. 각 문장을 펼치면 Multi와 선택 카드·수정 제안·막힌 이유까지 확인할 수 있습니다.</p><div class="filters"><input id="search" placeholder="문장 또는 ID 검색" aria-label="문장 검색"><select id="filter" aria-label="결과 필터"><option value="all">전체 50문장</option><option value="different">새 카드로 출력이 달라진 문장</option><option value="failure">새 카드 출력 실패</option><option value="unchanged">새 카드 Single 원문 유지</option></select><span id="count"></span></div>'
    for c in cases:
        outputs=c['results'];different=any('v2_'+a in outputs and 'v3_'+a in outputs and outputs['v2_'+a]['output']!=outputs['v3_'+a]['output'] for a in ('single','multi'))
        failure=any(outputs.get('v3_'+a,{}).get('output','pending') is None for a in ('single','multi'))
        unchanged=outputs.get('v3_single',{}).get('output')==c['input']
        h+='<article class="case" data-search="'+E(c['id']+' '+c['input'])+'" data-different="'+str(int(different))+'" data-failure="'+str(int(failure))+'" data-unchanged="'+str(int(unchanged))+'"><h3>'+E(c['id'])+'</h3><p><b>표준어:</b> '+E(c['input'])+'</p><p class="reference"><b>사용자 승인 표현:</b> '+E(c['reference'])+'</p><table>'
        for k in ('v2_single','v3_single'):
            r=outputs.get(k);h+='<tr><th>'+LABELS[k]+'</th><td>'+E(r['output'] if r else '실행 대기')+'</td></tr>'
        h+='</table><details><summary>Multi 결과와 처리 과정 보기</summary><table>'
        for k in ('v2_multi','v3_multi'):
            r=outputs.get(k);h+='<tr><th>'+LABELS[k]+'</th><td>'+E(r['output'] if r else '실행 대기')+'</td></tr>'
        h+='</table>'
        for k,r in outputs.items():
            h+='<details><summary>'+LABELS[k]+' · 선택·수정·검사</summary><p><b>모델이 적은 판단:</b> '+E(r['reason'])+'</p>'
            if r['error']:h+='<p class="error"><b>출력 중단:</b> '+E(r['error_label'])+'</p>'
            h+='<p><b>실제 반영 카드:</b> '+E(', '.join(by[x]['title']+' ['+x+']' for x in r['applied']) or '없음')+'</p>'
            if r['edits']:
                h+='<table><tr><th>원문 부분</th><th>모델 제안</th><th>최종 문장에 남은 표현</th><th>처리·막힌 이유</th></tr>'
                for ed in r['edits']:
                    issues='; '.join(ISSUES.get(i.get('code'),i.get('message') or i.get('code') or str(i)) if isinstance(i,dict) else ISSUES.get(i,i) for i in ed.get('issues',[]))
                    applied=ed.get('outcome')=='applied'
                    actual=ed.get('after') if applied else ed.get('before')
                    state='반영' if applied else '보류하여 원문 유지' if ed.get('outcome') in ('held','needs_review') else '원문 유지'
                    h+='<tr><td>'+E(ed.get('before'))+'</td><td>'+E(ed.get('proposed_after',ed.get('after')))+'</td><td>'+E(actual)+'</td><td>'+E(state+' · '+(issues or '검사 지적 없음'))+'</td></tr>'
                h+='</table>'
            elif r['proposed_edits']:
                h+='<p>아래는 실패 전에 모델이 제안한 내용이며 실제 반영된 문장이 아닙니다.</p><ul>'
                for ed in r['proposed_edits']:h+='<li>'+E(ed.get('instruction',''))+(' → '+E(ed['after']) if ed.get('after') else '')+'</li>'
                h+='</ul>'
            h+='</details>'
        h+='</details></article>'
    h+='<h2>호출·시간</h2><table><tr><th>방식</th><th>실제 호출</th><th>보고된 토큰</th><th>입력별 처리 시간 합계</th></tr>'
    for k,v in summary.items():h+='<tr><th>'+LABELS[k]+'</th><td>'+str(v['physical_calls'])+'</td><td>'+format(v['tokens'],',')+'</td><td>'+str(round(v['sum_generation_seconds'],1))+'초</td></tr>'
    h+='</table><p>이전 분석 비용은 제외했습니다. 병렬 실행이므로 입력별 시간 합계는 사용자가 기다린 전체 시간과 다릅니다. 공유 서버의 부하도 영향을 줍니다.</p>'
    if resources:h+='<p><b>전체 실제 실행:</b> '+str(round(resources['wall_seconds']/60,1))+'분 · '+str(resources['physical_api_attempts'])+'회 호출 · '+format(resources['physical_total_tokens'],',')+'토큰</p>'
    h+='<details><summary>비교 조건과 한계</summary><ul><li>26문장은 직전 카드 전달 실험의 목록, 나머지는 기존 목록을 고정했습니다. 각 문장의 이전/새 카드 조건에는 같은 목록을 줬습니다.</li><li>카드 ID·순서·형태 목록은 같고, 설명·조건과 이에 따른 요청 식별값만 다릅니다. 프롬프트와 검사 코드는 같습니다.</li><li>새 버전은 관리 정보 정리와 10개 카드의 변환 안내를 함께 바꿨습니다. 이번 비교만으로 두 변경의 효과를 따로 분리할 수는 없습니다.</li><li>문장별 실행은 조건당 1회입니다. 같은 설정에서도 모델 출력이 달라질 수 있습니다.</li><li>이 50문장은 이미 수정·분석에 활용한 회귀 자료입니다. 처음 보는 문장에서의 성능으로 주장하지 않습니다.</li><li>승인 표현은 비교 화면에만 표시합니다. 생성 요청에 정답 문장 전체를 넣지 않았습니다.</li><li>자연스러움에 대한 새 사람 평가는 아직 없습니다.</li></ul><p>요청 검증 '+str(verified_requests)+'건 · 짝 비교 검증 '+str(verified_pairs)+'쌍 · 실행 ID '+E(active['batch'])+'</p></details>'
    css='body{margin:0;background:#f5f7fa;color:#193047;font:17px/1.7 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:30px}h1{font-size:30px}h2{margin-top:32px}h3{font-size:19px}.lead,.flow,.reference{padding:16px;background:#eaf2ff;border-radius:10px}.flow{text-align:center;background:#e9f5ef}.case,details,section{background:white;border:1px solid #dce3eb;border-radius:10px;padding:16px;margin:14px 0}summary{cursor:pointer;font-weight:650}table{width:100%;border-collapse:collapse;margin:12px 0}th,td{border:1px solid #dbe1e8;padding:11px;vertical-align:top;text-align:left;overflow-wrap:anywhere}th{background:#f0f4f8}small{color:#56697b}.error{background:#fff1ec;padding:12px}.filters{position:sticky;top:0;background:#f5f7fa;padding:12px 0;display:flex;gap:10px;flex-wrap:wrap}input,select{font:inherit;padding:8px;max-width:95%}[hidden]{display:none!important}@media(max-width:700px){main{padding:12px}th,td{padding:6px;font-size:14px}}'
    js="const q=document.querySelector('#search'),f=document.querySelector('#filter'),cards=[...document.querySelectorAll('.case')];function update(){let n=0;for(const c of cards){let ok=c.dataset.search.toLowerCase().includes(q.value.toLowerCase())&&(f.value==='all'||c.dataset[f.value]==='1');c.hidden=!ok;n+=ok;}document.querySelector('#count').textContent=n+'문장 표시';}q.addEventListener('input',update);f.addEventListener('change',update);update();"
    (BASE/'private/report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>새 카드 실제 비교 실험</title><link rel="stylesheet" href="report.css"><main>'+h+'</main><script src="report.js"></script></html>',encoding='utf-8')
    (BASE/'private/report.css').write_text(css,encoding='utf-8');(BASE/'private/report.js').write_text(js,encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
