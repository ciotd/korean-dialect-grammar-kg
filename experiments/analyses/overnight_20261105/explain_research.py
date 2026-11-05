"""Read-only evidence join and a plain-language guide; no model/KG mutations."""
from pathlib import Path
import collections, datetime, hashlib, html, json

H = Path(__file__).resolve().parent
R = H.parents[2]
OUT = H / 'private'
RUN = R / 'experiments/runs/20261104T152433297395Z_past_copula_paired_regression'
REF = R / 'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl'
FILES = {}

def read(p):
    raw = p.read_bytes(); FILES[str(p.relative_to(R))] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

def esc(x): return html.escape(str(x))

TERMS = {
 'clause_role':'절의 역할', 'speech_act':'말하는 목적', 'addressee_level':'듣는 사람에 대한 높임',
 'question_kind':'질문 종류', 'predicate_class':'서술어 종류', 'prefinal_type':'어미 앞의 시제 등 형태',
 'prefinal_sequence':'시제·높임 형태의 순서', 'tense':'시간 의미', 'subject_honorific':'주체 높임',
 'polarity':'긍정·부정', 'source_final':'입력의 종결어미', 'nominal_kind':'명사 부분의 종류',
 'main':'주절', 'embedded':'안긴절', 'quoted':'인용절', 'information_question':'정보를 묻는 질문',
 'statement':'평서', 'request':'요청·명령', 'rhetorical_question':'반어 질문', 'confirmation':'확인',
 'suggestion':'제안', 'exclamation':'감탄', 'self_question':'혼잣말 질문', 'plain':'반말', 'polite':'공손',
 'polar':'예/아니오 질문', 'wh':'무엇·어디 등 구체적인 답을 묻는 질문', 'verb':'동사', 'adjective':'형용사',
 'copula':'이다', 'negative_copula':'아니다', 'none':'해당 형태 없음', 'eoss':'-었- 계열',
 'si':'-시-', 'si_eoss':'-시- 뒤 -었-', 'gess':'-겠-', 'deo':'-더-', 'other':'현재 분류의 다른 형태',
 'past':'과거', 'present':'현재', 'future':'미래', 'absent':'없음', 'positive':'긍정', 'negative':'부정',
 'lexical_nominal':'일반 명사류', 'bound_nominal':'의존명사', 'not_nominal':'명사 구성이 아님', 'unknown':'미확정',
 'title':'이름', 'origin':'가져온 곳·작성 방식', 'feature':'판정할 특징', 'value':'특징값', 'allowed':'허용 값',
 'operator':'판정 연산', 'basis':'설정 근거의 성격', 'basis_explanation':'근거 설명', 'scope':'적용 범위',
 'status':'기록 상태', 'summary':'용법 설명', 'meaning':'의미', 'preserve':'보존할 정보', 'target':'적용 대상',
 'limits':'해석 범위', 'generation_operation':'생성 작업 종류', 'form':'실현 형태', 'unit':'적용 단위',
 'composition':'조합 설명', 'allomorphs':'다른 결합 형태', 'includes_copula':'계사 포함 여부',
 'operation':'처리 설명', 'surface_postcondition':'출력에서 확인할 형태', 'choice_policy':'후보 선택 방침',
 'document_id':'문헌 ID', 'pdf_page':'PDF 쪽', 'page_system':'쪽수 기준', 'quote':'저장된 원문 발췌',
 'builder_paraphrase':'연구자가 풀어쓴 해석', 'evidence_kind':'근거 종류', 'access':'원문 확인 수준',
 'source_family':'재인용·자료 계통', 'source_scope':'자료의 지역·시기 범위', 'start':'시작 위치', 'end':'끝 위치',
 'page_text_sha256':'쪽 본문 검증값', 'source_pdf_sha256':'PDF 검증값', 'reason':'이유', 'linguistic_fact':'문헌 사실 여부',
 'code_reference':'관련 구현', 'excluded':'이번 범위에서 제외한 것', 'deferred':'후속 확인할 것',
 'user_reference_role':'사용자 참조의 역할', 'runtime_active':'실행 사용 여부', 'alternatives':'다른 후보',
 'direct_attestation_search':'직접 용례 탐색 상태', 'legacy_card_conflict':'기존 카드와의 차이',
 'evidence_ids':'근거 연결 ID', 'primary_evidence_ids':'주 근거 ID', 'supporting_evidence_ids':'보조 근거 ID',
 'delivery_evidence_ids':'생성에 전달할 근거 ID', 'interpretation_evidence_ids':'해석 근거 ID',
 'decision_ids':'구현 결정 ID', 'decision_id':'구현 결정 ID', 'evidence_role':'근거의 역할',
 'realization_basis':'실현형 선택 근거', 'field_basis':'조건별 설정 근거', 'related_rule_ids':'관련 규칙 ID',
 'applies_to_lemmas':'적용 어휘', 'inherited_identity_only':'기존 이름·식별자만 계승',
 'same_clause':'같은 절 안에서 판정', 'in':'허용 목록에 속하는지 판정',
 'source_interpretation':'문헌을 읽고 정리한 해석', 'implementation_scope':'현재 구현 범위',
 'implementation_scope_not_linguistic_prohibition':'실험에서 지원하는 범위이며 다른 표현을 문법적으로 금지하지 않음',
 'ready_for_generation_trial':'규칙을 생성 단계에 전달함', 'out_of_slice':'현재 구현한 문법 구성의 범위 밖',
 'no_matching_usage':'관련 구성은 있지만 맞는 세부 규칙 없음', 'needs_analysis':'분석 미확정으로 전달 보류',
 'boundary_relation_unresolved':'문장 부분 사이의 연결을 확정하지 못함', 'eligible':'조건에 맞는 후보를 찾음',
 'true':'조건 충족', 'false':'조건 불일치', 'lexical_meaning':'어휘 의미', 'argument_roles':'누가 무엇을 하는지',
 'source_condition_and_examples_not_heldout_translation_gold':'문헌 조건·용례에 기반하며 독립 번역 정답은 아님',
}
TYPE = {
 'Framework':('전체 틀','공통 척추를 가리키는 출발점입니다.'),
 'Module':('문법 분야','동사·높임·절 등 큰 분류입니다. 분류가 있다고 그 분야가 구현된 것은 아닙니다.'),
 'AnalysisConcept':('분석 개념','종결어미 등 입력을 이해하는 데 쓰는 개념의 이름입니다.'),
 'GrammarFeature':('문법 특징 개념','질문·높임 같은 개념 연결용 노드입니다.'),
 'SourceAtom':('기존 문헌 항목','예전 KG 항목과의 연결 주소입니다. 이 버전에서는 이름만 계승한 항목도 있습니다.'),
 'GrammarConstruction':('문법 구성','예를 들어 반말 정보 질문처럼 함께 처리할 용법 묶음입니다.'),
 'ProcessingScope':('현재 지원 범위','이 구성으로 지금 처리할 문장 범위를 정합니다.'),
 'SemanticRule':('용법 규칙','조건에 맞을 때 어떤 어미·구성을 후보로 제시할지 설명합니다.'),
 'ApplicabilityBranch':('조건 묶음','하나의 규칙이 성립하는 방법입니다. 다른 묶음 중 하나가 맞으면 되고, 묶음 안 조건은 모두 맞아야 합니다.'),
 'Condition':('개별 조건','예를 들어 질문 종류가 구체적인 답을 묻는 질문인지 확인합니다.'),
 'FeatureValue':('조건이 받아들이는 값','동사·과거·반말처럼 분석 결과와 맞춰 보는 값입니다.'),
 'Realization':('실현 방법','어떤 어미를 어떤 부분 뒤에 붙일지 기록합니다. 완성 문장을 저장하는 것은 아닙니다.'),
 'Evidence':('문헌 근거','원문 발췌·쪽수·자료 계통·연구자 해석을 구별하여 기록합니다.'),
 'ImplementationDecision':('구현 결정','문헌 사실과 별도로 이번 실험의 지원 범위나 분석기 대응을 정한 이유입니다.'),
 'UsageObservation':('참고 용례·변이','관련 표현을 보존하지만 현재 실행 규칙으로 쓰지 않는 기록도 포함합니다.'),
 'ResearchCandidate':('후속 연구 후보','아직 적용하지 않거나 별도 후보로 검토할 항목입니다.'),
}
REL = {'HAS_MODULE':'큰 문법 분야로 나뉨','IN_MODULE':'이 문법 분야에 속함','HAS_USAGE':'이 용법 규칙을 포함함',
 'SUPPORTED_IN':'현재 지원 범위를 지정함','ANY_BRANCH':'이 조건 묶음들 중 하나가 맞아야 함','ALL':'묶음 안에서 모두 만족해야 함',
 'ACCEPTS':'이 특징값을 받아들임','REALIZES':'이 형태·조합법으로 실현함','SUPPORTED_BY':'이 문헌을 근거로 연결함',
 'INTERPRETS_SOURCE':'이 문헌을 이렇게 해석함','DEFINED_BY_DECISION':'이 구현 결정으로 정함','DEFINED_BY':'정의 연결',
 'REFINES':'기존 항목을 정제함','DESCRIBES_USAGE':'용법을 설명함','HAS_CONTEXT_NOTE':'참고 관찰을 연결함',
 'EVIDENCE_ROLE':'근거의 역할을 구분함','HAS_CONTEXT_EVIDENCE':'직접 적용 허가와 다른 문맥 근거',
 'PRESERVATION_SUPPORTED_BY':'보존할 특징의 근거','PRESERVATION_LIMITED_BY':'보존 해석의 한계 근거',
 'HAS_RECORDED_VARIANT':'다른 관찰 형태를 보존함','CONTRASTS_WITH':'차이를 비교함','RELATED_COMPONENT':'관련 문법 요소',
 'REFINES_CANDIDATE':'기존 후보를 정제함'}

def word(x):
    if x is None: return '미확정 / 값 없음'
    if isinstance(x,bool): return '예' if x else '아니오'
    return TERMS.get(str(x), str(x))

def feature_word(k, v):
    if k == 'subject_honorific' and v == 'present': return '주체를 높임'
    return word(v)

def pretty(x):
    if isinstance(x,dict):
        return '<dl>'+''.join(f'<dt>{esc(TERMS.get(k,k))} <small>({esc(k)})</small></dt><dd>{esc(feature_word(k,v)) if k=="subject_honorific" and not isinstance(v,(list,dict)) else pretty(v)}</dd>' for k,v in x.items())+'</dl>'
    if isinstance(x,list): return '<ul>'+''.join('<li>'+pretty(v)+'</li>' for v in x)+'</ul>' if x else '목록 없음'
    return esc(word(x))

def table(head,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def para(x): return '<p>'+x+'</p>'

CASES = {
 'DEV012':('과거 정보는 전달됐지만 출력에서 빠졌습니다.',
 '실제 요청에는 어간 두, 과거 형태 었, 바꿀 어미 노와 “과거를 보존한다”는 지시가 함께 있었습니다. 분석이 과거를 현재로 잘못 판단한 사례도, 과거 정보를 보내지 않은 사례도 아닙니다. Qwen의 원시 출력이 두노였습니다.',
 '확정할 수 있는 것은 생성 단계에서 과거 형태를 반영하지 못했다는 점입니다. 왜 모델 내부에서 그 선택을 했는지는 기록만으로 알 수 없습니다. “두+었+노를 조합하기 어려웠다” 또는 “어간+노만 따라 썼다”는 설명은 가설입니다.',
 '현재 정보와 수정 정보를 같은 문장들에 전달해 과거 형태의 결합을 비교하고, 두다 외의 동사에도 같은 현상이 생기는지 확인합니다. 과거형이 사라진 출력을 잡는 검사도 의문문까지 넓힙니다.'),
 'DEV017':('요청을 처리하는 실행용 규칙이 아직 연결되지 않았습니다.',
 '분석은 “공손한 요청”으로 나왔습니다. 하지만 이번 실행용 그래프에는 질문·공손 평서·일부 계사만 있습니다. 이 입력에 전달한 변환 지시는 0개이고, 생성 지시문은 지시가 없으면 원문을 유지하도록 되어 있었습니다.',
 '기존 큰 KG에는 명령의 -이소·-시소 항목(GS_ENDRULE_ISO_IMP, D02 PDF154)이 있습니다. 따라서 자료에 관련 지식이 전혀 없다고 설명하면 틀립니다. 그 지식을 요청·보조용언 주다·높임 조건과 결합해 현재 실행 그래프로 옮기는 작업이 남았습니다. 이번 확인만으로 주이소라는 완성형의 직접 문헌 용례를 확정하지는 않습니다.',
 '주세요를 무조건 문자열 치환하지 않고, 해 주다의 요청인지·주다의 다른 쓰임인지 구분한 요청 구성으로 연결합니다. 같은 높임의 다른 동사·부정 요청과 함께 검사합니다.'),
 'DEV020':('금지 표현을 바꾸는 실행용 규칙이 없습니다.',
 '분석은 요청·반말·부정이고, 말다라는 보조용언도 기록돼 있습니다. 그러나 금지 구성을 선택할 규칙이 없어 변환 지시가 0개였습니다. 이번 생성 정책에 따라 원문이 남았습니다.',
 '기존 KG에는 -지 말다 항목(GS_HAM_NEG_MAL, D07 PDF22)이 있습니다. 예전 진단의 “표준어와 공유하는 형태 가능”이라는 설명은 원문 유지가 언어적으로 허용될 가능성을 뜻할 뿐, 실제로 왜 변환되지 않았는지 설명하는 실행 원인은 아닙니다. 실제 원인은 미구현과 원문 유지 지시입니다. 마라로 달라지는 것만으로 자연스러운 방언이라는 검증을 대신할 수는 없습니다.',
 '금지의 의미·듣는 사람 높임·말다의 활용을 묶어, 사용자가 제안한 마라를 후보로 검토합니다. 하지 마·하지 마세요·다른 부정 표현을 서로 섞지 않는 검사도 필요합니다.'),
 'DEV026':('규칙은 찾았지만 전달 전에 막혔습니다.',
 '나왔어요는 과거·공손 평서로 분석됐고 -어요를 -어예로 실현하는 규칙의 조건도 맞았습니다. 그런데 앞의 늦을까가 봐와 어떻게 연결되는지 모델이 미확정으로 답했습니다. 현재 코드는 이 미확정을 전체 변환 준비 상태에 반영하여 나왔어요에 대한 지시도 보내지 않았습니다.',
 '아니었어요가 바뀐 사례와 달리, 이 문장은 생성 모델이 예체를 거절한 것이 아닙니다. 받을 규칙이 전달되지 않았습니다. 다만 앞부분의 모든 미확정을 무조건 무시하는 것은 다른 문장에서 부정·높임·인용 범위를 잘못 연결할 수 있습니다.',
 '미확정 경계가 어느 규칙의 판단에 영향을 주는지 추적합니다. 나왔어요의 시제·높임·문장 기능에 영향이 없음을 확인한 경우만 해당 위치를 허용하고, 영향이 있는 반례에서는 계속 보류하는 방식으로 비교합니다.'),
 'LONG001':('어디를 어이로 바꾸라는 지식은 전달하지 않았습니다.',
 '첫 질문의 요청에는 명사 부분 어디, 계사 이, 종결형 고가 있었습니다. 어데라는 어휘 치환도 보내지 않았습니다. Qwen이 어이고로 쓰면서 원문 어디의 디를 잃었습니다. 두 번째 질문에도 어간 오와 어미 노를 보냈지만 안 노로 출력해 오를 잃었습니다. 마지막 있을게는 약속 규칙이 없어 그대로 남았습니다.',
 '한편 -고에 includes_copula=true라는 표시와 “계사 이형태를 포함해 조합”이라는 설명이 함께 있습니다. 명사 뒤에 어떤 조각을 남기고 어떤 조각을 붙일지 더 명확히 해야 합니다. 이 모호함이 디 탈락을 유발했다는 인과관계까지 확인한 것은 아닙니다.',
 '명사 부분 보존과 계사·어미 조합을 분리하여 설명하고, 모음·받침으로 끝나는 다른 명사 및 현재·과거 질문에서 비교합니다. 어디→어데는 어휘 변환으로 별도 다룹니다. 단일 변경과 여러 변경을 같은 조건에서 비교해 복수 지시의 영향도 확인합니다.'),
}

COVERAGE = [
 ('동사','반말 정보 질문과 일부 공손 종결에서 동사 특징을 사용합니다.','반말 평서·명령·약속·동사별 활용 전체는 미완료.','F01·F03·F04·F05·F07'),
 ('형용사·계사','형용사는 질문/공손 종결의 일부 조건에 포함됩니다. 현재 긍정 계사와 과거 긍정·부정 계사 후보가 있습니다.','형용사별 활용·모든 높임/질문/시제 계사 조합은 미완료.','F02·F03·F04'),
 ('명사류','명사·의존명사·명사 아닌 구성을 구별하고 계사 조합에 사용합니다.','명사 자체 변환, 대명사·수사·셈 단위 전체는 실행 연결 대기.','F11·F12'),
 ('조사','이전 큰 KG와 전체 작업지도에 항목이 있습니다.','현재 12개 실행 규칙에는 조사 전용 변환이 없습니다.','F09·F10'),
 ('어미·종결','반말 질문 6용법, 공손 평서 3용법, 현재 계사 1, 공손 질문 1, 과거 계사 후보 1이 있습니다.','반말 평서·요청·금지·청유·약속·확인/감탄 전체 체계는 미완료.','F03~F07'),
 ('높임','듣는 사람 높임과 주체 높임을 구별하고 일부 시 형태를 보존합니다.','요청의 세요 분석, 객체 높임·특수 어휘·지역별 화계 대응 전체는 미완료.','F08'),
 ('절 연결','Qwen이 연결·보조용언·인용 등의 경계를 분석하는 코드가 있습니다.','연결어미의 방언화와 모든 절 경계 처리는 미완료. 늦을까 봐에서 차단 사례 확인.','F13~F17'),
 ('시제·상·양태·부정','과거 여부·었/시었 형태열과 긍정/부정을 일부 규칙의 조건·보존값으로 사용합니다.','진행/완료상, 겠/더의 의미별 변환, 안/못/말다·금지 전체 체계는 미완료.','F07·F18·F19'),
 ('사동·피동·보조용언','보조용언 경계와 끝 서술어를 묶는 분석 코드가 일부 있습니다.','사동·피동 변환 규칙, 보조용언 의미별 방언 대응은 미완료. 계세요 오분석도 남음.','F20·F21'),
 ('어휘','문헌 어휘 항목과 승인 참조를 대조하는 자료가 있습니다.','현재 실행 그래프에는 먹다→묵다·어디→어데 같은 일반 어휘 치환 체계가 없습니다.','F11·F22'),
 ('형태음운·표기','Kiwi 관측과 보조 조합기 비교를 수행했습니다. 최종 활용은 Qwen이 만듭니다.','축약·불규칙·관습 표기 전체를 정제하지 않았고, 어간/과거 탈락이 남습니다.','F01·F23'),
 ('지역·변이·실행 관리','근거의 자료 계통·범위, 후보/운영 버전, 실행 기록을 보존합니다.','현대 화자 적합성·변이 선택·독립 품질 평가는 미완료.','F24·F25'),
]

def build():
    OUT.mkdir(exist_ok=True)
    for name in ['guide.css','guide.js']:
        (OUT/name).write_bytes((H/name).read_bytes())
    g = read(RUN/'private/graph_r10.json'); base=read(RUN/'private/graph_r7.json')
    nodes={n['id']:n for n in g['nodes']}; results=read(RUN/'private/results.json')
    FILES[str(REF.relative_to(R))]=hashlib.sha256(REF.read_bytes()).hexdigest()
    refs={x['id']:x for x in map(json.loads,REF.read_text('utf8').splitlines())}
    results={x['source_id']:x for x in results if x['arm']=='r10'}
    assert len(results)==len(refs)==50
    pages=[]; joined=[]
    def name(i): return nodes.get(i,{}).get('properties',{}).get('title', i)
    def node_link(i): return f'<a href="#node-{esc(i)}">{esc(name(i))}</a> <small>{esc(i)}</small>'
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
    pages.append('''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>KG 연구 길잡이 · 문법 확장과 50문장 처리 기록</title><link rel="stylesheet" href="guide.css"><script src="guide.js" defer></script></head><body><main><header><p>처음 읽는 연구자를 위한 설명</p><h1>문법 지식은 어디까지 만들었고,<br>문장은 왜 아직 잘못 바뀔까요?</h1>''')
    pages.append(para('이 문서는 연구의 시작, 현재 그래프의 내용, 실제 50문장의 처리 과정을 순서대로 설명합니다. 새 번역 실험이 아니라 저장된 기록을 다시 읽어 정리한 문서입니다.'))
    pages.append(para(esc(now)+' · 비교 대상: 11월 5일 과거 계사 후보를 사용한 기존 50문장 실행'))
    pages.append('</header><nav><a href="#story">연구의 흐름</a><a href="#versions">버전 이름</a><a href="#coverage">문법 확장 현황</a><a href="#structure">그래프 이해</a><a href="#questions">질문한 5사례</a><a href="#cases">전체 50문장</a><a href="#next">다음 계획</a><a href="#dictionary">용어·세부 자료</a></nav>')
    pages.append('<section id="story"><h2>1. 처음 목표와 지금까지 한 일</h2>')
    pages.append(para('목표는 표준어 문장의 뜻·시간·높임을 유지하면서 경상도 방언으로 바꾸는 것입니다. 문헌에서 문법 지식을 읽고, 언제 어떤 표현을 쓸 수 있는지 그래프로 연결한 뒤, 입력에 맞는 정보만 Qwen에 전달합니다. 마지막 문장은 Qwen이 작성합니다.'))
    pages.append(para('처음의 공통 척추와 12개 문법 모듈은 전체 문법을 정리할 지도였습니다. 문헌 내용을 저장하고 Neo4j에서 연결을 보는 작업도 했습니다. 그러나 지식이 저장돼 있다는 것과 실제 문장 조건에 맞춰 찾아서 활용할 수 있다는 것은 달랐습니다. 초기에는 적용 코드가 붙은 지식이 적었고, 이후에는 큰 분류의 카드를 너무 넓게 가져오는 문제가 있었습니다.'))
    pages.append(para('그래서 문헌의 의미를 다시 읽고, 조건·용법·실현 방법을 분리해 실제 관계로 좁혀 찾는 작은 실행용 그래프를 만들었습니다. 의문문에서 시작해 일부 공손 평서·계사 표현으로 넓혔습니다. 이 과정에서 분석 오류, 전달 차단, 형태 조합 실패가 서로 다른 문제임을 확인했습니다. 지금의 작은 그래프가 원래 계획한 전체 문법 체계를 대신 완성한 것은 아닙니다.'))
    pages.append(table(['기록 시기','실제 작업','남은 문제'],[
        ['초기 설계~10월','7종 문헌과 19개 설계 보고서를 바탕으로 큰 KG 저장·시각화','저장 항목 전체가 실행 가능한 문법 규칙은 아니었음'],
        ['10월24~25일','일부 항목에 17개 적용 코드를 연결하고 검색 범위를 넓힘','좁은 적용 코드와 넓은 문헌 검색 사이의 간극'],
        ['10월28~30일','카드 정리, 단일/다중 역할, 참조 번역과 실패 경로 대조','카드 수·전달 문구를 바꾸는 것만으로 해결되지 않음'],
        ['11월2일','전체 문헌·기존 항목의 작업지도와 의문문 조건 그래프 작성','전체 의미 정제는 끝나지 않음'],
        ['11월3일','Kiwi·Qwen 분석 연결, 일부 공손 평서·높임·절 처리 보완','분석·조합·경계 판정의 실패가 남음'],
        ['11월4일','현재 계사/공손 질문 확장, 제한·지시문·전달 방식 비교','과거 형태가 전달 후 빠지는 현상 지속'],
        ['11월5일 야간','오류 피드백, 과거 계사 후보, 기존50와 쉬운30 비교','지원은 일부 증가했지만 안정적 생성·독립 평가 미완료']]))
    pages.append(para('전체 문헌 지도에는 26개 작업 묶음이 있습니다. 이는 일을 나누는 목록이며 26개 규칙이라는 뜻이 아닙니다. 12개 모듈은 분야 분류, 26개 묶음은 정제 작업 단위, 현재 5개 구성·12개 규칙은 이번 실행 후보가 실제로 처리하는 좁은 범위입니다.'))
    pages.append('</section><section id="versions"><h2>2. r7과 r10은 무엇인가요?</h2>')
    pages.append(para('r은 revision, 즉 수정본을 표시하기 위해 붙인 내부 파일 이름입니다. 연구의 성공 단계나 모델 이름이 아닙니다. 날짜와 전체 경로를 함께 봐야 합니다. 서로 다른 초기 실험 폴더에서도 r2·r3 같은 번호를 사용했기 때문에 숫자만으로 전체 연구 순서를 알 수는 없습니다.'))
    pages.append(table(['이름과 기록일','무엇이 들어 있는가','현재 용도'],[
        ['11월2일 의문문 정제본','반말 정보 질문 1구성·6용법','조건 기반 조회의 첫 작은 범위'],
        ['11월3일 문법 확장 r2→r4','공손 평서 3용법 추가. r4는 근거·구현 결정 연결 보완','후속 그래프의 기반'],
        ['11월4일 r5·r6','r5는 검토 초안, r6는 첫 개발 실행본','이전 후보로 보존'],
        ['11월4일 r7 — 기존 기본본',f'{len(base["nodes"])}노드·{len(base["edges"])}관계. 현재 긍정 계사·공손 질문을 포함한 4구성·11규칙','이번 비교의 기준. 품질이 인증됐다는 뜻은 아님'],
        ['11월4일 r8·r9','결합 형태·수정 단위를 바꾼 실험 후보','기본본으로 채택하지 않음'],
        ['11월5일 r10 — 과거 계사 추가 후보',f'{len(g["nodes"])}노드·{len(g["edges"])}관계. 기존 기본본에 과거 긍정·부정 계사 1구성·1규칙 추가','이번 50문장 표의 출력. 운영 채택 보류']]))
    pages.append(para('현재 실험은 버전이 고정된 JSON 파일의 실제 노드·관계를 코드로 읽습니다. 초기 Neo4j 적재 DB를 실시간 조회한 실험은 아닙니다. JSON은 저장 형식이며, 그래프인지 여부는 조건과 지식이 관계로 연결돼 있고 그 관계를 조회하는지로 구별합니다. 이번 후보를 Neo4j에 새로 적재하지 않았습니다.'))
    pages.append('</section><section id="coverage"><h2>3. 아직 남아 있는 문법 확장</h2>')
    pages.append(para('확장은 계속 추적해야 합니다. 생성 오류를 먼저 점검한다고 다른 문법을 완료로 처리하거나 목록에서 지우면 안 됩니다. 아래는 분야별 현재 상태입니다. “일부 사용”은 그 분야 전체를 정제했다는 뜻이 아니고, 분석에 쓰는 것과 방언 변환 규칙이 있는 것도 구별했습니다.'))
    pages.append(table(['문법 분야','현재 사용·확인된 부분','아직 남은 부분','기존 작업지도 묶음'],[[esc(v) for v in row] for row in COVERAGE]))
    packages=read(R/'experiments/analyses/source_workmap_20261102/work_packages.json')
    pages.append('<details><summary>26개 작업 묶음의 기존 목적과 종료 기준 보기</summary>'+para('11월2일에 만든 계획입니다. 아래 종료 기준이 적혀 있다는 것 자체가 완료 증거는 아닙니다. 현재 진행 상태는 위 표와 실행 기록을 기준으로 봅니다.')+table(['묶음','다루는 하위 내용','기존에 정한 종료 기준'],[[esc(x['id']+' '+x['title']),esc(x['split']),esc(x['exit'])] for x in packages])+'</details>')
    pages.append(para('앞으로 각 묶음은 ①문헌 내용 확인 ②조건·실현 정제 ③실제 KG 연결 ④새 문장 조회 ⑤Qwen 생성 ⑥사람 표현 검토를 구별해 갱신합니다. 50문장에 없다는 이유로 해당 문법을 목록에서 제외하지 않습니다. 현재 남은 39곳은 이 50문장 안의 미지원 위치 수이며, 전체 미완료 문법이 39종이라는 뜻은 아닙니다.'))
    pages.append('</section><section id="structure"><h2>4. 노드·관계·구성·규칙을 실제로 이해하기</h2>')
    pages.append(para('노드는 정보를 담는 한 항목이고, 속성은 그 항목 안의 값입니다. 관계는 항목끼리의 연결입니다. “구성”과 “규칙”도 각각 노드의 종류입니다. 구성은 함께 처리할 문법 현상의 묶음이고, 규칙은 그 안에서 조건에 따라 고를 특정 용법입니다.'))
    pages.append('<div class="flow"><span>표준어 문장</span><b>→</b><span>Kiwi: 형태·위치<br>Qwen: 뜻·절 관계</span><b>→</b><span>KG의 구성·조건 대조</span><b>→</b><span>맞는 규칙·실현 방법 전달</span><b>→</b><span>Qwen이 전체 문장 생성</span></div>')
    pages.append(para('예를 들어 “열쇠를 어디에 뒀어?”에서 뒀어는 동사이고, 과거이며, 어디라는 구체적인 답을 묻는 반말 질문입니다. 이 값들이 같은 위치에 묶여 조건과 대조됩니다. 조건에 맞는 질문 규칙은 -노를 제시합니다. 실현 방법에는 어간과 과거 형태를 남기고 종결어미를 붙이라고 적혀 있습니다. 조건을 찾았다는 사실만으로 최종 활용이 올바르다는 보장은 없고, 실제 이번 출력은 두노로 실패했습니다.'))
    pages.append('<div class="flow"><span>반말 정보 질문 구성</span><b>→</b><span>동사·구체 질문 규칙</span><b>→</b><span>질문 종류 / 서술어 / 선어말 조건</span><b>→</b><span>-노 실현 + 과거 보존</span></div>')
    counts=collections.Counter(n['type'] for n in g['nodes'])
    pages.append(table(['노드 종류','쉽게 설명하면','이번 후보의 개수'],[[f'{TYPE[t][0]} <small>({t})</small>',TYPE[t][1],str(c)] for t,c in counts.items()]))
    rules=[n for n in g['nodes'] if n['type']=='SemanticRule']
    pages.append('<h3>현재 실행 후보에 있는 12개 규칙 전체</h3>')
    rule_rows=[]
    for n in rules:
        parents=[name(e['source']) for e in g['edges'] if e['relation']=='HAS_USAGE' and e['target']==n['id']]
        forms=[nodes[e['target']]['properties'].get('form','') for e in g['edges'] if e['source']==n['id'] and e['relation']=='REALIZES']
        rule_rows.append([esc(' / '.join(parents)),node_link(n['id']),esc(' / '.join(forms))])
    pages.append(table(['구성','규칙','저장된 실현형'],rule_rows))
    pages.append(para('카드는 별도의 언어학적 단위가 아닙니다. 이전에는 주요 문헌 정보를 추린 저장 항목을 카드라고 불렀습니다. 현재 실행에서는 선택한 규칙·실현·조건과 입력 위치를 묶어 변환 지시(actions)를 만듭니다. 이 묶음은 기존 KG 지식을 코드로 모은 것이며 매번 Qwen이 새로운 문법 규칙을 지어내는 단계가 아닙니다. 구성 하나, 규칙 하나, 전달 지시 하나를 같은 것으로 세면 안 됩니다.'))
    pages.append('</section><section id="questions"><h2>5. 질문하신 다섯 사례의 확인 결과</h2>')
    for i,(answer,actual,limit,fix) in CASES.items():
        pages.append(f'<article><h3>{esc(i)} · {esc(answer)}</h3>'+para('<b>실제 기록:</b> '+actual)+para('<b>어디까지 알 수 있나:</b> '+limit)+para('<b>보완 방법:</b> '+fix)+f'<a href="#case-{i}">원문·참조·출력·전달 내용 함께 보기</a></article>')
    pages.append('</section><section id="cases"><h2>6. 50문장을 하나씩 읽어보기</h2>')
    pages.append(para('원문, 사용자 승인 참조, Qwen 출력은 저장된 문장을 그대로 표시합니다. 참조는 사용자가 현재 목표 표현으로 승인한 문장입니다. 이번 생성 요청에는 넣지 않았습니다. 출력이 다르면 검토해야 하지만 글자 차이만으로 자동 오류 판정을 하지는 않습니다. 아래 설명은 실제 기록을 사람이 읽도록 풀어쓴 것이며 Qwen에 보낸 지시의 원문 자체는 아닙니다.'))
    pages.append('<label>문장 ID·표현 검색 <input id="search" placeholder="예: DEV012, 주세요, 과거"></label><p id="count" aria-live="polite"></p>')
    for i,result in results.items():
        folder=RUN/'private/records'/i/'r10'; packet=read(folder/'generation_packet.json'); traces=read(folder/'traces.json')
        req=read(folder/'generation_call/request.json'); response=read(folder/'generation_call/parsed.json')
        assert refs[i]['input']==result['input_text']; assert response['output_text']==result['output_text']
        assert json.loads(req['messages'][1]['content'])==packet
        joined.append({'id':i,'input':result['input_text'],'reference':refs[i]['reference'],'output':result['output_text'],'packet':packet,'trace_file':str((folder/'traces.json').relative_to(R))})
        pages.append(f'<details class="sentence" id="case-{i}"><summary><strong>{i}</strong> {esc(result["input_text"])}</summary>')
        pages.append(table(['구분','실제 문장'],[['표준어 원문',esc(result['input_text'])],['사용자 승인 참조',esc(refs[i]['reference'])],['이번 Qwen 출력',esc(result['output_text'])]]))
        if i in CASES: pages.append(para('<b>확인된 문제:</b> '+CASES[i][0]))
        else: pages.append(para('자동 기록상 변환 지시 '+str(len(packet['actions']))+'개를 전달했습니다. 이 문장의 자연스러움·정답 여부는 이번 문서에서 새로 확정하지 않았습니다.'))
        for t in traces:
            a=t['analysis']['clauses'][0]; trace=t['trace']; target=a['target_text']; p=trace['packet']['clauses'][0]; q=trace['retrieval']['clauses'][0]
            pages.append('<h4>입력의 '+esc(target)+' 부분</h4>')
            f=a['features']
            pages.append(para('컴퓨터가 판단한 이 부분의 말하는 목적은 <b>“'+esc(word(f.get('speech_act')))+'”</b>입니다. 듣는 사람에게 쓰는 말투는 “'+esc(word(f.get('addressee_level')))+'”, 서술어 종류는 “'+esc(word(f.get('predicate_class')))+'”로 분류했습니다. 시간 의미는 “'+esc(word(f.get('tense')))+'”로 기록했고, '+('부정의 뜻이 있다고' if f.get('polarity')=='negative' else '긍정의 뜻이라고')+' 판단했습니다. 이 분석 자체도 틀릴 수 있으므로 사람의 정답 판단과 구별합니다.'))
            pages.append('<details><summary>분석 항목 전체를 표로 보기</summary>'+table(['어떤 내용을 분석했나','기록된 값'],[[esc(TERMS.get(k,k)),esc(feature_word(k,v))] for k,v in f.items()])+'</details>')
            eligible=[x['rule_id'] for x in q.get('eligible',[])]
            pages.append(para('찾은 적용 후보: '+(' / '.join(node_link(x) for x in eligible) or '없음')+'. 최종 전달 상태: <b>'+esc(word(p['readiness']))+'</b>.'))
            if p.get('needs_analysis'): pages.append(para('미확정 또는 보류 정보: '+', '.join(esc(word(v)) for v in p['needs_analysis'])+'.'))
            action=next((x for x in packet['actions'] if x['target_id']==t['target']['uid']),None)
            if action:
                pages.append(table(['모델에 전달된 정보','실제 값'],[
                    ['바꿀 위치',esc(action['target'])+' (원문 문자 '+esc(action['span'])+')'],
                    ['관측 형태소',esc(' + '.join(m[0] for m in action['source_morphs']))],
                    ['남길 어간 / 명사 부분',esc(action.get('stem') or '없음')+' / '+esc(action.get('nominal') or '없음')],
                    ['남길 시제·높임 형태',esc(' + '.join(action.get('prefinals',[])) or '없음')],
                    ['바꿀 종결형',esc(action.get('source_final',''))+' → '+esc(' / '.join(f['selected_combining_form'] for f in action['forms']))],
                    ['선택 규칙',node_link(action['rule_id'])],
                    ['실제 조합 설명','<br>'.join(esc(v) for v in action['composition'])],
                    ['보존하라는 정보',pretty(action['preserve'])],
                ]))
                pages.append('<details><summary>조건이 맞았다고 판단한 근거 보기</summary>'+table(['특징','분석값','규칙이 받는 값','판정'],[[esc(TERMS.get(c['feature'],c['feature'])),esc(word(c.get('observed'))),pretty(c.get('allowed',[])),esc(word(c['state']))] for c in action.get('condition_checks',[])])+'</details>')
            else:
                pages.append(para('이 위치에는 변환 지시를 보내지 않았습니다. 이번 비교에서 사용한 생성 지시문은 “지원한 위치만 고치고 나머지는 유지, 지시가 0개면 원문 전체 유지”였습니다. 따라서 원문 유지 자체를 모델 능력의 실패로 단정할 수 없습니다.'))
        pages.append('<small>근거 기록: '+esc(str(folder.relative_to(R)))+'의 generation_packet.json, traces.json, generation_call/request.json 및 parsed.json</small></details>')
    pages.append('</section><section id="next"><h2>7. 다음 작업의 순서와 끝나는 기준</h2>')
    pages.append(para('이번 문서에서는 분석·KG·생성 코드를 수정하거나 Qwen을 새로 호출하지 않았습니다. 원인 확인 기록과 문법 확장 목록을 정리했습니다. 다음 구현은 한 번에 모든 것을 바꾸지 않고, 같은 원인을 가진 사례 묶음으로 비교해야 합니다.'))
    pages.append(table(['순서','실제 작업','끝나는 기준','예상대로 되지 않으면'],[
        ['1 · 기록과 확장 대장','이번 5사례의 요청·출력 확인, 전체 분야의 현재/미완료 상태 공개','각 사례가 분석·미지원·차단·전달·생성 중 어디서 끊겼는지 근거로 구분. 이번 문서에서 수행','모르는 부분을 추측으로 확정하지 않고 미확정으로 남김'],
        ['2 · 이미 전달되는 규칙의 실패','과거·명사·어간 보존, 계사 결합 설명의 모호함을 분리해 통제 비교','동일 분석·규칙에서 원인별 수정 전후와 새 어휘 비교. 단문·복수 변경 모두 확인','개선이 반복되지 않으면 같은 문구 탐색 중단, 생성 한계로 기록'],
        ['3 · 전달 차단의 범위','DEV026 같은 경계 미확정의 영향 범위 추적','영향 없는 위치는 전달하고 부정·높임·인용에 영향 있는 반례는 보류','영향을 입증 못한 위치는 보류 유지. 전역 해제 금지'],
        ['4 · 지식 확장 병행','반말 평서, 요청·금지, 약속·청유, 절 연결 순으로 정제. 높임·시제·명사·보조용언은 필요한 공통 부분을 함께 보완','묶음마다 문헌/해석, KG 조건·관계, 새로운 개발 문장 조회·생성, 사람 확인 상태를 기록','자료가 부족한 가지는 후보로 남기고 다른 가지 진행. 미완료는 대장에서 유지'],
        ['5 · 회귀와 본 평가 준비','확장할 때 기존50 회귀 확인. 지원 범위 고정 뒤 새 독립 쉬운 평가셋 준비','지식 없음·텍스트 검색·조건 KG 조회를 같은 정보 원천·생성기에서 비교할 수 있음','지원 범위·생성 안정성이 부족하면 논문 주장 범위를 좁히고 한계를 명시']]))
    pages.append(para('리드는 구현·실험·집계를 수행합니다. 기존 Codex 검토자는 조회·차단·전달 코드와 비교 통제를, Claude 검토자는 문헌 해석·적용 조건·표현 누락을 검토합니다. 두 검토자는 “문제 위치 → 실제 근거 → 수정안”을 남깁니다. 사용자에게는 현대 표현의 허용 여부나 연구 범위를 바꿔야 하는 선택만 묻습니다. 이번 설명 문서에 대해 두 검토자의 새 검토를 받았다고 주장하지 않습니다.'))
    pages.append('</section><section id="dictionary"><h2>8. 낯선 표현을 다시 풀어 설명합니다</h2>')
    pages.append(table(['이전 표현','앞으로 사용할 쉬운 설명'],[
        ['계약 회복 0/6 대 0/6','과거형 등 미리 정한 보존 항목을 고쳤는지 검사했는데, 두 방식 모두 대상 6회에서 수정 성공을 확인하지 못했다는 뜻입니다. 자연스러움 점수가 아닙니다.'],
        ['신규 대상 표면 보존','새 예문에서 남기라고 한 글자·형태가 출력에 남았다는 뜻입니다. 뜻과 자연스러움 전체가 맞다는 뜻은 아닙니다.'],
        ['개발 파일럿','방법이 작동하는지 작게 미리 해 보는 실험입니다. 개선에 사용했으므로 독립 최종 평가와 다릅니다.'],
        ['17개 실행 규칙','10월24~25일 구현에서 17개 기존 항목에 연결한 적용 코드 수입니다. 한국어의 기본 규칙 총수도, 모든 문장이 17개 관문을 통과한다는 뜻도 아닙니다. 현재 조건 그래프의 12개 용법과는 다른 버전·다른 단위입니다.'],
        ['후보 / 전달 / 생성 성공','후보는 조건에 맞아 찾은 지식입니다. 전달은 실제 요청에 그 지식을 넣은 것입니다. 생성 성공은 모델이 이를 올바르게 반영했는지 별도로 확인해야 합니다.'],
        ['시제와 선어말 형태','시제는 과거·현재 같은 시간 의미입니다. 었·시 같은 형태는 실제 문장에 관측된 조각입니다. 현재 분석은 두 종류를 별도 값으로 기록합니다.'],
        ['지원 범위 밖','현재 실행 구현으로 처리하지 않는다는 뜻입니다. 문헌에 없거나 문법적으로 틀렸다는 뜻이 아닙니다.'],
        ['사용자 승인 참조','사용자가 목표 표현으로 승인한 비교 문장입니다. 개별 정답을 외우는 변환 규칙이나 이번 생성 요청의 정답으로 쓰지 않았습니다.'],
    ]))
    pages.append('<h3>현재 그래프가 받아들이는 분석값 전체</h3>'+table(['분석 항목','가능한 값'],[[esc(TERMS.get(k,k))+f' <small>({esc(k)})</small>', ' / '.join(esc(feature_word(k,v))+f' <small>({esc(v)})</small>' for v in vs)] for k,vs in g['feature_schema'].items()]))
    pages.append(para('예를 들어 request라는 분석값이 존재해도 요청용 구성·규칙이 없으면 변환하지 못합니다. 분석값의 목록이 지원 문법 전체 목록은 아닙니다.'))
    pages.append('<h3>실제 노드의 속성과 값</h3>'+para('아래는 이번 실행에 고정해 둔 그래프에서 직접 읽었습니다. 종류를 열면 모든 노드와 저장된 속성값을 볼 수 있습니다. 한국어 설명 뒤의 괄호에는 원래 필드명을 남겼습니다. 원문 근거·구현 해석·미완료 후보를 같은 사실로 취급하지 않습니다.'))
    for typ in counts:
        pages.append('<details><summary>'+esc(TYPE[typ][0])+' · '+str(counts[typ])+'개</summary>')
        for n in g['nodes']:
            if n['type']!=typ:continue
            pages.append(f'<details id="node-{esc(n["id"])}"><summary>{esc(name(n["id"]))} <small>{esc(n["id"])}</small></summary>'+pretty(n['properties']))
            edges=[e for e in g['edges'] if e['source']==n['id']]
            pages.append(table(['나가는 관계','연결 대상'],[[esc(REL.get(e['relation'],e['relation']))+' <small>'+esc(e['relation'])+'</small>',node_link(e['target'])] for e in edges])+'</details>')
        pages.append('</details>')
    ec=collections.Counter(e['relation'] for e in g['edges'])
    pages.append('<details><summary>관계 종류·개수와 연결 속성 보기</summary>'+table(['관계','뜻','개수'],[[esc(k),esc(REL.get(k,k)),str(v)] for k,v in ec.items()]))
    pages.append(para('각 관계에는 id(연결 식별자), source(출발 노드), relation(관계 종류), target(도착 노드)가 있습니다. 다음 표는 이 네 항목 외에 추가 속성이 실제로 저장된 관계입니다.'))
    pages.append(table(['연결','추가 속성'],[[esc(e['source']+' → '+e['relation']+' → '+e['target']),pretty({k:v for k,v in e.items() if k not in {'id','source','relation','target'}})] for e in g['edges'] if set(e)-{'id','source','relation','target'}])+'</details>')
    pages.append('</section><footer>실험 기록은 바꾸지 않았습니다. 원인에 대한 가설과 기록으로 확인한 사실을 구별했습니다. <a href="report.html">야간 실험 원 보고서</a> · <a href="paper_handoff.md">논문 인계 원문</a></footer></main></body></html>')
    (OUT/'guide.html').write_text(''.join(pages),encoding='utf8')
    (OUT/'guide_cases.json').write_text(json.dumps(joined,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'guide_manifest.json').write_text(json.dumps({'generated_kst':now,'run_id':RUN.name,'cases':len(joined),'nodes':len(g['nodes']),'edges':len(g['edges']),'new_model_calls':0,'source_hashes':FILES,'all_inputs_references_outputs_joined':True,'request_packets_verified':True,'node_property_keys_untranslated':sorted({k for n in g['nodes'] for k in n['properties'] if k not in TERMS})},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'html':str(OUT/'guide.html'),'cases':len(joined),'source_files':len(FILES),'new_model_calls':0},ensure_ascii=False))

if __name__=='__main__': build()
