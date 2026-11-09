"""Readable audit overview with searchable complete inventories; offline only."""
from pathlib import Path
import json,html,re
BASE=Path(__file__).resolve().parent
d=json.loads((BASE/'private/audit.json').read_text(encoding='utf8'))
esc=lambda s:html.escape(str(s))
def inline(s):
 s=esc(s);s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s);s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
 return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def markdown(s):
 lines=s.splitlines();i=0;o=[]
 while i<len(lines):
  s=lines[i]
  if s.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].startswith('|'):
    cells=[c.strip() for c in lines[i].strip('|').split('|')]
    if not all(re.fullmatch(r'[:\- ]+',c) for c in cells):rows.append(cells)
    i+=1
   o.append(table(rows[0],rows[1:]));continue
  m=re.match(r'(#{1,3}) (.*)',s)
  if m:
   n=min(4,len(m[1])+1);o.append(f'<h{n}>{inline(m[2])}</h{n}>')
  elif s.strip():o.append('<p>'+inline(s)+'</p>')
  i+=1
 return ''.join(o)
style=re.search(r'<style>(.*?)</style>',(BASE.parent/'current_state_20261109/report.html').read_text(encoding='utf8'),re.S)[1]
style+='''.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:15px 0}select,input{padding:10px;border:1px solid #aabdc7;border-radius:6px;font:inherit}.rulebox{margin:12px 0;padding:15px;border:1px solid #c5d7de;border-radius:10px}.rulebox h4{margin-top:8px}.rulebox ul{padding-left:22px}td{overflow-wrap:anywhere}#inventory td:first-child{max-width:260px}.chain{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.chain span{background:#edf5f4;padding:15px;border-radius:9px}.tag{background:#eef2f8;padding:4px 8px;border-radius:5px;font-size:13px}.note code{background:transparent}'''
type_names={'Framework':'공통 척추','Module':'문법 분류','SourceAtom':'미정제 문헌 항목','SemanticRule':'조건 조회 규칙','ApplicabilityBranch':'조건 묶음(분기)','Condition':'조건','FeatureValue':'허용값','Realization':'실현 표현','GrammarConstruction':'문법 구성','AnalysisConcept':'분석 개념','Construction':'기존 구성 설계','GrammarFeature':'문법 특징','AggregateInterface':'통합 인터페이스 설계','TechnicalResponsibility':'처리 역할 설계','Claim':'문헌 주장','UsageObservation':'용법 관찰','ProcessingScope':'공통 적용 범위','ImplementationDecision':'구현 결정','ResearchCandidate':'연구 후보'}
features={'clause_role':'절의 역할','speech_act':'문장 기능','addressee_level':'상대 높임','subject_honorific':'주체 높임','predicate_class':'서술어 종류','question_kind':'질문 종류','unit_kind':'검사 단위','source_form':'형태 분석에서 잡은 표현','source_final':'어미 형태','prefinal_type':'선어말 어미 종류','prefinal_sequence':'선어말 어미 순서','past_form':'과거 형태 유무','nominal_kind':'명사 종류','nominal_end':'명사 끝소리','semantic_function':'단위의 문법 기능','auxiliary_kind':'보조 구성 의미','lemma':'기본 어간·어휘','ending_tag':'어미 품사','polarity':'긍정·부정','tense':'시간 의미','voice':'능동·피동·사동','morph_tag':'형태 품사'}
values={'main':'주절','embedded':'안긴절','quoted':'인용절','statement':'평서','information_question':'정보 질문','request':'부탁','prohibition':'금지','command':'명령','plain':'반말','polite':'공손체','formal':'격식 높임','present':'있음/현재(항목별 구별)','absent':'없음','verb':'동사','adjective':'형용사','copula':'이다','negative_copula':'아니다','polar':'예/아니오 질문','wh':'의문사 질문','predicate':'서술어','nominal':'명사류','particle':'조사','connector':'연결·전성 어미','construction':'복합 구성','positive':'긍정','negative':'부정','none':'없음','eoss':'았/었/였','si':'시','si_eoss':'시+었','EF':'종결 어미','EC':'연결 어미','lexical_nominal':'일반 명사류','past':'과거','future':'미래','benefactive':'수혜·해 줌','attempt':'시도·경험','progressive':'진행','resultative':'결과 상태'}
def translated(key,vs):
 def v(x):
  if key=='past_form' and x=='present':return '과거 형태 있음'
  if key=='tense' and x=='present':return '현재'
  return values.get(x,x)
 return features.get(key,key)+' = '+ ' 또는 '.join(v(x) for x in vs)
rulehtml=[]
for r in d['rules']:
 branches=[b for b in d['branches'] if b['rule_id']==r['rule_id']]
 bs=''.join('<div><b>조건 묶음 '+str(i+1)+' — 아래 조건 모두 필요</b><ul>'+''.join('<li>'+esc(translated(k,v))+'</li>' for k,v in b['effective_conditions'].items())+'</ul></div>' for i,b in enumerate(branches))
 forms=' / '.join(str(f.get('form','')) for f in r['forms'])
 counts=r['record_counts'];mods=', '.join(r['direct_modules']) or '구성 경유: '+', '.join(r['family_modules'])
 rulehtml.append('<details class="rulebox" data-rule="'+esc(r['title']+' '+r['rule_id']+' '+mods)+'"><summary>'+esc(r['title'])+'</summary><p><code>'+esc(r['rule_id'])+'</code> · '+esc(mods)+'</p><p><strong>전달 지시:</strong> '+esc(r['instruction'])+'</p><p><strong>표현 후보:</strong> '+esc(forms)+'</p>'+bs+'<p><strong>필요한 단위 사이 관계:</strong> '+esc(', '.join(r['required_relations']) or '별도 필수 관계 없음')+'</p><p><strong>최근50의 문장 수:</strong> 조건통과 '+str(counts['eligible'])+' / 전달 '+str(counts['delivered'])+' / 사용 신고 '+str(counts['reported_used'])+'. 자연스러움 합격 수가 아닙니다.</p><p><strong>검사 상태:</strong> 연결·조건값 대조 완료. 문헌 의미 전수 확인·새 자연어 예문 검사는 미완료.</p></details>')
result=markdown((BASE/'RESULTS.md').read_text(encoding='utf8'))
review=markdown((BASE/'REVIEW_RESOLUTION.md').read_text(encoding='utf8')).replace('href="private/','href="')
package_table=table(['묶음','내용','추가44 중 규칙 수','전체 완료 표시'],[(p['id'],p['title'],str(len(p['new_rule_ids'])),'미완료') for p in d['work_packages']])
names={n['id']:n['title'] or n['id'] for n in d['nodes']}
inv_nodes=[{'ID':n['id'],'내용':n['title'] or '(제목 없음: ID로 구별)','종류':type_names.get(n['type'],n['type']),'연결 수':str(n['incoming']+n['outgoing']),'검사':'참조·고립·중복 검사 / 의미 미확인','속성 항목':', '.join(n['property_keys'])} for n in d['nodes']]
inv_edges=[{'ID':e['id'],'출발':names.get(e['source'],e['source'])+' ['+e['source']+']','관계':e['relation'],'도착':names.get(e['target'],e['target'])+' ['+e['target']+']','검사':'양끝 존재·중복 검사 / 관계 의미 미확인'} for e in d['edges']]
payload=json.dumps({'nodes':inv_nodes,'edges':inv_edges},ensure_ascii=False).replace('<','\\u003c')
body=f'''<header><small>2026년 11월 9일 · ② 목록·구조 검사</small><h1>연결은 끊어지지 않았습니다.<br>하지만 조건의 뜻과 전달 방식에는 보완할 부분이 있습니다.</h1><p>전체 항목을 코드로 검사하고, 기존 Orca Claude·Codex의 검토를 실제 기록과 대조했습니다.<br>이번 결과는 문법 전체가 맞다는 인증이 아닙니다. 새 예문·Qwen 실험과 KG 수정은 하지 않았습니다.</p></header>
<nav><a href="#result">검사 결과·수정안</a><a href="#rules">56개 규칙</a><a href="#inventory">전체 항목 검색</a><a href="#review">두 리뷰어 검토</a></nav>
<div class="cards"><div class="card"><b>1,491개 노드</b>5,037개 관계 전체의 참조·중복·고립 검사</div><div class="card"><b>56규칙 · 57분기</b>실제 조회기가 읽는 조건을 전부 대조</div><div class="card warn"><b>새 예문 실행 0회</b>기존 예문57개를 다음 검사 대상에 연결. 아직 통과로 세지 않음</div></div>
<div class="chain"><span>전체 항목·연결 검사<br><strong>이번 작업</strong></span>→<span>규칙별 적용·비적용 예문 검사<br><strong>다음 작업</strong></span>→<span>생성 방식 비교<br>전체 연결 재검증</span></div>
<section id="result">{result}</section>
<details><summary>26개 작업묶음의 기존 대응 상태</summary><p>추가44규칙의 소속 대응은 모두 존재합니다. 기존12규칙은 이 대장에 포함되지 않으며, 0을 현재 지원 없음으로 읽으면 안 됩니다. 같은 규칙의 여러 묶음 소속을 더하지 않습니다.</p>{package_table}</details>
<h2 id="rules">규칙을 직접 확인하기</h2><p>각 규칙을 펼치면 실제 KG에서 조회기가 읽는 조건과 표현을 볼 수 있습니다. 한 조건 묶음 안에서는 모두 맞아야 하고, 묶음이 여러 개면 그중 하나가 맞으면 후보가 됩니다. 문장 속 관계가 필수인 규칙은 그 연결도 필요합니다.</p><input id="rule-search" class="search" placeholder="예: 의문, 과거, 요청, SEM_Q"><span id="rule-count">56개 표시</span>{''.join(rulehtml)}
<h2 id="inventory">전체 항목 검색 — 검사에서 빠진 항목이 있는지 보기</h2><p>모든 노드·관계가 아래 목록에 있습니다. 제목·종류·ID로 검색할 수 있습니다. ‘구조 검사’는 내용의 언어학적 정확성을 보증하지 않습니다.</p><div class="controls"><select id="inventory-kind"><option value="nodes">노드1,491개</option><option value="edges">관계5,037개</option></select><input id="inventory-search" placeholder="종류·제목·ID 검색"><button id="prev">이전</button><button id="next">다음</button><span id="page-label"></span></div><div id="inventory-table" class="scroll"></div>
<h2>원본 목록과 다음 예문 검사 준비</h2><p><a href="nodes.csv">전체 노드 CSV</a> · <a href="edges.csv">전체 관계 CSV</a> · <a href="rules.csv">56규칙 명세 CSV</a> · <a href="branches.csv">57분기 명세 CSV</a></p><p>CSV와 JSON은 재현 자료입니다. 위 화면의 설명과 표만으로 먼저 검수할 수 있습니다. <a href="example_test_plan.json">분기별 다음 검사 목록</a>에는 기존57예문 후보를 연결했으며, 각 예문이 해당 분기를 실제로 만족하는지는 아직 확인하지 않았습니다.</p>
<details id="review"><summary>두 검토자 의견과 리드의 반영·보류 판단</summary>{review}</details>
<footer><a href="../README.md">파일 안내</a> · <a href="../summary.json">자동 검사 집계</a> · <a href="claude_structure_review.md">Claude 검토 원문</a> · <a href="codex_structure_review.md">Codex 검토 원문</a><p>출처·문헌 원문은 기존 별도 기록에서 보존합니다. 이 보고서는 외부 사이트에 새로 게시하지 않았습니다.</p></footer>'''
js='''const dataset=JSON.parse(document.querySelector('#data').textContent);let page=0;const pageSize=25;function render(){const kind=document.querySelector('#inventory-kind').value,q=document.querySelector('#inventory-search').value.trim();const rows=dataset[kind].filter(r=>Object.values(r).join(' ').includes(q));page=Math.max(0,Math.min(page,Math.ceil(rows.length/pageSize)-1));const cols=Object.keys(dataset[kind][0]);const table=document.createElement('table'),head=table.createTHead().insertRow();cols.forEach(k=>{const th=document.createElement('th');th.textContent=k;head.append(th)});const body=table.createTBody();rows.slice(page*pageSize,(page+1)*pageSize).forEach(r=>{const tr=body.insertRow();cols.forEach(k=>tr.insertCell().textContent=r[k])});document.querySelector('#inventory-table').replaceChildren(table);document.querySelector('#page-label').textContent=rows.length+'개 · '+(page+1)+' / '+Math.max(1,Math.ceil(rows.length/pageSize))+'쪽';}['inventory-kind','inventory-search'].forEach(id=>document.querySelector('#'+id).addEventListener(id.endsWith('kind')?'change':'input',()=>{page=0;render()}));document.querySelector('#prev').onclick=()=>{page--;render()};document.querySelector('#next').onclick=()=>{page++;render()};document.querySelector('#rule-search').oninput=e=>{let n=0;document.querySelectorAll('[data-rule]').forEach(r=>{r.hidden=!r.textContent.includes(e.target.value.trim());if(!r.hidden)n++});document.querySelector('#rule-count').textContent=n+'개 표시'};render();'''
(BASE/'private/report.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>전체 KG 구조 검사와 수정안</title><style>'+style+'</style></head><body><main>'+body+'</main><script id="data" type="application/json">'+payload+'</script><script>'+js+'</script></body></html>',encoding='utf8')
print('private/report.html generated with 1491/5037 inventories and 56 rule details')
