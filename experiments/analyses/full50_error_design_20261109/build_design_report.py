"""Render this bounded Markdown design into a readable offline report."""
from pathlib import Path
import html,re
BASE=Path(__file__).parent
def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    return s
lines=(BASE/'DESIGN.md').read_text(encoding='utf-8').splitlines(); out=[];i=0
flow='<div class="flow">'+''.join('<span>'+x+'</span>' for x in ['원문 + Kiwi','절 범위','관계·의미 판단','KG 조건 조회','Qwen 전체 작성','보존 검토'])+'</div><p class="note">분석 담당을 나누는 비교와 생성 계획 담당을 두는 비교를 따로 진행합니다. 아래 그림은 제안의 위치이며 새 구현 완료를 뜻하지 않습니다.</p>'
while i<len(lines):
    line=lines[i]
    if line.startswith('```'):
        i+=1
        while i<len(lines) and not lines[i].startswith('```'): i+=1
        out.append(flow);i+=1;continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            cells=[c.strip() for c in lines[i].strip('|').split('|')]
            if not all(re.fullmatch(r'[:\- ]+',c) for c in cells):rows.append(cells)
            i+=1
        out.append('<div class="scroll"><table>'+''.join('<tr>'+''.join(f'<{"th" if n==0 else "td"}>{inline(c)}</{"th" if n==0 else "td"}>' for c in row)+'</tr>' for n,row in enumerate(rows))+'</table></div>');continue
    if line.startswith('#'):
        m=re.match(r'(#{1,3}) (.*)',line)
        if m:
            n=len(m[1]);out.append(f'<h{n}>{inline(m[2])}</h{n}>')
    elif line.startswith('- '):out.append('<p class="bullet">• '+inline(line[2:])+'</p>')
    elif line.strip():out.append('<p>'+inline(line)+'</p>')
    i+=1
style='''*{box-sizing:border-box}body{margin:0;background:#eff4f8;color:#1c3044;font:17px/1.85 "Malgun Gothic",sans-serif}main{max-width:1220px;margin:auto;padding:30px 42px;background:white}h1{font-size:33px;line-height:1.4}h2{margin-top:54px;padding-top:24px;border-top:3px solid #dce8f2;color:#124e6b}h3{margin-top:32px}p{max-width:1050px}a{color:#075c9c}strong{color:#153b52}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px;margin:20px 0}td,th{padding:15px;border:1px solid #d8e2ec;vertical-align:top;min-width:130px}th{background:#e8f3f6;text-align:left}code{overflow-wrap:anywhere;font-size:14px;background:#f1f4f6}.flow{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.flow span{background:#e2f0ee;border-radius:10px;padding:13px}.flow span:not(:last-child):after{content:' →';margin-left:12px}.note{padding:18px;background:#fff6e5;border-left:4px solid #c78a28}.bullet{padding-left:16px}header{padding:22px;background:#153d55;color:white;border-radius:12px}header a{color:#c0e9ff}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:15px}.stats div{padding:18px;background:#eef5f7;border-radius:10px}.stats b{display:block;font-size:26px}@media(max-width:700px){main{padding:20px}.stats{grid-template-columns:1fr}h1{font-size:27px}}@media print{body{background:white}main{padding:0}.scroll{overflow:visible}tr{break-inside:avoid}h2{break-after:avoid}}'''
head='<header>이번 작업: 결과를 다시 읽고 다음 설계를 제안했습니다.<br>연구 코드·KG 수정 및 새 Qwen 실행은 하지 않았습니다.<br><a href="https://gyeongsang-kg-full50-20261109.piai-2-3424.chatgpt.site/#case-DEV002">공유된 50문장 보고서</a> · <a href="DESIGN.md">설계 원문</a></header>'
stats='<div class="stats"><div><b>분석 오류</b>틀린 조건값으로 잘못된 규칙을 찾거나 필요한 규칙을 놓침</div><div><b>전달·검사 문제</b>설명 경고로 후보 제외, 사용 신고 중복으로 중단</div><div><b>생성 오류</b>과거·높임을 전달받고도 출력에서 손실</div></div>'
document='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>50문장 오류 구분과 보완 설계</title><style>'+style+'</style><main>'+head+stats+''.join(out)+'</main></html>'
(BASE/'report.html').write_text(document,encoding='utf-8')
print('report.html written; source DESIGN.md retained')
