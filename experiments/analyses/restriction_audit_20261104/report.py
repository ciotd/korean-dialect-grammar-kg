"""Render the read-only audit from saved evidence; no model calls."""
from pathlib import Path
import json,html,collections
H=Path(__file__).resolve().parent;R=H.parents[2];P=H/'private'
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def esc(x):return html.escape(str(x))
def link(p,label):return '<a href="'+Path(p).resolve().as_uri()+'">'+esc(label)+'</a>'
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def main():
 s=read(P/'summary.json');cs=read(P/'cases.json');ts=read(P/'targets.json')
 source=R/'experiments/runs'/s['source_run'];snap=source/'code_snapshot'
 titles={'construction_scope_excluded':'현재 지원 범위 밖','no_rule_satisfies_conditions':'범위 안이지만 맞는 규칙 없음','analysis_or_alignment_unresolved':'분석·위치 미확정','delivered':'수정 지시 전달'}
 reasons=[]
 for t in ts:
  entries=[]
  for q in t['all_constructions']:
   zeros=[{'feature':n['feature'],'observed':n['value'],'before':n['before'],'after':n['after']} for n in q['narrowing'] if n['before'] and not n['after']]
   entries.append({'construction':q['id'],'state':q['state'],'scope_failures':q['scope_failures'],'candidate_exhaustion':zeros})
  reasons.append({'id':t['id'],'route':t['route'],'needs_analysis':t['needs_analysis'],'construction_details':entries})
 save(P/'restriction_reasons.json',reasons)
 ledger=[
 ('ENTRY','수정 위치를 종결어미가 있는 어절에서만 찾음','62곳 모두 해당. 연결어미·관형절·조사는 독립 수정 대상이 아님. 문맥 분석에는 포함됨.','입력 범위 결정','experiments/analyses/research_loop_20261103/pipeline.py',24,'⑤에서 용법군별로 확장. 지금 모든 형태소를 무조건 수정 대상으로 만들지 않음.'),
 ('SCOPE','현재 연결된 네 문법 구성의 범위 확인','62곳 중 29곳은 네 구성 모두 범위 밖. 자연스러운 방언이 없다는 뜻이 아님.','실제 전달 차단','experiments/analyses/question_refinement_20261102/query.py',119,'현재 지원과 앞으로 정제할 지식을 분리해 표시.'),
 ('CONDITION','문법 특징을 따라 규칙 후보를 좁힘','12곳은 범위에 들어가는 구성에서도 후보가 없음. 규칙에 없는 어미·명사 종류 등이 관찰됨.','실제 전달 차단','experiments/analyses/question_refinement_20261102/query.py',119,'규칙 미지원과 잘못 분석된 특징을 구분. 아무 조건이나 해제하지 않음.'),
 ('UNKNOWN','필요한 분석이 미확정이면 전달 보류','DEV026은 규칙에 맞지만 경계 미확정. QUAL017의 첫 위치는 서술어 종류 미확정.','실제 전달 보류','experiments/analyses/boundary_qwen_20261103/run.py',64,'두 사례의 분석 근거부터 대조. 미확정을 허용값으로 바꾸지 않음.'),
 ('FORM','결합형이 있는 선택지만 생성에 전달','전달 대상 19개 형태 중 삭제 0개. 이 필터가 이번 실패를 만들었다고 볼 근거 없음.','존재하지만 이번 삭제 없음','experiments/analyses/boundary_qwen_20261103/run.py',81,'현재 실패 원인으로 지목하지 않음.'),
 ('NOTES','생성에 전달할 속성을 정해 추림','관찰 메모 18회분이 context_notes로는 전달되지 않음. 메모에는 지역 변이·다른 기능 등이 포함.','필드 생략, 영향 미검증','experiments/analyses/boundary_qwen_20261103/run.py',77,'전부 덧붙이기보다 현재 선택에 필요한 정보인지 검토. 누락 자체를 오류로 계산하지 않음.'),
 ('PROMPT','지시 없는 문장은 원문 유지 / 허용 위치 밖 수정 금지','지시가 없는 33문장은 모두 원문 유지. 지시 있는 17문장은 일부 변경.','실제 요청 지시와 출력 일치','experiments/analyses/boundary_qwen_20261103/runtime.py',134,'②에서 수정 범위와 지식 부족을 분리한 비교 설계. 범위 완화는 아직 미실행.'),
 ('COMPOSITION','어간·시제·어미를 Qwen이 결합','과거 었 보존 지시가 전달돼도 설명했어요→설명해예 발생. 같아요→같어예도 관찰.','원시 생성에서 오류 관찰','experiments/analyses/boundary_qwen_20261103/runtime.py',131,'카드 표현·결합 설명·편집 역할 중 어느 요인이 원인인지 통제 비교. 서버 오류로 단정 금지.'),
 ('CHECK','생성 뒤 검사는 경고만 기록','50건 모두 저장 출력=원시 응답의 output_text. 검사가 원문으로 되돌린 사례 0건.','현재 출력의 원인 아님','experiments/analyses/boundary_qwen_20261103/run.py',43,'후처리 복원 가설은 이번 실행에서 제외.'),
 ]
 save(P/'restriction_ledger.json',[dict(zip(('id','restriction','observed','classification','code_path','line','next'),x)) for x in ledger])
 htmlparts=['''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>어디서 변환이 멈췄나 · 1단계</title><style>body{font:17px/1.65 system-ui,sans-serif;color:#203047;background:#f3f6fa;margin:0}main{max-width:1160px;margin:auto;padding:32px 22px}h1{font-size:30px}h2{margin-top:38px;font-size:23px}h3{font-size:19px}section,.box,details{background:white;border:1px solid #dae2ed;border-radius:12px;padding:18px;margin:14px 0}table{border-collapse:collapse;width:100%;font-size:15px}td,th{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #dde3ed}th{background:#eaf0f7}a{color:#155caa}.scroll{overflow:auto}.flow{display:flex;gap:10px;flex-wrap:wrap}.flow div{flex:1;min-width:180px;background:#e8eff9;border-radius:9px;padding:15px}.small{font-size:14px;color:#566577}.warn{background:#fff3dc}.good{background:#e6f4ec}summary{cursor:pointer;font-weight:650}input,select{font:inherit;padding:8px;border:1px solid #acbbcd;border-radius:6px}pre{white-space:pre-wrap;word-break:break-word;font-size:13px}.badge{padding:4px 9px;background:#e9eef5;border-radius:9px}#cases details{scroll-margin-top:15px}</style><main><p>① 제한 위치 확인 · 2026-11-04 · 기존 기록 재검토</p><h1>정보가 안 간 문제와, 받고도 잘못 쓴 문제는 다릅니다.</h1><div class="box"><b>이번에 한 일</b>: 50문장 → 62개 종결 위치 → 조회 결과 → 실제 생성 요청 → 원시 응답을 전부 연결했습니다.<br>새 Qwen 호출·KG 변경·운영 코드 변경: 모두 0. 검토 모델의 자료 읽기와 의견 작성은 별도입니다.</div>''']
 htmlparts.append('<div class="flow"><div><b>50문장</b><br>62개 종결 위치 분석</div><div><b>43곳 미전달</b><br>범위 밖 29 + 후보 없음 12 + 미확정 2</div><div><b>19곳 전달</b><br>17문장에 수정 지시</div><div><b>최종 출력</b><br>17문장 일부 변경<br>33문장 원문 유지</div></div><p class="small">문장 수와 위치 수는 다릅니다. 한 문장에 여러 종결 위치가 있을 수 있습니다. 변경 수는 품질 점수가 아닙니다.</p>')
 htmlparts.append('<h2>1. 지금 확실히 말할 수 있는 것</h2>'+table(['질문','기록으로 확인한 답'],[
 ['왜 33문장이 그대로였나?','33문장 모두 수정 지시가 없었고, 프롬프트는 그런 경우 원문을 유지하라고 지시했습니다. 각 문장에 가능한 방언 표현이 없다는 판정은 아닙니다.'],
 ['선별 코드가 정보를 다 버렸나?','현재 결합형 필터는 19개 중 0개를 삭제했습니다. 복수 준비 후보 보류도 0곳입니다. 대신 지원 범위·문법 조건·분석 미확정 단계에서 43곳이 미전달됐습니다.'],
 ['정보를 받으면 잘 생성했나?','아닙니다. 었을 보존하라는 정보가 갔는데도 설명했어요가 설명해예로 나왔습니다. LONG001의 와는 노를 전달받고도 그대로 남았습니다.'],
 ['검사 코드가 출력 문장을 되돌렸나?','아닙니다. 50건 모두 Qwen 원시 응답과 저장 문장이 같습니다.'],
 ['현재도 큰 분류 전체만 가져오나?','이 실행은 네 문법 구성에서 조건 관계를 따라 후보를 좁힙니다. 과거의 큰 분류 카드 조회와 구분해야 합니다. 다만 종결 위치 중심이고 지원 규칙은 11개입니다.'],
 ['원인이 확정됐나?','어디서 정보가 미전달됐는지와 어디서 잘못 출력됐는지는 확인했습니다. 그 제한을 풀거나 전달 설명을 바꾸면 좋아지는지는 다음 통제 비교가 필요합니다.']]))
 htmlparts.append('<h2>2. 실제 사례로 보면</h2>'+table(['사례','흐름에서 확인한 사실','수정 방향'],[
 ['DEV002 · 빵을 샀어','평서·반말. 현재 네 구성 모두 지원 범위 밖 → 지시 없음 → 원문 유지.','⑤에서 평서·반말 지식과 연결을 정제할 대상. 아무 의문형 규칙을 붙이지 않음.'],
 ['DEV011 · 출발했나요?','공손한 정보 질문 범위에는 들어감. 현재 해당 규칙의 어미 조건과 맞지 않아 후보 0.','-나요?에 맞는 지식·조건 연결을 확보. 문헌 자체에 없다는 결론은 아님.'],
 ['DEV026 · 나왔어요','평서 규칙 후보는 있음. 앞부분과의 경계 관계가 미확정 → 전달 보류.','분석 연결을 점검할 대상. 규칙을 새로 추가하는 문제와 다름.'],
 ['ADVCE006A/B · 설명했어요','과거 었과 보존 지시가 실제 전달됨 → 설명해예.','생성 지시 이해·활용 조합을 분리 검증. 후처리나 정보 미전달이 원인은 아님.'],
 ['QUAL003 · 같아요','분석 기본형 어요와 결합형 어예를 받음 → 같어예.','기본형과 실제 표기 관계가 불명확할 가능성. 카드 설명과 모델 결합 능력 중 원인 미확정.']]))
 htmlparts.append('<section class="warn"><h3>미전달 43곳 = KG 지식 부족 43곳은 아닙니다.</h3><p>“계세요”는 조회용 형태 분석에서 “계 + 이다”로 잡혔습니다. Qwen의 원시 설명에는 “계시다”라고 되어 있는데, 조회는 계사 규칙으로 갔습니다. “빌려드릴게요”를 요청으로 분류한 값은 Qwen의 원시 분석부터 들어 있었습니다.</p><p>범위 밖·후보 없음으로 분류된 곳 중 4곳에는 분석 미확정도 겹칩니다. 따라서 29/12/2는 현재 실행의 경로 수이며, 원인을 하나씩 나눈 숫자가 아닙니다.</p><p>이번에 추적한 62곳은 종결어미가 있는 어절입니다. 다른 연결어미·관형절·조사 태그 어절 193회는 독립 수정 대상으로 선택되지 않았습니다. 193은 문법 규칙 수가 아닙니다.</p></section>')
 htmlparts.append('<h2>3. 코드 제한과 실제 영향</h2>'+table(['제한','이번 영향','다음 조치','실행 당시 코드'],[[esc(x[1]),esc(x[2]),esc(x[6]),link(snap/x[4],Path(x[4]).name+' '+str(x[5])+'행')] for x in ledger]))
 htmlparts.append('<h2>4. 같은 실험을 반복하지 않기 위한 기준</h2><section><ul><li>이전의 설명 축약, 결합형 변경, 보존 접두부 추가, 시스템 지시 두 문장 변경, 온도 비교는 이미 일부 수행했습니다. 그것만 다시 바꾸는 일을 새 원인 검증으로 포장하지 않습니다.</li><li>이번 추가 확인은 <b>50개 입력 전체의 미전달 경로와 실제 최종 요청을 연결</b>한 것입니다. 최종 프롬프트에 없는 옛 설명을 실패 원인으로 지목하지 않습니다.</li><li>관찰 메모 누락 18회, 계사 높임 필드의 의미 차이, 어요/어예 결합 설명은 검토 후보입니다. 원인 확정 목록이 아닙니다.</li><li>과거 표현과 사용자 승인 참조의 차이는 문법·지역·화용 맥락을 따로 검토합니다. 참조와 글자가 다르다는 이유만으로 전부 오답 처리하지 않습니다.</li></ul></section>')
 htmlparts.append('<h2>5. 다음 순서와 논문 연결</h2>'+table(['단계','무엇을 할 것인가','종료 기준 / 안 되면'],[
 ['② 비교 조건 확정','이번 기록을 이용해 지식·분석·모델 설정을 고정하고 바꾸는 요소를 하나씩 지정. 기존의 실패한 비교와 다른 점을 먼저 설명.','가설·비교군·실제 요청·측정 기준·중단 기준이 정해지면 종료. 같은 실험이면 제외.'],
 ['③ 생성 비교','같은 지식으로 지시 충돌·편집 범위를 분리 확인하고 새 개발 문장에도 적용.','반복 개선이면 통합. 없으면 프롬프트 수정 반복을 멈추고 역할·지식 표현 가설 재검토.'],
 ['④ 전체 50 재실험','분석·조회까지 연결해 기존 오류와 새 오류 확인.','개발·회귀 결과로 기록. 독립 최종 성능이라고 주장하지 않음.'],
 ['⑤ 미지원 문법 확장','현재 네 구성 밖의 용법을 원문에 근거해 정제하고 연결.','각 용법에 근거·조건·새 문장 확인 확보. 불확실한 범위는 구분.'],
 ['⑥ 논문 효과 평가','같은 Qwen의 KG 없음·문헌 텍스트 검색·조건 KG 등을 공정하게 비교.','최종 평가는 개발에 쓰지 않은 입력과 사람 평가. 선행연구 방식은 출처·구현 차이를 확인한 뒤 비교군 확정.']]))
 htmlparts.append('<p class="box warn">논문에서 이번 자료가 뒷받침하는 것: 현재 구현의 지원 범위와 오류 발생 위치. 아직 뒷받침하지 못하는 것: KG가 자연스러움을 향상시킨다는 결론, 서버가 원인이라는 결론.</p>')
 htmlparts.append('<h2>6. 두 검토자의 확인</h2>')
 for who,label in [('codex','Codex · 코드와 집계'),('claude','Claude · 문법과 전달 설명')]:
  p=P/'reviewers'/who/'review.md'
  htmlparts.append('<details><summary>'+label+(' · 의견 도착' if p.exists() else ' · 검토 요청 전달, 결과 대기')+'</summary>'+(('<pre>'+esc(p.read_text('utf8'))+'</pre>') if p.exists() else '<p>결과를 받기 전 완료로 표시하지 않습니다.</p>')+'</details>')
 resolution=H/'reviewer_resolution.md'
 if resolution.exists():htmlparts.append('<section><h3>리드의 대조·판정</h3><pre>'+esc(resolution.read_text('utf8'))+'</pre></section>')
 htmlparts.append('<h2>7. 50문장 전부 확인</h2><p>문장을 열면 미전달 이유와 실제 수정 지시 위치를 볼 수 있습니다. “후보 없음”은 현재 구현 기준이며 방언 표현이 없다는 뜻이 아닙니다.</p><input id="search" placeholder="ID 또는 문장 검색"><select id="mode"><option value="all">전체 50문장</option><option value="none">지시 없음 33문장</option><option value="some">지시 있음 17문장</option></select><div id="cases">')
 for c in cs:
  rows=[]
  for t in c['targets']:
   ds=[]
   for q in t['all_constructions']:
    if q['scope_failures']:
     reason=' / '.join(f"{x['feature']}={x['observed']} (지원 {', '.join(map(str,x['supported']))})" for x in q['scope_failures'])
    else:
     zero=[n for n in q['narrowing'] if n['before'] and not n['after']]
     reason=' / '.join(f"{n['feature']}={n['value']}에서 후보 {n['before']}→0" for n in zero) or q['state']
    ds.append(esc(q['id'])+': '+esc(reason))
   state=titles[t['route']]
   if t['needs_analysis']:state+=' / 미확정: '+', '.join(t['needs_analysis'])
   a=t['action'];transfer=('규칙 '+esc(a['rule_id'])+'<br>어간 '+esc(a.get('stem'))+' · 앞 어미 '+esc(a.get('prefinals'))+'<br>실제 출력: <b>'+esc(t['replacement'])+'</b>') if a else '전달 없음'
   rows.append([esc(t['target_id']+' · '+t['target']),esc(state),transfer,'<details><summary>네 구성의 조회 근거</summary>'+'<br>'.join(ds)+'<p>'+link(t['trace_path'],'조회 원본')+'</p></details>'])
  htmlparts.append('<details class="case" data-mode="'+('some' if c['action_count'] else 'none')+'"><summary>'+esc(c['id']+' · '+c['input_text'])+'</summary><p><b>실제 출력:</b> '+esc(c['output_text'])+'</p>'+table(['위치','결정','전달·출력','근거'],rows)+'<p>'+link(c['packet_path'],'실제 전달 정보')+' · '+link(c['request_path'],'요청 원본')+' · '+link(c['response_path'],'응답 원본')+'</p></details>')
 htmlparts.append('</div><h2>8. 재현·검증</h2><p>원본 1,023개 파일의 해시(내용 식별값) 확인. 50건 요청과 전달 정보 일치, 50건 응답과 저장 출력 일치. 62개 위치 모두 포함. 아래 자료로 다시 집계할 수 있습니다.</p><p>'+link(H/'audit.py','집계 코드')+' · '+link(P/'validation.json','검증 결과')+' · '+link(P/'restriction_ledger.json','제한 목록')+' · '+link(P/'restriction_reasons.json','62곳 조건 상세')+'</p><p class="small">운영 코드·KG·원본 실험 불변. 새 Qwen 실험 없음. 현재 보고서는 원인 진단이며 자연스러움 평가가 아닙니다.</p></main><script>function filter(){let q=document.getElementById("search").value.toLowerCase(),m=document.getElementById("mode").value;document.querySelectorAll(".case").forEach(x=>x.hidden=!((m==="all"||x.dataset.mode===m)&&x.textContent.toLowerCase().includes(q)))}document.getElementById("search").oninput=filter;document.getElementById("mode").onchange=filter;</script></html>')
 (P/'report.html').write_text(''.join(htmlparts),'utf8')
 print('Report created:',P/'report.html')

if __name__=='__main__':main()
