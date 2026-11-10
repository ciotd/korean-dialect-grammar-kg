"""Readable output from saved replay artifacts. No quality score is inferred."""
import html,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'private';ROOT=BASE.parents[2]
def read(name):return json.loads((P/name).read_text(encoding='utf8'))
E=lambda x:html.escape(str(x if x is not None else '확인할 출력 없음'))
LABEL={'plain':'반말','polite':'공손한 말','formal':'격식체','unknown':'미확인','politeness':'말높임','functions':'문법 기능',
       'polar_question':'예/아니오 질문','wh_question':'의문사 질문','progressive':'진행','negation':'부정'}
REASON={'original_stale_request_not_repaired':'당시 요청 번호가 틀렸음. 올바른 응답처럼 바꾸지 않음.',
        'no_complete_saved_model_response':'당시 응답이 길이 제한으로 끊김. 재사용할 완성 응답 없음.',
        'no_saved_downstream':'분석 뒤 단계의 저장 응답 없음. 분석 형식 통과와 출력 회복은 다름.',
        'no_saved_worker_response':'이전 계획 단계에서 멈춰, 활용 담당 모델의 응답이 없음.',
        'previous_program_skip_needs_new_worker':'이전에 활용 담당 호출을 생략함. 새 호출 없이는 결과를 만들 수 없음.'}
ISSUES={'function_not_supported':'선택 카드의 용법이 입력 분석과 맞지 않음','function_unverified':'카드가 요구하는 기능의 근거 미확인',
 'binding_not_ending':'어미로 지정한 위치가 허용된 어미 위치가 아님','source_analysis_conflict':'두 분석이 충돌함 · 확정 수정 안 함',
 'source_suffix_composition_disagreement':'바꾼 뒤 어휘·시제 등의 보존을 확인하지 못함','function_evidence_insufficient':'말하는 상황의 근거 부족',
 'predicate_kind_disagreement':'동사·형용사·이다 구분이 카드 조건과 다름','scoped_operation_source_unavailable':'지정된 교체 범위 밖임',
 'dependency_group_not_applied':'함께 바꿔야 하는 다른 부분이 보류됨','target_realization_unverified':'선택한 형태가 제대로 실현됐는지 미확인'}
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
 rows=read('cases.json');s=read('summary.json');tests=read('test_results.json')
 h='<header><p class="eyebrow">기존 50문장 × Single·Multi · 새 Qwen 호출 0회</p><h1>고친 것은 연결 오류입니다.<br>자연스러운 번역 완성은 아직입니다.</h1><p>예전 Qwen 답변을 그대로 두고, 수정한 프로그램으로 다시 검사했습니다. 카드 721개와 KG는 바꾸지 않았습니다.</p></header>'
 h+='<nav><a href="#answer">핵심 결과</a><a href="#examples">실제로 달라진 3건</a><a href="#changes">무엇을 고쳤나</a><a href="#next">다음 작업</a><a href="#cases">50문장 확인</a><a href="/work">진행·승인</a></nav>'
 h+='<section id="answer"><h2>결론부터</h2><ol><li><b>잘못된 변경 1개를 막았습니다.</b> 할머니께 하는 금지 요청을 화자의 의지 표현으로 바꾸던 문제입니다.</li><li><b>출력 실패 1개를 복구했습니다.</b> 별도로 나뉜 ‘요’를 처리하지 못해 전체 출력이 없던 Single 기록입니다.</li><li><b>새로운 부족한 점도 확인했습니다.</b> 파생동사를 인식하게 되자 ‘시작했나요’가 ‘시작했나’로 바뀌었습니다. 공손함을 잃으므로 성공으로 볼 수 없습니다.</li></ol><p class="notice">이번 결과는 “옛 답변을 새 프로그램으로 처리한 결과”입니다. Qwen이 수정된 분석을 읽고 새로 선택·작성한 결과가 아닙니다.</p>'
 numbers=[]
 for arm in ('single','multi'):
  for mode,label in [('baseline','이전 실제 출력'),('contract_only','수정 작업만 보완'),('aligned_analysis','분석 보정도 추가')]:
   v=s['modes'][mode][arm];numbers.append([arm.title(),label,v['changed'],v['unchanged'],v['unavailable']])
 h+=table(['방식','확인 조건','원문과 다름','원문 그대로','출력 확인 불가'],numbers)
 h+='<p>각 행은 50건입니다. “원문과 다름”은 자연스러움·정확도 점수가 아닙니다. Multi의 확인 불가 5건은 새 응답이 없다는 뜻이며, 모두 새 코드의 실패라는 뜻도 아닙니다.</p></section>'
 h+='<section id="examples"><h2>실제로 달라진 세 가지</h2>'
 examples=[('LONG004','금지 요청을 의지 표현으로 바꾸던 변경을 차단','마세요 → 말끼를 적용하지 않고 마세요를 유지합니다. 그러나 같은 문장의 오는데 → 오아도는 여전히 남아 있습니다. 이 문장 전체가 해결된 것은 아닙니다.'),
           ('NEW004','동사는 알아봤지만, 공손함은 잃음','시작+하를 동사로 인식하도록 고쳤습니다. 이제 선택된 -나 카드가 적용됩니다. 그러나 원문의 공손함과 카드의 해라체가 맞는지 검사하는 부분은 아직 부족합니다.'),
           ('QUAL017','한 어미 때문에 전체가 실패하던 문제를 해소','저장 분석의 려고/EF + 요/JX를 기존 카드의 지정 범위로 처리합니다. Single은 출력이 생겼습니다. Multi는 당시 활용 담당 응답이 없어 아직 확인할 수 없습니다. 하려고예가 승인 표현 할라꼬예와 같아진 것은 아닙니다.')]
 for id,title,explain in examples:
  r=next(r for r in rows if r['id']==id);v=r['arms']['single']
  h+='<article><h3>'+E(id+' · '+title)+'</h3><p>'+E(explain)+'</p>'
  h+=table(['구분','문장'],[['표준어',E(r['input'])],['이전 Single',E(v['baseline']['output'])],['저장 응답 재처리',E(v['aligned_analysis']['output'])],['사용자가 승인한 비교 표현',E(r['reference'])]])+'</article>'
 h+='</section><section id="changes"><h2>무엇을 고쳤나</h2>'
 h+=table(['문제','이번 변경','확인 범위'],[
 ['기능 이름이 서로 안 맞음','동시·병행, 부사절 기능을 요청 형식과 검사 목록에 함께 등록','QUAL002의 저장 분석은 통과. 이후 모델 답변은 없어 번역 미확인'],
 ['반말을 공손한 말로 읽음','원문 끝맺음이 명확한 경우에만 분석값 보정',f'말높임 {s["analysis_changes"].get("politeness",0)}개 값 보정'],
 ['부정·진행 근거를 찾지 못함','거짓이라고 단정하지 않고 “미확인”으로 분리. 카드 조건 검사에도 이 상태 전달',f'부정 {s["unverified_features"].get("negation",0)}개, 진행 {s["unverified_features"].get("progressive",0)}개 값'],
 ['왜 묻는 질문을 예/아니오 질문으로 읽음','단순한 같은 절의 의문사와 종결형을 함께 확인','질문 기능 1개 보정. 내포절 전체 해석은 구현하지 않음'],
 ['시작+하를 동사로 못 봄','파생동사의 말단 형태를 확인','동사 인식은 회복. 말높임 조건은 별도 문제'],
 ['별도 요 때문에 전체 실패','등록된 카드에서 EF+요/JX만 처리. 잘못된 위치는 해당 변경만 보류','독립 변경은 유지, 함께 바꿔야 하는 변경은 함께 보류'],
 ['요청 번호 오타·장문 반복','매 요청의 정확한 번호만 출력 형식에서 허용, 설명 길이 제한','새 Qwen 호출 전이므로 서버에서 효과를 확인하지 못함'],
 ['계세요 분석 충돌','Kiwi와 Qwen의 충돌을 기록하고 보류','올바른 형태소 분석으로 복구한 것은 아님']])
 h+=f'<p>총 {len(s["analysis_changed_input_ids"])}개 입력에서 분석값이 달라졌습니다. 이는 {len(s["analysis_changed_input_ids"])}개 번역이 좋아졌다는 뜻이 아닙니다. 이번에는 카드 목록과 Qwen 선택을 고정했기 때문에, 분석 보정만 추가했을 때의 최종 문장 차이는 0건이었습니다. 조회·선택 개선 효과는 별도 실험이 필요합니다.</p>'
 h+='<div class="flow"><span>원문 + 저장 분석</span><b>→</b><span>명확한 값 보정<br>불확실한 값 구별</span><b>→</b><span>저장 카드·선택 고정</span><b>→</b><span>수정 범위·조건 검사</span><b>→</b><span>재처리 결과 비교</span></div></section>'
 h+='<section id="next"><h2>다음에는 무엇을 해야 하나</h2><p><b>바로 50건 전체를 또 돌리기보다, 아래 두 문제의 처리 방식을 먼저 완성하는 것이 합리적입니다.</b> 아래는 제안이며 아직 구현·새 모델 호출하지 않았습니다.</p>'
 h+=table(['우선순위','확인된 문제','제안하는 보완','통과 기준'],[
 ['1','카드를 쓸 수 있게 됐지만 원문 공손함이 사라짐','NEW004의 입력 높임과 -나 카드의 해라체 조건을 대조. 불일치 시 그대로 막는 데서 끝내지 않고, 공손한 판정 질문 후보를 찾아 전달','새 모델 결과에서 공손함 유지. 맞는 후보가 없으면 지식 공백으로 분리'],
 ['2','오는데 → 오아도처럼 기능·활용이 어긋난 출력이 통과','해당 연결어미의 원래 기능, 선택 카드 조건, 수정 지시, 완성 활용형을 한 줄로 대조. 잘못된 카드 선택과 활용 조합을 별도 원인으로 검증','입력 관계를 임의로 바꾸지 않고, 선택 형태도 정상 조합'],
 ['그다음','분석 개선이 실제 선택 개선으로 이어지는지 미확인','위 두 검사 완성 후 동일한 50건에 새 Qwen 실험. 카드·프롬프트·코드 버전 고정','원문·승인 표현·선택 이유·실패 지점 함께 비교. 단순 변경 수를 품질로 사용하지 않음']])
 h+='<p>사용자가 지금 다시 50개를 평가할 필요는 없습니다. 먼저 프로그램이 명백한 높임·기능·활용 오류를 설명하고 줄이는지 확인해야 합니다. 어휘·구문 변환의 범위를 넓히는 작업은 이 수정과 구분해서 기록하겠습니다.</p></section>'
 h+='<section id="cases"><h2>50문장 전체 확인</h2><p>검색하거나 “출력 차이만”을 선택하세요. 문장을 펼치면 원문, 승인 표현, 이전 결과와 이번 재처리 결과를 함께 볼 수 있습니다.</p><div class="controls"><label>검색 <input id="search" placeholder="번호 또는 문장"></label><label><input type="checkbox" id="changed"> 출력 차이만</label><span id="count"></span></div>'
 for r in rows:
  diff=any(v['baseline']['output']!=v['aligned_analysis']['output'] for v in r['arms'].values())
  h+=f'<details class="case" id="{E(r["id"])}" data-changed="{str(diff).lower()}"><summary>{E(r["id"])} · {E(r["input"])}</summary><p><b>승인 표현</b> {E(r["reference"])}</p>'
  h+=table(['방식','이전 실제 출력','저장 응답 재처리'],[[a.title(),E(v['baseline']['output']),E(v['aligned_analysis']['output'])+('<p class="small">'+E(REASON.get(v['aligned_analysis'].get('reason'),v['aligned_analysis'].get('error','')) )+'</p>' if v['aligned_analysis']['output'] is None else '')] for a,v in r['arms'].items()])
  review=r['arms']['single']['alignment_review'];words={w['uid']:w['surface'] for w in r['arms']['single']['source_words']};changes=[]
  for c in review['changes']:changes.append([E(words[c['word_id']]),E(LABEL.get(c['field'],c['field'])),E(LABEL.get(c['before'],c['before']))+' → '+E(LABEL.get(c['after'],c['after']))])
  for c in review['unverified_functions']:changes.append([E(words[c['word_id']]),E(LABEL.get(c['function'],c['function'])),'단정된 분석에서 미확인 항목으로 분리'])
  for c in review['source_conflicts']:changes.append([E(words[c['word_id']]),'분석 충돌','Kiwi와 Qwen이 다른 구조로 해석 · 임의 수정 안 함'])
  if changes:h+='<h3>분석에서 달라진 점</h3>'+table(['대상','항목','변경'],changes)
  else:h+='<p>이번 범위에서 분석값 보정 없음.</p>'
  h+='<details><summary>선택한 수정과 처리 이유</summary>'
  for a,v in r['arms'].items():
   edits=v['aligned_analysis'].get('final_plan',v['aligned_analysis'].get('planner_plan',{})).get('edits',[])
   h+='<h4>'+E(a.title())+'</h4>'
   if not edits:h+='<p>재검증 가능한 수정 기록 없음.</p>';continue
   er=[]
   for e in edits:
    reasons=' / '.join(ISSUES.get(x['code'],x['code']) for x in e['issues'])
    outcome={'applied':'반영','needs_review':'보류','kept':'유지','unchanged':'변경 없음','planned':'계획만 확인'}.get(e.get('outcome'),e.get('outcome'))
    er.append([E(e['before']),E(e.get('proposed_after',e['after'])),E(e['after']),E(outcome),E(reasons or e.get('reason','')),E(', '.join(e['rule_ids']))])
   h+=table(['원문 부분','저장 Qwen 제안','프로그램 처리 형태','처리','이유','카드 ID'],er)
  h+='</details></details>'
 h+='</section><section id="evidence"><h2>검증 범위와 기록</h2>'
 h+=f'<p>코드 검사 {tests["tests"]}개 · 실패 {len(tests["failures"])}개 · 오류 {len(tests["errors"])}개. 이는 프로그램 검사이며 방언 자연스러움 평가가 아닙니다.</p>'
 h+='<ul><li>50개 입력, 승인 표현, 100개 기존 처리 기록은 해시로 변경 없음을 확인했습니다.</li><li>이전 요청 번호가 맞았던 응답만 새 프로그램의 번호에 연결했습니다. 원래 번호가 틀렸던 3건은 그대로 확인 불가입니다.</li><li>길이 제한으로 끊긴 응답 3건, 이후 단계가 없는 QUAL002 2건, 활용 응답이 없는 QUAL017 Multi 1건은 결과를 새로 만들어 넣지 않았습니다.</li><li>독립 검토자가 제시한 네 가지 문제와 반례를 수정·검증했습니다. 검토자도 전체 방언 자연스러움을 인증한 것은 아닙니다.</li><li>원본 결과와 이번 재처리 결과는 별도 파일입니다. cases.json에 입력별 변화, protocol.json에 비교 조건, input_hashes.json과 code_hashes.json에 재현 정보를 저장했습니다.</li></ul><p><a href="/reports/bottleneck-audit-20261030/report.html">이전: 어디서 정보가 끊겼는지 조사한 보고서</a></p></section>'
 (P/'report.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>문장 분석·수정 연결 보완</title><link rel="stylesheet" href="report.css"><script defer src="report.js"></script></head><body><main>'+h+'</main></body></html>',encoding='utf8')
 (P/'report.css').write_text('''*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#1d2c40;font:17px/1.75 "Malgun Gothic",sans-serif}main{max-width:1180px;margin:auto;padding:28px}header{padding:32px;background:#112b46;color:#fff;border-radius:18px}h1{font-size:34px;line-height:1.45}h2{font-size:26px;margin-top:0}h3{font-size:21px}.eyebrow{color:#a6d7ff}section{background:#fff;padding:28px;margin-top:22px;border-radius:14px}nav{display:flex;gap:16px;flex-wrap:wrap;padding:18px 0}a{color:#1263a5}table{border-collapse:collapse;width:100%;font-size:15px}th,td{padding:12px;border-bottom:1px solid #d9e2ed;text-align:left;vertical-align:top;min-width:90px;overflow-wrap:anywhere}th{background:#e9f1fa}.scroll{overflow:auto}.notice{padding:16px;background:#fff2d7;border-left:5px solid #ba7821}.flow{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:24px}.flow span{padding:14px;background:#eaf3fc;border-radius:8px}article+article{margin-top:30px;padding-top:20px;border-top:2px solid #e2eaf2}.case{border:1px solid #d8e3ef;border-radius:10px;padding:15px;margin:12px 0}.case>summary{font-weight:bold;cursor:pointer}.case[open]>summary{margin-bottom:14px}.controls{display:flex;gap:20px;flex-wrap:wrap;align-items:center}input{padding:8px;font:inherit}input[type=checkbox]{width:18px;height:18px}.small{font-size:14px;color:#57677a}li{margin-bottom:10px}[hidden]{display:none!important}@media(max-width:650px){main{padding:12px}section,header{padding:18px}h1{font-size:26px}}''',encoding='utf8')
 (P/'report.js').write_text("""const q=document.getElementById('search'),c=document.getElementById('changed'),rows=[...document.querySelectorAll('.case')];function filter(){let n=0;for(const r of rows){r.hidden=!(r.textContent.toLowerCase().includes(q.value.toLowerCase())&&(!c.checked||r.dataset.changed==='true'));if(!r.hidden)n++;}document.getElementById('count').textContent=n+' / 50문장';}q.addEventListener('input',filter);c.addEventListener('change',filter);filter();""",encoding='utf8')
 print('Generated 50-case human-readable report')
if __name__=='__main__':main()
