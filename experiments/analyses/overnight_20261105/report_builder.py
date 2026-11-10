"""Meeting report from saved runs. Exact outputs stay private."""
from pathlib import Path
import json,html,collections,datetime
H=Path(__file__).resolve().parent;R=H.parents[2];O=H/'private'
def read(p,default=None):return json.loads(p.read_text('utf8')) if p.exists() else default
def esc(v):return html.escape(str(v))
def table(headers,rows,cls=''):
 return '<div class="scroll"><table class="'+cls+'"><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
 keys={'feedback':'latest_feedback.json','development':'latest_past_development.json','regression':'latest_past_regression.json','pilot':'latest_pilot.json'}
 runs={k:Path(read(O/v)['directory']) for k,v in keys.items()};metrics={k:read(v/'metrics.json',{}) for k,v in runs.items()}
 reg=read(runs['regression']/'private/results.json',[]);pilot=read(runs['pilot']/'private/results.json',[]);pairs={};easy={}
 for r in reg:pairs.setdefault(r['source_id'],{})[r['arm']]=r
 for r in pilot:easy.setdefault(r['source_id'],{})[r['arm']]=r
 calls=sum(m.get('api_attempts',0) for m in metrics.values());tokens=sum(m.get('reported_usage',{}).get('total_tokens',0) for m in metrics.values())
 now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
 parts=['''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>11월5일 연구 미팅 · KG와 Qwen</title><link rel="stylesheet" href="report.css"><script src="report.js" defer></script></head><body><main><header><p class="eyebrow">연구 미팅 / 논문 인계</p><h1>무엇을 고쳤고,<br>무엇이 아직 안 되는가?</h1><p class="lead">문장의 조건에 맞는 지식을 찾는 부분은 좁은 범위에서 작동합니다.<br>그 지식을 받은 Qwen이 항상 올바른 문장을 만드는 단계까지는 도달하지 못했습니다.</p>''',f'<p class="muted">{now} · Qwen 최종 생성 유지 · 사람 자연스러움 평가 전</p></header>', '''<nav><a href="#answer">핵심 결과</a><a href="#method">제안 방법</a><a href="#history">연구 흐름</a><a href="#example">실제 사례</a><a href="#all50">50문장</a><a href="#easy">쉬운30</a><a href="#next">다음 단계</a><a href="paper_handoff.md">논문 인계</a></nav>
<section id="answer"><h2>먼저 이것만 보면 됩니다</h2><div class="cards"><article><b>지식 누락은 일부 보완</b><p>과거 긍정·부정 계사 규칙을 추가했습니다. 새 개발8개에서 과거를 남긴 예 종결이 생성됐습니다.</p></article><article><b>생성 오류는 남음</b><p>기존50의 새 지원4곳 중2곳은 ‘어’를 빠뜨렸습니다. 기존 과거형 소실도 남았습니다.</p></article><article><b>기본 버전은 보존</b><p>r7은 유지하고 r10은 실험 후보로 남겼습니다. 실패한 피드백 방식은 채택하지 않았습니다.</p></article></div>''']
 parts.append(table(['순서','한 일','확인된 결과','상태'],[
 ['①','같은 실패에 중립/구체 피드백 비교','계약 회복0/6 대0/6. 같은 문구 수정 반복 중단','완료·미채택'],
 ['②','과거 긍정·부정 계사 KG 후보 + 새16 비교','신규 대상8개 표면 보존. 대조8개 출력 동일','완료·후보 유지'],
 ['③','62위치 분석/차단과 Kiwi 후보 대조','전역 구조 미확정 차단1곳. 계세요의 형태 분석 오류 확인','진단 완료·자동 완화 미채택'],
 ['④','같은62분석으로 r7/r10 각50 생성','4위치 새 전달,2위치 계약 충족·2위치 어 탈락','완료·운영 채택 보류'],
 ['⑤','남은39위치 기록·확장 순서 구분','반말 평서/질문/요청/절 연결 등이 남음','일부 확장·전면 완료 아님'],
 ['⑥','쉬운30, 무지식/텍스트/JSON 비교','개발 파일럿. 독립 평가·사람 품질 평가 미실행','완료' if metrics['pilot'] else '실행 중']]))
 parts.append('''<p class="note">표면 계약은 규칙이 요구한 글자·형태가 출력에 남았는지 보는 좁은 검사입니다. 자연스러운 방언인지 판단하는 점수가 아닙니다.</p></section>
<section id="method"><h2>우리가 제안하는 방법</h2><p><strong>문장의 조건에 맞는 문법 지식을 골라</strong> Qwen에 전달하는 방식을 구현했습니다. Qwen이 그 정보를 참고해 전체 방언 문장을 씁니다.</p>
<div class="flow"><div>표준어 입력</div><span>→</span><div>Kiwi 위치<br>Qwen 뜻 분석</div><span>→</span><div>KG 조건·관계<br>필요한 규칙 조회</div><span>→</span><div>규칙·보존 정보<br>전달</div><span>→</span><div>Qwen 전체<br>문장 생성</div></div>''')
 parts.append(table(['단계','실제로 하는 일','판단 주체'],[
 ['분석','형태소·원문 위치와 평서/질문·높임·절 관계를 구분','Kiwi 관측 + Qwen 판단'],
 ['KG 연결','분석값을 FeatureValue에 연결. 구성의 지원 범위와 각 조건을 대조','코드 + 실제 그래프'],
 ['조회','HAS_USAGE → ANY_BRANCH → ALL → Condition → ACCEPTS. 실현 REALIZES, 근거 SUPPORTED_BY','그래프 Reader'],
 ['전달','위치·어간/선어말/종결형·선택 규칙·조합 설명·보존 정보','코드'],
 ['생성','전체 문장을 작성. 조합기나 코드가 결과를 몰래 대신 쓰지 않음','Qwen'],
 ['검사','원시 요청/응답/경로/버전/비용 보존. 의미·자연스러움은 사람 평가 필요','코드 + 사람']]))
 parts.append('''<details><summary>큰 설계와 실제 구현의 차이</summary><p>공통 척추와12모듈은 전체 문법 지식을 놓을 지도입니다. 현재 r7/r10은 그중 일부를 조건 조회 가능한 작은 그래프로 정제한 실행 범위입니다. 7종 문헌 전체가 실행 규칙으로 정제된 상태가 아닙니다.</p>''')
 parts.append(table(['구분','현재 상태'],[
 ['원래 큰 KG','문헌 근거·개념·설계 연결. 과거 Neo4j 적재 이력 있음'],
 ['r7 실행 범위','195노드·472관계·4문법 구성·11규칙'],
 ['r10 후보','222노드·541관계·5문법 구성·12규칙. 과거 계사 한 묶음 추가'],
 ['이번 조회 방식','동결 JSON 그래프의 실제 노드·관계를 Reader로 탐색. Neo4j 실시간 조회 아님'],
 ['12모듈','동사 / 형용사·계사 / 명사류 / 조사 / 어미·종결 / 높임 / 절 / 시제·상·양태·부정 / 사동·피동·보조용언 / 어휘 / 형태음운·표기 / 지역·변이·실행제어'],
 ['논문 주장 한계','조건 기반 지식 선택·전달 구조. 전체12모듈 구현·자연스러움 우월성은 미입증']]))
 parts.append('''</details></section><section id="history"><h2>많은 실험은 무엇을 알아내기 위한 것이었나?</h2>''')
 parts.append(table(['연구 묶음','확인하려던 것','현재 얻은 교훈'],[
 ['문헌7종·설계19개·초기 KG·Neo4j','개념과 출처를 연결해 볼 수 있는가','저장·시각화와 실행 조건 조회는 다른 단계'],
 ['single/multi·카드 내용·선별','어떤 지식을 어떻게 넘길 것인가','큰 분류의 문헌 조각 조회만으로 적절한 규칙이 선택되지는 않음'],
 ['의문문 정제·조건 대응·Kiwi 결속','문장의 기능을 KG 조건에 연결할 수 있는가','형태/뜻/절 범위를 나눠 묻고 실제 관계로 좁혀야 함'],
 ['공손 평서·높임·지원 확장','작은 구성을 다른 범위로 넓힐 수 있는가','지원 지식이어도 생성은 틀릴 수 있음'],
 ['제한 점검·A/B/C·최소 지시·온도','복사 강제나 지시가 실패 원인인가','변경 증가와 품질은 다름. 서버 오류로 확정할 근거 없음'],
 ['이번 피드백·r10·통제 파일럿','수정 효과를 같은 조건에서 분리할 수 있는가','지식 확대 확인. 생성 안정성·독립 평가 남음']]))
 parts.append('''<p>입력·조건·평가 기준이 다른 과거 실험의 수치를 하나의 정확도로 합치지 않습니다.</p></section>
<section id="example"><h2>실제 한 문장은 이렇게 움직였습니다</h2><p class="example">작년에는 이곳이 도서관이었어요.</p>''')
 parts.append(table(['순서','실제 기록'],[
 ['분석','주절 / 평서 / 공손 / 긍정 계사 / 과거 eoss / 주체높임 없음 / 일반명사'],
 ['구성 연결','SEM_CX_EXT_COP_PAST → SUPPORTED_IN → SCOPE_EXT_COP_PAST'],
 ['조건 대조','SEM_EXT_COP_PAST_HAEYE → positive branch → Condition / ACCEPTS 값 대조'],
 ['실현·근거','REALIZES → FORM_EXT_COP_PAST_HAEYE / SUPPORTED_BY → EV_DECL_STRUCTURE (D02 PDF203)'],
 ['전달','목표 도서관이었어요; 계사·과거를 남기고 해체 뒤 예를 결합. 완성 정답 미전달'],
 ['실제 출력','작년에는 이곳이 도서관이었어예.']]))
 parts.append('''<p class="note">문헌은 해체+예의 일반 구성 근거를 줍니다. 이번 과거 계사 범위와 제외 조건은 제한된 조합 후보입니다. 모든 완성형의 직접 문헌 인증이 아닙니다.</p><h3>하지만 이것은 아직 실패했습니다</h3>''')
 parts.append(table(['입력','실제 r10 출력','끊긴 지점'],[[pairs['NEW012']['r10']['input_text'],pairs['NEW012']['r10']['output_text'],'규칙2개 조회·전달 완료. 생성에서 어 탈락. 다중 action 원인설은 가설']]))
 parts.append('<p class="note">두 버전에 공통으로 남은 오류도 있습니다: 설명했어요→설명해예(과거 소실), 안 와?→안 노?(동사 형태 손실). 달라진3개만 보고 나머지가 모두 정상이라고 판단하면 안 됩니다.</p>')
 parts.append('''<p>‘지식이 없다’와 ‘전달받고도 잘못 쓴다’를 구별했습니다. 한 사례로 입력 길이 때문이라고 단정하지는 않습니다.</p></section>
<section id="all50"><h2>기존50 전체 비교</h2><p>같은 분석에서 KG만 바꿨습니다. 아래는 원본 출력 대조이며 품질 점수가 아닙니다.</p><label>검색 <input id="filter50" placeholder="ID 또는 문장"></label><label><input id="changedOnly" type="checkbox">달라진3개만</label>''')
 parts.append(table(['ID','표준어','기존 r7','후보 r10'],[[i,p['r7']['input_text'],p['r7']['output_text'],p['r10']['output_text']] for i,p in pairs.items()],'results50'))
 parts.append('''</section><section id="easy"><h2>쉬운30: 무엇을 비교했나?</h2><p>한 주요절·한 종결 위치 중심30개를 출력 전에 고정했습니다. 검토자가 지원 범위를 알고 만든 <strong>개발 파일럿</strong>입니다. 독립 평가셋이 아닙니다.</p>''')
 parts.append(table(['조건','공통','차이'],[
 ['N 지식 없음','같은 원문·분석·Qwen·호출기회','빈 참고 블록. 사전학습 활용 허용'],
 ['T 펼친 텍스트','같은 원문·분석·Qwen·호출기회','KG 선택 지식을 경로=값으로 전달'],
 ['J JSON','같은 원문·분석·Qwen·호출기회','T와 같은 지식을 계층형 JSON으로 전달']]))
 parts.append('''<p>세 조건 모두 빈 지식에서 원문 복사를 강제하지 않습니다. T/J 정보 동일성을 역복원으로 검사했습니다. 길이·키 순서도 달라집니다. 이 비교는 텍스트 검색과 그래프 검색의 비교가 아닙니다.</p>''')
 pm=metrics['pilot']
 if pm:
  parts.append(table(['자동 관찰 — 정확도 아님','N','T','J'],[
   ['생성 응답 수',*[pm['arm_counts'].get(a,0) for a in ['N','T','J']]],
   ['원문 동일 출력(품질 아님)',*[pm['unchanged_counts'][a] for a in ['N','T','J']]],
   ['과거 형태소 감소 경고(오분석 가능)',*[pm['past_count_decrease_warnings'][a] for a in ['N','T','J']]],
   ['사람 자연스러움 평가','미실시','미실시','미실시']]))
 else:parts.append('<p class="note">아직 실행 중입니다.</p>')
 parts.append('<p class="note">단문 우체국이었어요도 T/J에서 우체국이예로 바뀌어 과거형이 빠졌습니다. 긴 문장만의 문제는 아닙니다. r10 후보12출력 중 표면 계약9충족/3불충족이며 개발8/8·회귀2/4와 합산하지 않습니다.</p>')
 parts.append(table(['층','입력 수','T/J 출력 상이'],[['선택 규칙 있음',24,3],['선택 규칙 없음',6,4]]))
 parts.append('<p>조건당1회 결과입니다. 같은 형식의 반복 변동성은 측정하지 않았습니다. 7개 차이를 모두 안정적인 형식 효과나 규칙 적용 차이로 세지 않습니다.</p>')
 parts.append(table(['생성30회 비용','N','T','J'],[['요청 입력 토큰',10736,69453,29262],['모델 출력 토큰',3578,3275,2706],['입력+출력 합',14314,72728,31968],['호출 지연 합(초)',68.364,69.268,54.242]]))
 parts.append('<p>공통 분석59,020토큰은 한 번만 더합니다. T/J의 길이·키 순서 차이가 있고, 단회 지연으로 일반 속도 순위를 정하지 않습니다.</p>')
 parts.append('<details><summary>쉬운30 실제 출력 전체</summary>'+table(['ID','입력','N','T','J'],[[i,next(iter(p.values())).get('input_text','분석 실패'),*[p.get(a,{}).get('output_text','실패/미완료') for a in ['N','T','J']]] for i,p in easy.items()])+'</details><p class="note">형태소 감소 경고는 표준어 분석기의 방언 오분석 가능성이 있어 정확도·보존률로 쓰지 않습니다. EZ01/EZ21은 알려진 아요 정규화 전달 결함 문항입니다.</p></section>')
 parts.append('<section><h2>비용과 재현 기록</h2>')
 rows=[]
 for k,t in [('feedback','피드백'),('development','새16 KG 전후'),('regression','기존50 KG 전후'),('pilot','쉬운30 지식·형식')]:
  m=metrics[k];rows.append([t,m.get('api_attempts','진행 중'),m.get('reported_usage',{}).get('total_tokens','—'),round(m.get('wall_seconds',0),2),runs[k].name])
 parts.append(table(['실험','API 시도','입출력 토큰','경과 초','Run ID'],rows))
 parts.append(f'<p>완료 묶음 합계 <b>{calls:,}호출 · {tokens:,}토큰</b>. 반복 호출은 독립 문장 수가 아닙니다. 각 run에 입력·요청·응답·코드/KG 사본·해시·오류를 보존했습니다.</p>')
 checkpoints=[]
 for p in sorted((R/'local/version_history').glob('*/manifest.json')):
  m=read(p)
  if m.get('status')=='committed':checkpoints.append([m['id'],m['commit'][:12],'로컬 복구용 / 품질 인증 아님','푸시 안 함'])
 parts.append('<details><summary>단계별 복구 버전</summary>'+table(['시점 UTC','커밋','의미','원격'],checkpoints)+'''<p>마지막 확인한 원격 main은26291f5(2026-10-27 17:06 KST 커밋)입니다. 정확한 push 시각이 아닙니다. 최종 복구점은 local/version_history/latest.json에 별도 기록합니다. 이번 백업은 로컬 복구용이며 다른 디스크 백업은 아닙니다. 원본 PDF·인증정보는 커밋하지 않습니다.</p></details></section>
<section><h2>검토자는 무엇을 고쳤나?</h2>''')
 parts.append(table(['검토자','지적','반영'],[
 ['Codex','구현 조건과 문헌 사실 구분 / 기대형 유출 검사 / 공정한 비교','조건 근거 분리, 전체 전달 검사, 개발/평가 구별'],
 ['Claude','불필요한 부정계사 조건 / 경쟁 근거 / 이중 인코딩 / 자동 평가 편향','조건 제거·문맥 근거 연결·전송 검사. 경고는 품질 점수로 안 씀'],
 ['리드','실제 코드·기록 대조와 채택/보류','r10 운영 미채택, 전역 차단 해제 미채택, 피드백 반복 중단']]))
 parts.append('''<p><a href="codex_review.md">Codex 원문</a> · <a href="claude_review.md">Claude 원문</a> · <a href="paper_handoff.md">논문 제안 방법·실험 인계</a></p></section>
<section id="next"><h2>다음 작업과 종료 기준</h2>''')
 parts.append(table(['순서','작업','종료 기준','실패하면'],[
 ['1','새 후보 표현의 현대 방언 적합성 사용자 검토','허용/오류와 표기 선택 기록','용법·실현 선택 보완. 정답 문장 암기 금지'],
 ['2','복수 변경 생성 실패 원인 확인','같은 지식에서 변경 수/입력 복잡도 한 번 통제','같은 프롬프트 반복 대신 생성 한계 기록'],
 ['3','반말 평서→질문→요청·약속→절 연결 정제','근거·반례·새 개발례에서 조회와 생성 확인','미지원 명시, 논문 검증 범위 고정'],
 ['4','논문용 독립 쉬운 평가셋 확보','지원 범위·어휘/템플릿 분리·평가 절차 사전 고정','50/CP16/EZ30을 독립 평가로 이름 바꾸지 않음'],
 ['5','무지식/텍스트 검색/조건 KG 검색 비교','동일 지식 원천·생성기·평가자·비용 기록','우월성 대신 이익과 한계 보고']]))
 parts.append('''<p class="note">사람이 판단해야 할 것은 현대 방언 표현의 허용 여부와 최종 평가 범위·평가자입니다. AI 검토를 사람의 자연스러움 점수로 대신하지 않습니다.</p></section><footer>실측은 실행 원본에서, 해석은 검토 기록에서 왔습니다. 미완료를 완료로 표시하지 않았습니다.</footer></main></body></html>''')
 (O/'report.html').write_text(''.join(parts),encoding='utf8')
 for who in ['codex','claude']:(O/(who+'_review.md')).write_text((O/'reviewers'/who/'review.md').read_text('utf8'),encoding='utf8')
 print(json.dumps({'report':str(O/'report.html'),'calls':calls,'tokens':tokens,'pilot_complete':bool(pm)},ensure_ascii=False))
if __name__=='__main__':main()
