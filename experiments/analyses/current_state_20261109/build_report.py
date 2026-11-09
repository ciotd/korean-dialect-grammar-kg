"""Render a human overview from existing evidence; no model or KG mutation."""
from pathlib import Path
import html,json,re
BASE=Path(__file__).resolve().parent
d=json.loads((BASE/'overview.json').read_text(encoding='utf-8'))
def esc(s):return html.escape(str(s))
def inline(s):
    s=esc(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
def table(headers,rows,cls=''):
    return '<div class="scroll"><table class="'+cls+'"><thead><tr>'+''.join('<th>'+inline(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def markdown(txt):
    lines=txt.splitlines();o=[];i=0
    while i<len(lines):
        s=lines[i]
        if s.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                row=[c.strip() for c in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',c) for c in row):rows.append(row)
                i+=1
            o.append(table(rows[0],rows[1:]));continue
        m=re.match(r'(#{1,3}) (.*)',s)
        if m:o.append(f'<h{min(4,len(m[1])+1)}>{inline(m[2])}</h{min(4,len(m[1])+1)}>')
        elif s.strip():o.append('<p>'+inline(s)+'</p>')
        i+=1
    return ''.join(o)
flow=[('형태 관찰','Kiwi','어간·어미·위치'),('절 범위','Qwen ①','어디부터 어디까지 한 절인지'),('의미·관계','Qwen ②','질문·과거·높임·보조 관계'),('KG 조건 조회','코드 + 파일 KG','조건 대조 → 후보 → 전달'),('문장 전체 작성','Qwen ③','후보 선택 + 방언 생성'),('결과 진단','Qwen ④','오류 의견 기록 / 자동 재작성 0')]
flowhtml='<ol class="flow">'+''.join(f'<li><small>{esc(b)}</small><b>{esc(a)}</b><span>{esc(c)}</span></li>' for a,b,c in flow)+'</ol>'
status=table(['항목','끝낸 부분','남은 부분'],[
('전체 처리 연결','분석→조회→Qwen 생성까지 50건 시도','48건 처리 완료 ≠ 48건 올바른 번역'),
('KG 지식','12개 분류 틀, 56개 조건 조회 규칙·57개 조건 분기','26개 작업묶음 전체 정제·검증은 미완료'),
('출처 분리','출처·검토 전용 자료 별도 저장','규칙 설명에 섞인 쪽수·검토 메모가 일부 요청에 남음'),
('문법 분업','절 담당 / 의미·관계 담당 / 작성 / 검토','의미·관계 자체를 나누는 새 분업은 설계만'),
('품질·연구 효과','실패 위치를 확인할 실행 기록 확보','사람의 독립 평가, 일반 검색 대비 KG 효과 미검증')])
errors=table(['실제 사례','처음 확인된 문제 위치','다음에 확인할 것'],[
('뒀어를 존댓말로 판단해 -노 후보를 놓침 · DEV012','분석값 → KG 조건','검토한 분석값으로는 규칙을 찾는지 대조'),
('맛있더라를 질문으로 읽어 맛있더나 생성 · LONG002','문장 기능 분석','문장별 기능과 절 관계가 섞이는지'),
('연결어미 후보 12건 보류 · 9문장','관계 분석 → 조회','필수 앞뒤 용언 연결이 왜 비었는지'),
('들었어요 → 들어예 · QUAL020','정보 전달 후 생성','과거를 전달받고도 잃는 원인 비교'),
('제가 → 내가 · LONG004','정보 전달 후 생성','모델의 친밀도 추정이 보존 지시를 덮는지'),
('초안 없음 / 초안은 있으나 신고 모순 · LONG001, ADVCE005B','절 검사 / 출력 신고 검사','문법 오류와 기록 형식 실패를 구분')])
packages=[]
for p in d['work_packages']:
    note='기존 12규칙은 이 추가분 수에 포함하지 않음'
    if p['id']=='F02':note='현재 계사 규칙은 존재. 추가분 0 = 미지원 0이 아님'
    packages.append((p['id'],p['title'],str(len(p['new_rule_ids'])),str(len(p['deferred_candidate_ids'])),p['status'].replace('部分','부분'),note))
packagehtml=table(['작업 ID','무슨 내용을 정리하는가','추가44 중 소속 수','보류 후보 소속 수','당시 대장 상태','읽을 때 주의'],packages,'packages')
modulehtml=table(['모듈','분야','직접 연결된 규칙 수'],[(x['id'],x['title'],str(x['direct_rule_count'])) for x in d['modules']])
nexttable=table(['다음 작업 순서','얻을 결과·종료 기준'],[
('① 모든 노드·관계의 역할과 연결 상태 목록화','분류/문헌항목/규칙/조건을 구분. 검사·미확인·문제 항목이 모두 기록됨'),
('② 12모듈·26묶음·56규칙을 한 표로 연결','기존 규칙을 빠뜨리지 않음. 직접 모듈 연결 없는6개는 간접 연결까지 확인'),
('③ 설명 속 관리 메모와 실제 조건 구분','삭제/분리할 메모와 반드시 보존할 문법 조건의 수정 후보표'),
('④ 조건 통과 미관찰30개와 실패 위치 연결','입력에 현상이 없음 / 분석이 놓침 / 조건 부족 / 미확인을 구분'),
('⑤ 조건별 예문 검사의 범위 확정','적용/비적용/미확정 예문 목록. 이후 실제 검사와 생성 비교로 연결')])
style='''*{box-sizing:border-box}body{margin:0;background:#f0f4f6;color:#203247;font:16px/1.8 "Malgun Gothic",sans-serif}main{max-width:1240px;margin:auto;padding:30px 36px;background:#fff}header{background:#123e50;color:white;padding:27px 30px;border-radius:18px}header p{margin:9px 0}header h1{font-size:32px;line-height:1.45;margin:6px 0}h2{font-size:25px;margin:38px 0 15px}h3{font-size:22px;margin-top:30px}h4{font-size:19px}a{color:#096393}header a{color:#bee8fa}nav{display:flex;gap:20px;flex-wrap:wrap;padding:14px 0}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:20px 0}.card{background:#edf5f4;border-radius:12px;padding:18px}.card b{display:block;font-size:23px;color:#195667}.card.warn{background:#fff2de}.note{padding:17px 20px;background:#fff5df;border-left:4px solid #b77a16}.flow{list-style:none;display:grid;grid-template-columns:repeat(6,1fr);gap:10px;padding:0}.flow li{border:1px solid #b4cdd5;border-radius:12px;padding:14px 10px;position:relative;background:#f5fafb}.flow b,.flow span,.flow small{display:block}.flow small{color:#267384}.flow span{font-size:13px;margin-top:7px}.flow li:not(:last-child):after{content:'→';position:absolute;right:-12px;top:50%;z-index:1}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:14px 0}td,th{padding:14px;border:1px solid #d8e2e7;vertical-align:top;min-width:115px}th{background:#e9f1f4;text-align:left}tbody tr:nth-child(even){background:#f9fbfc}details{border:1px solid #d4e0e5;border-radius:10px;padding:17px;margin:18px 0}summary{cursor:pointer;font-weight:bold;font-size:18px}code{overflow-wrap:anywhere;font-size:13px;background:#edf2f5}footer{margin-top:25px;border-top:1px solid #cbdde5;padding:15px}.bar{display:flex;height:32px;border-radius:7px;overflow:hidden;background:#dce4e8}.bar span{display:block;text-align:center;line-height:32px;font-size:13px;color:white}.good{background:#337f8b;width:96%}.bad{background:#ae6238;width:4%;min-width:32px}.caption{font-size:14px;color:#536579}.search{padding:12px;border:1px solid #aabdc7;border-radius:7px;width:min(100%,500px);font-size:16px}button{padding:9px 13px;cursor:pointer;border:1px solid #9fb7c2;background:white;border-radius:6px}@media(max-width:850px){.flow{grid-template-columns:repeat(2,1fr)}.flow li:after{display:none}.cards{grid-template-columns:1fr}main{padding:18px}header{padding:20px}header h1{font-size:26px}}@media print{body{background:white}main{padding:0}.scroll{overflow:visible}nav,.search,button{display:none}tr{break-inside:avoid}details{break-inside:auto}h2,h3{break-after:avoid}}'''
body=f'''<header><small>2026년 11월 9일 · ① 현재 상태 정리 완료</small><h1>연결은 만들었습니다.<br>이제 지식과 실패 지점을 빠짐없이 점검할 차례입니다.</h1><p>기존 기록을 다시 모으고 Orca의 Claude·Codex 검토를 반영했습니다.<br>이번에는 KG·실행 코드를 바꾸거나 Qwen 실험을 새로 하지 않았습니다.</p></header>
<nav><a href="#flow">현재 흐름</a><a href="#status">완료와 미완료</a><a href="#errors">실패 위치</a><a href="#next">다음 검사</a><a href="#details">전체 근거</a></nav>
<div class="cards"><div class="card"><b>48 / 50 처리 완료</b>39건 출력 변경 · 9건 원문 동일<br>번역 정확도나 자연스러움 합격 수가 아닙니다.</div><div class="card"><b>56규칙 · 57조건 분기</b>전체 KG는 1,491노드 · 5,037관계<br>모든 노드가 변환 규칙인 것은 아닙니다.</div><div class="card warn"><b>전체 정제는 미완료</b>12문법 모듈·26작업묶음 중 부분 구현이 존재하지만 전체 완료로 인증하지 않았습니다.</div></div>
<h2 id="flow">1. 지금 문장 한 개가 지나가는 길</h2>{flowhtml}
<p>정상 입력은 같은 Qwen 모델을 역할별로 4번 호출합니다. <strong>최종 문장 전체는 Qwen이 작성합니다.</strong> Kiwi가 최종 방언 문장을 대신 만드는 구조가 아닙니다.</p>
<p class="note"><strong>검색했다고 전부 전달되는 것은 아닙니다.</strong> 미정제 문헌 항목721개는 검색·기록 대상으로 남아 있습니다. 최근 작성자에게 전달된 것은 56규칙 중 조건을 통과하고 선별된 후보입니다. Neo4j는 시각화 사본이며 실제 조회는 KG 파일을 읽는 코드가 수행했습니다.</p>
<p><a href="../kiwi_focused_full50_20261109/private/pipeline.html">기존 Archify 대화형 흐름도 열기</a> · <a href="https://gyeongsang-kg-full50-20261109.piai-2-3424.chatgpt.site/#case-DEV002">최근 50문장 원문·출력·전달 정보 보기</a></p>
<h2 id="status">2. 무엇을 끝냈고, 무엇을 아직 못 끝냈나</h2>{status}
<p>현재 기본은 Kiwi + 11월7일 첫 연결 보완입니다. 최신50은 본·보조용언 질문을 구체화한 <strong>후속 후보</strong>를 선택해 실행했습니다. 최신 후보를 기본 품질 버전으로 채택한 것은 아닙니다.</p>
<details><summary>최근 실행 숫자를 정확히 읽기</summary><div class="bar" aria-label="처리 완료48건 중단2건"><span class="good">처리48</span><span class="bad">2</span></div><p>작성 초안49건 / 검토 응답48건 / 끝까지 처리48건. 형식 처리와 언어 품질은 다릅니다. 196회 호출·623,910토큰·37.35분입니다.</p><p>56규칙 중 조건 통과가 관찰된 규칙26개 → 전달된 고유 규칙26개 → 사용 신고22개. 신고는 실제 올바른 적용이 아닙니다. 나머지30개는 입력에 그 현상이 없었는지, 분석·조건 문제로 놓쳤는지 아직 구분해야 합니다.</p></details>
<h2 id="errors">3. 오류가 시작된 위치와 다음 검사</h2>{errors}
<p>한 원인으로 모두 설명할 수 없습니다. <strong>틀린 분석으로 필요한 규칙을 놓친 사례</strong>와 <strong>필요한 정보를 받고도 생성에서 잃은 사례</strong>를 분리해야 합니다. ‘하지 마’ 유지처럼 현재 규칙이 허용하는 출력은 원문과 같다는 이유만으로 오류로 세지 않습니다.</p>
<h2 id="next">4. 다음은 전체 KG 목록·구조 검사입니다</h2>{nexttable}
<p class="note"><strong>종료 기준:</strong> 모든 검사 대상에 확인 결과·미확인 이유·다음 조치가 연결되면 끝냅니다. 모든 번역이 완벽해질 때까지 같은 수정을 반복하는 작업이 아닙니다. 구조가 확인되면 조건별 예문 검사로, 지식 부족·충돌이 드러나면 근거와 수정안을 정리해 판단 단계로 갑니다.</p>
<h2>5. 두 리뷰어가 실제로 한 일</h2>{table(['담당','실제 검토','이번 반영'],[('Claude','문법 범위, 실제 규칙 전달·사용 신고, 잔여 출처 메모','분리 미완료·30규칙 미관찰·사용 신고의 한계 명시'),('Codex','실행 기본값, 파일 조회, 집계·해시, 구현/제안 경계','Kiwi에서 별도 계획 옵션 거절, 분모·버전 구분'),('리드','두 의견을 코드·원시 기록과 재대조','수치 재현, 과도한 표현 수정, 다음 검사 목록 연결')])}
<p>두 리뷰어가 이번에 원본 문헌7종을 전부 다시 검증한 것은 아닙니다. <a href="REVIEW_RESOLUTION.md">의견별 반영표</a> · <a href="private/claude_state_review.md">Claude 원문</a> · <a href="private/codex_state_review.md">Codex 원문</a></p>
<h2 id="details">6. 필요한 범위만 펼쳐 읽기</h2>
<details id="packages"><summary>26개 작업묶음 전체 상태</summary><p>11월6일 대장의 <strong>추가44규칙 소속 수</strong>입니다. 이전12규칙은 제외되므로 0을 미지원으로 읽으면 안 됩니다. 여러 묶음에 같은 규칙이 들어가므로 행을 더하지 않습니다. 전체 묶음 완료 표지는26개 모두 미완료이며, 부분 작업이 없었다는 뜻은 아닙니다.</p><input id="package-search" class="search" placeholder="찾을 문법 입력: 높임, 조사, 계사…" aria-label="작업묶음 검색"><span id="package-count">26개 표시</span>{packagehtml}</details>
<details><summary>12모듈과 직접 규칙 연결</summary><p>직접 IN_MODULE 관계만 센 값입니다. 간접 연결·실제 적용 범위와 같지 않습니다. 모듈별 수를 더해 고유 규칙 수로 쓰지 않습니다.</p>{modulehtml}<p>직접 연결이 없는6개: {', '.join('<code>'+esc(x)+'</code>' for x in d['rules_without_direct_module_edge'])}. 실행 불가능이라는 결론은 아닙니다.</p></details>
<details><summary>처음부터 현재까지의 변화·분야별 범위·세부 근거</summary>{markdown((BASE/'SNAPSHOT.md').read_text(encoding='utf-8'))}</details>
<details><summary>두 검토자 의견을 어떻게 반영했나</summary>{markdown((BASE/'REVIEW_RESOLUTION.md').read_text(encoding='utf-8'))}</details>
<footer><strong>이번 범위:</strong> 상태 정리와 실제 두 검토 반영까지. 전체 구조 검사·새 Qwen 실험은 아직 시작하지 않았습니다.<br><a href="SNAPSHOT.md">설명 원문</a> · <a href="overview.json">재집계 원본</a> · <a href="collect_snapshot.py">재현 스크립트</a> · <button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">모두 펼치기</button></footer>'''
script="""document.querySelector('#package-search').addEventListener('input',e=>{let n=0;document.querySelectorAll('table.packages tbody tr').forEach(r=>{r.hidden=!r.textContent.includes(e.target.value.trim());if(!r.hidden)n++;});document.querySelector('#package-count').textContent=n+'개 표시';});"""
(BASE/'report.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>연구 현재 상태와 다음 검사 · 2026-11-09</title><style>'+style+'</style></head><body><main>'+body+'</main><script>'+script+'</script></body></html>',encoding='utf-8')
print('report.html built from snapshot, inventory and review resolution')
