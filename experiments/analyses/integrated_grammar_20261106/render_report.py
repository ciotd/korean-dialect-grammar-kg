"""Readable report rendered from actual graph, decisions, and immutable run records."""
import collections
import datetime as dt
import html
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save
HERE=Path(__file__).resolve().parent
E=lambda x:html.escape(str(x),quote=True)
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def pill(text):return '<span class="pill">'+E(text)+'</span>'
FEATURE={'source_form':'입력 형태','source_final':'마지막 어미','lemma':'어간/단어','predicate_class':'서술어 종류','speech_act':'문장의 기능','question_kind':'질문 종류','clause_role':'절 위치','addressee_level':'듣는 사람 높임','subject_honorific':'주어 높임','tense':'시간 해석','past_form':'과거 형태 관찰','polarity':'부정','semantic_function':'뜻의 역할','auxiliary_kind':'보조용언 기능','voice':'사동/피동','unit_kind':'분석 단위','root_tag':'어근 품사','ending_tag':'어미 종류','morph_tag':'형태소 품사','prefinal_type':'선어말 형태','prefinal_sequence':'선어말 순서','nominal_kind':'명사 종류','nominal_end':'명사 끝소리'}
VALUE={'predicate':'서술어','nominal':'명사류','particle':'조사','connector':'절·용언 연결','construction':'여러 용언의 구성','statement':'평서','information_question':'정보 질문','request':'부탁','command':'명령','prohibition':'금지','suggestion':'청유','promise':'약속','plain':'반말','polite':'공손한 말','formal':'격식 높임','past':'과거','present':'현재/있음','absent':'없음','none':'없음','wh':'구체적 정보를 묻기','polar':'예/아니오 질문','confirmation':'확인 질문','verb':'동사','adjective':'형용사','copula':'이다','negative_copula':'아니다','benefactive':'남을 위한 행동','progressive':'진행','resultative':'완료/결과','main':'주절','embedded':'안긴절','quoted':'인용절','positive':'긍정','negative':'부정','EF':'종결어미','EC':'연결어미','VX':'보조용언','VV':'본동사','VA':'형용사','conversion':'표현 후보','preserve_only':'의미 보존','block':'잘못된 적용 주의'}
VALUE.update({'comitative':'함께 하는 대상','coordination':'나란히 잇기','comparison':'비교 기준','similarity':'서로 닮음','degree_equal':'같은 정도','restriction':'한정','emphatic_focus':'강조','possessive':'소유','exclusive_negative':'그것 외에는 없음','endpoint':'끝점','interrogative':'의문사','reflexive':'앞의 사람을 다시 가리킴','reason':'이유','sequence':'앞뒤 순서','condition':'조건','purpose':'목적','intention':'의도','become_auxiliary':'~하게 됨','simultaneity':'동시에 일어남','interruption':'하던 일의 중단','quotation':'인용','conjecture':'추측','volition':'의지','recipient':'받는 대상','object':'목적어','subject':'주어','topic':'화제','direction':'방향','location':'장소','limitation':'범위 한정','contrast':'대조','concession':'양보','condition_encounter':'~하면 그때','inference':'추정','other':'기타','active':'능동','passive':'피동','causative':'사동','desire':'바람','attempt':'시도','necessity':'필요·의무','eoss':'았/었 형태','si':'시 높임 형태','si_eoss':'시+았/었','gess':'겠 형태','deo':'더 형태','JKB':'부사격 조사','JX':'보조사','JC':'접속 조사','JKG':'관형격 조사','XSV':'동사 파생 접미사','XSA':'형용사 파생 접미사'})
def value(x):return '판단 못함' if x is None else VALUE.get(str(x),str(x))

PHASE={'smoke':'연결 시험','development':'새 개발 문장 시험','regression':'기존 50문장 재실험','repair':'연결 오류 보완 확인'}

def rule_title(r):
    if r['id'].startswith('INT_NOM_WH_'):
        return '의문사 '+', '.join(r['conditions'].get('lemma',r['conditions'].get('source_form',[])))+' → '+' / '.join(r['forms'])
    return r['title']

def reviews():
    found=[]
    for who in ('claude','codex'):
        for phase in ('development','regression','repair'):
            p=HERE/'private'/who/(phase+'_review.json')
            if p.exists():
                data=read(p)
                found.append((who,phase,data))
    return found
def condition(c):return '<br>'.join(E(FEATURE.get(k,k))+': '+E(' / '.join(value(x) for x in vs)) for k,vs in c.items())
def main():
    latest=read(HERE/'latest_graph.json');gp=Path(latest['graph']);g=read(gp);stats=read(latest['statistics'])
    cov=read(HERE/('coverage_'+latest['revision']+'.json'));rules=read(gp.parent/'refined_knowledge.json')['rules'];byrule={r['id']:r for r in rules}
    nodes={n['id']:n for n in g['nodes']}
    names={i:(rule_title(byrule[i]) if i in byrule else n.get('title') or n['properties'].get('title') or n['properties'].get('meaning') or i) for i,n in nodes.items() if n['type']=='SemanticRule'}
    modules={n['id']:n.get('title',n['id']) for n in g['nodes'] if n['type']=='Module'}
    refs={x['id']:x for x in (json.loads(l) for l in (ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl').read_text(encoding='utf8').splitlines() if l.strip())}
    runs=[]
    for p in sorted((ROOT/'experiments/runs').glob('*_integrated_grammar_*')):
        if not (p/'config.json').exists():continue
        cfg=read(p/'config.json');res=read(p/'private/results.json') if (p/'private/results.json').exists() else []
        m=read(p/'metrics.json') if (p/'metrics.json').exists() else {}
        runs.append((p,cfg,res,m))
    parts=['<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>9분야 KG 통합 구현·실험</title><link rel="stylesheet" href="report.css"></head><body><main>',
       '<header><p class="eyebrow">2026-11-06 · 실제 파일과 실행 기록에서 계산</p><h1>문장 끝만 보던 KG를<br>문장 안의 여러 부분으로 넓혔습니다.</h1><p>명사·조사·절 연결·보조용언을 각각 찾고, 조건이 맞는 지식을 Qwen에 전달하는 통합 후보 버전입니다. 마지막 문장은 Qwen이 직접 씁니다.</p></header>',
       '<nav><a href="#answer">핵심 결과</a><a href="#scope">문법 범위</a><a href="#flow">실제 처리 방법</a><a href="#cases">입력별 결과</a><a href="#knowledge">지식 내용</a><a href="#review">검토·다음 단계</a></nav>',
       '<section id="answer"><h2>먼저 알아야 할 세 가지</h2><ol><li><b>기존 원본 KG는 삭제하거나 덮어쓰지 않았습니다.</b> 전체 자료와 새로 정리한 지식을 합친 별도 파일을 만들었습니다.</li><li><b>새 용법 44개가 생겼지만, 26개 작업 묶음 전체가 끝난 것은 아닙니다.</b> 어떤 부분을 실제로 연결했는지 아래에 나눠 표시합니다.</li><li><b>문장이 바뀌었다고 자연스러워진 것은 아닙니다.</b> 원문 유지·과거 손실 경고·모델 보류를 분리하고, 품질은 출력 문장을 보고 판단해야 합니다.</li></ol>',
       table(['구분','이번 파일 기준','무엇을 뜻하나'],[
       ['보존한 원본 그래프','1,625 노드 / 6,167 관계','12개 문법 모듈, 문헌·설계·출처 정보가 들어 있는 이전 자료 전체'],
       ['새 통합 후보 그래프',f"{stats['combined_candidate']['nodes']:,} 노드 / {stats['combined_candidate']['edges']:,} 관계",'원본 자료 + 기존 실행 지식 + 새 용법·조건·근거. 파일 기반으로 조회했으며 Neo4j DB 교체는 하지 않음'],
       ['조건으로 조회하는 용법',str(stats['all_interpreted_rules'])+'개 (기존12 + 새44)','각각 조건이 맞을 때만 조회되는 데이터. 56개를 순서대로 모두 통과해야 하는 검사가 아님'],
       ['새44개의 성격','표현 후보41 · 보존2 · 주의1','공통형이나 높임 단계 변경도 포함. 모두 방언 고유 변환이거나 현대 화자 검증을 받은 것은 아님'],
       ['전체 작업 목록','26묶음 / 기존 설계항목911개',f"{cov['legacy_items_with_new_refinement']}개 설계항목에 이번 정제 용법을 연결. 연결된 항목 전체의 의미 검증 완료를 뜻하지 않음"],
       ['정제하지 못한 지식','원본 SourceAtom 721개는 검색 가능','제목·문헌 조건의 문자열 검색 결과는 관련 자료로만 전달. 자동 적용 규칙으로 승격하지 않음']]),'</section>']
    total_calls=sum(m.get('api_attempts',0) for _,_,_,m in runs)
    rows=[]
    for p,cfg,res,m in runs:
        rows.append([E(p.name),E(PHASE.get(cfg['phase'],cfg['phase']))+' / '+str(cfg['input_count'])+'입력',str(len(res)),str(m.get('valid_output_records','진행 중')),str(m.get('actual_text_changes','—')),str(m.get('model_review_requested','—')),str(m.get('api_attempts','—')),str(round(m.get('wall_seconds',0),1))+'초',E(m.get('stop_reason') or ('종료' if m else '진행 중'))])
    parts+=['<section><h2>실제 실행 결과</h2><p>“출력 수”는 읽을 수 있는 응답을 받은 수입니다. 정답 수가 아닙니다. 모델이 자체 보류를 표시해도 비어 있지 않은 응답은 출력 수에 포함하며, 보류 수를 옆에 따로 표시합니다. 연결 시험의 두 문장은 개발30에도 들어 있으므로 서로 독립 표본이 아닙니다.</p>',table(['Run ID','용도/계획','시도 입력','출력 수','원문과 다름','모델 보류','실제 호출','전체 시간','실행 상태'],rows),f'<p>완료 실행의 호출 합계: {total_calls}회. 전체 프로그램 상한은 200회입니다. 개발30과 기존50은 독립 최종 평가셋이 아닙니다.</p></section>']
    parts+=['<section><h2>연결은 넓어졌지만, 아직 해결되지 않은 문제가 있습니다.</h2><p>두 검토자의 개발30 점검에서 아래처럼 서로 다른 위치의 문제가 확인됐습니다. 이것들을 모두 “KG가 부족하다” 또는 “모델이 못한다”로 묶지 않았습니다.</p>',
      table(['실제 사례','어디에서 처음 어긋났나','이번 판단과 대응'],[
       ['“열지 마세요”, “갑시다”','Qwen이 금지·청유를 부탁으로 판단해 KG 조건과 맞지 않음','분석 지시에 기능의 뜻과 관계 방향을 명료하게 설명. 같은18입력을 한 번만 재확인'],
       ['“도서관이야”에 대명사 야/가/자 자료가 붙음','같은 글자 야만 맞춘 참고자료 검색·전달','원본 검색은 보존하고 단위 종류·입력 방향을 확인하는 전달 대안을 별도 재생'],
       ['“집에 와서 손을 씻었어” → “집에 와 손 씻다”','과거 형태와 보존 지시는 전달됐지만 생성에서 과거 소실','정보 누락으로 설명하지 않음. 출력 오류로 보존하고 같은 보존 지시 반복은 중단'],
       ['“건물” → “건울”','입력 어휘를 바꾸라는 해당 KG 지식 없이 생성에서 바뀜','생성 단계의 근거 없는 어휘 변화로 기록. 자연스러움과 별개로 확인할 문제'],
       ['“계세요”가 계+이다로 분석됨','Kiwi 관찰 단계','새로운 전역 차단을 만들지 않음. 형태 분석 대안 검토가 남아 있음']]),'</section>']
    replay_path=HERE/'private/reference_replay_summary.json'
    if replay_path.exists():
        replay=read(replay_path)
        parts+=['<section><h2>불필요한 참고자료 줄이기: 실제 생성과 구분</h2><p>이미 저장된 분석값을 고정한 뒤 참고자료 전달만 다시 계산했습니다. 맞지 않는 단위·방향을 제외하고, 관계 해시와 반복 관리 설명을 덜었습니다. 정제 지식은 그대로입니다. 아래 대안은 이 보고서의 기존 Qwen 출력에 사용된 요청이 아닙니다.</p>',
          table(['대상 실행','재생 가능한 입력','참고 건수 전→후','참고 글자 수 전→후','추가 모델 호출'],[[E(s['run_id']),str(len(s['cases'])),f"{s['before_reference_count']} → {s['after_reference_count']}",f"{s['before_chars']:,} → {s['after_chars']:,}",'0'] for s in replay]),'<p>글자 수 감소는 토큰 절감률이나 번역 정확도 개선율이 아닙니다. 실제 품질 효과는 별도 비교 전입니다.</p></section>']
    fieldrows=[]
    for number in range(1,13):
        mid=f'M{number:02}';rs=[r for r in rules if number in r['modules']]
        fieldrows.append([E(modules[mid]),str(len(rs)),E(' / '.join(r['title'] for r in rs[:4]))+(' 등' if len(rs)>4 else ''), '부분 구현·검증 대상' if rs else '기존 자료 보존 / 이번 신규 변환 없음'])
    parts+=['<section id="scope"><h2>문법 범위: 어디까지 됐나?</h2><p>한 용법이 높임과 보조용언에 함께 속할 수 있으므로 아래 숫자를 합하면 44보다 큽니다. 사동·피동은 특히 범위가 작습니다. 사동은 문헌에 나온 일부 어휘, 피동은 의미 보존 지식이며, 일반적인 피동 변환이 완성된 것은 아닙니다.</p>',table(['기존 문법 모듈','새 용법 소속 수','이번에 연결한 내용 예','상태'],fieldrows),'<details><summary>26개 작업 묶음 전체 상태 보기</summary>',table(['묶음','이해하기 쉬운 이름','기존 항목 수','새 용법 수','상태'],[[E(p['id']),E(p['title']),str(p['legacy_items']),str(len(p['new_rule_ids'])),E(p['status'].replace('部分','일부'))] for p in cov['packages']]),'</details></section>']
    parts+=['<section id="flow"><h2>어떤 순서로 바뀌나?</h2><div class="flow"><div>① 표준어 입력</div><b>→</b><div>② Kiwi가 위치·형태를 찾고<br>Qwen이 뜻·문장 기능·관계를 판단</div><b>→</b><div>③ 실제 KG의 조건 관계 대조<br>맞음 / 안 맞음 / 모름을 기록</div><b>→</b><div>④ 위치·표현·보존할 내용을 전달</div><b>→</b><div>⑤ Qwen이 문장 전체 작성</div></div><p>예를 들어 “창문 좀 닫아 주세요”에서는 ‘닫아’가 할 일이고 ‘주세요’는 남을 위한 행동을 부탁하는 부분입니다. 두 부분이 연결돼 있다는 판단까지 맞아야 ‘해 주이소’ 지식이 후보가 됩니다. 생성 뒤에는 원시 응답을 그대로 저장합니다. 코드는 틀린 문장을 몰래 고치지 않습니다.</p>',
      table(['그래프 안 이름','쉬운 뜻','저장 내용'],[['문법 구성','함께 작동하는 표현 묶음','예: 본동사 + 연결어미 + 보조 주다'],['용법/규칙','언제 어떤 표현을 선택할 수 있는지','조건, 표현 후보, 보존할 뜻, 문헌 근거, 한계'],['조건','적용 전에 확인할 질문','요청인가? 공손한 말인가? 실제 어간은 주인가?'],['실현형','선택할 수 있는 말 모양','예: 주이소. 지역·시기 차이도 함께 남김'],['근거','원문을 다시 확인할 자리','문헌 번호·PDF쪽·발췌·텍스트 해시'],['관계','위 항목끼리의 실제 연결','구성→용법→조건→허용값, 용법→실현형/근거/원본항목']]),
      '<p>관련 자료는 전체721개에서 문자열로 찾고, 입력 위치마다 상위3개만 참고로 전달합니다. 그 밖의 일치 항목도 조회 기록에 남깁니다. 정제된 용법은 이 상위3 제한을 사용하지 않고 조건으로 조회합니다. 지식 전달에는 24,000자 예산을 두며, 제외 이유를 기록합니다. 이 예산은 실제 모델 토큰 수와 같은 단위가 아닙니다.</p></section>']
    parts+=['<section id="cases"><h2>입력별로 직접 확인하기</h2><p>참고 문장은 사용자가 승인한 비교 자료입니다. 생성 요청에는 넣지 않았습니다. 출력과 다르다는 이유만으로 자동 오답 처리하지 않습니다. 펼치면 Qwen의 분석 판단, 실제 전달한 지식, 빠진 조건을 볼 수 있습니다.</p><label>검색 <input id="search" placeholder="ID 또는 문장 검색"></label> <label>실행 <select id="run"><option value="">전체</option>'+''.join('<option value="'+E(p.name)+'">'+E(PHASE.get(cfg['phase'],cfg['phase'])+' · '+p.name)+'</option>' for p,cfg,_,_ in runs)+'</select></label><p id="visible"></p>']
    for p,cfg,res,m in runs:
        for result in res:
            rid=result['id'];rd=p/'private/records'/rid
            packet=read(rd/'generation_packet.json') if (rd/'generation_packet.json').exists() else {}
            bound=read(rd/'bound_analysis.json') if (rd/'bound_analysis.json').exists() else []
            traces=read(rd/'retrieval.json') if (rd/'retrieval.json').exists() else []
            lookup={t['unit_id']:t for t in traces}
            reference=refs.get(rid,{})
            parts+=['<article class="case" data-run="'+E(p.name)+'" data-search="'+E(rid+' '+result['input_text']+' '+str(result.get('output_text')))+'"><h3>'+E(rid)+' '+pill(PHASE.get(cfg['phase'],cfg['phase']))+'</h3>',
              table(['구분','문장'],[['입력',E(result['input_text'])],['Qwen 원시 출력',E(result.get('output_text') or '(출력 없음)')],['사용자 승인 참고',E(reference.get('reference','이 개발 문장은 승인 참고 없음'))]]),
              '<p>'+pill('원문 유지' if result.get('unchanged') else '변경 있음' if result.get('output_text') is not None else '출력 실패')+pill('전달 용법 '+str(result.get('delivered_knowledge',0)))+pill('과거 형태 수 감소 경고' if 'past_marker_count_decreased' in result.get('observational_warnings',[]) else '과거 감소 자동 경고 없음' if 'observational_warnings' in result else '생성 후 검사 미수행')+'</p>']
            matched=[(who,f) for who,phase,review in reviews() if phase==cfg['phase'] for f in review.get('findings',[]) if f.get('id')==rid]
            if matched:
                parts+=['<details><summary>검토자가 발견한 문제와 수정 제안</summary>',table(['검토자 / 처음 확인한 단계','실제 관찰','제안·확실성'],[[E(who)+' / '+E(f.get('first_observed_stage','')),E(f.get('observation','')),E(f.get('repair',''))+'<small>'+E(f.get('certainty',''))+'</small>'] for who,f in matched]),'</details>']
            if result.get('error_type'):parts+=['<p class="warn">실패 위치: '+E(result.get('stage'))+' / '+E(result['error_type'])+' '+E(result.get('error_detail',''))+'</p>']
            ar=[]
            for u in bound:
                fs=u['features'];tr=lookup.get(u['id'],{})
                important={k:v for k,v in fs.items() if k in ('speech_act','question_kind','predicate_class','auxiliary_kind','semantic_function','addressee_level','subject_honorific','past_form') and v is not None}
                elig=tr.get('eligible',[]);unknown=tr.get('unresolved',[])
                reasons=[]
                for h in unknown:
                    missing={c['feature'] for b in h['branches'] if b['state']=='unknown' for c in b['checks'] if c['state']=='unknown'}
                    reasons.append(names.get(h['rule_id'],h['rule_id'])+': '+', '.join(FEATURE.get(k,k) for k in sorted(missing))+(' / 관계 '+','.join(h['missing_relations']) if h.get('missing_relations') else ''))
                ar.append([E(u['text'])+'<small>'+E(value(u['kind'])+' · '+u['id'])+'</small>', '<br>'.join(E(FEATURE.get(k,k)+': '+value(v)) for k,v in important.items()),'<br>'.join(E(names.get(h['rule_id'],h['rule_id'])) for h in elig) or '조건을 충족한 용법 없음','<br>'.join(E(x) for x in reasons) or '—'])
            parts+=['<details><summary>분석 → 조건 조회 → 전달 내용 보기</summary>',table(['입력의 위치','실제 분석값','조건이 맞은 용법','판단/관계 미확정'],ar)]
            for a in packet.get('verified_scope_knowledge',[]):
                parts+=['<div class="knowledge"><h4>'+E(names.get(a['rule_id'],a['rule_id']))+'</h4><p><b>적용 위치:</b> '+E(a['source_text'])+' · '+E(a['unit_id'])+'</p><p>'+E(a['instruction'])+'</p><p><b>남길 내용:</b> '+E(' / '.join(a.get('preserve',[])))+'</p><p><b>근거:</b> '+E(', '.join(str(s['doc'])+' PDF '+str(s['page'])+'쪽' for s in a.get('sources',[])))+'</p><small>'+E(a['rule_id'])+'</small></div>']
            parts+=['<p>관련 원본 자료 '+str(len(packet.get('related_unprocessed_sources',[])))+'건을 별도로 전달했습니다. 조건으로 승인된 변환 명령과는 다릅니다. 예산/상위3 정책으로 제외된 항목 '+str(len(packet.get('delivery_omissions',[])))+'건은 원시 기록에 남아 있습니다.</p>',
                '<p>문장 전체 생성: Qwen · 사용 규칙 ID: 모델의 자기보고 · 자연스러움: 사람 평가 전</p></details></article>']
    parts+=['</section><section id="knowledge"><h2>새 지식 44개: 내용과 근거</h2><p>노드의 속성을 그대로 나열하지 않고 실제 사용 조건과 지시문을 표시했습니다. 원문 발췌와 해석·조건은 별도 속성으로 보존합니다. 원문에 있는 표현이 모든 문장에 적용된다는 뜻은 아닙니다.</p>']
    for r in rules:
        parts+=['<details><summary>'+E(rule_title(r))+' '+pill(value(r.get('rule_type','conversion')))+'</summary><p>'+E(r['instruction'])+'</p>'+table(['실제 적용 조건','실제 출력 후보'],[[condition(r['conditions']),E(' / '.join(r['forms']))]])+'<p><b>한계:</b> '+E(r['limitations'])+'</p><p>근거: '+E(', '.join(s['doc']+' PDF '+str(s['page'])+'쪽' for s in r['source_refs']))+'</p><small>'+E(r['id'])+'</small></details>']
    parts+=['</section><section id="review"><h2>누가 무엇을 확인했나?</h2>',table(['담당','실제로 수행한 일','구분해야 할 한계'],[['리드','원본911항목/26묶음 대응, 통합 코드·데이터 작성, 검토 반영, 시험 실행·집계·백업','원문 근거와 연구자의 대응 해석을 분리. 자연스러움을 혼자 확정하지 않음'],['Claude','57개 지식 후보, 전체 후보 재판정, 추가5개 원문·형태소 대조, 조건/형태/구성 오류 지적','모델 의견은 현대 경상도 화자의 독립 평가를 대신하지 않음'],['Codex','내부 어미 오적용, 동일 본/보조 연결, 중단·선별·집계 오류 검토 및 수정 재확인','코드 반례 검증이며 실제 번역 품질 인증이 아님']]),
       '<h2>무엇을 검사했고, 무엇은 아직 검사하지 못했나?</h2>',table(['검사','확인 내용','한계'],[['새 코드 24개 검사','내부 연결어미/종결어미 구분, 본/보조 관계, 중단 기록, 원시 출력 보존, 조건의 미확정 처리','실제 방언 자연스러움 점수가 아님'],['기존 관리기 38개 검사','기록·집계·비교·관리 기능의 회귀 검사','수치가 정확히 기록돼도 번역이 정확하다는 뜻은 아님'],['발췌 연결 114개 검사(중복 포함)','새 용법의 발췌 문자열이 해당 문헌·쪽에 실제 존재하는지 검사','인용과 해석의 의미 관계는 별도 언어 검토가 필요'],['그래프 구조','중복 ID·끊긴 참조 검사, 원본 파일 해시 보존','이전 후보에서 물려온 미연결 근거 EV_Q_SCOPE 1개는 보존했고 조회에는 쓰이지 않음'],['모델 생성','실제 요청과 원시 응답·사용 토큰·소요 시간 저장','품질 개선·그래프 우월성은 아직 독립 평가하지 않음']]),
       '<h2>다음 단계와 멈출 기준</h2>',table(['작업','끝나는 기준','예상과 다르면'],[['이번 결과의 최초 오류 위치 확인','분석·조회·전달·생성 중 실제 기록에서 처음 어긋난 곳을 입력별로 분류','참고와 다르다는 사실만으로 KG 오류라 단정하지 않음'],['후속 지식 정제','보류20후보와 아직 연결되지 않은 용법을 근거·조건 단위로 보완','문헌 표/의미가 불확실하면 미확인으로 남기고 다른 용법을 진행'],['모델과 검색 방식 비교','동일 지식·입력·생성 모델·예산에서 KG없음/문서검색/조건표/그래프 비교','효과가 없으면 그래프 우월성을 주장하지 않고 한계를 기록'],['독립 최종 평가','새 쉬운 평가 문장을 동결하고 사람의 블라인드 자연스러움·의미 보존 평가','기존50과 개발30을 독립 최종평가로 다시 이름 붙이지 않음']]),
       '<p><b>이 보고서의 종료 의미:</b> 통합 구현과 실행 결과를 확보하는 개발 검증입니다. 26묶음 전체의 의미 정제, 모든 지역·세대의 자연스러움, 논문을 위한 그래프 효과 비교는 별도 남은 작업입니다.</p></section>',
       '<footer>원본 KG 및 과거 실행 보존 · 로컬 복구 체크포인트 별도 관리 · 이 보고서에는 인증정보 없음<br>작성 '+E(dt.datetime.now().isoformat(timespec='seconds'))+'</footer></main><script src="report.js"></script></body></html>']
    (HERE/'private/report.html').write_text('\n'.join(parts),encoding='utf8')
    save(HERE/'private/report_manifest.json',{'graph':str(gp),'runs':[p.name for p,_,_,_ in runs],'cases':sum(len(r) for _,_,r,_ in runs),'total_calls':total_calls,'notes':'All displayed cases loaded from immutable raw runs; no output rewriting.'})
    print('Rendered',sum(len(r) for _,_,r,_ in runs),'cases')

if __name__=='__main__':main()
