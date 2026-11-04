"""Readable post-run report. Approved references are loaded only here, after calls."""
import json,sys,html,re,hashlib,statistics,datetime
from collections import Counter
from pathlib import Path
from html.parser import HTMLParser
H=Path(__file__).resolve().parent;R=H.parents[2];P=H/'private'
sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import read,save,sha,load_jsonl
from research_management.work import WorkStore
from research_management.core import Registry
E=lambda v:html.escape(str(v if v is not None else ''))
def table(headers,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
 latest=read(P/'latest.json');assert latest['state'].startswith('completed'),latest['state']
 root=R/latest['root'];summary=read(root/'summary.json');prep=read(P/'preparation.json')
 rows=load_jsonl(R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl')
 refs={r['id']:r['reference'] for r in read(R/'experiments/analyses/pre_experiment_review_20261102/private/index.json')}
 by={};counts={};verified={};all_calls=[]
 for arm,rid in latest['runs'].items():
  out=R/'experiments/runs'/rid;results=read(out/'private/results.json');assert len(results)==50
  assert {r['id'] for r in results}=={r['id'] for r in rows};by[arm]={r['id']:r for r in results}
  bad=[]
  for path,h in read(out/'artifact_hashes.json').items():
   if sha((out/path).read_bytes())!=h:bad.append(path)
  assert not bad;verified[arm]={'artifact_count':len(read(out/'artifact_hashes.json')),'mismatches':bad}
  meta=[read(f) for f in out.glob('private/records/*/*_call/meta.json')];all_calls+=meta
  failures=Counter()
  for m in meta:
   if m['status']!='failed':continue
   if m.get('http_status')==400 and 'maximum context length' in m.get('server_error',''):failures['context_limit']+=1
   elif m.get('error','').startswith('non_stop_finish:'):failures[m['error']]+=1
   else:failures[m.get('error_type','unknown')+':'+str(m.get('http_status',''))]+=1
  c=summary['arms'][arm]
  counts[arm]={'input_count':50,'cards_min':min(s['cards'] for s in prep if s['arm']==arm),'cards_max':max(s['cards'] for s in prep if s['arm']==arm),
   'outputs':c['valid_output_records'],'changed':c['changed_records'],'unchanged':sum(r.get('output_text')==r['input_text'] for r in results),'failed_records':sum(r.get('output_text') is None for r in results),
   'http_attempts':len(meta),'received_model_responses':sum(m.get('http_status')==200 for m in meta),'errors':dict(failures),'record_errors':dict(Counter(r.get('error','unknown') for r in results if r.get('output_text') is None)),'statuses':c['status_counts'],'usage':c['reported_usage'],
   'api_seconds':c['summed_api_seconds'],'median_record_seconds':statistics.median(r['incremental_generation_seconds'] for r in results),'mean_record_seconds':statistics.mean(r['incremental_generation_seconds'] for r in results),
   'model_held_edits':c['held_by_model'],'program_held_edits':c['held_by_program'],'repair_events':c['repair_events']}
 comparable=sum(by['filtered'][r['id']].get('output_text') is not None and by['unfiltered'][r['id']].get('output_text') is not None for r in rows)
 assert counts['unfiltered']['errors'].get('context_limit')==50,'This report narrative requires all 50 context-limit rejections; inspect differing outcomes first.'
 frozen=read(root/'freeze.json');assert all(sha((R/k).read_bytes())==h for k,h in frozen.items())
 assert all(sha((root/'snapshot'/k).read_bytes())==h for k,h in frozen.items())
 facts={'arms':counts,'comparable_output_pairs':comparable,'wall_seconds':summary['wall_seconds'],'physical_http_attempts':len(all_calls),'source_files_verified':len(frozen),'run_artifacts_verified':verified,
 'new_analysis_calls':0,'new_graph_queries':0,'quality_accuracy':None,'conclusion':'All-card single-request arm infeasible under current limit; no dialect-quality comparison possible' if counts['unfiltered']['errors'].get('context_limit')==50 else 'Inspect errors and paired outputs; no automatic naturalness scoring',
 'context_error_count_is_lower_bound':'Server says at least 26769 input tokens, not exact total token length.'}
 save(P/'analysis.json',facts)
 # The reused generator counts a stored retrieval as kg_queries=1. Do not
 # rewrite frozen records: make the actual live-query count explicit here.
 save(P/'record_field_clarification.json',{'field':'kg_queries','inherited_meaning':'stored retrieval used; copied from existing generate helper','actual_new_live_queries':0,'actual_new_analysis_calls':0,'affected_runs':latest['runs'],'applies_to':'all 100 records','raw_records_modified':False})
 names={'filtered':'A：既存 선별 사용'.replace('既存','기존'),'unfiltered':'B：선별 우회'}
 attrs=[('입력 문장','input_count'),('최종 출력이 있는 문장','outputs'),('원문과 달라진 문장','changed'),('원문 그대로인 문장','unchanged'),('최종 출력 없는 문장','failed_records'),('HTTP 요청 횟수','http_attempts'),('서버의 모델 응답 수(HTTP 200)','received_model_responses'),('모델이 보류한 편집 수','model_held_edits'),('검사가 보류한 편집 수','program_held_edits'),('코드 보정 횟수','repair_events')]
 md='''# 카드 선별 사용·우회 비교 결과

## 먼저 알아야 할 결론

실험은 전체50에 대해 두 조건으로 실행했다. 그러나 선별 우회 조건이 서버 입력 한도에서 거절되어, 선별 유무에 따른 방언 품질의 우열은 판단할 수 없다. 선별이 필요하다는 증거도, 선별을 없애면 품질이 나빠진다는 증거도 아니다.

## 실제로 바꾼 것

- A는 같은 저장 분석·실제 KG 조회 결과에서 현재 기존 선별 코드를 실행해 48장을 전달했다. 과거 출력을 새 기준선으로 재사용하지 않았다.
- B는 같은 조회 결과의 모든 카드를 ID 순으로 전달했다. 초기 점수·48장 제한·위치별 상위3개·조건 대조에 따른 탈락·추천 후보 안내를 우회했다. 새 카드나 정답 문장은 넣지 않았다.
- 두 조건 모두 기존 Qwen 계획 담당과 생성 담당을 사용했다. 적용 카드와 위치는 모델이 선택하며, 수동 정답 선택표를 사용하지 않았다.
- 카드 역할(candidate/reference/restriction), 사용자 제한, 선택 후 문법 검사·보정은 동일하게 유지했다. 따라서 모든 룰 기반 처리를 제거한 실험이 아니다.
- 원문·Kiwi 분석·Qwen 문법 분석·실제 조회 결과·카드 내용·프롬프트·seed·생성 설정·후단 코드는 고정했다. 카드 수·순서·추천 안내·파생 request_id는 함께 달라지는 정책 비교이며 각각의 독립 효과를 분리하지 않는다.
- 50문장 × 두 조건 × 1회. 출력 토큰 상한6000, temperature0, top_p1, seed20261028, thinking=false, 동시 처리2, 자동 재시도0. 전체50은 노출된 회귀·진단용이며 독립 평가셋이 아니다.

## 결과

| 항목 | A: 선별 사용 | B: 선별 우회 |
|---|---:|---:|
'''
 for title,k in attrs:md+=f'| {title} | {counts["filtered"][k]} | {counts["unfiltered"][k]} |\n'
 md+=f'| 전달 카드 수 | {counts["filtered"]["cards_min"]}~{counts["filtered"]["cards_max"]} | {counts["unfiltered"]["cards_min"]}~{counts["unfiltered"]["cards_max"]} |\n'
 md+=f'| 입력 한도 거절 | {counts["filtered"]["errors"].get("context_limit",0)} | {counts["unfiltered"]["errors"].get("context_limit",0)} |\n'
 md+=f'\n서로 출력이 있어 비교할 수 있는 문장은 **{comparable}/50**이다. 출력 변화는 정확도나 자연스러움 점수가 아니다. 새 분석·조회 호출은 없었고 기존 자료를 공통 재사용했다. 전체 경과시간 {summary["wall_seconds"]:.1f}초, HTTP 요청 {len(all_calls)}회다. 입력 한도 거절은 모델의 문법 판단 실패와 구분한다.\n'
 md+='''
기존 선별 조건의 출력 실패2건은 DEV012의 잘못된 선택 형태 번호(invalid_target_index)와 QUAL005의 생성 길이 한도 종료다. HTTP200으로 응답이 왔어도 유효한 최종 문장 생성에 실패할 수 있다.

## 무엇이 막혔나

서버가 공개한 최대 문맥 길이는32768토큰이다. 요청은 출력용6000토큰을 예약하므로 입력·서식 등에 남는 공간은 그보다 작다. 서버는 B 요청에 대해 입력이 최소26769토큰이라고 알리며 HTTP400으로 거절했다. 이26769는 정확한 입력 길이가 아니라 거절 시 확인된 하한이다. 출력 예약을 조금 줄이면 전부 들어간다고 판단할 수 없다.

카드를 줄이거나 다시 선별해 넣으면 승인한 ‘조회된 전체 카드’ 조건이 바뀐다. 그래서 실행 도중 조건을 바꾸지 않고 실패 원본을 보존했다. A는 기준선으로 전부 수행했지만 B가 생성되지 않았으므로 A의 수치를 두 방법의 품질 비교로 사용하지 않는다.

## 다음에 필요한 결정

‘선별 없이 전부 한 번에 전달’은 현재 서버 설정에서 실행되지 않았다. 다음 비교를 하려면 입력량 제약을 먼저 해결해야 한다.

1. 서버의 문맥 한도를 늘릴 수 있는지 확인한다. 가능하면 카드·선택 절차를 바꾸지 않고 기존 설계를 유지할 수 있다. 모델 지원 범위·GPU 메모리·지연시간 확인이 필요하며 지금 설정을 변경하지 않았다.
2. 늘릴 수 없다면 모든 카드를 빠짐없이 여러 묶음으로 나눠 Qwen이 검토하고, 그 후보를 합쳐 판단하는 방식을 별도 실험으로 설계한다. 이것은 코드의 문법 선별을 되살리는 방법은 아니지만 호출 수와 처리 구조가 바뀌므로 새 비교 조건이다.

이번 결과를 이유로 기존 선별이 더 낫다고 결론내리거나, 또 카드 내용을 고치지 않는다. 먼저 위 실행 제약을 해결하고 품질 비교를 다시 해야 한다.

## 재현과 검증

- experiment.py: 저장 분석·조회 재사용, 현재 A 선별 재계산, B 전체 조회 카드 전달, 기존 planner/worker/검사 재사용, 원본 요청·응답·지연·실패·후단 추적 저장.
- test_experiment.py: 전체50 동일 입력·분석과 실제 조회 출처, 카드 내용 보존, 기존 미전달 카드 포함, 빈 계획의 정상 처리, 잘못된 응답의 실패 처리. 5개 테스트 통과.
- report.py: 원본에서 집계·표·전체50 결과를 재생성한다. 승인 참조는 이 단계에서만 읽는다.
- 재사용 실행기의 기록 필드 kg_queries=1은 저장 조회자료 사용 표시다. 실제 새 DB 조회는0회다. 원본 수정 없이 private/record_field_clarification.json에 구분을 기록했다.
- private/하위 UTC 실행폴더: 실제 요청에 사용된 입력 묶음, 실험 조건, 코드·자료 스냅숏, 요약. private/analysis.json에 독립 집계.
- 각 experiments/runs/Run ID: 설정·요청·응답·원시 선택·생성·최종 계획·검사·코드 보정·오류 및 해시. 원본을 덮어쓰지 않음.
'''
 md+='\n실행 ID:\n'+''.join('- '+v+'\n' for v in latest['runs'].values())
 (H/'README.md').write_text(md,encoding='utf8')
 out='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>카드 선별 사용·우회 실험</title><style>body{font:16px/1.7 system-ui,"Malgun Gothic",sans-serif;background:#f4f6f8;color:#1c2938;margin:0}main{max-width:1080px;margin:auto;padding:28px}section,article{background:white;padding:22px;border-radius:12px;margin:16px 0}h1,h2{line-height:1.4}.notice{border-left:5px solid #b45d15;background:#fff5e9;padding:16px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #dbe2eb;padding:10px;text-align:left;vertical-align:top;min-width:90px}th{background:#eaf0f7}.scroll{overflow:auto}details{margin:12px 0}summary{cursor:pointer;font-weight:bold}small{color:#586779}pre{white-space:pre-wrap;word-break:break-word;font:inherit;font-size:14px}input{padding:12px;width:90%;font:inherit}a{color:#165f9d}.flow{padding:15px;background:#eef3f8}footer{color:#536273}</style><main><h1>선별을 빼면 좋아질까?</h1><p>2026-11-02 · 전체50문장 × 두 조건 · 실제 Qwen 요청</p>'''
 out+='<section><h2>결론부터</h2><p class="notice"><b>아직 품질을 비교할 수 없습니다.</b> 선별 우회 조건은 카드가 너무 많아 서버가 요청을 거절했습니다. 모델이 번역을 시도한 뒤 실패한 것이 아닙니다.</p><p>이번에 확인한 것은 “선별 없는 방식이 나쁘다”가 아니라 <b>“현재 서버에서는 조회된 카드를 전부 한 번에 넣을 수 없다”</b>는 점입니다.</p>'
 out+=table(['항목','A: 선별 사용','B: 선별 우회'],[[E(t),E(counts['filtered'][k]),E(counts['unfiltered'][k])] for t,k in attrs[:7]])
 out+=f'<p>전달 카드: A 48장 / B {counts["unfiltered"]["cards_min"]}~{counts["unfiltered"]["cards_max"]}장. 양쪽 출력 비교 가능: <b>{comparable}/50문장</b>.</p><p>원문이 바뀐 수는 정확도가 아닙니다. A에도 활용 오류나 부자연스러운 표현이 있을 수 있습니다.</p></section>'
 out+='<section><h2>어디에서 멈췄나?</h2><p class="flow">같은 문장 분석·KG 조회 → B는 전체 카드 전달 → <b>서버 입력량 검사에서 거절</b> → Qwen의 카드 선택·방언 생성에 도달하지 못함</p><p>서버 한도는 입력과 출력을 합쳐 32,768토큰입니다. 출력용6,000토큰을 예약한 요청에서 입력이 너무 길었습니다. 서버가 제시한 최소26,769는 실제 전체 입력 길이가 아닙니다.</p><h2>다음 선택</h2><p><b>먼저 서버 입력 한도를 늘릴 수 있는지 확인</b>하는 것이 가장 적은 변경입니다. 불가능하면 모든 카드를 여러 묶음으로 나눠 Qwen이 검토하는 새 실험이 필요합니다. 두 방법 모두 이번에는 실행하지 않았습니다.</p><details><summary>설계·비용·검증 상세</summary><pre>'+E(md)+'</pre>'+table(['비용 항목','A','B'],[[E('총 API 시간(초)'),E(round(counts['filtered']['api_seconds'],2)),E(round(counts['unfiltered']['api_seconds'],2))],[E('문장별 평균 처리시간(초)'),E(round(counts['filtered']['mean_record_seconds'],2)),E(round(counts['unfiltered']['mean_record_seconds'],2))],[E('서버 보고 토큰'),E(counts['filtered']['usage']),E(counts['unfiltered']['usage'])]])+'<p>오류 응답에 토큰 사용량이 없으면 미보고입니다. B의 빠른 거절 시간을 빠른 번역 성능으로 비교하지 않습니다.</p></details></section>'
 out+='<section><h2>50문장 전체 결과</h2><p>원문·승인 참조·A 출력·B 실패와 처리 기록을 확인할 수 있습니다. 승인 참조는 모델에 전달하지 않았습니다.</p><input id="q" aria-label="문장 검색" placeholder="문장 ID 또는 원문 검색"><p id="count">50문장</p></section>'
 labels={'needs_review':'보류·확인 필요','partial':'일부 반영','unchanged':'원문 유지','generated_requires_human_review':'변경됨·품질 미평가','planning_failed':'선택 단계 실패','generation_failed':'생성 단계 실패'}
 for row in rows:
  key=row['id'];a=by['filtered'][key];b=by['unfiltered'][key]
  out+='<article class="case" data-text="'+E(key+' '+row['text'])+'"><details><summary>'+E(key)+' · '+E(row['text'])+'</summary><p><b>승인 참조:</b> '+E(refs[key])+'</p>'
  out+=table(['조건','최종 출력','상태'],[[names[arm],E(r['output_text']) if r.get('output_text') is not None else '<b>출력 없음</b>',E(labels.get(r['status'],r['status']))] for arm,r in [('filtered',a),('unfiltered',b)]])
  for arm,r in [('filtered',a),('unfiltered',b)]:
   out+='<details><summary>'+names[arm]+' · 선택·생성·검사 기록</summary>'
   out+=table(['선택 편집','원문 위치','선택 카드','모델의 계획'],[[E(e['edit_id']),E(', '.join(e['word_ids'])),E(', '.join(z['card_id'] for z in e['bindings'])),E(e['action'])] for e in r.get('planner_selected_bindings',[])])
   out+=table(['원래 표현','Qwen 원시 표현','검사 후 표현','처리','검사/보정'],[[E(t['before']),E(t['raw']),E(t['after']),E(t['outcome']),E(', '.join(v['code'] for v in t['issues']))+'<br>'+E(', '.join(v['kind'] for v in t['repairs']))] for t in r.get('edit_trace',[])])
   if r.get('failed_call_details'):out+='<p><b>실패 원문:</b></p><pre>'+E('\n'.join(m.get('server_error',m.get('error',m.get('error_type',''))) for m in r['failed_call_details']))+'</pre>'
   elif r.get('error'):out+='<p>'+E(r['error'])+'</p>'
   out+='</details>'
  out+='</details></article>'
 out+='''<footer>기존 KG·카드·생성 코드와 과거 결과는 변경하지 않았습니다. 이번에는 새 비교 실행기와 결과만 추가했습니다.</footer></main><script>document.querySelector('#q').addEventListener('input',e=>{let n=0;document.querySelectorAll('.case').forEach(a=>{a.hidden=!a.dataset.text.toLowerCase().includes(e.target.value.toLowerCase());if(!a.hidden)n++});document.querySelector('#count').textContent=n+'문장';});</script></html>'''
 assert out.count('class="case"')==50;HTMLParser().feed(out)
 (P/'report.html').write_text(out,encoding='utf8')
 save(P/'validation.json',{'tests':5,'tests_passed':True,'input_pairs':50,'html_cases':50,'run_artifacts_verified':verified,'source_files_unchanged':len(frozen),'model_reference_leak':'references never read by preparation/runner; no claims about unknown model pretraining','browser_visual_check':False})
 taskid='filter-ablation-20261102';ws=WorkStore(R)
 with ws.connect() as db:prior=db.execute('SELECT body FROM tasks WHERE id=?',(taskid,)).fetchone()
 if not prior or json.loads(prior['body'])['status']!='completed':
  ws.task(dict(id=taskid,title='50문장 카드 선별 사용·우회 비교',actor='Codex 총괄',stage='전체 실행·실패 원인 대조 완료',status='completed',done=100,total=100,unit='조건별 처리',unit_key='result_audit',message=f'양쪽 품질 비교 가능 {comparable}/50. 선별 우회 입력 한도 거절 {counts["unfiltered"]["errors"].get("context_limit",0)}건. 자세한 결과는 로컬 HTML·등록 Run에 보존.'))
 print(json.dumps(facts,ensure_ascii=False))
if __name__=='__main__':main()
