"""Render a readable standalone planning report. No model calls or KG writes."""
import html,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
E=html.escape
def inline(s):
    s=E(s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',r'<a href="\2">\1</a>',s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    return s
def markdown(text,prefix):
    rows=text.splitlines();out=[];i=0;toc=[];n=0
    while i<len(rows):
        line=rows[i].strip()
        if not line:i+=1;continue
        if line.startswith('|'):
            table=[]
            while i<len(rows) and rows[i].strip().startswith('|'):
                cells=[x.strip() for x in rows[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\-\s]+',c) for c in cells):table.append(cells)
                i+=1
            out.append('<div class="table"><table>')
            for j,cs in enumerate(table):
                tag='th' if j==0 else 'td'
                out.append('<tr>'+''.join('<'+tag+'>'+inline(c)+'</'+tag+'>' for c in cs)+'</tr>')
            out.append('</table></div>');continue
        if line.startswith('#'):
            level=len(line)-len(line.lstrip('#'));title=line[level:].strip();n+=1;ident=prefix+str(n)
            if level==2:toc.append((ident,title))
            tag='h'+str(min(level+1,4))
            out.append(f'<{tag} id="{ident}">'+inline(title)+f'</{tag}>');i+=1;continue
        if line.startswith('- ') or re.match(r'^\d+\. ',line):
            ordered=not line.startswith('- ');tag='ol' if ordered else 'ul';out.append('<'+tag+'>')
            while i<len(rows):
                l=rows[i].strip()
                match=re.match(r'^\d+\. (.*)',l) if ordered else re.match(r'^- (.*)',l)
                if not match:break
                out.append('<li>'+inline(match[1])+'</li>');i+=1
            out.append('</'+tag+'>');continue
        out.append('<p>'+inline(line)+'</p>');i+=1
    return '\n'.join(out),toc
plan,toc=markdown((HERE/'PLAN.md').read_text(encoding='utf8'),'plan-')
decision_path=HERE/'DECISIONS.md'
decisions=markdown(decision_path.read_text(encoding='utf8'),'decision-')[0] if decision_path.exists() else '<p>독립 의견을 대조하고 있습니다.</p>'
reviews=[]
for who,label in [('claude','Claude'),('codex','GPT 검토자')]:
    for phase,title in [('independent','독립 의견'),('cross_review','상호 검토')]:
        p=HERE/'private'/who/(phase+'.md')
        if p.exists():
            body,_=markdown(p.read_text(encoding='utf8'),who+'-'+phase+'-')
            reviews.append('<details><summary>'+label+' · '+title+'</summary><p class="note">검토자의 원래 의견입니다. 리드가 모두 채택한 것은 아닙니다. 반영 여부는 위 결정 기록에서 확인하세요.</p>'+body+'</details>')
css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f6f8;color:#172c3a;font:17px/1.75 "Malgun Gothic",sans-serif}main{max-width:1150px;margin:auto;padding:28px 24px 80px}header{padding:28px 0}h1{font-size:34px;line-height:1.4;margin:12px 0}h2{font-size:26px;margin:36px 0 12px}h3{font-size:22px;margin:32px 0 12px}h4{font-size:18px;margin-top:24px}p{margin:12px 0}a{color:#096892}strong{color:#112e41}nav{display:flex;gap:15px;flex-wrap:wrap;padding:12px 0}.note{background:#fff2d5;padding:14px 18px;border-left:4px solid #b88310}.lead{font-size:20px}.section{background:white;padding:22px;margin:18px 0;border-radius:10px}.table{overflow:auto;margin:16px 0}table{width:100%;border-collapse:collapse;min-width:570px;font-size:15px}th,td{text-align:left;vertical-align:top;padding:13px;border-bottom:1px solid #dbe4ea}th{background:#eaf1f5}td:first-child{min-width:130px}code{overflow-wrap:anywhere;font-size:15px}details{background:#fff;margin:16px 0;padding:18px}summary{cursor:pointer;font-weight:700}li{margin:8px 0}.flow{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.node{padding:18px;background:#eaf1f5;border-radius:8px;flex:1;min-width:170px}.parallel{display:grid;grid-template-columns:1fr 1fr;gap:12px;flex:2;min-width:280px}.arrow{font-size:24px;color:#527084}.small{font-size:14px;color:#496170}.tag{font-size:14px;color:#496170;letter-spacing:.08em}.buttons{display:flex;gap:10px;flex-wrap:wrap}button{font:inherit;cursor:pointer;border:1px solid #527084;border-radius:6px;background:white;color:#17384d;padding:8px 16px}button[aria-pressed=true]{background:#17384d;color:white}[hidden]{display:none!important}.toc{columns:2}.toc a{display:block;margin:6px 0}@media(max-width:650px){main{padding:16px 12px}h1{font-size:27px}.section{padding:14px}.parallel{grid-template-columns:1fr;min-width:0}.flow{flex-direction:column;align-items:stretch}.arrow{text-align:center}.toc{columns:1}table{min-width:520px}}'''
overview='''<section class="section"><h2>두 팀을 혼동하지 않는 것이 출발점입니다.</h2><div class="flow"><div class="node"><strong>연구팀</strong><p>GPT 리드 · Claude · GPT 검토자</p><p>지식과 실험을 점검하고<br>수정 근거를 기록합니다.</p></div><div class="arrow">↓ 설계·검토</div><div class="node"><strong>번역 실험팀</strong><p>같은 Qwen을 역할별로 호출</p><p>표준어 분석 → KG 조회 → 방언 생성<br>Claude의 정답은 전달하지 않습니다.</p></div></div></section>
<section class="section"><h2>비교할 번역 구조</h2><p>아래에서 현재 구조와 제안 구조를 바꿔 볼 수 있습니다. 제안 구조는 아직 실행하지 않았습니다.</p><div class="buttons"><button id="current-button" aria-pressed="true">현재 기본 구조</button><button id="proposed-button" aria-pressed="false">역할 분담 후보</button></div>
<div id="current"><p class="small">Qwen 기본 2호출: 분석 1 + 생성 1</p><div class="flow"><div class="node">Kiwi 관찰 + 원문</div><span class="arrow">→</span><div class="node">Qwen<br><strong>분석 전체</strong></div><span class="arrow">→</span><div class="node">KG 조건 조회</div><span class="arrow">→</span><div class="node">Qwen<br><strong>문장 전체 생성</strong></div></div></div>
<div id="proposed" hidden><p class="small">첫 후보는 분석만 분리해 3호출. 생성까지 분리하는 후보는 5호출이며, 두 변경을 한꺼번에 시험하지 않습니다.</p><div class="flow"><div class="node">같은 원문 전체<br>+ 위치 정보</div><span class="arrow">→</span><div class="node">Qwen ①<br><strong>문장 구조</strong><p>절·단어 구간<br>본동사–보조동사 관계</p></div><span class="arrow">→</span><div class="node">Qwen ②<br><strong>문법 의미</strong><p>부탁·질문·시제<br>부정·높임<br>앞 단계 구조도 확인</p></div><span class="arrow">→</span><div class="node">위치를 맞추고<br>충돌을 기록<br><strong>KG 조건 조회</strong></div></div><p>생성 분업은 별도 비교합니다.</p><div class="flow"><div class="node">Qwen<br><strong>문장 전체 초안</strong></div><span class="arrow">→</span><div class="node">Qwen<br><strong>뜻·시제·높임 점검</strong></div><span class="arrow">→</span><div class="node">Qwen<br><strong>최종 문장 작성</strong></div></div><p class="note">단어마다 한 명씩 배치하지 않습니다. 같은 Qwen을 더 많이 호출하는 것이므로, 같은 3호출로 일반 재검토를 하는 대조군과 비용도 비교합니다.</p></div></section>'''
page='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KG와 멀티에이전트 연구 재설계</title><link rel="stylesheet" href="report.css"></head><body><main><header><div class="tag">2026-11-06 · 실행 전 연구 계획</div><h1>KG가 맞는지 먼저 확인하고,<br>역할을 나누는 효과를 따로 시험합니다.</h1><p class="lead">전체 그래프 검사, Qwen 분석·생성 분업, 공정한 비교 실험을 하나의 계획으로 정리했습니다.</p><p class="note"><strong>이번 작업은 설계와 검토입니다.</strong> 새 Qwen 실험 0회, KG 변경 없음. 아래 그림의 제안 구조는 아직 구현·성능 검증하지 않았습니다.</p><nav><a href="#overview">구조 그림</a><a href="#decision">검토 결과·채택 이유</a><a href="#plan">전체 계획</a><a href="#reviewers">두 검토자의 원문</a></nav></header><div id="overview">'+overview+'</div><section id="decision" class="section">'+decisions+'</section><section id="plan" class="section"><h2>전체 계획 — 궁금한 부분부터 읽으세요</h2><div class="toc">'+''.join('<a href="#'+ident+'">'+E(title)+'</a>' for ident,title in toc)+'</div>'+plan+'</section><section id="reviewers"><h2>두 검토자의 의견을 직접 확인하기</h2>'+''.join(reviews)+'</section><footer><p>원본 KG와 과거 실험 기록 보존 · 모델 합의는 사람 평가를 대신하지 않음</p></footer></main><script src="report.js"></script></body></html>'
js='function showMode(proposed){document.getElementById("current").hidden=proposed;document.getElementById("proposed").hidden=!proposed;document.getElementById("current-button").setAttribute("aria-pressed",String(!proposed));document.getElementById("proposed-button").setAttribute("aria-pressed",String(proposed));}document.getElementById("current-button").addEventListener("click",()=>showMode(false));document.getElementById("proposed-button").addEventListener("click",()=>showMode(true));'
dest=HERE/'private/report.html';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(page,encoding='utf8');(dest.parent/'report.css').write_text(css,encoding='utf8');(dest.parent/'report.js').write_text(js,encoding='utf8')
print(json.dumps({'report':str(dest),'bytes':dest.stat().st_size,'review_documents':len(reviews)},ensure_ascii=False))
