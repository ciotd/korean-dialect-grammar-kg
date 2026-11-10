"""Human-readable findings; preserve the initial diagnostic classifications."""
import collections
import copy
import html
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_pipeline.io import read,save,sha
from kg_pipeline.integrated import IntegratedReader
from audit import LABELS,VALUES

HERE=Path(__file__).resolve().parent
STATUS={
'reached_and_delivered':'필요 후보를 찾아 전달함','reached_not_delivered':'찾았지만 전달에서 빠짐',
'knowledge_scope_not_supported':'현재 규칙 범위 밖','analysis_unavailable':'당시 분석 결과 없음',
'meaning_judgment_candidate':'의미 판단을 다시 확인할 부분','observed_form_or_rule_scope_mismatch':'형태 분석과 규칙 범위 대조 필요',
'relation_binding_missing':'필요한 대상 연결이 잘못되거나 빠짐','target_unit_not_found':'필요한 분석 단위가 만들어지지 않음',
'combined_or_unresolved':'원인 추가 확인 필요','semantic_axis_collision':'한 질문에 다른 종류의 뜻이 섞임',
'non_discriminating_unknown_gate':'구별에 쓰이지 않는 값의 미확정으로 보류'}

FINDINGS=[
{'title':'‘장소’와 ‘의문사’를 서로 다른 답으로만 받는 문제','location':'DEV012 어디에 / NEW005 어디에 / LONG001 어디야의 명사 단위',
 'evidence':'실제 반환값은 location 또는 subject이고 규칙은 interrogative만 허용한다. 장소를 묻는 ‘어디’는 장소 표현이면서 의문사일 수 있다. 한 칸에 하나만 고르게 한 설계 때문에 정당한 분석도 탈락할 수 있다.',
 'cause':'모델 오답으로 단정할 수 없는 분석 질문·조건 표현의 충돌',
 'fix':'명사 자체의 성격(의문·재귀 등)과 문장 안 역할(장소·주어 등)을 구별한다. 먼저 분석 단위별 질문과 허용값을 필요한 조건에 맞추는 작은 대안을 시험하고, 정보가 둘 다 필요하면 두 항목으로 분리한다.',
 'exit':'어디/누구/무엇의 새 질문·비질문 문장에서 각 뜻이 보존되고, 질문에만 의문사 규칙이 연결되는지 확인한다. 특정 문장 문자열로 연결하지 않는다.'},
{'title':'본동작과 보조동작을 거꾸로 연결한 문제','location':'DEV020 “하지 마”',
 'evidence':'Qwen은 본동작을 U7(마), 보조동작을 U5(하지)로 반환했다. 코드가 보조동작 연결을 거부해 필요한 연결이 없어졌다. 본동작으로 잘못 남은 ‘마’를 거르는 검사도 현재 부족하다. 절 번호도 하지=C2, 마=C1로 다르다.',
 'cause':'모델의 역할·절 판단 오류와 연결 검사 공백이 함께 있음',
 'fix':'문법 역할에 맞는 실제 후보 ID를 제공하고 본용언/보조용언 방향을 각각 검사한다. 잘못된 연결을 단순 삭제한 뒤 끝내지 말고 무엇을 다시 물어야 하는지 기록한다. 코드가 의미를 임의 확정하여 연결하지 않는다.',
 'exit':'금지·시도·완료·진행 및 본동사 대비 문장에서 방향이 맞고 잘못된 연결이 통과하지 않아야 한다.'},
{'title':'높임을 둘 다 허용하면서 미확정이면 막는 문제','location':'DEV004 친구예요 / DEV026 나왔어요',
 'evidence':'두 사례 모두 주어 높임이 null이다. 해당 조건은 있음과 없음 모두를 허용하지만, 현재 조회기는 null을 미확정으로 처리하여 후보에서 보류한다. 다른 조건은 맞는다.',
 'cause':'선택에 꼭 필요한 조건과 보존 확인 항목의 역할이 구분되지 않음',
 'fix':'이 값이 표현 선택을 실제로 바꾸는지 확인한다. 바꾸지 않으면 선택 필수 조건에서 분리하고 원래 높임 형태를 보존하도록 전달하는 대안을 비교한다. 모든 unknown을 통과시키는 수정은 하지 않는다.',
 'exit':'다른 표현을 골라야 하는 미확정 조건은 계속 보류하고, 불필요한 보류만 사라지는지 반례와 함께 확인한다.'},
{'title':'한 문장 묶음의 질문·금지·약속을 혼동한 문제','location':'LONG004 챙기셨어요? / 나가지 마세요. / 모셔다드릴게요.',
 'evidence':'실제 분석은 질문과 금지 부분도 promise(약속)로 반환했다. 질문에 필요한 규칙과 금지 규칙이 조건에서 탈락한다. 뒤의 약속 표현 때문에 앞부분까지 같은 값이 되었는지는 아직 원인 가설이다.',
 'cause':'관찰된 문장 기능 오분류. 정보량·모델 크기만으로 원인을 확정할 수 없음',
 'fix':'각 문장의 범위와 해당 위치를 명확하게 제시한다. 같은 입력·같은 KG에서 전체 문맥 포함 방식과 문장별 판단 후 연결 방식을 비교한다.',
 'exit':'질문·금지·약속을 각각 구별하면서 참여자·높임·문장 간 관계를 잃지 않아야 한다.'},
{'title':'모델이 서술어 대신 다른 단위를 연결한 문제','location':'QUAL017 도전하려고 / QUAL020 같다고',
 'evidence':'오른쪽 서술어로 반환한 U10, U33이 각각 서술어 단위가 아니어서 연결 검사에서 제거되었다. QUAL020은 인용을 양보로 분석한 문제도 함께 있다.',
 'cause':'잘못된 관계 대상 ID 및 일부 의미 판단 오류',
 'fix':'역할별로 선택 가능한 실제 서술어 ID를 좁혀 제시하고, 인용절 경계와 보고하는 서술어의 관계를 별도로 확인한다. 아무 후행 단어와 연결하지 않는다.',
 'exit':'새 인용·의도·조건절에서 실제 앞뒤 서술어를 연결하고 무관한 명사·조사 ID가 거절되는지 확인한다.'},
{'title':'‘계세요’를 올바른 구성으로 보지 못한 문제','location':'ADVCE002A 읽고 계세요',
 'evidence':'저장 분석에는 계세요를 포함한 보조구성 단위가 없다. 서술어는 계사로 반환되었고, 관찰된 마지막 형태 세요는 규칙이 기대한 어요/아요와 다르다. 반면 새 단순 예문의 형태 분석 통과가 이 사례의 해결을 증명하지 않는다.',
 'cause':'형태 분석·대상 추출·모델 분류가 겹친 문제',
 'fix':'계시다와 이다의 분석 후보를 대조하고 현재/과거·주체 높임을 보존한 보조구성으로 연결한다. 세요를 전부 어요로 고정 치환하지 않는다.',
 'exit':'계세요/계셨어요와 일반 계사, 명령 세요의 대비에서 분석과 후보가 구별되어야 한다.'},
{'title':'설명은 넓고 실제 조건은 좁은 규칙','location':'목적 -구로 규칙 / 끝점 -꺼지 규칙',
 'evidence':'-구로 설명에는 목적·정도·도급이 있지만 조건은 purpose만 허용한다. -꺼지 설명은 첨가 의미까지 포함하지만 조건은 endpoint만 허용한다. 조건을 무조건 넓혀서는 안 되며 설명이 현재 구현 범위를 넘었는지 먼저 구별해야 한다.',
 'cause':'사람이 읽는 규칙 설명과 실행 조건의 범위 불일치',
 'fix':'현재 지원 설명을 좁혀 맞추거나, 문헌에서 의미 차이를 확인한 뒤 별도 조건 분기로 추가한다. D04의 목적·강조와 D01의 정도·도급을 하나의 검증된 뜻으로 합치지 않는다.',
 'exit':'각 의미마다 적용·비적용 예문이 있고 설명·조건·전달이 같은 범위를 가리켜야 한다.'},
{'title':'설명에만 있고 검사하지 않는 제한','location':'-인데의 대상 종류 / -의 생략의 추상·관용 표현 / -겄-의 세대 설명',
 'evidence':'사람·동물 대상, 추상·관용의 제외, 세대 우선 사용 등이 설명에 있으나 그 전부가 현재 조건 노드에 있지는 않다. D04는 50대 이상 겄 사용이 잦고 아래 세대는 혼용한다고 기술하므로 “50대 이상만”은 원문보다 강한 제한이다.',
 'cause':'문헌의 경향·연구 정책·실행 필수 조건이 설명에 섞임',
 'fix':'각 문장을 필수 조건/표현 선택 참고/미확인으로 구별한다. 이미 합의한 대로 세대를 새 필수 입력으로 강제하지 않는다. 필요 이상의 제한 문구는 원문과 대조해 고친다.',
 'exit':'정책을 문헌 사실로 표시하지 않고, 실제로 막을 조건은 분석 질문부터 연결되어야 한다.'},
{'title':'보존 지식에 도달한 것을 변환 성공으로 세면 안 됨','location':'피동·진행·시도 등 보존 규칙',
 'evidence':'일부 규칙은 방언 어미를 제시하지 않고 원래 구성의 뜻을 유지하라고 한다. 이런 규칙에 도달해도 특정 말끝의 방언형이 준비된 것은 아니다.',
 'cause':'검색 성공·보존 지식 전달·방언 변환의 성과 단위 혼동 위험',
 'fix':'도달 현황에서 변환 후보와 보존 지식을 분리하고, 필요한 종결형이 없는 경우는 지원 공백으로 표시한다.',
 'exit':'-나요/-ㄹ까요/현재 부정계사 등 미지원이 다른 보존 규칙의 성공 수에 가려지지 않아야 한다.'},
{'title':'저장된 제한 설명이 전달 경로에 빠진 경우','location':'기존 해예체 규칙 3개의 limits 속성',
 'evidence':'규칙에는 limits 목록이 있으나 payload는 limitations 문자열만 읽는다. 직접 후보 조건에 일부 제외 사항은 반영되어 있어 곧바로 오용이라고 단정할 수는 없다. 그러나 저장된 규칙의 보존 지시가 전달되는지 점검할 필요가 있다.',
 'cause':'버전별 속성 이름과 전달 형식이 다른 문제',
 'fix':'관리 문구를 다시 넣지 말고 실제 적용·보존에 필요한 항목만 공통 제약 필드로 정제한다. 저장→전달 누락 검사를 추가한다.',
 'exit':'의미 있는 제약은 전달되거나 코드 조건으로 검사됨이 추적되고, 출처·검토 사족은 다시 들어가지 않아야 한다.'},
]


def render():
    pointer=read(HERE/'latest.json');out=ROOT/pointer['directory'];summary=read(out/'summary.json');rows=read(out/'regression50.json');probes=read(out/'natural_probes.json')
    gp=read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json');graph=read(ROOT/gp['graph']);reader=IntegratedReader(graph);archive=read(ROOT/gp['audit'])
    coverage=read(out/'recorded_rule_coverage.json')
    # Explicit post-review corrections; original judgment.json files stay intact.
    reviewed=copy.deepcopy(rows);corrections=[]
    for row in reviewed:
        for goal in row['goals']:
            prior=goal['status']
            if row['id'] in ('DEV012','NEW005','LONG001') and goal['rule_id']=='INT_NOM_WH_EODE_A' and prior=='meaning_judgment_candidate':
                goal['status']='semantic_axis_collision';goal['fix']=FINDINGS[0]['fix'];goal['review_note']='location/subject를 오답으로 단정하지 않는다. 명사의 성격과 문장 역할의 서로 다른 질문이 한 칸에 섞였다.'
            if row['id'] in ('DEV004','DEV026') and prior=='combined_or_unresolved':
                goal['status']='non_discriminating_unknown_gate';goal['fix']=FINDINGS[2]['fix']
            if row['id']=='QUAL003' and goal['target']=='선정해가지고':
                goal['status']='knowledge_scope_not_supported';goal['review_note']='최초 점검 기대를 수정: -어 가지고를 -어서 규칙으로 바로 처리할 근거가 충분하지 않다. 형태 분석 오류로 단정하지 않는다.';goal['fix']='-어 가지고 구성의 의미와 실현을 별도 정제한다. 기존 -어서의 조건을 느슨하게 하여 끼워 넣지 않는다.'
            if row['id']=='QUAL020' and goal['target']=='사람들한테는':goal['review_note']='현재 조건은 맞지만 이 문맥의 영향을 받는 대상과 물건을 받는 대상이 같은 의미 범위인지 문헌 검토가 더 필요하다. 조회 성공이 해석의 정확성을 보장하지 않는다.'
            if goal['status']!=prior:corrections.append({'id':row['id'],'target':goal['target'],'before':prior,'after':goal['status'],'reason':goal.get('review_note',goal['fix'])})
    counts=collections.Counter(g['status'] for r in reviewed for g in r['goals'])
    save(out/'reviewed_regression50.json',reviewed);save(out/'classification_corrections.json',corrections);save(out/'findings.json',FINDINGS)
    save(out/'reviewed_summary.json',{**summary,'reviewed_goal_states':dict(counts),'post_review_corrections':len(corrections),'all_grammar_in_each_sentence_exhaustively_labeled':False})
    evidence_nodes={n['id']:n for n in archive['documentary_nodes']}
    source_review_ids=['INT_PART_DATIVE_INDE','INT_PART_UNTIL_KKEOJI','INT_CONN_PURPOSE_GURO','INT_TAM_GET_GEOT','INT_END_PROHIB_MAISO','INT_LEAD_REQUEST_JU_AUX','INT_PART_GEN_ZERO']
    source_review={rid:[evidence_nodes[e['target']] for e in archive['documentary_edges'] if e['source']==rid and e['relation']=='SUPPORTED_BY'] for rid in source_review_ids}
    save(out/'source_excerpt_review.json',{'scope':'7 identified rule source excerpts; not rereading all 7 documents','rules':source_review})
    esc=lambda v:html.escape(str(v))
    def human(v):
        if v is None:return '미확정'
        if isinstance(v,list):return ' / '.join(human(x) for x in v)
        return VALUES.get(str(v),str(v))
    def table(headers,rs):return '<div class="tablewrap"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rs)+'</tbody></table></div>'
    body=[]
    for i,r in enumerate(reviewed,1):
        parts=[]
        for goal in r['goals']:
            rid=goal['rule_id'];title=reader.rules[rid]['node']['properties'].get('title',rid) if rid else '현재 직접 대응 규칙 없음'
            parts.append('<div class="goal"><b>'+esc(goal['target'])+' → '+esc(title)+'</b><p class="badge">'+esc(STATUS[goal['status']])+'</p>')
            if goal.get('hit'):
                bad=min(goal['hit']['branches'],key=lambda b:sum(c['state']!='true' for c in b['checks']))
                checks=[c for c in bad['checks'] if c['state']!='true']
                if checks:parts.append(table(['확인할 것','실제 분석값','KG가 요구하는 값'],[[esc(LABELS.get(c['feature'],c['feature'])),esc(human(c['value'])),esc(human(c['allowed']))] for c in checks]))
                missing=goal['hit'].get('missing_relations',[])
                if missing:parts.append('<p>빠진 연결: '+esc(' · '.join(LABELS.get(k,k) for k in missing))+'</p>')
            if goal.get('review_note'):parts.append('<p class="warn">검토 의견: '+esc(goal['review_note'])+'</p>')
            if goal.get('diagnostic_meaning_only_state')=='eligible':parts.append('<p>수동으로 의미값만 보충하면 이 규칙에 도달했습니다. 실제 Qwen이 그렇게 분석했다는 뜻은 아닙니다.</p>')
            parts.append('<p><b>다음 조치:</b> '+esc(goal['fix'].replace('先 확인','먼저 확인'))+'</p>')
            if rid:parts.append('<details><summary>추적용 규칙 ID</summary><code>'+esc(rid)+'</code></details>')
            parts.append('</div>')
        categories=' '.join({g['status'] for g in r['goals']})
        output=r.get('historical_output')
        body.append('<details class="sentence" data-search="'+esc(r['id']+' '+r['input'])+'" data-states="'+categories+'"><summary>'+esc(r['id'])+' · '+esc(r['input'])+'</summary><p><b>과거 실험의 실제 출력:</b> '+esc(output if output is not None else '저장된 출력 없음')+'</p><p class="muted">출력은 과거 기록입니다. 새 Neo4j 적재 뒤 Qwen이 다시 만든 문장이 아닙니다.</p>'+''.join(parts)+'</details>')
    rule_rows=[]
    for rid,r in reader.rules.items():
        p=r['node']['properties'];cases=[x for x in probes if x['rule_id']==rid]
        conditions=[]
        for b in r['branches']:
            conditions.append(' + '.join(LABELS.get(k,k)+'='+human(v) for k,v in b['conditions'].items()))
        rule_rows.append([esc(p.get('title',rid)),str(len(r['branches'])),str(coverage[rid]['eligible_units']),esc(' / '.join(x['text'] for x in cases)),
                         '<details><summary>실제 조건 보기</summary>'+''.join('<p>'+esc(x)+'</p>' for x in conditions)+'<code>'+esc(rid)+'</code></details>'])
    neo=read(HERE/'neo4j_latest.json');queries=(ROOT/neo['directory']/'explore.cypher').read_text(encoding='utf8')
    diagram=ROOT/'.archify/workflow-rule-branches-20261107-1435/rule-branches.html'
    diagram_link=Path(os.path.relpath(diagram,out)).as_posix()
    findings=''.join('<details class="finding"'+(' open' if i<3 else '')+'><summary>'+str(i+1)+'. '+esc(f['title'])+'</summary><p><b>어디서:</b> '+esc(f['location'])+'</p><p><b>실제 근거:</b> '+esc(f['evidence'])+'</p><p><b>원인 판단:</b> '+esc(f['cause'])+'</p><p><b>수정 방향:</b> '+esc(f['fix'])+'</p><p><b>끝나는 기준:</b> '+esc(f['exit'])+'</p></details>' for i,f in enumerate(FINDINGS))
    statusrows=[[esc(STATUS[k]),str(v)] for k,v in counts.items()]
    page=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>실제 문장에서 KG 지식까지 — 1차 점검</title>
<style>body{{font-family:Malgun Gothic,Arial,sans-serif;background:#f4f7fa;color:#17314c;line-height:1.8;max-width:1080px;margin:32px auto;padding:0 22px}}h1{{font-size:30px}}h2{{font-size:23px}}section{{padding:26px;background:white;border:1px solid #dce4ed;border-radius:12px;margin:22px 0}}summary{{cursor:pointer;font-weight:700}}details{{border:1px solid #dce4ed;padding:14px;border-radius:8px;margin:12px 0}}.finding{{background:#f9fbff}}.goal{{padding:16px;margin:12px 0;border-left:4px solid #4d7eb7;background:#f8fafc}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border:1px solid #dce4ed;padding:9px;text-align:left;vertical-align:top}}th{{background:#eaf1f9}}.tablewrap{{overflow:auto}}.muted{{color:#5d6d80;font-size:14px}}.warn{{background:#fff4de;padding:10px}}.badge{{display:inline-block;padding:2px 8px;background:#e9f0fa;border-radius:6px}}.large{{font-size:19px}}.flow{{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}}.flow span{{background:#eaf4f2;padding:14px;border-radius:8px}}input,select,button{{font:inherit;padding:8px;margin:5px;max-width:95%}}code{{font-size:12px;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;word-break:break-word;font-size:12px;background:#f3f5f7;padding:16px}}a{{color:#155da8}}@media print{{body{{background:white;margin:0}}section{{break-inside:avoid}}button,input,select{{display:none}}details:not([open])>summary{{font-size:11px}}}}</style>
<h1>지식이 없어서인가, 있는 지식까지 못 가서인가?</h1><p class="large">둘 다 있습니다. 이번에는 실제 문장 기록에서 어느 단계가 막혔는지 확인했습니다. ‘어디’의 뜻을 묻는 방식, 본동작·보조동작 연결, 미확정 값의 처리에 구체적인 문제가 드러났습니다.</p><p class="muted">2026년 11월 7일 · 새 KG 내용·조건 1차 점검 · 신규 Qwen 호출 0회 · 문법의 정답률/번역 품질 평가 아님</p>
<section><h2>1. 이번에 실제로 한 일</h2><p>기존 Qwen이 실제 문장을 분석한 99개 기록을 새 KG에 넣어 규칙 도달 현황을 확인했습니다. 별도로 기존 50문장에서 중요한 확인 지점 90개를 지정하고, 필요한 지식이 실제로 선택·전달되는지 대조했습니다. 한 문장에 여러 확인 지점이 있으므로 90건은 문장 수가 아닙니다. 50문장의 모든 문법 현상을 완전히 정답 라벨링했다는 뜻도 아닙니다.</p><p>56개 규칙마다 자연어 점검 예문을 만들어 총 57개를 준비했습니다. 과거 계사 규칙은 긍정·부정 두 예문입니다. 57개 모두 Kiwi가 필요한 형태의 대상을 만들 수 있었지만, 새 Qwen 의미 분석은 서버 연결 실패로 하지 못했습니다. 이를 57개 성공 번역이라고 세지 않습니다.</p><div class="flow"><span>실제 문장</span><span>저장된 실제 분석</span><span>필요한 규칙과 대조</span><span>조건·연결·전달의 막힌 지점</span><span>근거와 수정안</span></div>
{table(['점검','확인한 범위'],[['실제 저장 분석','99기록 · 802개 위치. 재시험을 포함한 수이며 독립 문장 수 아님'],['기존50문장','49개 분석 확보, LONG002의 분석 없음도 기록'],['규칙 도달','56개 중 31개가 저장 분석에서 후보로 도달. 나머지25개가 모두 잘못됐다는 뜻은 아님'],['새 자연어 예문','57개 형태 분석 통과. Qwen 의미 판단·최종 생성 미실행'],['원문 근거 확인','7개 쟁점 규칙의 별도 근거 발췌 대조. 원본7종 전체 재정독은 아님']])}</section>
<section><h2>2. 무엇이 막혔나요?</h2><p>아래는 90개 확인 지점의 분류입니다. ‘찾아 전달함’은 방언 문장이 자연스럽다는 뜻이 아닙니다. 기대한 규칙 자체에 대한 리드의 해석도 재검토 대상입니다.</p>{table(['확인 지점의 상태','건수'],statusrows)}<p>최초 자동 분류 뒤 ‘어디’ 관련 3건은 모델 오답이 아니라 질문 설계 충돌로 다시 분류했습니다. 또한 ‘-어 가지고’를 바로 ‘-어서’ 규칙으로 검사한 기대 1건은 부적절하여 현재 지원 밖으로 정정했습니다. 이 정정 전 기록도 보존했습니다.</p>{findings}</section>
<section><h2>3. 규칙·조건·분기는 이렇게 다릅니다</h2><p><b>규칙</b>은 어떤 표현을 쓸 수 있는지 담은 지식입니다. <b>조건</b>은 그 지식을 사용할 수 있는지 묻는 한 가지 확인입니다. <b>분기</b>는 조건들을 모두 만족해야 하는 한 묶음입니다. 한 규칙에 여러 묶음이 있으면 그중 하나가 맞으면 됩니다.</p><p>실제 과거 계사 규칙은 ① 긍정 계사+과거+존댓말 등의 묶음 또는 ② 부정 계사+과거+존댓말 등의 묶음을 허용합니다. 규칙은 하나이고 분기는 둘입니다. 그래서 56규칙에 57분기가 있습니다. 57단계를 차례로 통과한다는 뜻이 아닙니다.</p><p><a href="{esc(diagram_link)}">규칙과 두 조건 묶음 그림 열기</a></p><p>채팅에서 두 퀴즈에 모두 올바르게 답하셨습니다. ① 조회 성공과 생성 성공은 다르다. ② 규칙 하나에 분기 둘이 있을 수 있고 어느 한 묶음이 맞으면 된다. 핵심 구별을 확인했습니다.</p></section>
<section><h2>4. 이제 Neo4j에서도 새 KG를 볼 수 있습니다</h2><p>이전에는 저장 분리와 손실 확인을 먼저 해서 DB 적재가 뒤에 남아 있었습니다. 이번에는 예전 DB를 백업하고 새 버전을 추가했습니다. 새 버전 1,491노드·5,037관계의 모든 저장 속성이 파일과 일치하고, 이전 버전 내용은 변하지 않았습니다.</p><p><a href="http://localhost:7474/browser/">Neo4j Browser 열기</a> → 로그인 후 아래 질의를 붙여 넣으면 새 버전만 보입니다. 모든 버전을 한꺼번에 표시하면 예전 노드와 혼동할 수 있습니다.</p><details><summary>실제로 붙여 넣을 탐색 질의</summary><pre>{esc(queries)}</pre></details><p class="warn">현재 Qwen 실험의 조회기는 여전히 파일에 저장된 그래프 관계와 조건을 읽습니다. Neo4j는 동일 버전을 시각화·탐색하는 사본입니다. DB에 넣었다고 실험의 조회 엔진까지 Neo4j로 바뀐 것은 아닙니다.</p><p>현재 조회는 문장 분석값과 56개 규칙의 조건을 대조합니다. 721개 미정제 지식의 참고 검색은 별도의 문자열 검색입니다. 이 참고 검색이 조건을 따라 정제된 규칙에 도달하는 과정과 같다고 설명하면 안 됩니다.</p></section>
<section><h2>5. 앞으로 무엇부터 고칠까요?</h2>{table(['순서','할 일','완료 기준'],[
['1','명사·조사·연결어미 등 단위별로 물을 뜻을 분리. 본동작/보조동작/앞뒤 절의 실제 후보 ID와 역할 검사 정비','새 질문·반례에서 뜻과 관계가 맞는지 확인. 단순히 후보가 많아지는 것으로 성공 판정하지 않음'],
['2','선택을 바꾸지 않는 조건의 미확정 처리와 설명/조건 범위 불일치 정리','필요한 미확정은 계속 보류하고 불필요한 보류만 감소. 설명과 실행이 같은 범위'],
['3','서버 연결 후 준비한 57예문을 새 Qwen으로 분석하고 기존50에 회귀 적용','수동 보충 없이 필요한 지식에 실제 도달하고 반례의 부당 적용이 늘지 않음'],
['4','조회·전달이 확인된 지식으로 최종 생성 점검','과거·어간·높임 보존과 실제 방언 자연스러움을 분리 평가'],
['5','미지원 -나요/-ㄹ까요/현재 부정계사 등과 나머지 지식의 의미 정제','문헌·조건·새 문장 도달·생성·사람 검토 상태를 각각 갱신']])}<p>이번에는 진단과 수정안을 작성했고 문법 조건을 바꾸지 않았습니다. 1~2단계의 작은 수정은 새 후보 버전에서 반례와 함께 검사해야 합니다. 개선이 없으면 같은 프롬프트 강조를 반복하지 않고 분석 형식 또는 관계 표현을 다시 검토합니다. 자료가 부족하거나 언어 해석이 충돌하면 그 항목만 사용자에게 판단을 요청합니다.</p><p>외부 Claude·Codex 리뷰어를 새로 호출하지 않았습니다. 현재 결과는 리드의 검토와 코드 집계이며 독립 검증은 아닙니다. 다음 독립 검토에서는 Claude가 질문 분리와 문헌 해석을, Codex가 조건·관계 검사 및 비교 통제를 확인하는 것이 적절합니다.</p></section>
<section><h2>6. 50문장 각각 보기</h2><p>문장을 누르면 실제 막힌 값과 수정 방향을 볼 수 있습니다. 과거 출력은 비교를 위한 기록이며 새 실험 결과가 아닙니다.</p><input id="search" placeholder="ID 또는 문장 검색" aria-label="문장 검색"><select id="filter" aria-label="문제 종류"><option value="">모든 문장</option>{''.join('<option value="'+k+'">'+esc(v)+'</option>' for k,v in STATUS.items())}</select><button id="openall">보이는 문장 펼치기</button><button id="closeall">접기</button>{''.join(body)}</section>
<section><h2>7. 규칙 56개 전체 확인표</h2><p>‘실제 후보 도달 위치’는 기존 분석99기록에서의 수입니다. 0이면 기존 문장에 해당 용법이 없었을 수도 있고, 분석·조회 문제일 수도 있습니다. 새 예문의 형태 준비 여부만으로 이를 해결했다고 하지 않습니다.</p>{table(['저장 규칙','분기 수','실제 후보 도달 위치','새 점검 예문','조건'],rule_rows)}</section>
<p class="muted">점검 ID: {esc(summary['run_id'])}. 원시 분석·판정·수동 보충 진단·분류 정정·DB 백업은 같은 분석 폴더의 비공개 기록에 보존합니다. 새 KG 전체의 언어학적 정확성이 검증됐다고 주장하지 않습니다.</p>
<script>const cards=[...document.querySelectorAll('.sentence')];function filter(){{let q=document.getElementById('search').value.toLowerCase(),s=document.getElementById('filter').value;cards.forEach(c=>c.hidden=!(c.dataset.search.toLowerCase().includes(q)&&(!s||c.dataset.states.split(' ').includes(s))))}}document.getElementById('search').oninput=filter;document.getElementById('filter').onchange=filter;document.getElementById('openall').onclick=()=>cards.filter(c=>!c.hidden).forEach(c=>c.open=true);document.getElementById('closeall').onclick=()=>cards.forEach(c=>c.open=false);</script></html>'''
    (out/'report.html').write_text(page,encoding='utf8')
    save(HERE/'report_latest.json',{'report':str((out/'report.html').relative_to(ROOT)),'reviewed_goal_states':dict(counts),'neo4j_dataset':neo['dataset_id']})
    print(json.dumps({'report':str(out/'report.html'),'reviewed_goal_states':dict(counts)},ensure_ascii=False))


if __name__=='__main__':render()
