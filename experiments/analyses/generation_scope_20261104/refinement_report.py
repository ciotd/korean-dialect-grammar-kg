"""Human-readable evidence-linked refinement report; no model calls."""
from pathlib import Path
import json,html,collections,hashlib
H=Path(__file__).resolve().parent;R=H.parents[2]
def read(p):return json.loads(p.read_text('utf8'))
def e(s):return html.escape(str(s))
def link(p,label):return '<a href="'+Path(p).resolve().as_uri()+'">'+e(label)+'</a>'
def table(head,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+e(x)+'</th>' for x in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def main():
 out=Path(read(H/'private/latest_refinement.json')['directory']);cases=read(out/'cases.json');notes={x['id']:x for x in read(out/'lead_notes.json')};assert len(cases)==len(notes)==50
 states=collections.Counter(t['readiness'] for c in cases for t in c['current_targets'])
 labels={'out_of_slice':'현재 실행 범위 밖','no_matching_usage':'범위 안이지만 맞는 용법 없음','needs_analysis':'분석 미확정으로 전달 안 됨','ready_for_generation_trial':'Qwen에 전달됨'}
 areas={'knowledge':'실행 지식 연결','partial':'부분 성공·추가 연결','generation':'전달 후 생성 오류','gate':'조건 차단 재검토','mixed':'여러 단계 문제','lexical':'어휘 연결','analysis':'분석 불일치','choice':'허용 표현의 선택 차이'}
 h=['''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>참조처럼 바꾸려면 어디를 고쳐야 하나?</title><style>body{margin:0;background:#f4f6fa;color:#172a40;font:17px/1.65 system-ui,sans-serif}main{max-width:1150px;margin:auto;padding:24px}h1{font-size:30px}h2{font-size:23px}.box,details{background:white;border:1px solid #d5deea;border-radius:10px;padding:18px;margin:16px 0}.note{background:#fff4d9}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #dce3ee}th{background:#edf2f8}summary{cursor:pointer;font-weight:650}a{color:#145aa8}input,select{font:inherit;padding:9px}pre{white-space:pre-wrap;font:14px/1.6 system-ui}.small{font-size:14px;color:#53647b}.flow{display:flex;flex-wrap:wrap;gap:10px}.flow span{background:#e4edf9;padding:10px;border-radius:7px}</style><main><p>2026-11-04 · 승인 참조 기반 보완 / 새 Qwen 호출 0회</p><h1>참조처럼 바꾸려면 어디를 고쳐야 하나?</h1><div class="box"><b>한 가지 원인이 아닙니다.</b><br>① 실행 KG에 연결되지 않은 지식, ② 불필요할 수 있는 조건 차단, ③ 정보를 받고도 잘못 만드는 생성 문제가 함께 있습니다.<br>50문장 전체의 실제 요청과 조회 기록을 대조해 각각의 수정안을 적었습니다. 아직 번역 품질이 개선됐다는 결과는 아닙니다.</div>''']
 h.append(table(['상태','이번에 한 일'],[['완료','승인 참조50·현재62종결 위치·300요청/출력 연결'],['구현·오프라인 검사','기존 보존 검사 위반을 구체 피드백으로 만드는 보조 코드'],['유지','A 기준·Qwen 최종 생성. 원본 KG·운영 생성기 변경 없음'],['미실행','새 Qwen 재생성 실험·전체 문법 확장']]))
 h.append('<h2>같은 문장 안에도 두 문제가 있습니다</h2>'+table(['구분','내용'],[['원문','저는 그 내용을 설명했어요.'],['승인 참조','지는 그 내용을 설명했어예.'],['A 출력','저는 그 내용을 설명해예.'],['저는→지는','현재 요청에는 이 어휘 변환 지시가 없습니다. 지식 연결의 문제입니다.'],['했어요→해예','과거·었·보존 명령은 실제로 전달됐습니다. 전달 후 생성에서 어긋났습니다.']]))
 h.append('<h2>우선 수정할 구조</h2><div class="flow"><span>Qwen 첫 출력</span><span>→ 확실한 조건 위반 검사</span><span>→ 틀린 부분과 조건 전달</span><span>→ Qwen이 다시 문장 작성</span></div><p>이전에는 검사 경고만 남겼습니다. 새 후보는 그 경고를 실제 수정 요청으로 바꿉니다. 코드가 문장을 대신 고치거나 승인 정답 문장을 넣지 않습니다.</p>')
 preview_file=out/'feedback_preview_v2.json' if (out/'feedback_preview_v2.json').exists() else out/'feedback_preview.json'
 preview=read(preview_file);counts=collections.Counter(x['feedback']['status'] for x in preview)
 h.append('<div class="box note">오프라인 확인: A의100출력 중 <b>16출력</b>만 이 한정된 검사의 대상입니다. 그중 <b>6출력(3문장×2회)</b>의 위반을 피드백으로 만들었습니다. 나머지84출력은 검사 범위 밖이며 정답 판정이 아닙니다. 모델에 보내서 고쳐지는지는 아직 확인하지 않았습니다.</div>')
 h.append(table(['수정안','근거','검증 방법'],[['구체 오류 피드백','설명했어요→설명해예, 같아요→같어예 등 전달된 보존 조건 위반','같은 첫 출력에 중립 재검토와 오류 위치 피드백을 각각 한 번씩 비교. 추가 계산량을 맞춤.'],['조건 의존 범위 정리','나왔어요는 규칙이 조회됐지만 앞절 경계 unknown으로 전달 차단','그 규칙이 실제로 필요로 하는 조건만 의존하도록 설계. 모든 unknown을 무시하지 않음.'],['참조의 지식 연결','옛 자료의 다/니꺼/께예/이소/어휘 등이 현재 실행 구성에 미연결','형태의 존재와 입력 적용 조건을 나누고 작은 묶음별 새 문장 검증.']]))
 h.append('<p>'+link(H/'REFINEMENT_PLAN.md','수정안·종료 기준·이전 실험과의 차이')+'</p>')
 h.append('<details><summary>62개 종결 위치의 현재 경로 — 오류율이 아닙니다</summary>'+table(['경로','위치 수'],[[e(labels.get(k,k)),str(v)] for k,v in states.items()])+'<p>이 표는 승인 참조에 필요한 어휘·절 연결 전체 개수가 아닙니다. 현재 실행기가 분석한 종결 위치만 셌습니다.</p></details>')
 h.append('<h2>50문장별로 무엇을 고칠 것인가</h2><p>관찰과 수정안은 리드의 검토입니다. 참조와 글자가 다르다는 이유만으로 오류로 세지 않았습니다.</p><input id="q" placeholder="문장·ID 검색"><select id="area"><option value="all">모든 보완 영역</option>'+''.join('<option value="'+k+'">'+v+'</option>' for k,v in areas.items())+'</select>')
 for c in cases:
  n=notes[c['id']];h.append('<details class="case" data-area="'+n['primary_work_area']+'"><summary>'+e(c['id']+' · '+c['input'])+'</summary>')
  outputs=[]
  for x in c['outputs']['A']:
   if x['text'] not in outputs:outputs.append(x['text'])
  h.append(table(['비교','문장'],[['승인 참조',e(c['approved_reference'])],['A 실제 출력',e(' / '.join(outputs))]]))
  h.append('<p><b>확인한 문제:</b> '+e(n['observation'])+'</p><p><b>수정안:</b> '+e(n['proposed_fix'])+'</p>')
  h.append(table(['현재 목표 위치','실제 경로','조회/전달 후보','근거'],[[e(t['target_id']),e(labels.get(t['readiness'],t['readiness'])),e(', '.join(t['selected_rule_ids']) or '없음'),link(t['query_path'],'조회 기록')] for t in c['current_targets']]))
  h.append('<p class="small">관련 옛 카드 후보: '+e('; '.join(f['label']+': '+', '.join(f['legacy_card_ids']) for f in c['historical_families']))+'<br>옛 카드의 존재는 현재 규칙의 적용 가능성을 증명하지 않습니다. 상세 원문 재검증이 남은 항목을 포함합니다.</p>'+link(c['outputs']['A'][0]['request'],'실제 요청')+' · '+link(c['outputs']['A'][0]['response'],'Qwen 원시 응답')+'</details>')
 h.append('<h2>두 검토자와 반영 결과</h2>')
 resolution=out/'reviewer_resolution.md'
 if resolution.exists():h.append('<div class="box"><pre>'+e(resolution.read_text('utf8'))+'</pre></div>')
 for who in ('codex','claude'):
  p=out/'reviewers'/who/'review.md'
  if p.exists():h.append('<details><summary>'+who+' 독립 검토 원문</summary><pre>'+e(p.read_text('utf8'))+'</pre></details>')
  else:h.append('<p>'+who+' 검토 진행 중</p>')
 h.append('<p>'+link(out/'manifest.json','원본 기록과 해시')+' · '+link(out/'lead_notes.json','50개 검토 원본')+' · '+link(preview_file,'오프라인 피드백 검사 기록')+'</p>')
 h.append('''</main><script>function filter(){const q=document.getElementById('q').value.toLowerCase(),a=document.getElementById('area').value;document.querySelectorAll('.case').forEach(x=>x.hidden=!((a==='all'||x.dataset.area===a)&&x.textContent.toLowerCase().includes(q)))}document.getElementById('q').oninput=filter;document.getElementById('area').onchange=filter;</script></html>''')
 (out/'report.html').write_text(''.join(h),'utf8')
 nav=R/'experiments/management/report_navigation.json';entries=read(nav);key='40 · 승인 참조50 기반 수정안'
 entries=[x for x in entries if x['title']!=key]+[{'title':key,'url':(out/'report.html').as_uri(),'summary':'50입력·62조회 위치 대조. 실행 지식 공백·조건 차단·전달 후 생성 실패 분리. 구체 오류 피드백 후보 오프라인 검사. 새 모델 호출 없음.'}]
 nav.write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n','utf8');print(out/'report.html')
if __name__=='__main__':main()
