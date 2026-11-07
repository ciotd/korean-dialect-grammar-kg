"""Readable measured report; original JSON remains linked as technical evidence."""
import html,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(HERE)]
from kg_pipeline.io import read,save
from assess import assess
E=lambda v:html.escape(str(v if v is not None else '미확정'))
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def build():
    run=ROOT/read(HERE/'latest_development.json')['run'];a=assess(run);metrics=read(run/'metrics.json')
    decision=read(HERE/'private/decision.json') if (HERE/'private/decision.json').exists() else {'title':'결과를 검토하고 있습니다.','reason':'아직50건 진행 여부를 결정하지 않았습니다.','next':'원시 출력과 보존 항목을 두 검토자와 대조합니다.'}
    labels={'baseline':'옛 기준선','kiwi_improved':'첫 보완','kiwi_focused':'질문 형식 보완'};acts={'prohibition':'금지','request':'요청','statement':'평서','promise':'약속','information_question':'질문'}
    left,right=a['policies'];left_label,right_label=labels[left],labels[right]
    rows=[];details=[]
    for c in a['cases']:
        b=c['policies'].get(left,{});n=c['policies'].get(right,{})
        rows.append([f'<a href="#case-{E(c["id"])}">{E(c["id"])}</a>',E(c['source']),E(b.get('output')),E(n.get('output'))])
        block=f'<details id="case-{E(c["id"])}"><summary>{E(c["id"])} · {E(c["source"])}</summary><p>확인할 내용: {E(" · ".join(c["expected"].get("preserve",[])))}</p>'
        for policy,p in c['policies'].items():
            block+=f'<h3>{labels[policy]}</h3><p class="quote">{E(p["output"])}</p>'
            if p['constructions']:
                block+=table(['분석 대상','Qwen이 판단한 기능','본동작 연결','보조동작 연결'],[[E(x['text']),E(acts.get(x['act'],x['act'])),E(', '.join(x['relations'].get('main_predicate',[])) or '없음'),E(', '.join(x['relations'].get('auxiliary_predicate',[])) or '없음')] for x in p['constructions']])
            if p['connection_match'] is not None:block+=f'<p>사전 지정한 기능·관계 검사: <b>{"맞음" if p["connection_match"] else "불일치 또는 누락"}</b>. 자연스러움 점수는 아닙니다.</p>'
            block+=table(['모델에 전달된 위치','전달한 지식의 실제 설명','작성자의 사용 신고와 이유'],[[E(x['target']),E(x['instruction']),E(('사용' if x['applied'] else '미사용')+' — '+str(x['reason']))] for x in p['delivered']]) if p['delivered'] else '<p>조건을 통과하여 작성자에게 전달된 KG 지식이 없습니다. Qwen은 자체 지식으로도 작성할 수 있습니다.</p>'
            if p.get('missing_coverage'):block+='<p class="warn">조회 단위가 없는 것으로 의심한 구절: '+E(', '.join(dict.fromkeys(x['text'] for x in p['missing_coverage'])))+'. 자동으로 틀린 형태라고 확정하거나 새 규칙을 만들지 않았습니다.</p>'
            if p['analysis_objections']:block+='<p class="warn">분석에 이의가 남은 구절: '+E(', '.join(dict.fromkeys(x['text'] for x in p['analysis_objections'])))+'. 관련 후보의 전달 여부를 기록에서 확인할 수 있습니다.</p>'
        finding=next((f for f in decision.get('cases',[]) if f['id']==c['id']),None)
        if finding:block+='<p><b>원문 대조:</b> '+E(finding['finding'])+'</p>'
        details.append(block+'</details>')
    costs=table(['항목',left_label,right_label],[[name,E(metrics['by_policy'][left][key]),E(metrics['by_policy'][right][key])] for name,key in [('실행한 경로','records'),('출력 완료','complete'),('후속 모델 호출','api_attempts'),('후속 입력·출력 토큰','tokens')]])
    doc='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kiwi 기본 전환과 연결 보완</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#172b42;font:17px/1.75 system-ui,"Malgun Gothic",sans-serif}main{max-width:1240px;margin:auto;padding:35px 24px}h1{font-size:32px;line-height:1.35}h2{margin-top:38px;font-size:24px}h3{font-size:19px}p{max-width:1000px}.card,details{background:white;border:1px solid #d7e1ed;border-radius:12px;padding:23px;margin:16px 0}.lead{border-left:6px solid #196d91}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid #d9e1eb;padding:12px;vertical-align:top;min-width:100px}th{background:#e8eff8;text-align:left}.quote{background:#edf5fa;padding:14px;border-radius:7px}.warn{color:#8a4e00}a{color:#126496}summary{cursor:pointer;font-weight:700}.flow{display:flex;gap:8px;flex-wrap:wrap}.flow span{padding:10px;background:#e5eff8;border-radius:8px}small{color:#54677a}@media print{details{break-inside:avoid}main{padding:10px}body{font-size:12px}table{font-size:11px}}</style><main>'''
    doc+='<p>2026년11월7일 · 개발 실험 · Qwen이 최종 문장을 작성</p><h1>Kiwi로 읽고, Qwen으로 쓰기<br>연결 보완으로 무엇이 달라졌나?</h1>'
    doc+=f'<section class="card lead"><h2>{E(decision["title"])}</h2><p>{E(decision["reason"])}</p><p><b>다음 행동:</b> {E(decision["next"])}</p></section>'
    doc+='<h2>무엇을 바꿨나요?</h2><p>Kiwi는 문장을 어간·어미·조사로 나눕니다. Qwen은 문장의 뜻과 각 부분의 관계를 판단합니다. 그 결과로 KG에서 조건에 맞는 지식을 찾고, 다른 Qwen 호출이 문장 전체를 씁니다. 마지막 Qwen은 오류를 지적하지만 문장을 자동으로 다시 쓰지는 않습니다.</p><div class="flow">'+''.join('<span>'+t+'</span>' for t in ['원문 → Kiwi 형태','→ Qwen 절 구획','→ Qwen 의미·관계','→ KG 조건 조회','→ Qwen 전체 문장 작성','→ Qwen 진단·기록'])+'</div>'
    doc+='<p><a href="../../../../.archify/workflow-kiwi-default-20261107-1736/pipeline.html">클릭하며 보는 처리 흐름 그림</a></p>'
    doc+=table(['남아 있던 문제','이번 보완','보완의 한계'],[[E('읽지 못한 형태를 없음으로 취급'),E('미해석 선어말은 미확정으로 남기고, 조회 단위 누락을 별도 기록'),E('누락을 발견해도 Kiwi 오분석을 자동 교정하지 않음')],[E('하지 마를 요청으로 판단하거나 보조동작 연결 누락'),E('금지·요청 의미를 구별해 묻고 실제 본·보조 후보 ID를 제공'),E('후보는 정답이 아니며 Qwen이 최종 관계를 판단')],[E('제/저를 내/나로 바꿈'),E('겸양 보존 힌트와 소유 조사 규칙의 적용 범위를 설명'),E('기존 KG 조회 조건은 고정; 부적절한 후보가 조회될 가능성은 남음')]])
    doc+='<h2>어떻게 비교했나요?</h2><p>새12문장의 Kiwi 형태와 Qwen 절 구획을 양쪽에 똑같이 사용했습니다. 최초 비교는 옛 기준선과 첫 보완 묶음입니다. 추가 비교는 첫 보완과 질문 형식 보완입니다. 추가 비교에서는 작성·검토 지시를 같게 두고, 최초의 형태·절 구획을 재사용합니다. 모델·KG·설정은 같습니다. 검사 기대값과 방언 정답은 모델 요청에 넣지 않았습니다. 이미 본 개발 문장의 결과이며 독립 최종 평가는 아닙니다.</p>'
    doc+=table(['문법 연결 검사',left_label,right_label],[[E('금지2·요청3·시도 평서1: 기능과 본·보조 관계 모두 일치'),E(str(a['connection_matches'][left])+'/'+str(a['connection_denominator'])),E(str(a['connection_matches'][right])+'/'+str(a['connection_denominator']))]])
    doc+=costs+f'<p>공통 절 구획 호출 {metrics["scope_calls"]}회는 위 양쪽 비용과 별도로 한 번만 집계합니다. 전체 실제 호출 {metrics["api_attempts"]}회, 총 보고 토큰 {metrics["reported_usage"]["total_tokens"]:,}개. 한 번씩의 개발 관찰이며 자연스러움 정확도가 아닙니다.</p>'
    doc+='<h2>실제12문장 출력</h2><p>문장 ID를 누르면 분석과 전달된 지식, 작성자의 사용 신고를 함께 볼 수 있습니다. 사용 신고는 실제로 올바르게 적용했다는 증거가 아니므로 출력과 다시 대조해야 합니다.</p>'+table(['ID','표준어 원문',left_label,right_label],rows)+''.join(details)
    doc+='<h2>두 검토자와 리드의 역할</h2><p>Claude는 문법 기능·지식의 적용 범위·겸양 손실을, Codex는 동일 조건·코드·누락과 집계를 확인합니다. 리드는 두 의견을 원시 기록과 대조해 수정과 실험을 수행했습니다. AI들의 합의는 사람의 자연스러움 평가를 대신하지 않습니다.</p>'
    for name in ('claude','codex'):
        for stage in ('design','implementation','outcome'):
            p=HERE/'private'/f'{name}_{stage}_review.md'
            if p.exists():doc+=f'<p><a href="{p.name}">{name} — '+{'design':'설계','implementation':'구현','outcome':'결과'}[stage]+' 검토 원문</a></p>'
    doc+='<h2>앞으로의 순서</h2><p>'+E(decision['next'])+'</p><p>이번 비교가 끝나도 전체 문법의 정제·확장, 일반 검색과 그래프 검색의 비교, 독립 평가와 사람의 자연스러움 검토는 남습니다. 이번 결과를 전체 연구의 성공이나 실패로 확대하지 않습니다.</p>'
    doc+=f'<details><summary>재현 기록과 실제 코드</summary><p>Run ID: {E(run.name)}</p><p>KG와 코드 변경 여부: {E(read(run/"postflight.json"))}</p><p><a href="../PLAN.md">계획</a> · <a href="../DECISIONS.md">판단·변경 기록</a> · <a href="assessment_{E(run.name)}.json">집계 원본</a></p></details></main></html>'
    (HERE/'private/report.html').write_text(doc,encoding='utf8')
    print(HERE/'private/report.html')

if __name__=='__main__':build()
