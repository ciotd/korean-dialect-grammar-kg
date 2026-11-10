"""Read-only, reproducible explanation of common design items and trial usages.

No model calls, changes to KG, or semantic certification. Output stays private.
Archify finalize is a separate, mandatory delivery step for overview.html.
"""
from pathlib import Path
import collections, datetime, hashlib, html, json, shutil
from examples import EXAMPLES

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DESIGN = 'knowledge/authored/kg_v3_evidence_20261019_r2/inputs/design.json'
GRAPH = 'knowledge/authored/semantic_grammar_20261106_integrated_r2/private/graph.json'
BRANCHES = 'experiments/analyses/kg_understanding_audit_20261107/private/20261107T031711223906Z/branch_specifications.jsonl'
OLD_GRAPH = 'experiments/analyses/kg_understanding_audit_20261107/private/20261107T031711223906Z/snapshot/candidate_graph.json'
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def esc(v): return html.escape(str(v),quote=True)
def title(n): return n.get('title') or n['properties'].get('title',n['id'])
def human(v):
    if isinstance(v,list): return '；'.join(map(human,v))
    if isinstance(v,dict): return '；'.join(f'{k}：{human(x)}' for k,x in v.items())
    s=str(v)
    for a,b in [('target request','목표 표현 선택 요청'),('typed feature bundle','종류가 구별된 특징 묶음'),('feature bundle','특징 묶음'),('features','특징'),('feature','특징'),('relation','관계'),('UNKNOWN','미확정'),('DEFER','보류'),('scope','적용 범위'),('target','목표'),('binding','연결'),('interface','묶음 창구')]:s=s.replace(a,b)
    return s

FEATURES=dict(line.split('=',1) for line in '''addressee_level=듣는 사람에게 쓰는 말높임
auxiliary_kind=보조용언의 기능
clause_role=절의 위치
ending_tag=끝 어미의 품사
lemma=사전형의 어간
morph_tag=해당 조각의 품사
nominal_kind=명사 종류
polarity=긍정·부정
predicate_class=서술어 종류
prefinal_sequence=선어말어미의 순서
prefinal_type=선어말어미 종류
question_kind=질문의 기능
root_tag=어근 품사
semantic_function=문맥 속 기능
source_final=원문 종결형
source_form=원문 형태
speech_act=말하려는 의도
subject_honorific=주체높임 표시
tense=시제
unit_kind=분석한 조각의 종류
voice=능동·피동'''.splitlines())
VALUES=dict(line.split('=',1) for line in '''formal=격식 높임
plain=반말
polite=공손한 말
attempt=시도
benefactive=남을 위해 하는 행동
desire=희망
necessity=필요·당위
other=기타
progressive=진행
resultative=결과 상태
main=주절
EF=종결어미
EC=연결어미
JC=접속조사
JKB=부사격조사
JKG=관형격조사
JX=보조사
lexical_nominal=어휘 명사
negative=부정
positive=긍정
adjective=형용사
verb=동사
copula=이다 계사
negative_copula=아니다 부정계사
eoss=었 계열
none=없음
si=시 계열
si_eoss=시 다음 었
gess=겠 계열
confirmation=확인
polar=맞는지 아닌지 묻기
wh=누구·무엇 등 정보 묻기
VA=형용사
VV=동사
XSA=형용사 파생 접미사
XSV=동사 파생 접미사
become_auxiliary=게 되다 보조구성
comitative=동반
comparison=비교
condition=조건
condition_encounter=조건적 상황
conjecture=추측
coordination=나열
degree_equal=같은 정도
emphatic_focus=강조
endpoint=끝 지점
exclusive_negative=제외를 동반한 부정
inference=추론·추측
intention=의도
interrogative=의문
interruption=중단
possessive=소유·관형 관계
purpose=목적
quotation=인용
reason=이유
recipient=받는 사람
reflexive=자기 지시
sequence=앞뒤 순서
similarity=유사
simultaneity=동시
volition=의지
command=명령
exclamation=감탄
information_question=정보 질문
prohibition=금지
promise=약속
request=요청
statement=진술
suggestion=제안
absent=없음
present=있음
connector=절 연결 부분
construction=여러 조각의 문법 구성
nominal=명사 부분
particle=조사 부분
predicate=서술어 부분
passive=피동'''.splitlines())
RELATIONS={'left_predicate':'앞 절 서술어','right_predicate':'뒤 절 서술어','main_predicate':'본용언','auxiliary_predicate':'보조용언','host_nominal':'조사가 붙는 명사','quoted_predicate':'인용절 서술어','matrix_predicate':'바깥 절 서술어'}
TYPE_TEXT={'AnalysisConcept':'분석·검사 책임','Construction':'여러 요소가 묶인 문법 구성','GrammarFeature':'구별해서 보존할 문법 특징','AggregateInterface':'세부 책임들을 묶어 전달하는 창구'}

def build():
    run_id=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=HERE/'private'/run_id; (out/'snapshot').mkdir(parents=True)
    inputs=[DESIGN,GRAPH,BRANCHES,'src/kg_pipeline/integrated.py','knowledge/authored/kg_v3_evidence_20261019_r2/code/build_evidence_kg.py']
    hashes={p:sha(ROOT/p) for p in inputs}
    prior=load(ROOT/'experiments/analyses/kg_understanding_audit_20261107/private/20261107T031711223906Z/summary.json')
    assert hashes[GRAPH]==prior['sources']['candidate']['sha256']
    assert hashes['src/kg_pipeline/integrated.py']==prior['sources']['reader']['sha256']
    for i,p in enumerate(inputs):shutil.copy2(ROOT/p,out/'snapshot'/f'{i}_{Path(p).name}')
    d=load(ROOT/DESIGN);g=load(ROOT/GRAPH);nodes={n['id']:n for n in g['nodes']}
    common=sorted([n for n in nodes.values() if n['properties'].get('role')=='grammar'],key=lambda n:(int(n['properties']['module']),n['id']))
    rules=sorted([n for n in nodes.values() if n['type']=='SemanticRule'],key=lambda n:n['id'])
    C={n['id'] for n in common};R={n['id'] for n in rules}
    assert len(common)==136 and len(rules)==56 and C==set(EXAMPLES), (len(common),len(rules),C-set(EXAMPLES),set(EXAMPLES)-C)
    outgoing=collections.defaultdict(list);direct=collections.defaultdict(list)
    for e in g['edges']:
        outgoing[e['source']].append(e)
        if (e['source'] in C and e['target'] in R) or (e['source'] in R and e['target'] in C):
            direct[e['source']].append(e);direct[e['target']].append(e)
    links=[e for e in g['edges'] if e in direct.get(e['source'],[])]
    assert len(links)==55 and len(C&set(direct))==29 and len(R&set(direct))==29
    branches=collections.defaultdict(list)
    for line in (ROOT/BRANCHES).read_text(encoding='utf-8').splitlines():
        b=json.loads(line);assert b['rule_id'] in R and b['branch_id'] in nodes
        assert set(b['path_edge_ids']) <= {e['id'] for e in g['edges']}
        branches[b['rule_id']].append(b)
    # Capture all four historical integrated-run result records; repetition is explicit.
    cases=[]; records=[]
    for run in sorted((ROOT/'experiments/runs').glob('*integrated_grammar*')):
        for f in sorted((run/'private/records').glob('*/result.json')):
            res=load(f); packet_path=f.parent/'generation_packet.json'
            packet=load(packet_path) if packet_path.exists() else {}
            delivered=[x['rule_id'] for x in packet.get('verified_scope_knowledge',[])]
            case={'run':run.name,'id':res['id'],'input':res.get('input_text'),'output':res.get('output_text'),'declared_used':res.get('used_rule_ids',[]),'delivered':delivered,'status':res.get('status'),'source':f.relative_to(ROOT).as_posix(),'source_sha256':sha(f)}
            cases.append(case);records.append({'path':case['source'],'sha256':case['source_sha256']})
            if packet_path.exists():records.append({'path':packet_path.relative_to(ROOT).as_posix(),'sha256':sha(packet_path)})
    save(out/'snapshot/observed_cases.json',cases)
    latest_examples={}
    for case in cases:
        for rid in set(case['delivered']):latest_examples[rid]=case
    selected=['IG019','IG013','IG010','IG006','IG005','IG021','IG028']
    repair='20261106T060407624135Z_integrated_grammar_repair'
    for cid in selected:
        src=ROOT/'experiments/runs'/repair/'private/records'/cid
        if src.exists():shutil.copytree(src,out/'snapshot/cases'/cid)
    modules={int(m['number']):m for m in d['root']['module_catalog']}
    common_rows=[];rule_rows=[]
    def other(e,id):return e['target'] if e['source']==id else e['source']
    def references(refs):
        if not refs:return '本 항목의 source_refs에는 문헌 위치가 없다. 설계·관리상의 근거를 별도로 확인해야 한다.'.replace('本','이')
        return ' · '.join(f"{r.get('document_id',r.get('doc','?'))} PDF {', '.join(map(str,r.get('pdf_pages',[])))}쪽" for r in refs)
    def case_html(case,rid):
        if not case:return '<p class="muted">검토한 4개 실행 기록에서 이 용법의 실제 전달 예를 찾지 못했다. 미구현 또는 적용 불가능하다는 뜻은 아니다.</p>'
        used=rid in case['declared_used']
        return f'<div class="observed"><strong>저장된 실제 실행 예</strong><p>{esc(case["input"])} → <b>{esc(case["output"])}</b></p><p>해당 용법 전달: 확인 · Qwen의 사용 선언: {"있음" if used else "없음"}. 사용 선언은 실제 준수·자연스러움의 증명이 아니다. 당시 판본의 기록이며 현재 판본의 재검증과 구분한다.</p><small>{esc(case["run"])} / {esc(case["id"])}</small></div>'
    for i,n in enumerate(common,1):
        id=n['id'];p=n['properties'];s=p['original_spec'];ex=EXAMPLES[id];rs=[other(e,id) for e in direct[id]]
        source=references(s.get('source_refs',[]))
        linkage=''.join(f'<p><button class="jump" data-target="{esc(rid)}">{esc(title(nodes[rid]))}</button> <code>{esc(rid)}</code></p>' for rid in rs)
        if not rs:linkage='<p>56개 용법과의 직접 연결이 저장되어 있지 않다. 관련 코드가 없다는 뜻까지 확인한 것은 아니다.</p>'
        observed=''.join(case_html(latest_examples.get(rid),rid) for rid in rs if rid in latest_examples)
        if not observed:observed='<p class="muted">이 설계 항목을 직접 실행했다는 문장 로그는 제시할 수 없다. 아래 예시는 이해를 위한 작성 예문이다.</p>'
        match=human(s.get('match','이 항목에 별도 조건 없음'));block=human(s.get('block','이 항목에 별도 차단 조건 없음'))
        card=f'''<article class="card" id="{id}" data-module="{p['module']}" data-linked="{int(bool(rs))}"><div class="eyebrow">{i:03d} / 136 · {esc(modules[int(p['module'])]['name'])}</div><h3>{esc(title(n))}</h3><div class="badges"><span>공통 설계</span><span>{esc(TYPE_TEXT[n['type']])}</span><span>{'직접 연결 '+str(len(rs))+'개' if rs else '직접 연결 없음'}</span></div><p class="example">{esc(ex['text'])}</p><p>{esc(ex['explanation'])}</p><p class="muted">위 문장은 이번 설명을 위해 작성한 예시다. 아래 ‘저장된 실제 실행 예’와 구분한다.</p><dl><dt>왜 독립 항목인가?</dt><dd>{esc(TYPE_TEXT[n['type']])}을 구별하기 위해서다. {esc(human(s.get('graph_contract',{}).get('minimum_boundary','세부 계약들을 선택·결속해 묶는 역할이며, 개별 문법 규칙을 추가하는 항목이 아니다.')))}</dd><dt>무엇을 확인하도록 설계했나?</dt><dd>{esc(match)}</dd><dt>무엇을 막도록 설계했나?</dt><dd>{esc(block)}</dd><dt>어떤 정보를 남기나?</dt><dd>{esc(human(s.get('output','명시 없음')))}</dd><dt>문헌 위치 기록</dt><dd>{esc(source)}<br>문헌이 보여준 구별을 설계에 반영했다는 기록이다. 해당 쪽이 이 설계 전체를 입증한다고 재검증한 것은 아니다.</dd><dt>구현 상태를 어떻게 말해야 하나?</dt><dd>원본 항목은 설계 청사진이며 실행 활성값은 false다. 아래 별도 용법과의 연결은 대응 관계이지, 이 ID의 함수가 호출됐다는 기록이 아니다.</dd></dl><h4>56개 용법과의 저장된 직접 연결</h4>{linkage}{observed}<details><summary>개발자에게 전달할 실제 필드와 연결 ID</summary><p>항목 ID: <code>{id}</code></p><p>입력 필드: {esc(human(s.get('input',[])))}</p><p>동작 이름: <code>{esc(s.get('action','미기재'))}</code> — 설계 명칭이며 같은 이름의 함수 존재를 뜻하지 않음.</p><p>보존 필드: {esc(human(s.get('preserve',[])))}</p><p>미확정 대응: {esc(human(s.get('on_unknown','미기재')))}</p>{''.join(f'<p>{esc(e["source"])} — {esc(e["relation"])} → {esc(e["target"])}<br><small>{esc(e["id"])}</small></p>' for e in direct[id])}</details></article>'''
        common_rows.append({'id':id,'module':p['module'],'title':title(n),'type':n['type'],'direct_rules':rs,'refs':s.get('source_refs',[]),'html':card})
    for i,n in enumerate(rules,1):
        id=n['id'];p=n['properties'];cs=[other(e,id) for e in direct[id]]
        forms=[nodes[e['target']]['properties'].get('form') for e in outgoing[id] if e['relation']=='REALIZES']
        ev=[nodes[e['target']]['properties'] for e in outgoing[id] if e['relation']=='SUPPORTED_BY']
        cond=[]
        for j,b in enumerate(branches[id],1):
            rows=[]
            for k,vals in b['conditions'].items():
                vals=['현재' if k=='tense' and v=='present' else VALUES.get(str(v),str(v)) for v in vals]
                rows.append(f'<tr><th>{esc(FEATURES.get(k,k))}</th><td>{esc(" 또는 ".join(vals))}</td></tr>')
            cond.append(f'<h4>조건 묶음 {j} — 표의 모든 행을 충족해야 함</h4><table>{"".join(rows)}</table>')
        relation_text=' · '.join(RELATIONS.get(x,x) for x in p.get('required_relations',[])) or '추가 필수 관계 없음'
        evrefs=' · '.join(dict.fromkeys(f"{x.get('document_id','?')} PDF {x.get('pdf_page','?')}쪽" for x in ev)) or 'SUPPORTED_BY 연결 없음'
        linked=''.join(f'<p><button class="jump" data-target="{cid}">{esc(title(nodes[cid]))}</button> <code>{cid}</code></p>' for cid in cs) or '<p>공통 136개로 가는 직접 연결이 없다. 동작 조건이 없는 용법이라는 뜻은 아니다.</p>'
        card=f'''<article class="card rule" id="{id}" data-linked="{int(bool(cs))}"><div class="eyebrow">{i:02d} / 56 · 현재 후보 KG</div><h3>{esc(title(n))}</h3><div class="badges"><span>조건 조회 구현</span><span>언어 품질 미인증</span></div><p>{esc(p.get('meaning',p.get('instruction','설명 미기재')))}</p><dl><dt>Qwen에 전달할 형태 후보</dt><dd>{esc(human(forms))}</dd><dt>반드시 연결해야 할 문장 관계</dt><dd>{esc(relation_text)}</dd><dt>보존하도록 지시한 내용</dt><dd>{esc(human(p.get('preserve',[])))}</dd><dt>출처 위치</dt><dd>{esc(evrefs)}</dd><dt>제한·미확인 사항</dt><dd>{esc(p.get('limitations','별도 limitations 필드 없음. 제한이 없다는 뜻은 아님.'))}</dd></dl>{''.join(cond)}<p class="muted">조건 묶음이 여러 개면 그중 하나를 충족한다. 필수 정보가 없으면 판단을 미룬다. 표는 저장 조건의 설명이며 문헌상 타당성 인증이 아니다.</p><h4>공통 문법 틀과의 실제 연결</h4>{linked}{case_html(latest_examples.get(id),id)}<details><summary>식별자와 조사 범위</summary><code>{id}</code><p>{esc(p.get('status','status 미기재'))}</p><p>역사적 실행 4개에서 이 용법이 전달된 기록 {sum(id in c['delivered'] for c in cases)}건. 같은 입력의 재실행을 포함하며 성공률이 아니다.</p></details></article>'''
        rule_rows.append({'id':id,'title':title(n),'direct_common':cs,'html':card})
    stats={'common_items':len(common),'atomic_responsibilities':125,'aggregate_interfaces':11,'types':dict(collections.Counter(n['type'] for n in common)),'modules':dict(collections.Counter(n['properties']['module'] for n in common)),'rules':len(rules),'branches':sum(map(len,branches.values())),'direct_edges':len(links),'linked_common':29,'unlinked_common':107,'linked_rules':29,'unlinked_rules':27,'common_with_source_refs':sum(bool(n['properties']['original_spec'].get('source_refs')) for n in common),'historical_result_records':len(cases),'historical_unique_input_texts':len({c['input'] for c in cases}),'rules_with_observed_delivery':len(latest_examples),'new_model_calls':0,'new_quality_evaluation':False}
    save(out/'mapping.json',{'stats':stats,'common':[{k:v for k,v in x.items() if k!='html'} for x in common_rows],'rules':[{k:v for k,v in x.items() if k!='html'} for x in rule_rows],'edges':links})
    save(out/'manifest.json',{'id':run_id,'question':'136 common design items: provenance, responsibility, direct correspondence to 56 trial usages','contribution':'A traceable teaching artifact before semantic audit and controlled comparisons','decision_use':'Locate provenance and design/runtime gaps without upgrading validation status','before_checkpoint':'da7e7ac5c69772af122c3e3741d627d1a7a9660b','source_hashes':hashes,'record_hashes':records,'stats':stats,'limits':['Teaching examples are authored explanations, not executed tests.','Historical model-declared rule use is not causal attribution or quality validation.','Direct-edge absence is not proof of absent implementation.','Individual source pages were not independently reread for semantic validation in this task.']})
    (out/'candidate.archify.md').write_text(OVERVIEW,encoding='utf-8')
    options=''.join(f'<option value="{i}">{i:02d}. {esc(m["name"])} ({stats["modules"].get(i,0)})</option>' for i,m in modules.items())
    cases_table=''.join(f'<tr><td>{esc(c["id"])}</td><td>{esc(c["input"])}</td><td>{esc(c["output"])}</td><td>{esc(", ".join(c["delivered"]) or "없음")}</td></tr>' for c in cases if c['run']==repair and c['id'] in selected)
    source_table=''.join(f'<tr><th>{k}</th><td>{esc(s["title"])}<br>{esc(s["author"])} · {s["year"]}</td><td>{esc(s["notes"])}</td></tr>' for k,s in d['root']['source_policy'].items())
    body=PAGE.replace('@@COMMON@@',''.join(x['html'] for x in common_rows)).replace('@@RULES@@',''.join(x['html'] for x in rule_rows)).replace('@@OPTIONS@@',options).replace('@@CASES@@',cases_table).replace('@@SOURCES@@',source_table).replace('@@STAMP@@',run_id)
    (out/'guide.html').write_text(body,encoding='utf-8')
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    save(out/'build_receipt.json',{'status':'passed','all_136_have_authored_teaching_examples':True,'all_56_have_condition_cards':True,'all_input_hashes_unchanged':True,'archify_finalize':'pending','browser_review':'pending'})
    print(json.dumps({'directory':str(out),'stats':stats},ensure_ascii=False))

OVERVIEW = '''# 136개 설계와 56개 실행 용법은 어떻게 다른가? {#grammar-answer}

공통 문법 틀은 **무엇을 구별하고 보존할지 정한 136개 설계 항목**이다. 현재 후보 KG의 56개 용법은 그중 일부와 연결되어, 조건을 검사한 뒤 Qwen에 전달된다.

- 136 = 세부 책임 125 + 묶음 창구 11. 한국어 문법 전체를 입증한 규칙 수가 아니다.[](source:design)
- 저장된 직접 대응은 공통 29개 ↔ 용법 29개, 연결 55개다. 연결 수는 구현률이나 정확도가 아니다.[](source:mapping)
- 설계 ID, 조건 조회, 실제 전달, 올바른 문장 생성은 각각 다른 확인 단계다.[](source:reader)

@answer scope="2026-11-07 로컬 자료 대조 · 예문은 설명용과 저장 실행을 구별"
@meta locale=ko style=clean quality_profile=showcase
@source design title="2026-10-14 설계 기록: root.common_grammar_source_limit, atomic_definition, roles.grammar" path=knowledge/authored/kg_v3_evidence_20261019_r2/inputs/design.json
@source builder title="2026-10-19 원본 KG 구축 코드: design_blueprint와 실행 비활성 상태 보존" path=knowledge/authored/kg_v3_evidence_20261019_r2/code/build_evidence_kg.py
@source mapping title="이번 설명의 mapping.json: 후보 그래프에서 재집계한 136↔56 실제 연결" path=mapping.json
@source reader title="현재 통합 조회 구현: 조건 검사·관계 존재 확인·전달 패킷" path=src/kg_pipeline/integrated.py
@source actual title="저장 실행 20261106T060407624135Z_integrated_grammar_repair: IG019·IG013·IG006" path=experiments/runs/20261106T060407624135Z_integrated_grammar_repair/private/records

## 136개는 어떤 기준으로 만들어졌나? {#origin}

설계는 7개 방언 자료가 보여 주는 문법 구별에서 출발했다. 이를 분석·보존·형태 선택의 책임으로 나누고 공통 항목으로 정리했다. 별도의 표준어 문법책 전체를 제공받아 목차를 옮긴 작업은 아니다.[](source:design)

@architecture id=origin-map title="자료 → 공통 설계 → 별도 실행 용법"
| documents | 방언 자료 7개 | external |
| common | 공통 설계 136개 | database |
| usages | 후보 용법 56개 | database |
| documents > common | 구별을 설계 |
| documents > usages | 근거 정제 |
| common > usages | 직접 연결 55개 | dashed |

| 분리 기준 | 쉽게 말하면 | 실제 설계 예 |
| --- | --- | --- |
| 한 항목에 한 책임 | 무엇을 판단하는지 분명하게 | 조건인지 원인인지 구별 |
| 같은 모양도 기능이 다르면 분리 | 글자가 같다고 같은 뜻은 아님 | 먹어 보다 / 오는가 보다 |
| 다른 모양도 공통 기능으로 연결 | 형태와 기능을 따로 저장 | 조건 관계와 -면/-모 후보 |
| 뜻·시간·높임을 보존 | 바꿔도 남아야 하는 것 지정 | 과거와 주체높임 |
| 모르면 보류 | 없는 정보를 만들어 적용하지 않기 | 문맥 없는 의문사 해석 |
| 묶음 창구를 별도 표기 | 여러 세부 책임의 전달 창구 | 높임·시제·계사 interface |

## 자료의 근거와 설계자의 판단은 어디서 갈리는가? {#evidence}

문헌은 형태·용법·지역·시기의 관찰을 제공한다. 어떤 공통 ID와 속성으로 표현할지는 설계자의 모델링 판단이다. 문헌을 인용했다는 사실만으로 그 분해가 유일하거나 완전하다고 입증되지는 않는다.[](source:design)

| 자료 묶음 | 실제 성격 | 설명할 때의 한계 |
| --- | --- | --- |
| D01 양지현 2021 | 경남 -거로 연구 | 특정 구성과 결합 제약 |
| D02 조현준 2018 | 경북 종결어미 학위논문 | 과거 구비문학 자료의 범위 |
| D03–D06 | 동남 방언 관련 위키 저장본 4개 | 같은 자료 계통, 독립 증거 4개로 세지 않음 |
| D07 류성기 2014 | 함양 문법 형태 변화 조사 | 지역·세대의 제한적 관찰 |

136개 중 121개에 문헌 위치 목록이 저장돼 있다. 15개에는 그 목록이 없으며, 이 중 11개는 묶음 창구다. 위치가 있어도 설계 전체의 의미 검증이 끝났다는 뜻은 아니다.[](source:mapping)

## 136개 안에는 무엇이 들어 있나? {#composition}

| 저장 유형 | 개수 | 어린이에게 설명한다면 |
| --- | --- | --- |
| 분석·검사 책임 | 48 | 문장을 읽으며 확인할 질문 |
| 문법 구성 | 54 | 함께 움직이는 말 조각 묶음 |
| 문법 특징 | 23 | 과거·높임처럼 붙여 두는 이름표 |
| 묶음 창구 | 11 | 여러 이름표와 판단을 모아 전달하는 상자 |

48 + 54 + 23 = 125개 세부 책임이고, 창구 11개를 더해 136개다. 원본 항목의 실행 활성값은 false다. 원본 KG 구축은 이 상태를 그대로 보존했다.[](source:builder)

## 현재 프로그램은 설계 항목을 모두 실행하나? {#runtime}

현재 프로그램은 136개 ID를 순서대로 호출하지 않는다. 입력에서 얻은 특징으로 56개 후보 용법의 조건을 검사한다. 저장된 설계 연결은 실행 호출 순서가 아니다.[](source:reader)

@workflow id=runtime-flow title="현재 실행 경로의 큰 단계"
| lane analysis | 문장 읽기 |
| lane lookup | 조건과 전달 |
| lane generation | 문장 쓰기 |
| input | 표준어 입력 | external | analysis |
| kiwi | Kiwi 조각 관찰 | backend | analysis |
| qanalysis | Qwen 뜻 분석 | backend | analysis |
| binding | 코드로 연결 검사 | backend | lookup |
| lookup | 용법 조건 조회 | database | lookup |
| packet | 전달 내용 구성 | backend | lookup |
| generate | Qwen 전체 생성 | backend | generation |
| input > kiwi | |
| kiwi > qanalysis | 분석 단위 |
| qanalysis > binding | 특징·관계 |
| binding > lookup | 결속 결과 |
| lookup > packet | 후보·근거 |
| packet > generate | 생성 요청 |

조회기는 조건을 읽고, 전달 코드는 후보 형태·보존 지시·근거를 모은다. 마지막 문장 작성자는 Qwen이다. 설계의 동작 이름이 코드에 같은 이름의 함수로 구현됐다고 설명하면 안 된다.

## 사례 1: 조건문은 설계에서 실제 출력까지 어떻게 이어지나? {#conditional}

저장된 입력은 “시간이 나면 전화해.”이고, 출력은 “시간이 나모 전화해.”다. 

조건 용법 1개가 전달됐고 Qwen의 사용 선언에도 남아 있다. 이것은 한 실행의 경로 확인이며 일반적 품질 인증은 아니다.[](source:actual)

@architecture id=conditional-map title="조건 용법의 실제 저장 관계"
| concept | 조건 관계 설계 | database |
| rule | 조건 -모 후보 | database |
| conditions | 형태·기능 조건 | backend |
| forms | -모·-먼 등 | database |
| evidence | 문헌 위치 | external |
| rule > concept | 정제 대응 |
| rule > conditions | 조건 묶음 |
| rule > forms | 실현 후보 |
| rule > evidence | 근거 연결 |

| 단계 | 실제 정보 | 상태 |
| --- | --- | --- |
| 공통 설계 | G_END_CONDITIONAL: 앞 절과 뒤 절의 조건 관계 보존 | 설계 |
| 직접 연결 | INT_CONN_COND_MO가 REFINES로 위 항목을 가리킴 | 저장 확인 |
| 조건 | 원문 면/으면, 기능 조건, 연결어미 EC, 연결 단위 | 조회 구현 |
| 필수 관계 | 앞 서술어 U3, 뒤 서술어 U5 | 기록 확인 |
| 전달 | 나면 위치, 형태 후보, 조건 관계·시제·부정 보존 지시 | 패킷 확인 |
| 생성 | 시간이 나모 전화해. | 실제 출력 |

지역별 형태 차이는 후보와 설명에 들어 있지만, 이 용법의 조건 묶음에 지역을 강제하는 검사는 없다. “지역 조건까지 전부 구현됐다”는 설명은 범위를 넘는다.

## 사례 2: 여러 공통 항목이 하나의 질문 용법에 연결된다 {#question}

“너는 어느 버스를 타?”가 저장 실행에서 “니는 어느 버스를 타노?”로 생성됐다. 이때 2인칭 대명사 용법과 설명 의문 용법이 전달됐다.[](source:actual)

설명 의문 용법 SEM_Q_V_WH에는 G_Q_WH, G_MOOD_FUNCTION, G_HON_ADDRESSEE, G_END_FINAL의 직접 연결이 있다. 질문 기능·말높임·종결형을 함께 다룬다는 뜻이다. 네 설계 함수가 차례로 실행됐다는 뜻은 아니다.[](source:mapping)

과거 계사 질문 용법에는 G_TAM_PAST 연결도 있다. 여러 설계 항목이 한 용법에 관여하므로 56/136을 구현률로 계산할 수 없다.

## 사례 3: 출력이 좋아 보여도 KG 적용을 증명하지 못한다 {#request}

“창문 좀 닫아 주세요.”는 “창문 좀 닫아 주이소.”로 나왔다. 

그러나 저장 분석은 보조용언 기능을 none, 문맥 기능을 comitative로 기록했다. 요청 보조용언 용법의 조건을 충족하지 못했다.[](source:actual)

@workflow id=request-flow title="표현 변화와 KG 적용은 다른 증거"
| wrong | 분석 기능 불일치 | backend |
| absent | 해당 용법 미전달 | database |
| qwen | Qwen 문장 생성 | backend |
| output | 주이소 출력 | frontend |
| wrong > absent | 조건 불충족 |
| absent > qwen | 다른 참고 있음 |
| qwen > output | 생성 결과 |

이 실행의 조건 충족 용법 전달은 0개, 사용 선언도 0개다. 참고 문헌 항목은 12개 전달됐다. 따라서 완전히 지식 없는 생성이라고도 말하면 안 된다.

공통 G_AUX_BENEFACTIVE와 현재 INT_LEAD_REQUEST_JU_AUX는 개념상 관련 있지만 직접 연결이 없다. 이 관련성을 설명자의 해석으로 말할 수는 있어도, 이미 저장된 연결로 그리면 안 된다.

## 무엇까지 구현·검증됐다고 말할 수 있나? {#status}

| 확인 단계 | 이번에 확인한 것 | 아직 말할 수 없는 것 |
| --- | --- | --- |
| 설계 존재 | 136개 ID와 입력·조건·보존·출처 필드 | 표준어 전체 문법의 완전성 |
| 대응 관계 | 55개 직접 연결 | 공통 항목별 구현률 |
| 코드 동작 | 용법 조건 검사와 전달 구성 | 문법 조건의 언어학적 정당성 전체 |
| 저장 실행 | 입력·전달·출력을 연결한 사례 | 모든 용법의 품질과 일반화 |
| 별도 평가 | 이번에는 새 평가 없음 | 원문 전수 검증·지역 화자 평가 완료 |

현재 56개에는 변환 후보뿐 아니라 보존·차단 성격의 항목도 있다. “56개의 방언 변환이 모두 검증되어 사용 가능하다”는 문장은 피한다.[](source:mapping)

## 다른 사람에게 어떻게 설명하면 되는가? {#teach}

우리 연구는 표준어 문장을 방언으로 바꿀 때 뜻·시간·높임이 유지되는지를 확인한다. 이를 위해 무엇을 분석하고 보존할지 136개 공통 설계 항목으로 정리했다. 현재 후보 KG에는 조건을 검사해 Qwen에 전달하는 용법 56개가 있다.

두 목록은 일부만 명시적으로 연결되어 있고, 최종 문장은 Qwen이 작성한다. 저장된 실행 사례는 있지만, 전체 지식과 생성 품질의 검증은 별도 과제로 남아 있다.

- [ ] 136개를 표준 문법책의 규칙 수라고 소개하지 않는다.
- [ ] 직접 연결이 있는 사례와 연결이 없는 사례를 각각 설명한다.
- [ ] 조건을 통과한 후보와 Qwen의 실제 출력을 구별한다.
- [ ] 형식 검사와 원문 의미 검증·사람 평가를 구별한다.
'''

PAGE = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>공통 문법 136개와 실행 용법 56개 · 근거를 따라 읽기</title><style>
:root{color-scheme:light;--ink:#173044;--muted:#546676;--line:#d8e2e8;--blue:#0a6581;--paper:#f3f6f8;--gold:#fff4da}*{box-sizing:border-box}body{margin:0;background:var(--paper);font:17px/1.7 'Malgun Gothic',system-ui,sans-serif;color:var(--ink)}header{background:#173044;color:white;padding:36px max(24px,calc((100vw - 1200px)/2))}h1{font-size:32px;line-height:1.4;margin:8px 0 14px}h2{font-size:26px}h3{font-size:23px;margin:8px 0}h4{margin-bottom:8px}header p{max-width:1000px}nav{display:flex;gap:8px;flex-wrap:wrap;background:white;padding:12px 24px;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}button,select,input{font:inherit;border:1px solid #aebfc9;border-radius:8px;background:white;padding:8px 12px;color:var(--ink)}button{cursor:pointer}button.active,button:hover{background:var(--blue);color:white}main{max-width:1250px;margin:24px auto;padding:0 24px}.view[hidden],article[hidden]{display:none!important}.lead,.card,.panel{scroll-margin-top:95px;background:white;border:1px solid var(--line);border-radius:14px;padding:24px;margin:18px 0;overflow-wrap:anywhere}.lead{border-left:6px solid var(--blue)}.muted,small{color:var(--muted)}.eyebrow{font-size:14px;font-weight:bold;color:var(--blue)}.badges{display:flex;gap:7px;flex-wrap:wrap}.badges span{padding:3px 9px;border-radius:20px;background:#eaf2f5;font-size:13px}.example{font-size:22px;font-weight:bold;background:#eef7f8;padding:15px;border-left:4px solid #168b91}.observed{background:#edf5f1;padding:16px;margin:16px 0;border-radius:8px}.observed p{margin:8px 0}.tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:16px 0}.tools input{flex:1;min-width:220px}dl{display:grid;grid-template-columns:185px 1fr;gap:8px 18px}dt{font-weight:bold}dd{margin:0;padding-bottom:12px;border-bottom:1px solid #edf0f2}.jump{padding:3px 8px;font-size:15px;text-align:left}code{font-size:12px;word-break:break-all;color:#625777}table{width:100%;border-collapse:collapse;font-size:15px;margin:12px 0}td,th{border-bottom:1px solid var(--line);padding:12px;text-align:left;vertical-align:top}th{background:#f1f5f7}details{border-top:1px solid var(--line);padding-top:12px;margin-top:18px}summary{cursor:pointer;color:var(--blue)}iframe{width:100%;height:1250px;border:1px solid var(--line);border-radius:12px;background:white}a{color:#056383}.callout{background:var(--gold);border-radius:8px;padding:15px}.path{font-size:12px}footer{padding:24px;text-align:center;color:var(--muted)}@media(max-width:700px){body{font-size:16px}header{padding:22px}h1{font-size:26px}main{padding:0 12px}.card,.panel,.lead{padding:18px}dl{display:block}dt{margin-top:12px}nav{position:static;padding:10px}.tools>*{width:100%}table{font-size:13px}td,th{padding:8px}iframe{height:1100px}.example{font-size:19px}}
</style><header><div>연구 이해 자료 · 2026-11-07 · Archify 시각 설명 포함</div><h1>136개의 공통 설계가<br>56개의 후보 용법으로 이어지는 방식</h1><p>‘문장을 이해할 때 구별해야 할 것’과 ‘지금 프로그램이 조건을 검사해 전달하는 것’을 구분해서 읽습니다. 문헌 근거 → 설계 항목 → 실제 연결 → 저장된 실행을 따라갑니다.</p></header><nav aria-label="읽기 순서"><button data-view="overview" class="active">① 전체 그림</button><button data-view="walk">② 실제 사례 3개</button><button data-view="common">③ 공통 136개 하나씩</button><button data-view="rules">④ 용법 56개와 연결</button><button data-view="basis">⑤ 근거·판정 기준</button></nav><main>
<section class="view" id="overview"><div class="lead"><strong>먼저 기억할 문장</strong><p>136개는 세부 책임 125개와 묶음 창구 11개입니다. 56개는 별도로 조건 조회가 구현된 후보 용법입니다. 현재 직접 연결은 공통 29개 ↔ 용법 29개, 총 55개입니다. 연결이 없다고 미구현이라고 단정하거나 56/136을 구현률로 쓰면 안 됩니다.</p><a href="overview.html" target="_blank">Archify 설명을 넓은 화면에서 열기 ↗</a></div><iframe src="overview.html" title="Archify 공통 문법과 후보 용법 시각 설명"></iframe></section>
<section class="view" id="walk" hidden><h2>먼저 이 세 사례로 차이를 익히기</h2><article class="panel"><h3>1. 조건문: 설계와 실행이 연결된 사례</h3><p class="example">시간이 나면 전화해. → 시간이 나모 전화해.</p><p>‘나면’의 <b>면</b>은 두 절을 조건으로 연결합니다. 공통 설계는 조건 관계를 보존하라고 정합니다. 실행 용법은 ‘면/으면’, 조건 기능, 연결어미 품사, 연결 단위라는 조건을 검사합니다. 앞·뒤 서술어 관계까지 들어 있으면 후보 형태와 보존 지시를 Qwen에 보냅니다.</p><p>실제 IG019에서는 용법 1개가 전달됐습니다. 형태를 선택해 전체 문장을 쓴 주체는 Qwen입니다. 공통 설계 자체가 문자열을 직접 고친 것이 아닙니다.</p><button class="jump" data-target="G_END_CONDITIONAL">공통 조건 설계 읽기</button> <button class="jump" data-target="INT_CONN_COND_MO">실제 용법의 모든 조건 읽기</button><p class="callout">지역별 후보가 기록돼 있지만, 이 용법의 조회 조건에는 지역 필터가 없습니다. 문헌 설명이 저장됐다는 사실과 해당 제한을 코드가 강제한다는 사실을 구분해야 합니다.</p></article><article class="panel"><h3>2. 질문: 여러 공통 항목이 하나의 용법에 연결</h3><p class="example">너는 어느 버스를 타? → 니는 어느 버스를 타노?</p><p>대명사 용법과 설명 의문 용법이 각각 전달됐습니다. 설명 의문 용법에는 질문 기능, 발화 기능, 말높임, 종결형의 공통 설계가 연결됩니다. 한 문장에 여러 용법, 한 용법에 여러 설계가 관여하므로 일대일 계산이 되지 않습니다.</p><button class="jump" data-target="G_Q_WH">설명 의문 설계</button> <button class="jump" data-target="SEM_Q_V_WH">설명 의문 용법</button> <button class="jump" data-target="INT_NOM_P2_NI">2인칭 용법</button></article><article class="panel"><h3>3. 요청: 출력 변화만으로 KG 사용을 입증할 수 없음</h3><p class="example">창문 좀 닫아 주세요. → 창문 좀 닫아 주이소.</p><p>저장된 분석은 보조용언 기능을 ‘없음’, 문맥 기능을 ‘동반’으로 잘못 분류했습니다. 이 요청 용법은 조건을 통과하지 못했습니다. 조건 충족 용법 전달은 0개, Qwen 사용 선언도 0개였습니다. 다만 참고 문헌 항목 12개는 전달됐습니다.</p><p>따라서 ‘주이소가 나왔으니 요청 KG 규칙이 작동했다’고 해석하면 안 됩니다. 또한 수혜 보조구성 공통 항목과 해당 실행 용법의 직접 연결도 없습니다.</p><button class="jump" data-target="G_AUX_BENEFACTIVE">관련 공통 설계</button> <button class="jump" data-target="INT_LEAD_REQUEST_JU_AUX">요청 보조용언 용법</button></article><details class="panel"><summary>이 설명에 연결한 저장 실행 원문·출력</summary><p>20261106T060407624135Z_integrated_grammar_repair. 반복 진단 자료이며 독립 최종 평가가 아닙니다.</p><div style="overflow-x:auto"><table><tr><th>ID</th><th>입력</th><th>출력</th><th>실제 전달 용법</th></tr>@@CASES@@</table></div></details></section>
<section class="view" id="common" hidden><h2>공통 문법 136개를 하나씩 읽기</h2><p>모든 항목에 설명용 예문, 구별 이유, 저장된 판단·차단·출력 정보, 근거 위치와 직접 연결을 붙였습니다. <b>설명용 예문은 실행 결과가 아닙니다.</b> 실제 기록이 있는 경우에는 녹색 상자로 별도 표시합니다.</p><div class="tools"><input id="common-search" aria-label="공통 항목 검색" placeholder="예: 조건, 과거, 높임, G_TAM_PAST"><select id="module-filter" aria-label="분야 선택"><option value="">전체 12분야</option>@@OPTIONS@@</select><select id="common-link" aria-label="연결 여부"><option value="">모든 연결 상태</option><option value="1">직접 연결 있음</option><option value="0">직접 연결 없음</option></select></div><p id="common-count" aria-live="polite"></p><div id="common-cards">@@COMMON@@</div></section>
<section class="view" id="rules" hidden><h2>56개 후보 용법에서 거꾸로 따라가기</h2><p>모든 조건을 한국어로 풀어 보여줍니다. ‘조건 조회 구현’은 해당 형태가 모든 문맥에서 올바르다는 뜻이 아닙니다. <b>공통 설계와의 연결이 없는 27개 용법도 조건 조회 자체는 존재합니다.</b></p><div class="tools"><input id="rules-search" aria-label="용법 검색" placeholder="예: -모, 주이소, 설명 의문"><select id="rules-link" aria-label="용법 연결 여부"><option value="">모든 연결 상태</option><option value="1">공통 설계 연결 있음</option><option value="0">공통 설계 연결 없음</option></select></div><p id="rules-count" aria-live="polite"></p><div id="rule-cards">@@RULES@@</div></section>
<section class="view" id="basis" hidden><h2>무엇을 근거로, 어디까지 말할 수 있나?</h2><article class="panel"><h3>136개가 만들어진 근거와 한계</h3><p>2026-10-14 설계 기록은 방언 자료의 구별을 공통 분석·보존 계약으로 정리했습니다. 설계 문서는 별도의 공통 한국어 문법책 전체가 제공되지 않았다고 명시합니다. 따라서 특정 교과서 목차의 복제나 한국어 문법 전영역의 완전성은 주장하지 않습니다.</p><p>문헌은 언어 현상의 근거이고, 이를 136개 항목으로 나눈 방식은 설계 판단입니다. 기록된 AI 검토 합의는 언어학적 사실 인증이 아닙니다. 이번 작업에서도 각 원문 페이지를 새로 전수 의미 검증하지 않았습니다.</p><p>136개 중 121개에 문헌 위치 목록이 있고 15개에는 없습니다. 후자의 11개는 묶음 창구입니다. 쪽수 목록은 출처 추적의 출발점이며, 그 페이지가 해당 계약의 모든 내용을 입증한다는 판정이 아닙니다.</p><table><tr><th>자료</th><th>서지 기록</th><th>범위·주의점</th></tr>@@SOURCES@@</table></article><article class="panel"><h3>구현 상태를 설명하는 다섯 단계</h3><table><tr><th>단계</th><th>확인할 증거</th><th>이번 설명의 범위</th></tr><tr><td>설계됨</td><td>ID와 입력·조건·보존 계약</td><td>136개 전부 확인</td></tr><tr><td>코드가 읽음</td><td>조건 판정·전달 코드</td><td>후보 56개, 조건 묶음 57개</td></tr><tr><td>실제 도달함</td><td>입력별 조회·패킷 기록</td><td>과거 통합 실행 4개에서 찾은 사례를 제시</td></tr><tr><td>올바르게 생성함</td><td>출력의 뜻·높임·자연스러움 평가</td><td>이번에는 독립 평가를 수행하지 않음</td></tr><tr><td>범위 전체에서 검증됨</td><td>원문 대조·조건별 예문·사람 판정</td><td>향후 전수 검증 과제</td></tr></table><p>REFINES는 용법에서 공통 설계로 향하는 정제 대응 23개입니다. DESCRIBES_USAGE는 공통 설계에서 용법으로 향하는 설명 연결 32개입니다. 합계 55개이며, 서로 다른 공통 항목 29개와 용법 29개에 닿습니다.</p><p>직접 연결이 없는 공통 항목 107개에는 부분적으로 구현된 관련 책임이 있을 수 있습니다. 이번에는 그 전체를 항목별 코드 구현률로 판정하지 않았습니다.</p></article><article class="panel"><h3>다음에 확인할 것</h3><p>우선 조건문·질문·요청 사례를 자신의 말로 설명한 뒤, 분야별 공통 항목을 읽으면서 의미가 모호한 항목을 표시합니다. 그 다음에는 직접 연결의 타당성과 누락을 대조하고, 각 실행 분기의 적용·비적용·미확정 예문을 실제 파이프라인에 통과시켜 기록해야 합니다.</p><p>설계와 실행의 직접 대응이 부적절하면 원문 근거를 확인한 뒤 새 판본에서 고칩니다. 연결만 추가해서 의미 검증 완료로 처리하지 않습니다. 이미 읽은 136개를 모두 실행한 것으로도 처리하지 않습니다.</p><p>이번 자료는 KG·실행 코드를 변경하지 않았고 새 Qwen 호출도 없습니다. 검토용 산출물을 완성했으며 새 실험 시작이나 범위 변경에 대한 판단은 요청하지 않습니다.</p></article><details class="panel"><summary>재현 기록과 파일</summary><p>분석 ID: @@STAMP@@</p><p><a href="manifest.json">입력 파일·기록 해시와 한계</a> · <a href="mapping.json">기계 검증용 전체 연결 대장</a> · <a href="candidate.archify.md">Archify 설명 원고</a></p><p>기계 기록은 재현용입니다. 위의 설명 화면을 대신하는 자료가 아닙니다. 생성된 원문·출력 포함 자료는 private 폴더에 보존하며 원격에 게시하지 않습니다.</p></details></section></main><footer>기존 연구 기록을 읽어 만든 설명 자료 · 설계와 품질 검증을 구별합니다.</footer><script>
const views=[...document.querySelectorAll('.view')];function show(id){views.forEach(v=>v.hidden=v.id!==id);document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===id));}document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{show(b.dataset.view);window.scrollTo({top:0});});
function filter(kind){let isCommon=kind==='common',q=document.getElementById(kind+'-search').value.toLowerCase(),link=document.getElementById(kind+'-link').value,module=isCommon?document.getElementById('module-filter').value:'';let cards=[...document.querySelectorAll(isCommon?'#common-cards .card':'#rule-cards .card')],n=0;cards.forEach(c=>{c.hidden=!(c.textContent.toLowerCase().includes(q)&&(!link||c.dataset.linked===link)&&(!module||c.dataset.module===module));if(!c.hidden)n++;});document.getElementById(kind+'-count').textContent=n+' / '+cards.length+'개 표시';}
['common','rules'].forEach(k=>{document.getElementById(k+'-search').oninput=()=>filter(k);document.getElementById(k+'-link').onchange=()=>filter(k);filter(k);});document.getElementById('module-filter').onchange=()=>filter('common');
function jump(id){const c=document.getElementById(id);if(!c)return;const kind=id.startsWith('G_')?'common':'rules';show(kind);document.getElementById(kind+'-search').value='';document.getElementById(kind+'-link').value='';if(kind==='common')document.getElementById('module-filter').value='';filter(kind);c.scrollIntoView({behavior:'smooth',block:'start'});history.replaceState(null,'','#'+id);c.animate([{boxShadow:'0 0 0 4px #48b9ba'},{boxShadow:'none'}],{duration:1600});}document.querySelectorAll('.jump').forEach(b=>b.onclick=()=>jump(b.dataset.target));if(location.hash)jump(decodeURIComponent(location.hash.slice(1)));
</script></html>'''

if __name__=='__main__':build()
