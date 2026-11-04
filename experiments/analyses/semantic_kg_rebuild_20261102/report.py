"""Small local report generated from actual graph/query/reviewer artifacts."""
import html,json
from inventory import HERE,read,dump
def esc(x):return html.escape(str(x))
def rows(data):return ''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in data)
def table(head,data):return '<table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in head)+'</tr></thead><tbody>'+rows(data)+'</tbody></table>'
def run():
    p=HERE/'private';graph=read(p/'graph.json');spec=read(p/'foundation.json');data=read(p/'easy_development.json');access=read(p/'source_access.json');inv=read(p/'inventory.json')
    tests=read(p/'validation.json');decisions=read(p/'review_resolution.json');by={n['id']:n for n in graph['nodes']}
    raw_reviews=''
    for phase in ('independent','cross'):
        for who in ('claude','codex'):
            path=p/'dispatch'/phase/who/'response.md'
            raw_reviews+=f'<details><summary>{who} · '+('독립 검토' if phase=='independent' else '교차 검토')+'</summary><pre>'+esc(path.read_text(encoding='utf8'))+'</pre></details>'
    summary=table(['작업','이번 확인 결과'],[
      ['원본 문헌 접근',f'{sum(s["pdf_reopened"] for s in access)}종 PDF 해시 일치 · 과거 추출474쪽 일치 · 이번8쪽 화면 대조'],
      ['기존 KG 전체 집계','721개 항목 작업대장 작성. 전부 의미 검증한 것은 아님'],
      ['정제한 첫 구성','의문문 구성1개 / 조건별 용법6개 / 기존 항목5개와 부분 대응'],
      ['실제 새 그래프',f'{len(graph["nodes"])}개 노드 / {len(graph["edges"])}개 관계. 기존12모듈 ID 유지'],
      ['조회 확인',f'개발문장24개 예상 후보 확인 · {tests["tests_run"]}개 자동 테스트 통과'],
      ['아직 하지 않은 것','전체721개 의미 정제 완료, 자동 문장 분석, Qwen 생성, Neo4j 적재, 사람 평가']])
    rules=table(['용법','핵심 조건','찾는 형태'],[(r['title'],' / '.join(f'{k}={"·".join(v)}' for k,v in r['any_branches'][0].items() if k in ('predicate_class','prefinal_type','question_kind')),' · '.join(f['form'] for f in r['forms'])) for r in spec['rules']])
    issues=table(['문제','수정한 내용','아직 남은 부분'],[(r['problem'],r['action'],r['remaining']) for r in decisions])
    source=table(['문헌','PDF 동일','전체 의미 정제'],[(s['id']+' '+s['filename'],'확인' if s.get('pdf_hash_matches') else '미확인','미완료') for s in access])
    payload=json.dumps({'cases':data,'nodes':graph['nodes'],'edges':graph['edges'],'evidence':spec['evidence']},ensure_ascii=False).replace('<','\\u003c')
    document='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>문헌의 뜻을 사용하는 KG — 첫 검증 결과</title>
<style>body{margin:0;background:#f5f7fa;color:#172538;font:17px/1.75 system-ui,'Malgun Gothic',sans-serif}main{max-width:1120px;margin:auto;padding:36px 24px}h1{font-size:32px;line-height:1.4}h2{font-size:23px;margin-top:38px}p{max-width:940px}section,.box{background:white;border:1px solid #dce3ea;border-radius:12px;padding:22px;margin:20px 0}.badge{color:#135a48;background:#dff3ea;padding:5px 12px;border-radius:15px;font-size:14px}.warn{border-left:5px solid #d9902f;padding-left:18px}table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:12px;border-bottom:1px solid #e2e7ed;vertical-align:top}th{background:#edf2f7}td{overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px;line-height:1.65;background:#f1f4f7;padding:15px;max-height:600px;overflow:auto}summary{cursor:pointer;color:#245f99;padding:10px}select{font:inherit;padding:8px;width:100%;max-width:900px}.flow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.step{padding:13px;background:#eaf1f8;border-radius:8px;max-width:220px}.small{font-size:14px;color:#526173}a{color:#1b5c9d}code{font-size:14px}.scroll{overflow:auto}</style><main>
<span class="badge">2026-11-02 · 전체 재구축의 첫 검증 구간</span><h1>큰 분류를 통째로 가져오지 않고,<br>문장의 조건으로 필요한 용법을 찾습니다.</h1>
<p><b>지금 확인한 것은 ‘조회가 조건대로 움직이는가’입니다.</b> 방언 문장이 자연스러워졌다는 실험 결과는 아직 없습니다. 이번 결과를 전체 KG 완성으로 보지 마세요.</p>
<section><h2>1. 무엇을 했나</h2>SUMMARY</section>
<section><h2>2. 한 문장으로 직접 확인하기</h2><p>아래 분석값은 Qwen 결과가 아니라 총괄이 작성한 개발용 값입니다. 문장을 바꾸면 실제 저장된 조회 결과가 바뀝니다.</p><select id="case"></select><div id="example"></div><div id="network" class="scroll"></div><details><summary>실제 노드·관계와 조건 확인</summary><div id="trace" class="scroll"></div></details><details><summary>문헌에서 확인한 뜻과 원문 위치</summary><div id="evidence"></div></details><details><summary>Qwen에 전달할 데이터 — 아직 호출하지 않음</summary><pre id="packet"></pre></details></section>
<section><h2>3. 정제한 문법 지식</h2><p>하나의 의문문 구성 안에서 서술어 종류·물어보는 뜻·선어말 형태를 함께 확인합니다. <b>여기서6개는 전체 체계의 제한이 아닙니다.</b> 같은 형식으로 다른 용법을 추가하기 위한 첫 묶음입니다.</p>RULES<p class="small">prefinal_type=eoss는 -었- 계열 형태가 있다는 뜻입니다. ‘과거 의미’와 별개입니다. 계사 명사 말음의 이가/가, 이고/고는 실현형에 기록했습니다. 이랐- 계열 등 아직 정리하지 못한 변이는 남아 있습니다.</p></section>
<section><h2>4. 두 검토자 덕분에 고친 부분</h2><p>Claude는 문헌의 뜻·결합 형태를, Codex는 조건 연결·조회·전달의 오류를 점검했습니다. 서로의 의견과 구현도 교차 검토했습니다. 아래 수정 후 재시험은 총괄이 수행했고, 수정본 전체를 다시 독립 검토받았다고 주장하지 않습니다.</p>ISSUES<details><summary>두 검토자의 원문 의견4건</summary>REVIEWS</details></section>
<section><h2>5. 전체 지식을 어떻게 이어서 정리하나</h2><div class="flow"><div class="step">설계 규칙81개<br>뜻과 조건부터 확인</div>→<div class="step">형태 목록433개<br>어떤 용법인지 연결</div>→<div class="step">관찰183개·분류24개<br>근거·변이로 보존</div>→<div class="step">모듈 간 조합 확인<br>분석기·Qwen 연결</div></div><p>각 항목에는 ‘무엇을 읽었나 → 어떤 뜻으로 정리했나 → 왜 이 조건인가 → 어떤 그래프로 연결했나 → 무엇을 시험했나’를 남깁니다. 조건별 출처가 없는 부분은 사람이 판단할 항목으로 모읍니다. <b>형태 목록이나 관찰자료를 모두 실행 규칙으로 바꾸지는 않습니다.</b></p><p>쉬운24개는 개발용, 기존50개는 회귀 확인용입니다. 논문 최종 평가는 개발에 쓰지 않은 별도 문장으로 해야 합니다.</p></section>
<section><h2>6. KG가 좋다는 주장은 어떻게 증명하나</h2><p>Qwen 단독과 비교하면 ‘외부 지식의 도움’을 볼 수 있습니다. <b>그래프 구조의 이점</b>을 보려면 동일한 지식을 평면 규칙표로 찾는 방법과도 비교해야 합니다.</p><p>현재24개에서는 같은 조건의 평면 규칙 검색과 그래프 검색이 같은 후보를 찾았습니다. 이것은 정상적인 의미 일치 확인입니다. 그래프의 품질·속도 우월성은 증명하지 않았습니다. 근거 추적, 조건 재사용, 지식 수정·확장의 일관성도 이후 측정 대상입니다.</p></section>
<details><summary>원본 접근·정제 범위</summary>SOURCES</details><p class="small">구현·재현 명령: <a href="../README.md">README</a> · 검증 결과: <a href="validation.json">validation.json</a> · 전체721개 작업대장: <a href="refinement_ledger.json">작업대장</a><br>기존 KG·카드·실행 코드는 변경하지 않았습니다. 새 구조는 별도 버전이며 기존 Neo4j를 교체하지 않았습니다.</p>
<script id="payload" type="application/json">PAYLOAD</script><script>
const D=JSON.parse(document.getElementById('payload').textContent),by=Object.fromEntries(D.nodes.map(n=>[n.id,n]));
const esc=x=>String(x??'미확정').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={predicate_class:'서술어 종류',question_kind:'질문 뜻',prefinal_type:'선어말 형태',addressee_level:'청자 대우',subject_honorific:'주체 높임',speech_act:'발화 기능',clause_role:'절 역할'};
const values={copula:'계사(이다)',verb:'동사',adjective:'형용사',negative_copula:'아니다',polar:'예/아니오 답',wh:'내용을 묻는 질문',eoss:'-었- 계열 있음',none:'없음',gess:'-겠- 있음',plain:'반말',polite:'공손',absent:'없음',present:'있음',information_question:'정보 질문',main:'주절',request:'요청',statement:'서술'};
const tbl=(hs,rs)=>'<table><tr>'+hs.map(h=>'<th>'+esc(h)+'</th>').join('')+'</tr>'+rs.map(r=>'<tr>'+r.map(x=>'<td>'+esc(x)+'</td>').join('')+'</tr>').join('')+'</table>';
const sel=document.getElementById('case');D.cases.forEach(c=>{let o=document.createElement('option');o.value=c.id;o.textContent=c.id+' · '+c.analysis.text;sel.append(o)});sel.value='EASYQ013';
function draw(){const c=D.cases.find(x=>x.id===sel.value),r=c.retrieval.clauses[0],f=c.analysis.clauses[0].features;let result=r.eligible.map(x=>by[x.rule_id].properties.title+' → '+x.realization_edges.map(e=>by[e.target].properties.form).join('/')).join('; ');if(!result)result=r.out_of_slice.length?'아직 지원하지 않는 범위입니다. 틀린 문법이라는 뜻이 아닙니다.':r.unresolved.length?'분석값이 부족합니다. 판정/설명 의문을 임의로 고르지 않습니다.':'이 묶음에서 맞는 용법을 찾지 못했습니다.';
document.getElementById('example').innerHTML='<div class="box"><b>'+esc(c.analysis.text)+'</b><p>바꿀 대상: '+esc(r.target_text)+'</p>'+tbl(['확인할 것','이번 분석값'],Object.entries(f).filter(([k])=>labels[k]).map(([k,v])=>[labels[k],values[v]??v]))+'<p><b>조회 결과:</b> '+esc(result)+'</p><p class="small">완성된 방언 문장 생성은 아직 하지 않았습니다. 형태소 경계와 활용 조합은 후속 단계입니다.</p></div>';
const chosen=r.eligible[0];let net='<p class="small">현재 충족 후보가 없어 그래프 그림을 표시하지 않습니다. 미확정 또는 지원 범위를 확인하세요.</p>';
if(chosen){const branch=chosen.branches[0],cs=branch.conditions.filter(x=>['question_kind','predicate_class','prefinal_type'].includes(x.feature));let svg='<svg viewBox="0 0 1100 330" style="min-width:850px;width:100%" role="img" aria-label="실제 저장된 조건 관계"><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3z" fill="#56748e"/></marker></defs>';
const box=(x,y,w,s)=>'<rect x="'+x+'" y="'+y+'" width="'+w+'" height="55" rx="8" fill="#eaf1f8" stroke="#9bb1c3"/><text x="'+(x+w/2)+'" y="'+(y+33)+'" text-anchor="middle" font-size="15">'+esc(s)+'</text>';
const edge=(x,y,xx,yy,s)=>'<line x1="'+x+'" y1="'+y+'" x2="'+xx+'" y2="'+yy+'" stroke="#56748e" marker-end="url(#arr)"/><text x="'+((x+xx)/2)+'" y="'+((y+yy)/2-9)+'" text-anchor="middle" font-size="11">'+esc(s)+'</text>';
cs.forEach((z,i)=>{const y=25+i*95;svg+=edge(250,y+28,190,y+28,'ACCEPTS')+edge(490,150,420,y+28,'ALL')+box(20,y,170,values[z.observed]??z.observed)+box(250,y,170,labels[z.feature]+' 조건')});svg+=edge(690,150,620,150,'ANY_BRANCH')+edge(850,150,940,150,'REALIZES')+box(490,122,130,'조건 묶음')+box(690,122,160,'해당 의문 용법')+box(940,122,130,chosen.realization_edges.map(e=>by[e.target].properties.form).join('/'))+'</svg>';net='<p><b>실제 그래프 연결:</b> 핵심3조건만 표시했습니다. 화살표는 저장된 관계 방향이며, 조회할 때 역방향으로도 이동합니다.</p>'+svg}
document.getElementById('network').innerHTML=net;
const candidates=[...r.eligible,...r.unresolved];let traces=[];for(const x of candidates){for(const b of x.branches){for(const z of b.conditions){if(z.entry_edge_id){const e=D.edges.find(e=>e.id===z.entry_edge_id);traces.push([e.source,e.relation,e.target])}}for(const id of b.edge_ids){const e=D.edges.find(e=>e.id===id);traces.push([e.source,e.relation,e.target])}}for(const e of x.realization_edges)traces.push([e.source,e.relation,e.target])}
document.getElementById('trace').innerHTML=tbl(['출발 노드','실제 관계','도착 노드'],traces);
const ids=[...new Set(candidates.flatMap(x=>x.evidence_edges.map(e=>e.target)))];document.getElementById('evidence').innerHTML=ids.map(id=>{const e=D.evidence[id];return '<p><b>'+esc(e.document_id+' PDF '+e.pdf_page+'쪽')+'</b> — '+esc(e.builder_paraphrase)+'</p><blockquote>'+esc(e.quote)+'</blockquote>'}).join('')||'<p>지원 범위 밖 항목의 근거는 전체 정제 작업에서 추가합니다.</p>';
document.getElementById('packet').textContent=JSON.stringify(c.packet,null,2);}
sel.addEventListener('change',draw);draw();</script></main></html>'''
    for key,value in [('SUMMARY',summary),('RULES',rules),('ISSUES',issues),('REVIEWS',raw_reviews),('SOURCES',source),('PAYLOAD',payload)]:document=document.replace(key,value)
    (p/'report.html').write_text(document,encoding='utf8');print(str(p/'report.html'))
if __name__=='__main__':run()
