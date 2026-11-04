"""Trace-only evaluation. User-approved answers are references, not exact-match-only gold."""
import collections,html,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,sha,dumps,load_jsonl

def main():
    active=read(BASE/'private/active_run.json');plan=read(BASE/'private/plan.json')
    root=Path(active['root']);gold={x['id']:x for x in load_jsonl(ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl')}
    cards={x['id']:x for x in read(ROOT/'knowledge/authored/kg_cards_20261028_v2/cards.json')['cards']}
    cases=[];summary={};verified=0
    for row in plan['rows']:
        c={'id':row['id'],'input':row['input'],'reference':gold[row['id']]['reference'],'disposition':row['disposition'],
            'swaps':[dict(s,added_title=cards[s['added']]['title'],removed_title=cards[s['removed']]['title']) for s in row['swaps']],
            'promoted':row['promoted'],'results':{},'historical':{}}
        for arm in ['single','multi']:
            old=ROOT/'experiments/runs'/f"{plan['baseline_batch']}_cards_{arm}_regression/private/records"/row['id']/'result.json'
            c['historical'][arm]=read(old)
        if row['disposition']=='paired_rerun':
            for key,run in active['runs'].items():
                folder=ROOT/'experiments/runs'/run/'private/records'/row['id']
                if not (folder/'result.json').exists():continue
                r=read(folder/'result.json');final=read(folder/'final_plan.json') if (folder/'final_plan.json').exists() else {}
                agent=read(folder/'agent_call/parsed.json') if (folder/'agent_call/parsed.json').exists() else {}
                packet=read(folder/'reference_packet.json')
                # Actual request bytes after JSON parsing must agree with saved packet.
                request=read(folder/'agent_call/request.json') if (folder/'agent_call/request.json').exists() else None
                if request:
                    assert json.loads(request['messages'][1]['content'])==packet
                    assert len(packet['cards'])==48
                    assert all(x==cards[x['id']] for x in packet['cards'])
                    verified+=1
                agent_cards={b.get('card_id') for e in agent.get('edits',[]) for b in e.get('bindings',[])}
                promoted_selected=sorted(set(row['promoted'])&agent_cards)
                promoted_applied=sorted(set(row['promoted'])&set(r.get('applied_rules',[])))
                c['results'][key]={'output':r['output_text'],'status':r['status'],'error':r.get('error'),
                    'selected_rules':r['selected_rules'],'applied_rules':r.get('applied_rules',[]),
                    'promoted_selected':promoted_selected,'promoted_applied':promoted_applied,
                    'promoted_apply_proposed':sorted(set(row['promoted'])&{b.get('card_id') for e in agent.get('edits',[]) if e.get('action')=='apply' for b in e.get('bindings',[])}),
                    'reason':final.get('reason',agent.get('reason')),'edits':final.get('edits',[]),
                    'agent_reason':agent.get('reason'),'agent_edits':agent.get('edits',[]),
                    'physical_calls':len(r['calls']),'tokens':sum((x.get('usage') or {}).get('total_tokens',0) for x in r['calls']),
                    'reported_seconds':r['incremental_generation_seconds'],
                    'exact_reference_match':r['output_text']==c['reference'],
                    'output_changed_from_input':r['output_text'] is not None and r['output_text']!=c['input'],
                    'record':str(folder.relative_to(ROOT))}
            for arm in ['single','multi']:
                if 'control_'+arm in c['results'] and 'promoted_'+arm in c['results']:
                    a=ROOT/'experiments/runs'/active['runs']['control_'+arm]/'private/records'/row['id']
                    b=ROOT/'experiments/runs'/active['runs']['promoted_'+arm]/'private/records'/row['id']
                    for name in ['input.json','morphology.json','analysis_call/parsed.json','retrieval_raw.json']:
                        assert (a/name).read_bytes()==(b/name).read_bytes(),(row['id'],name)
                    pa=read(a/'reference_packet.json');pb=read(b/'reference_packet.json')
                    assert {k:v for k,v in pa.items() if k not in ('cards','contract_context')}=={k:v for k,v in pb.items() if k not in ('cards','contract_context')}
                    assert pa['contract_context']['user_restrictions']==pb['contract_context']['user_restrictions']
                    ra=read(a/'agent_call/request.json');rb=read(b/'agent_call/request.json')
                    assert ra['messages'][0]==rb['messages'][0]
                    assert {k:v for k,v in ra.items() if k!='messages'}=={k:v for k,v in rb.items() if k!='messages'}
        cases.append(c)
    for key in active['runs']:
        rows=[c['results'][key] for c in cases if key in c['results']]
        summary[key]={'n':len(rows),'changed':sum(r['output_changed_from_input'] for r in rows),
            'unchanged':sum(r['output'] is not None and not r['output_changed_from_input'] for r in rows),
            'no_output':sum(r['output'] is None for r in rows),'promoted_selected':sum(bool(r['promoted_selected']) for r in rows),
            'promoted_applied':sum(bool(r['promoted_applied']) for r in rows),
            'promoted_apply_proposed':sum(bool(r['promoted_apply_proposed']) for r in rows),
            'exact_reference_match':sum(r['exact_reference_match'] for r in rows),'physical_calls':sum(r['physical_calls'] for r in rows),
            'tokens':sum(r['tokens'] for r in rows),'seconds':sum(r['reported_seconds'] for r in rows),
            'errors':dict(collections.Counter(r['error'] for r in rows if r['error'])),
            'issues':dict(collections.Counter(i.get('code',str(i)) if isinstance(i,dict) else i for r in rows for e in r['edits'] for i in e.get('issues',[])))}
    paired={}
    for arm in ['single','multi']:
        pairs=[c for c in cases if all(k+'_'+arm in c['results'] for k in ['control','promoted'])]
        paired[arm]={'pairs':len(pairs),'different_outputs':sum(c['results']['control_'+arm]['output']!=c['results']['promoted_'+arm]['output'] for c in pairs),
            'same_as_historical_control':sum(c['results']['control_'+arm]['output']==c['historical'][arm]['output_text'] for c in pairs)}
    complete=all(v['n']==plan['eligible_inputs'] for v in summary.values()) and (root/'resources.json').exists()
    data={'complete':complete,'all_inputs':50,'rerun_inputs':26,'unchanged_delivery_inputs':23,'cached_analysis_failure_inputs':1,
        'conditions':summary,'paired':paired,'verified_actual_requests':verified,
        'resource':read(root/'resources.json') if (root/'resources.json').exists() else None,
        'quality_accuracy':None,'interpretation':'Selected/applied/changed are not quality scores. Exact reference match is descriptive; alternate valid outputs allowed.'}
    save(BASE/'private/results.json',cases);save(BASE/'private/summary.json',data)
    E=lambda x:html.escape(str(x if x is not None else '출력 없음'))
    labels={'control_single':'Single · 기존 전달','promoted_single':'Single · 변경 전달','control_multi':'Multi · 기존 전달','promoted_multi':'Multi · 변경 전달'}
    h='<h1>카드를 전달하면 달라질까?</h1><p class="lead"><strong>사용자가 승인한 정답 50개를 등록했습니다.</strong><br>문헌과 KG는 그대로 두고, 빠졌던 카드를 전달 목록에 넣어 비교했습니다.</p>'
    h+='<p>'+('실행·기록 완료' if complete else '실험 진행 중 · 아래는 현재까지 저장된 결과')+' · 50개 전체 확인 / 전달 변경 26개 / 변경 없음 23개 / 기존 분석 실패 1개</p>'
    h+='<div class="flow">같은 원문·분석·KG<br>↓<br>기존 48개 카드 ↔ 관련 카드를 넣은 48개<br>↓<br>같은 Qwen·지시·검사로 Single / Multi 비교</div>'
    h+='<h2>숫자는 결과의 상태입니다</h2><p>“문장이 바뀜”과 “올바른 방언”은 다릅니다. 아래 수치는 정답률이 아닙니다.</p><table><tr><th>방식</th><th>처리</th><th>원문과 다름</th><th>원문 유지</th><th>출력 없음</th><th>추가 카드 선택 / 적용</th></tr>'
    for k,v in summary.items():h+='<tr><td>'+E(labels[k])+'</td>'+''.join('<td>'+E(v[x])+'</td>' for x in ['n','changed','unchanged','no_output'])+'<td>'+E(str(v['promoted_selected'])+' / '+str(v['promoted_applied']))+'</td></tr>'
    h+='</table><p>추가 카드 선택·적용 수는 그 카드가 하나 이상 선택·적용된 문장 수입니다. 선택은 유지·보류 판단에 사용한 경우와 이후 실패한 계획도 포함합니다. 기존 전달에는 해당 카드가 없으므로 0입니다.</p>'
    finding=BASE/'private/findings.json'
    if finding.exists():
        findings=read(finding);h+='<h2>이번에 알게 된 것</h2>'
        for f in findings:h+='<article><h3>'+E(f['title'])+'</h3><p>'+E(f['description'])+'</p><p class="small">'+E(f.get('evidence',''))+'</p></article>'
    h+='<details><summary>카드를 어떻게 교체했나?</summary><p>승인 정답에서 확인한 표현과 관련된 기존 카드 중, 실제 조회됐지만 전달되지 않았던 카드만 넣었습니다. 한 문장당 1~3개이며 총 53개 자리입니다. 기존 분석에 연결된 검토 후보와 차단 카드는 보호하고, 나머지 중 점수가 낮은 카드를 교체했습니다. 다른 카드의 순서는 그대로입니다.</p><p>추가와 제거가 함께 일어나므로 추가 카드 하나만의 효과라고 단정하지 않습니다. 카드 수는 같지만 글자 수·토큰 수까지 같은 것은 아닙니다. 완성 정답 문장이나 Claude 답변은 Qwen 요청에 넣지 않았습니다.</p><p>정답을 참고해 후보를 골랐기 때문에 새로운 입력용 검색기 성능을 평가한 실험도 아닙니다. 아직 자동 검색기와 KG를 바꾸지 않았습니다.</p></details>'
    h+='<h2>50문장 확인</h2><p>문장을 펼치면 승인 정답과 결과를 볼 수 있습니다. 새 실험이 없는 24개는 이전 결과임을 표시했습니다.</p>'
    for c in cases:
        h+='<details class="case"><summary>'+E(c['id']+' · '+c['input'])+'</summary><p class="reference"><strong>승인 정답:</strong> '+E(c['reference'])+'</p>'
        if c['disposition']!='paired_rerun':
            reason='기존 문장 분석이 실패하여 조회 전에 종료됨' if c['disposition']=='cached_analysis_failed' else '이번 대상인 해예체 관련 카드의 전달 변경 없음'
            h+='<p>'+E(reason)+' · 새 모델 실행 없음</p><table>'
            for a in ['single','multi']:h+='<tr><th>이전 '+a.title()+'</th><td>'+E(c['historical'][a]['output_text'])+'</td></tr>'
            h+='</table>'
        else:
            h+='<table><tr><th>방식</th><th>실제 결과</th><th>추가 카드 사용</th></tr>'
            for k in labels:
                v=c['results'].get(k)
                if not v:h+='<tr><th>'+E(labels[k])+'</th><td>실행 중 / 대기</td><td>—</td></tr>';continue
                h+='<tr><th>'+E(labels[k])+'</th><td>'+E(v['output'])+'</td><td>'+E('적용' if v['promoted_applied'] else '선택했으나 미적용' if v['promoted_selected'] else '미선택')+'</td></tr>'
            h+='</table><details><summary>교체 카드와 Qwen 판단·검사 보기</summary><table><tr><th>넣은 카드</th><th>뺀 카드</th></tr>'
            for s in c['swaps']:h+='<tr><td>'+E(s['added_title'])+'<br><small>'+E(s['added'])+'</small></td><td>'+E(s['removed_title'])+'<br><small>'+E(s['removed'])+'</small></td></tr>'
            h+='</table>'
            for k,v in c['results'].items():
                h+='<h3>'+E(labels[k])+'</h3><p><strong>모델이 적은 이유:</strong> '+E(v['agent_reason'])+'</p>'
                if v['error']:
                    friendly={'binding_not_ending':'어미로 지정한 위치를 형태소 분석기는 조사 등 다른 종류로 분류함','invalid_target_index':'카드에 없는 형태 번호를 지정함','stale_worker_plan':'생성 응답의 계획 번호가 요청한 계획과 다름','CallError:200':'응답이 길이 제한에 도달해 완료되지 않음'}.get(v['error'],v['error'])
                    h+='<p>실행 오류: '+E(friendly)+'</p>'
                    if not v['edits'] and v['agent_edits']:
                        h+='<p>아래는 전체 계획이 실패하기 전 모델의 제안입니다. 최종 반영된 내용은 아닙니다.</p><ul>'
                        for e in v['agent_edits']:h+='<li>'+E(e.get('instruction',''))+(' → '+E(e['after']) if e.get('after') else '')+'</li>'
                        h+='</ul>'
                h+='<table><tr><th>부분</th><th>모델 제안 → 최종</th><th>처리·검사</th></tr>'
                for e in v['edits']:h+='<tr><td>'+E(e.get('before'))+'</td><td>'+E(e.get('proposed_after',e.get('after')))+' → '+E(e.get('after'))+'</td><td>'+E({'applied':'반영','kept':'유지','held':'보류','needs_review':'보류'}.get(e.get('outcome'),e.get('outcome')))+'<br>'+E('; '.join((i.get('message') or i.get('code') or str(i)) if isinstance(i,dict) else i for i in e.get('issues',[])))+'</td></tr>'
                h+='</table>'
            h+='</details>'
        h+='</details>'
    h+='<details><summary>비교 조건·재현 기록</summary><p>기존 방식도 같은 시간대에 재실행했습니다. 이전 문장 분석·조회 결과를 고정해 재사용했습니다. 26개 × 4조건 = 104개 결과이며 Multi의 추가 생성 호출 수는 계획에 따라 다릅니다. 반복 측정은 1회로, 서버 비결정성과 순서 효과를 완전히 배제하지 못합니다.</p><p>새 출력의 자연스러움에 대한 사용자 평가는 아직 없습니다. 승인 정답과 글자가 다르다는 이유만으로 오답 처리하지 않았습니다. 50개는 개발·회귀 자료이며 독립 최종 평가셋이 아닙니다.</p>'
    if data['resource']:
        z=data['resource'];h+='<p>실제 모델 호출 '+E(z['physical_api_attempts'])+'회 · 토큰 '+E(format(z['physical_total_tokens'],','))+'개 · 실행 '+E(round(z['wall_seconds']/60,1))+'분. 문장 분석 신규 호출 0회.</p>'
    h+='<p>실행 묶음: '+E(active['batch'])+'</p></details>'
    css='body{font:17px/1.75 system-ui,sans-serif;background:#f5f7fb;color:#173047;margin:0}main{max-width:1180px;margin:auto;padding:28px}h1{font-size:30px}.lead,.flow,.reference{padding:18px;border-radius:10px;background:#eaf1ff}.flow{text-align:center;background:#e8f4f0}table{border-collapse:collapse;width:100%;margin:15px 0;background:white}td,th{padding:12px;border:1px solid #d7e0eb;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#eef3f8}details,article{background:white;border:1px solid #dbe3ee;border-radius:10px;padding:16px;margin:12px 0}summary{font-weight:650;cursor:pointer}small,.small{font-size:13px;color:#425b70}h2{margin-top:30px}h3{font-size:19px}@media(max-width:650px){main{padding:10px}td,th{padding:6px;font-size:14px}}'
    (BASE/'private/report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>카드 전달 비교 실험</title><link rel="stylesheet" href="report.css"><main>'+h+'</main></html>',encoding='utf-8')
    (BASE/'private/report.css').write_text(css,encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
