"""Kiwi anchors + Qwen functions -> Neo4j -> compact cards -> generic edit plans."""
from kg_pipeline.validation import validate_schema
from .cards import FUNCTION_TERMS

def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
S={'type':'string'}
def arr(item):return {'type':'array','items':item}
ANALYSIS=obj({'units':arr(obj({'word_id':S,'functions':arr({'type':'string','enum':list(FUNCTION_TERMS)}),
    'politeness':{'type':'string','enum':['plain','polite','formal','unknown']},
    'tense':{'type':'string','enum':['past','present','future','unknown']},
    'subject_honorific':{'type':'boolean'},'concept_ids':arr(S),'reason':S}))})
from .edit_contract import EDIT, DECISION, WORKER, VERSION as CONTRACT_VERSION, context, bind_plan, realize_plan, assemble
ANALYSIS['properties']['units']['items']['properties'].update({
    'discourse_function':{'type':'string','enum':['unknown','answer','speaker_commitment','confirmation_question']},
    'discourse_evidence':S})
ANALYSIS['properties']['units']['items']['properties']['functions']['maxItems']=3
ANALYSIS['properties']['units']['items']['properties']['concept_ids']['maxItems']=3
ANALYSIS_PROMPT='''한국어 문법 분석가다. Kiwi가 제공한 원문 어절 ID에 문법 기능을 연결한다.
종결·연결 어미, 조사, 부정, 관형형, 보조용언 등 변환 판단에 관련된 어절을 분석한다.
원문 위치나 ID를 새로 만들지 않는다. 하나의 어절에 기능 여러 개 가능하다.
politeness는 청자 대우이며 subject_honorific와 다르다. -까요는 문맥에 따라 제안/의향 질문 또는 추측 질문이다.
concept_ids는 제공된 실제 개념 목록에서만 고른다. 없는 개념을 만들지 않는다. 해석이 불확실하면 reason에 명시한다.
방언 문장은 아직 생성하지 않는다. JSON만 출력한다.'''
ANALYSIS_PROMPT+='''
기능 이름: declarative=평서, polar_question=예/아니오 질문, wh_question=의문사 질문,
request=명령/요청, propositive=함께 하자는 청유, prohibition=금지, conditional=조건,
causal=원인, quotation=인용, intention=화자 의지/약속, conjecture=추측, retrospective=회상,
negation=부정, relative=관형절, progressive=진행, contrast=대조/양보, particle=조사,
simultaneous=동시·병행, adverbial=부사화·부사절, other=기타.
관련 없는 기능을 나열하지 않는다. 문장 전체의 기능을 모든 어절에 붙이지 않는다.
명사 자체는 생략하고 어미·조사·부정어 등 문법 기능을 지닌 어절을 우선하여 원문의 관련 어절을 빠짐없이 분석한다.
reason은 40자 이내로 짧게 쓴다. 각 원문 어절은 최대 한 번만 분석한다.
해요체 요청의 politeness는 polite이다. formal은 합쇼체처럼 격식적인 경우다.'''
ANALYSIS_PROMPT+='''
말높임은 명사·연결어미에 일괄 전파하지 않고 해당 종결형에서 판단한다. 반말 종결은 plain이다.
과거 어미가 있다는 이유로 progressive를, 확인 질문이라는 이유로 negation을 붙이지 않는다.
같은 절의 의문사와 종결 서술어를 함께 보고 질문 종류를 정한다. 내포절의 의문사는 주절에 무조건 전파하지 않는다.'''
ANALYSIS_PROMPT+='''
응답/화자의 확정 태도/상대 확인 요청이 원문 안에서 드러나면 discourse_function과 그 판단의 근거인 원문 그대로의 짧은 discourse_evidence를 적는다.
일반 평서라는 이유만으로 확정 태도나 응답이라고 쓰지 않는다. 없는 선행 발화를 만들지 않는다. 근거가 없으면 unknown과 빈 문자열이다.
이 값은 문맥에 관한 너의 분석이며 확정 사실이 아니다.'''
BASE="""경상도 방언 문법 편집자다. 의미·어휘·시제·부정·높임·문장 관계를 보존한다.
cards는 문헌 지식이다. contract_context.card_usage의 reference/restriction은 참고/차단 자료이며 수정 명령이 아니다.
조건이 맞는 candidate에서 실제 card_id와 forms의 0부터 시작하는 form_index를 고른다. 새 형태나 ID를 만들지 않는다.
when의 required/not_yet_verified는 충족된 조건이 아니다. 지역·시기 정보는 이번에 별도 사용자 프로필을 요구하는 조건으로 쓰지 않는다.
화계 이름을 표준어와 기계적으로 일치시키지 않는다. 공손함과 주체 높임을 보존한다.
request_id는 contract_context.request_id를 그대로 반환한다. 편집마다 edit_id, word_ids, bindings, depends_on을 적는다.
word_ids는 원문 순서의 연속 어절 ID들이다. 한 어절이 여러 어절로 바뀔 수 있다. 여러 원문 어절을 묶을 때는 같은 문법 구성인지 확인하고 instruction에 설명한다.
bindings에는 card_id, form_index, component(particle/ending/construction), source_word_id, morph_index를 적는다. morph_index는 words의 morphs 배열에서 바꿀 형태소의 0부터 시작하는 위치다. 조사 카드는 그 조사, 어미 카드는 마지막 어미를 가리킨다. 같은 부분을 서로 다른 형태로 바꾸지 않는다.
다른 수정과 함께 적용해야 뜻이 보존되면 depends_on에 그 edit_id를 적는다. 서로 무관한 수정은 빈 배열을 사용한다.
action은 apply/keep/needs_review다. 근거가 부족하면 needs_review, 원문을 유지하면 keep이다. 변경하지 않을 부분은 생략해도 된다.
instruction은 어떤 부분을 왜 바꿀지 짧게 적는다. after는 그 범위의 완성 표현이다. 공백을 허용하되 범위 밖 문장, 추가 설명, 없던 문장부호는 넣지 않는다.
부정어·시제·높임이나 명사·논항을 버리지 않는다. 붙임표/괄호/자모는 형태 설명용이다. 실제 결과는 완성된 한글로 활용한다.
contract_context.user_restrictions를 지킨다. -지/-제는 모든 평서에 자동 적용하지 않는다. 알림·자랑 등 주어지지 않은 상황을 만들지 않는다.
각 reason은 160자, instruction은 240자 이내로 짧게 쓴다. 같은 설명을 반복하거나 여러 대안을 장문으로 나열하지 않는다.
JSON만 출력한다."""
SINGLE=BASE+'\n계획과 활용을 함께 담당한다. after에 완성 표현을 적는다.'
PLANNER=BASE+'\n계획만 담당한다. after는 빈 문자열이다. instruction에 목표와 보존할 내용을 적는다.'
GENERATOR="""경상도 방언 활용 담당이다. 원문, 분석, 카드, 확정 계획이 주어진다.
plan_id는 plan.plan_id를 그대로 반환한다. 모든 edit_id를 정확히 한 번 반환한다. 새로운 편집·규칙·목표형을 추가하지 않는다.
각 편집의 bindings가 가리킨 형태와 instruction에 따라 after를 생성한다. 입력 범위 안에서 공백을 쓸 수 있다.
원문 어휘·논항·부정·시제·상·높임·절 관계를 유지한다. 형태 설명의 자모/괄호를 그대로 붙이지 말고 완성형으로 활용한다.
어울리지 않거나 활용을 만들 수 없으면 needs_review, 원문 유지면 keep으로 응답한다. 계획이 keep/needs_review면 apply로 승격하지 않는다.
없는 사실이나 상황을 추가하지 않는다. JSON만 출력한다."""

COMPATIBILITY_PROMPT='''
candidate_guidance는 원문 어절별 조건 대조와 대체 후보 안내다. 후보라는 이유만으로 모든 조건이 확인된 것은 아니다.
원문의 공손함을 유지한다. 카드의 source_level/target_register.level_id는 문헌에 기록된 방언 화계다.
해라·해체 후보로 공손한 질문을 반말로 바꾸지 않는다. 맞는 공손한 질문 후보를 비교해서 고른다.
카드 제목에 A → B가 명시되면 원문 형태소 A에만 대응시킨다. '-지만 → -아도'를 '-는데'에 적용하지 않는다.
일반적인 원인·대조 기능이 비슷하다는 이유로 원래 어미의 뜻을 바꾸지 않는다. 해당 원형의 근거가 없으면 유지하고 이유를 짧게 적는다.
고를 때는 문장 전체가 아니라 bindings가 지정하는 어절의 분석을 사용한다. 다른 절의 기능을 가져오지 않는다.
활용은 완성형으로 쓴다. 오+아도 같은 모음 결합은 와도로 조합하되, 그 카드 자체가 해당 원문 조건에 맞는지 먼저 확인한다.
'''
SINGLE+=COMPATIBILITY_PROMPT
PLANNER+=COMPATIBILITY_PROMPT
GENERATOR+=COMPATIBILITY_PROMPT

def validate_analysis(value,morph,concepts,aligned=False):
    # Program metadata is never an allowed field in the model output contract.
    core={k:v for k,v in value.items() if not(aligned and k=='source_alignment')}
    validate_schema(core,ANALYSIS)
    by={w['uid']:w for w in morph['words']};seen=set()
    for u in value['units']:
        if u['word_id'] not in by or u['word_id'] in seen:raise ValueError('invalid_analysis_word_id')
        if not set(u['concept_ids'])<=set(concepts):raise ValueError('invalid_analysis_concept_id')
        if not set(u['functions'])<=set(FUNCTION_TERMS):raise ValueError('invalid_analysis_function')
        quote=u.get('discourse_evidence','')
        if quote and quote not in morph['text']:raise ValueError('invented_discourse_evidence')
        seen.add(u['word_id'])
    if not seen:raise ValueError('empty_grammar_analysis')
    return [{'word_id':u['word_id'],'span':[by[u['word_id']]['start'],by[u['word_id']]['end']],
             'surface':by[u['word_id']]['surface'],'functions':u['functions']} for u in value['units']]

def request_schema(schema,field,identifier):
    """Request-local schema. Never mutate shared S/DECISION/WORKER or another call."""
    import copy
    result=copy.deepcopy(schema)
    result['properties'][field]={'type':'string','enum':[identifier]}
    result['properties']['reason']={'type':'string','maxLength':160}
    edit=result['properties']['edits']['items']['properties']
    edit['reason']={'type':'string','maxLength':160}
    if 'instruction' in edit:edit['instruction']={'type':'string','maxLength':240}
    return result
