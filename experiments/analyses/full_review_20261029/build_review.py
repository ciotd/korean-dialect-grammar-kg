"""Rebuild the full 50-input diagnostic view from immutable run records/reviews."""
import collections, hashlib, html, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8')
BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[2]
PRIVATE=BASE/'private'
def load(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def h(x):return html.escape(str(x if x is not None else ''))
def list_html(values):return '<ul>'+''.join('<li>'+h(x)+'</li>' for x in values)+'</ul>'
packets=[load(p) for p in sorted((PRIVATE/'packets').glob('B??.json'))]
source_cases=[c for p in packets for c in p['cases']]
assert len(source_cases)==50 and len({c['id'] for c in source_cases})==50
notes=load(BASE/'lead_observations.json')['cases'];assert set(notes)=={c['id'] for c in source_cases}
old=load(PROJECT/'experiments/analyses/error_triage_20261029/private/cases.json')['records']
human={(r['id'],r['arm']):r['human_rating'] for r in old if r.get('human_rating')}
feedback=load(PROJECT/'experiments/analyses/error_triage_20261029/private/human_feedback/20261029_reply01.json')
preferences={x['id']:x for x in feedback['preferences']}
reviews={who:{c['id']:c for f in sorted((PRIVATE/'reviews'/who).glob('B??.json')) for c in load(f)['cases']} for who in ['codex','claude']}
counts={who:len(rows) for who,rows in reviews.items()}
lead_status=load(BASE/'lead_reconciliation.json')
lead_common=set(lead_status['read_batches']['codex']) & set(lead_status['read_batches']['claude'])
lead_crosschecked=sum(len(p['cases']) for p in packets if p['batch_id'] in lead_common)
selection_diagnostics=load(PRIVATE/'selection_diagnostics.json')
cards={c['id']:c for c in load(PROJECT/'knowledge/authored/kg_cards_20261028_v2/cards.json')['cards']}
metrics={a:collections.Counter() for a in ['single','multi']}
checks=[];casebook=[];jamo=[];noop=[];failures=[];all_final_edits=0
run_batch='20261028T011829489985Z'
for c in source_cases:
    r={'id':c['id'],'input':c['input'],'lead_observations':notes[c['id']],
       'reviewers':{who:rows.get(c['id']) for who,rows in reviews.items()},'arms':{},'user_preference':preferences.get(c['id']),
       'shared_analysis':c['shared_analysis'],'words':c['words']}
    for a,v in c['arms'].items():
        source=PROJECT/v['source_record_dir'];actual=load(source/'result.json')
        assert actual['input_text']==c['input'] and actual['output_text']==v['output']
        actual_packet=load(source/'reference_packet.json')
        assert all(card==cards[card['id']] for card in actual_packet['cards'])
        outcome='no_output' if v['output'] is None else ('unchanged' if v['output']==c['input'] else 'changed')
        metrics[a][outcome]+=1
        if outcome=='no_output':
            length_calls=[x for x in v['call_facts'] if x['finish_reason']=='length']
            if length_calls: category='response_length';metrics[a]['response_length']+=1;metrics[a]['length_with_trailing_whitespace']+=any(x.get('trailing_whitespace',0)>1000 for x in length_calls)
            elif v['error']=='after_not_single_word':category='single_word_constraint';metrics[a][category]+=1
            elif v['error']=='unretrieved_rule_reference':
                empty=[e['word_id'] for e in (v['draft'] or {}).get('edits',[]) if not e.get('rule_ids')]
                missing=sorted({k for e in (v['draft'] or {}).get('edits',[]) for k in e.get('rule_ids',[]) if k not in c['supplied_card_ids']})
                assert empty and not missing
                category='empty_rule_ids';metrics[a][category]+=1
            else:category='other';metrics[a]['other_failure']+=1
            failures.append({'id':c['id'],'arm':a,'category':category,'error':v['error'],'call_facts':v['call_facts']})
        rating=human.get((c['id'],a))
        if rating:assert rating['rated_output']==v['output'];metrics[a]['human_rated_outputs']+=1
        final=v['final_plan']
        if final:
            restored=c['input']
            for e in reversed(final['edits']):
                assert c['input'][e['span'][0]:e['span'][1]]==e['before']
                restored=restored[:e['span'][0]]+e['after']+restored[e['span'][1]:]
                all_final_edits+=1
                if e['before']==e['after']:noop.append({'id':c['id'],'arm':a,'word_id':e['word_id'],'rule_ids':e['rule_ids']})
            assert restored==v['output']
        chars=sorted(set(re.findall('[\u1100-\u11ff\u3130-\u318f]',v['output'] or '')))
        if chars:jamo.append({'id':c['id'],'arm':a,'characters':chars,'output':v['output']})
        r['arms'][a]={**v,'outcome':outcome,'human_rating':rating,'standalone_jamo':chars}
    casebook.append(r)
source_manifest=load(PRIVATE/'manifest.json')
changed_sources=[p for p,sha in source_manifest['source_sha256'].items() if hashlib.sha256((PROJECT/p).read_bytes()).hexdigest()!=sha]
assert not changed_sources
assert len(human)==20
totals=sum((v for v in metrics.values()),collections.Counter())
summary={'created_utc':datetime.now(timezone.utc).isoformat(),'source_batch':run_batch,'dataset':'standard_inputs_50_20261023_v1',
         'inputs':50,'executions':100,'independent_review_coverage':counts,'lead_first_pass_inputs':50,
         'metrics':{a:dict(v) for a,v in metrics.items()},'totals':dict(totals),'standalone_jamo_outputs':jamo,
         'final_edits':all_final_edits,'unchanged_edits':noop,'failures':failures,
         'human_evaluation_is_partial':True,'naturalness_accuracy_calculated':False,'new_qwen_calls':0,'runtime_or_kg_modified':False}
summary['historical_card_selections_reproduced']=selection_diagnostics['inputs_reproduced']
summary['lead_crosschecked_inputs']=lead_crosschecked
save(PRIVATE/'summary.json',summary)
save(PRIVATE/'casebook.json',{'scope':'50 original v1 inputs, both arms; AI diagnosis is not human scoring','cases':casebook})
save(PRIVATE/'validation.json',{'input_ids':50,'execution_records':100,'reviewer_coverage':counts,'all_output_splices_reproduced':True,
  'actual_supplied_cards_equal_review_definitions':True,'human_ratings_exact_output_matched':20,
  'source_files_sha256_checked':len(source_manifest['source_sha256']),'changed_source_files':changed_sources,'new_qwen_calls':0})
progress=load(PRIVATE/'progress.json');progress.update(prepared_inputs=50,lead_first_pass_inputs=50,lead_crosschecked_inputs=lead_crosschecked,codex_reviewed_inputs=counts['codex'],claude_reviewed_inputs=counts['claude'])
save(PRIVATE/'progress.json',progress)
stages={'analysis':'文장 분석','mapping':'개념 연결','retrieval':'KG 조회','selection':'카드·수정 지시 선택','composition':'활용형 생성','validation':'검사·실행 처리','unknown':'원인 미확정'}
stages['analysis']='문장 분석'
verdicts={'no_output':'출력 없음','clear_issue':'내부 처리 또는 출력에 문제 지적','needs_human':'사람 판단 필요','no_specific_issue_found':'특정 문제를 지적하지 않음'}
certainty={'direct':'기록에서 확인','inference':'검토자의 해석','needs_human':'사람·문헌 확인 필요'}
def findings_table(findings):
    if not findings:return '<p class="muted">별도 지적 없음. 정확하다는 인증은 아닙니다.</p>'
    translations={'最初に観測される疑わしい対応は、場所・移動先の「에」を道具概念へ割り当てた点である。':'[총괄 번역] 처음 관찰되는 의심스러운 연결은 장소·이동 목적지의 에를 도구 개념에 배정한 점이다. 일본어 검토 원문은 별도 응답 파일에 보존했다.'}
    return '<table><thead><tr><th>단계</th><th>관찰 / 근거</th><th>판단 구분 / 제안</th></tr></thead><tbody>'+''.join(
        '<tr><td>'+h(stages.get(f.get('stage'),f.get('stage')))+'<br>'+h(f.get('severity'))+'</td><td>'+h(translations.get(f.get('observation'),f.get('observation')))+'<blockquote>'+h(f.get('evidence'))+'</blockquote></td><td>'+h(certainty.get(f.get('certainty'),f.get('certainty')))+'<br>'+h(f.get('recommendation'))+'</td></tr>' for f in findings)+'</tbody></table>'
def edits_html(v,c):
    plan=v['final_plan'] or v['draft']
    if not plan:return '<p>완성된 수정 계획이 없습니다. 호출 종료 기록을 확인해야 합니다.</p>'
    words={x['id']:x['text'] for x in c['words']}
    parts=['<p class="muted">'+('실제 최종 계획' if v['final_plan'] else '실패 전에 남은 계획 초안 — 최종 출력으로 보지 않음')+'</p><table><thead><tr><th>원문 → 계획/결과</th><th>선택 카드</th><th>모델이 작성한 수정 지시</th></tr></thead><tbody>']
    for e in plan['edits']:
        ids=e.get('rule_ids',[])
        ci='<br>'.join(h(k)+' · '+h(cards[k]['title'])+' · '+h(' / '.join(cards[k]['forms'])) if k in cards else h(k) for k in ids)
        parts.append('<tr><td>'+h(e['word_id'])+'<br>'+h(e.get('before',words.get(e['word_id'])))+' → '+h(e.get('after') or '(계획 단계)')+'</td><td>'+ci+'</td><td>'+h(e.get('instruction'))+'<details><summary>모델이 적은 이유</summary>'+h(e.get('reason'))+'</details></td></tr>')
    return ''.join(parts)+'</tbody></table>'

def flat_fields(value,prefix=''):
    if isinstance(value,dict):
        for k,v in value.items():yield from flat_fields(v,prefix+'.'+k if prefix else k)
    else:
        yield prefix,(' / '.join(str(x) for x in value) if isinstance(value,list) else str(value))

def path_html(v):
    rows=[]
    for card_id,paths in v['selected_path_examples'].items():
        for p in paths:
            rows.append('<tr><td>'+h(p['concept_id'])+' → '+h(p.get('via','직접 연결'))+' → '+h(p['rule_id'])+'</td><td>'+h(' / '.join(p['edge_ids']))+'</td></tr>')
    body='<table><tr><th>실제 관계로 이어진 경로 예시</th><th>관계 ID</th></tr>'+''.join(rows)+'</table>' if rows else '<p>최종 선택 경로가 남아 있지 않습니다. 출력 실패를 조회 실패와 동일시하지 않습니다.</p>'
    ids=sorted({k for e in (v['final_plan'] or v['draft'] or {}).get('edits',[]) for k in e['rule_ids']})
    for k in ids:
        if k not in cards:continue
        card=cards[k]
        body+='<details><summary>'+h(k)+' · '+h(card['title'])+'의 저장 조건</summary><p>분류: '+h(card['kind'])+' · 형태: '+h(' / '.join(card['forms']))+'</p><table><tr><th>원본 조건 이름</th><th>저장된 값</th></tr>'+''.join('<tr><td>'+h(a)+'</td><td>'+h(b)+'</td></tr>' for a,b in flat_fields(card['when']))+'</table><p>avoid: '+h(' / '.join(card['avoid']))+'</p></details>'
    relative=os.path.relpath(PROJECT/v['source_record_dir'],PRIVATE).replace('\\','/')
    return '<p class="muted">카드별 최대 2개 연결 예시입니다. 시간순 방문 기록이나 조건 충족의 증명이 아닙니다. 전체 원본은 <a href="'+h(relative+'/retrieval_raw.json')+'">조회 기록</a> · <a href="'+h(relative+'/result.json')+'">실행 결과</a>에서 확인할 수 있습니다.</p>'+body

def calls_html(v):
    labels={'analysis_call':'문장 분석','agent_call':'카드 선택·수정 계획','generation_call':'활용형 생성'}
    return '<table><tr><th>실행 단계</th><th>모델 응답 종료</th><th>응답 글자 수</th><th>끝에 남은 공백 수</th></tr>'+''.join('<tr><td>'+h(labels.get(x.get('stage'),x.get('stage')))+'</td><td>'+h(x.get('finish_reason'))+'</td><td>'+h(x.get('content_chars'))+'</td><td>'+h(x.get('trailing_whitespace'))+'</td></tr>' for x in v['call_facts'])+'</table><p class="muted">stop은 응답이 끝났다는 뜻이며 내용이 맞다는 판정이 아닙니다. length는 길이 제한으로 응답이 끊겼다는 기록입니다.</p>'
cards_html=[]
for i,c in enumerate(casebook,1):
    output_panels=[]
    for a,title in [('single','Single'),('multi','Multi')]:
        v=c['arms'][a];rating=v['human_rating'];status={'no_output':'출력 없음','unchanged':'원문 유지','changed':'출력 변경'}[v['outcome']]
        rh='<p class="human">기존 사람 평가 '+h(rating['naturalness'])+'/5 · '+h(rating['comment'])+'</p>' if rating else '<p class="muted">이 출력에 대한 기존 숫자 평가는 없음</p>'
        output_panels.append('<section><h3>'+title+' <small>'+status+'</small></h3><p class="output">'+h(v['output'] if v['output'] is not None else '최종 문장 없음 · '+str(v['error']))+'</p>'+rh+'</section>')
    details=[]
    for who,title in [('codex','Codex 검토자'),('claude','Claude 검토자')]:
        review=c['reviewers'][who]
        if review:
            section='<h4>공통 분석·조회</h4>'+findings_table(review['shared_findings'])
            for a in ['single','multi']:section+='<h4>'+a.title()+' · '+h(verdicts.get(review[a]['verdict'],review[a]['verdict']))+'</h4>'+findings_table(review[a]['findings'])
            if review.get('human_question'):section+='<p class="note">검토자가 제안한 확인 사항: '+h(review['human_question'])+'<br>기존 사용자 답변으로 해결되는 질문은 다시 요구하지 않습니다.</p>'
        else:section='<p>아직 독립 검토 응답을 수집하지 않았습니다.</p>'
        details.append('<details><summary>'+title+'의 독립 의견</summary>'+section+'</details>')
    pref=c['user_preference'];ph=''
    if pref:ph='<p class="human">사용자가 제안한 대안: '+h(' / '.join(pref['preferred_outputs_verbatim']))+'<br>유일한 정답 또는 새 점수가 아닙니다. '+('ADVCE008A는 다음 실행용 v2 입력에 대한 대안이며, 위 출력은 수정 전 v1입니다.' if c['id']=='ADVCE008A' else '')+'</p>'
    trace=''.join('<details><summary>'+a.title()+' 선택 카드와 실제 지시</summary>'+edits_html(c['arms'][a],c)+'<details><summary>그래프 연결 근거와 카드에 저장된 조건</summary>'+path_html(c['arms'][a])+'</details><details><summary>단계별 응답 종료 기록</summary>'+calls_html(c['arms'][a])+'</details></details>' for a in ['single','multi'])
    units='<table><thead><tr><th>위치 / 어절</th><th>기능 / 시제 / 대우</th><th>개념 ID / 분석 이유</th></tr></thead><tbody>'
    words={x['id']:x['text'] for x in c['words']}
    for u in c['shared_analysis']['units']:units+='<tr><td>'+h(u['word_id']+' '+words.get(u['word_id'],''))+'</td><td>'+h(', '.join(u['functions'])+' / '+u['tense']+' / '+u['politeness'])+'</td><td>'+h(', '.join(u['concept_ids']))+'<br>'+h(u['reason'])+'</td></tr>'
    units+='</tbody></table>'
    failing=any(v['outcome']=='no_output' for v in c['arms'].values());has_human=any(v['human_rating'] for v in c['arms'].values())
    cards_html.append('<article class="case" data-id="'+h(c['id'])+'" data-failure="'+str(failing).lower()+'" data-human="'+str(bool(has_human)).lower()+'"><h2><span>'+str(i).zfill(2)+'</span> '+h(c['id'])+'</h2><p class="input">'+h(c['input'])+'</p><div class="pair">'+''.join(output_panels)+'</div>'+ph+'<div class="lead"><b>총괄 원본 대조</b>'+list_html(c['lead_observations'])+'</div><details><summary>공통 문장 분석 보기</summary>'+units+'</details>'+trace+''.join(details)+'</article>')
adjud=load(BASE/'review_adjudication.json')
adjud_html='<table><thead><tr><th>검토 쟁점</th><th>총괄 판단</th><th>이유</th></tr></thead><tbody>'+''.join('<tr><td>'+h(x['topic'])+'</td><td>'+h(x['decision'])+'</td><td>'+h(x['reason'])+'</td></tr>' for x in adjud['decisions'])+'</tbody></table>'
metric_rows=''.join('<tr><td>'+a.title()+'</td><td>'+str(metrics[a]['changed'])+'</td><td>'+str(metrics[a]['unchanged'])+'</td><td>'+str(metrics[a]['no_output'])+'</td><td>'+str(metrics[a]['human_rated_outputs'])+'</td></tr>' for a in ['single','multi'])
rank_rows=''.join('<tr><td>'+h(x['input_id'])+'</td><td>'+h(x['id'])+'</td><td>'+str(x['overall_rank'])+'</td><td>'+('전달됨' if x['selected'] else '전달되지 않음')+'</td></tr>' for x in selection_diagnostics['examples'])
page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>50개 입력 전체 · 원인 진단</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#1d2939;font:16px/1.65 "Malgun Gothic",sans-serif}main{max-width:1250px;margin:auto;padding:36px 22px}h1{font-size:32px;letter-spacing:-1px}h2{font-size:21px;margin:0 0 14px}h2 span{color:#6680a0}h3{font-size:17px;margin:0 0 8px}small,.muted{font-size:13px;color:#667085}.hero,.case,.panel{background:white;border:1px solid #dbe3ef;border-radius:14px;padding:26px;margin-bottom:20px}.hero{border-top:6px solid #2563eb}.kpis,.flow{display:flex;gap:12px;flex-wrap:wrap}.kpis div{background:#eef4ff;padding:14px 22px;border-radius:10px;flex:1;min-width:130px}.kpis b{display:block;font-size:26px}.flow span{padding:8px 14px;background:#eaf0f8;border-radius:8px}.flow span.alert{background:#fff0d5}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.pair section{background:#f8fafc;border-radius:10px;padding:18px}.output,.input{white-space:pre-wrap;overflow-wrap:anywhere}.input{font-size:18px;border-left:4px solid #2563eb;padding:12px;background:#f4f8ff}.lead{margin:18px 0;padding:15px;background:#f0f7f5;border-radius:8px}.human{background:#fff6df;padding:12px;border-radius:7px;font-size:14px;white-space:pre-wrap}.note{background:#fff5e8;padding:15px}.toolbar{position:sticky;top:0;z-index:2;background:#f4f6faf5;padding:12px 0;display:flex;gap:10px;align-items:center;flex-wrap:wrap}input,select,button{font:inherit;padding:9px 12px;border:1px solid #bbc8db;border-radius:6px}input{flex:1;min-width:200px}button{background:white;cursor:pointer}table{width:100%;border-collapse:collapse;font-size:14px;margin:15px 0;table-layout:fixed}td,th{padding:11px;vertical-align:top;text-align:left;border-bottom:1px solid #e2e8f0;overflow-wrap:anywhere;white-space:pre-wrap}th{background:#edf2f8}details{margin:10px 0;border-top:1px solid #e4e9f1;padding-top:10px}summary{cursor:pointer;color:#2454a4;font-weight:600}blockquote{border-left:3px solid #bdcadb;margin:9px 0;padding-left:12px;color:#5a6777;font-size:13px}li{margin:6px 0}a{color:#2454a4}.badge{display:inline-block;border-radius:6px;padding:4px 8px;background:#edf2f8;font-size:13px}.hidden{display:none}@media(max-width:750px){.pair{grid-template-columns:1fr}main{padding:16px 10px}.hero,.case,.panel{padding:18px}table{font-size:12px}td,th{padding:7px}h1{font-size:25px}}@media print{.toolbar{display:none}.case{break-inside:avoid}body{background:white}}
</style><main><section class="hero"><p class="badge">2026-10-29 · 기존 실행의 전수 진단</p><h1>대표 8건이 아니라, 입력 50개 전체를 확인합니다.</h1><p>입력 50개 × Single/Multi 2방식 = 실행 기록 100건입니다. 새 데이터 100개가 아닙니다. 일부 입력은 여러 문장으로 구성되어 있습니다.</p><div class="kpis"><div><b>50</b>검토 입력</div><div><b>100</b>실행 기록</div><div><b>79</b>최종 출력 존재</div><div><b>21</b>최종 출력 없음</div></div><p>자료: 20261028T011829489985Z · v1 입력. ADVCE008A를 수정한 v2는 아직 이번 결과에 사용되지 않았습니다.</p><p>검토 완료: Codex <b>@@CODEX@@/50</b> · Claude <b>@@CLAUDE@@/50</b> · 총괄 1차 원본 대조 <b>50/50</b>. 두 검토자는 각각 동일한 50개를 보며, 서로의 결론과 사람 점수를 받기 전에 독립 의견을 냅니다.</p><p class="note">이 보고서는 오류 진단입니다. 변경된 출력도 틀릴 수 있으며, 원문 유지도 허용될 수 있습니다. AI 검토를 사람 평가나 자연스러움 정확도로 계산하지 않았습니다. 이번 진단에서 KG·실행 코드를 수정하거나 Qwen을 재호출하지 않았습니다.</p></section>
<section class="panel"><h2>전체 그림: 어디부터 어긋났는지 찾기</h2><div class="flow"><span>원문</span><span class="alert">문장 분석·개념</span><span>KG 조회</span><span class="alert">카드 조건·수정 지시</span><span class="alert">활용형 생성</span><span>검사·최종 출력</span></div><p>카드를 선택했다는 것은 전달된 지식의 ID를 수정 계획에 적었다는 뜻입니다. 기록된 조회 경로는 실제 그래프 관계의 연결 근거이며, 해당 문장에 그 규칙을 적용해도 된다는 증명이나 시간순 방문 기록은 아닙니다.</p><table><thead><tr><th>방식</th><th>출력 변경</th><th>원문 유지</th><th>출력 없음</th><th>기존 사람 평가</th></tr></thead><tbody>@@METRICS@@</tbody></table><p>출력 없음: 응답 길이 제한 16건, 한 어절 출력 제약 4건, 빈 카드 ID 목록 1건. 길이 제한 중 11건은 끝에 긴 공백이 남았습니다. 이 현상만으로 모델·서버·구조화 출력 중 어느 것이 원인인지 확정할 수 없습니다.</p><p>분리 자모가 남은 완성 출력: @@JAMO@@. 공백 제한은 문법의 옳고 그름을 검사하지 않으며, -아 가지고처럼 여러 어절인 지식을 막기도 합니다.</p><details><summary>검토 의견 중 그대로 채택하지 않은 점과 원본 대조</summary>@@ADJUD@@</details></section>
<div class="toolbar"><input id="search" placeholder="ID, 문장, 오류 내용 검색" aria-label="검토 검색"><select id="filter" aria-label="검토 필터"><option value="all">전체 50개</option><option value="failure">한쪽 이상 출력 없음</option><option value="human">기존 사람 평가 있음</option></select><button id="collapse">모두 접기</button><span id="count"></span></div>@@CASES@@
<section class="panel"><h2>다음 작업 제안 — 아직 실행하지 않음</h2><ol><li>잘못된 문법 기능·높임·어간 정보와 카드 조건을 명시적으로 대조합니다. 분석이 맞은 사례에서 계획이 틀리는지도 따로 확인합니다.</li><li>선택 카드 ID, 수정 지시, 실제 활용 결과가 같은 내용을 가리키도록 만들고, 시제·부정·어휘 보존과 여러 어절 구성의 처리 범위를 정합니다.</li><li>동일 입력·분석·카드 조건을 유지하면서 한 단계씩 바꾸어 원인 확인 실험을 설계합니다. 이번 결과만으로 개선 효과를 주장하지 않습니다.</li><li>수정 후에는 50개 전체를 새 실행으로 비교하고, 눈에 띄는 오류가 줄어든 뒤 사람의 자연스러움 평가를 진행합니다.</li></ol><p>원본 자료와 구조화 결과: <a href="casebook.json">50개 대조 기록</a> · <a href="summary.json">실제 집계</a> · <a href="validation.json">무결성 확인</a>. 이 파일들은 로컬 private 연구 자료입니다.</p></section></main><script>
const cards=[...document.querySelectorAll('.case')],search=document.querySelector('#search'),filter=document.querySelector('#filter');function update(){const q=search.value.toLocaleLowerCase();let n=0;for(const c of cards){const ok=c.textContent.toLocaleLowerCase().includes(q)&&(filter.value==='all'||(filter.value==='failure'?c.dataset.failure==='true':c.dataset.human==='true'));c.classList.toggle('hidden',!ok);if(ok)n++}document.querySelector('#count').textContent=n+' / 50개'}search.addEventListener('input',update);filter.addEventListener('change',update);document.querySelector('#collapse').addEventListener('click',()=>document.querySelectorAll('details').forEach(x=>x.open=false));update();
</script></html>'''
selection_panel='''<section class="panel"><h2>카드 선별에서도 확인된 문제</h2><p>실험 당시 코드로 50개 입력의 순위를 다시 계산했고 저장된 두 방식의 순위와 모두 일치했습니다. 새 모델 호출이나 조건 변경은 하지 않았습니다.</p><p>현재 점수 계산은 카드 제목·조건에 들어 있는 글자를 찾습니다. <b>조건문을 찾는 condition이라는 검색어가 받침 조건 coda_condition에도 걸립니다.</b> 이 때문에 목적격 조사 카드가 조건문 점수를 받았습니다. 조회된 카드의 조건을 실제 문장에 대조한 결과가 아닙니다.</p><table><tr><th>입력</th><th>실제로 조회된 카드</th><th>전체 점수 순위</th><th>최종 48장에 포함</th></tr>'''+rank_rows+'''</table><p>따라서 48장을 무작정 늘리는 것만으로 해결된다고 할 수 없습니다. 문장 속 각 구성에 필요한 후보가 남는지, 그 후보의 조건이 맞는지를 나누어 확인해야 합니다. 위 카드는 관련 유형의 후보 예시이며 해당 문장에 곧바로 적용해도 된다는 판정은 아닙니다.</p><p><a href="selection_diagnostics.json">50개 순위 재현 결과와 근거</a></p></section>'''
page=page.replace('<div class="toolbar">',selection_panel+'<div class="toolbar">',1)
page=page.replace('총괄 1차 원본 대조 <b>50/50</b>.','총괄 1차 원본 대조 <b>50/50</b> · 두 검토 의견까지 대조 <b>'+str(lead_crosschecked)+'/50</b>.')
page=page.replace('@@CODEX@@',str(counts['codex'])).replace('@@CLAUDE@@',str(counts['claude'])).replace('@@METRICS@@',metric_rows).replace('@@JAMO@@',h(', '.join(x['id']+' '+x['arm'] for x in jamo))).replace('@@ADJUD@@',adjud_html).replace('@@CASES@@',''.join(cards_html))
(PRIVATE/'review.html').write_text(page,encoding='utf8')
md=['# 50개 입력 전체 검토','', '기존 v1 입력 50개와 Single/Multi 실행 100건의 진단이다. 새 실험이나 사람 평가가 아니다.','',
    f"독립 검토 수집: Codex {counts['codex']}/50, Claude {counts['claude']}/50. 총괄 1차 원본 대조 50/50.",'',
    '| ID | Single | Multi | 총괄 관찰 |','|---|---|---|---|']
for c in casebook:
    cell=lambda x:str(x if x is not None else '출력 없음').replace('|','\\|').replace('\n',' ')
    md.append('| '+c['id']+' | '+cell(c['arms']['single']['output'])+' | '+cell(c['arms']['multi']['output'])+' | '+cell(' '.join(c['lead_observations']))+' |')
(PRIVATE/'casebook.md').write_text('\n'.join(md)+'\n',encoding='utf8')
print('FULL REVIEW: 50 inputs / 100 historical execution records')
print('Independent coverage:',counts)
print('Output counts:',json.dumps(summary['metrics'],ensure_ascii=False))
print(f'No-op edits {len(noop)}/{all_final_edits}; standalone-jamo outputs {len(jamo)}; human rated outputs 20/79')
print('Source SHA checks:',len(source_manifest['source_sha256']),'unchanged. No new Qwen calls / no runtime or KG edits.')
print('Report:',PRIVATE/'review.html')
