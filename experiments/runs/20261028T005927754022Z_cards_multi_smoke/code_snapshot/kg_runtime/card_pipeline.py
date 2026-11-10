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
EDIT=obj({'word_id':S,'rule_ids':arr(S),'instruction':S,'after':S,'reason':S})
DECISION=obj({'edits':arr(EDIT),'reason':S})
WORKER=obj({'edits':arr(obj({'word_id':S,'after':S,'reason':S})),'reason':S})
ANALYSIS_PROMPT='''한국어 문법 분석가다. Kiwi가 제공한 원문 어절 ID에 문법 기능을 연결한다.
종결·연결 어미, 조사, 부정, 관형형, 보조용언 등 변환 판단에 관련된 어절을 분석한다.
원문 위치나 ID를 새로 만들지 않는다. 하나의 어절에 기능 여러 개 가능하다.
politeness는 청자 대우이며 subject_honorific와 다르다. -까요는 문맥에 따라 제안/의향 질문 또는 추측 질문이다.
concept_ids는 제공된 실제 개념 목록에서만 고른다. 없는 개념을 만들지 않는다. 해석이 불확실하면 reason에 명시한다.
방언 문장은 아직 생성하지 않는다. JSON만 출력한다.'''
BASE='''경상도 방언 문법 편집자다. 원문의 의미, 시제, 부정, 인물, 청자 대우, 주체 높임을 보존한다.
cards는 문헌에서 정리한 문법 지식이다. title/when/forms/avoid를 함께 읽고 문장의 해당 기능에 맞는 것만 선택한다.
목록에 있는 어미를 아무 어간에 붙여서는 안 된다. 받침, 활용과 높임에 맞게 완성 어절을 만든다.
cards의 source_level은 방언 어미의 화계이다. 표준어 원문의 화계와 이름만 같아야 하는 조건이 아니지만 공손함을 낮추면 안 된다.
어미 목록은 완성 문장의 인용이 아니다. after는 네가 활용을 조합하는 값이다.
동일한 표준어/방언 형태는 그대로 둘 수 있다. 조건을 충족하는 방언 표현은 적극 활용하되 억지로 변경하지 않는다.
꾸며낸 자랑/알림 상황, 의미 추가, 욕설, 새로운 사실은 넣지 않는다.
수정할 원문 word_id와 근거인 rule_ids(반드시 제공된 cards의 실제 ID), 무엇을 왜 바꾸는지 instruction을 적는다.
원문 한 어절 전체를 after로 바꾼다. 여러 문법을 한 어절에 적용할 때 한 edit에 합친다. 같은 ID는 중복 금지.
after 안에 공백·문장부호·문장 전체를 넣지 않는다. 수정하지 않을 어절은 edits에서 생략한다.
단순 조사/어미를 바꾸기 위해 어휘나 부정어를 없애지 않는다. 결과는 지정 JSON뿐이다.'''
SINGLE=BASE+'\n너는 계획과 활용을 동시에 담당한다. instruction과 완성 어절 after를 모두 작성한다.'
PLANNER=BASE+'\n너는 계획 담당이다. instruction을 구체적으로 적고 after에는 빈 문자열을 적는다. 실제 활용은 다음 생성 담당이 수행한다.'
GENERATOR='''경상도 방언 활용 담당이다. 원문과 문법 분석, 확정된 계획, 관련 문법 카드가 주어진다.
계획의 word_id 각각에 대해 instruction에 맞는 완성 어절 after를 만든다. 원문 어휘 의미·시제·부정·높임을 유지한다.
계획 밖의 어절이나 새 규칙을 추가하지 않는다. 단순 어미 접합이 아니라 받침과 축약까지 자연스럽게 활용한다.
after에는 어절 하나만 넣고 공백과 문장부호는 넣지 않는다. 적용할 수 없으면 해당 원문 어절을 그대로 돌려준다.
모든 계획 word_id를 정확히 한 번씩 반환한다. JSON만 출력한다.'''

def validate_analysis(value,morph,concepts):
    validate_schema(value,ANALYSIS)
    by={w['uid']:w for w in morph['words']};seen=set()
    for u in value['units']:
        if u['word_id'] not in by or u['word_id'] in seen:raise ValueError('invalid_analysis_word_id')
        if not set(u['concept_ids'])<=set(concepts):raise ValueError('invalid_analysis_concept_id')
        seen.add(u['word_id'])
    if not seen:raise ValueError('empty_grammar_analysis')
    return [{'word_id':u['word_id'],'span':[by[u['word_id']]['start'],by[u['word_id']]['end']],
             'surface':by[u['word_id']]['surface'],'functions':u['functions']} for u in value['units']]

def bind_plan(value,morph,cards,realize=True):
    validate_schema(value,DECISION)
    by={w['uid']:w for w in morph['words']};ids={c['id'] for c in cards};seen=set();edits=[]
    import re
    for e in value['edits']:
        if e['word_id'] not in by or e['word_id'] in seen:raise ValueError('invalid_edit_anchor')
        if not e['rule_ids'] or not set(e['rule_ids'])<=ids:raise ValueError('unretrieved_rule_reference')
        if not e['instruction'].strip():raise ValueError('empty_instruction')
        if realize and (not e['after'].strip() or re.search(r'[\s.,!?…]',e['after'])):raise ValueError('after_not_single_word')
        w=by[e['word_id']];seen.add(e['word_id'])
        if morph['text'][w['start']:w['end']]!=w['surface']:raise ValueError('invalid_source_span')
        edits.append(dict(e,before=w['surface'],span=[w['start'],w['end']],surface_origin='qwen_composition'))
    edits.sort(key=lambda x:x['span'][0])
    if any(a['span'][1]>b['span'][0] for a,b in zip(edits,edits[1:])):raise ValueError('overlap')
    return {'edits':edits,'reason':value['reason']}

def realize_plan(plan,answer,morph,cards):
    validate_schema(answer,WORKER)
    after={x['word_id']:x for x in answer['edits']}
    if len(after)!=len(answer['edits']) or set(after)!={e['word_id'] for e in plan['edits']}:raise ValueError('worker_plan_mismatch')
    value={'edits':[{k:(after[e['word_id']]['after'] if k=='after' else e[k]) for k in EDIT['properties']} for e in plan['edits']], 'reason':answer['reason']}
    return bind_plan(value,morph,cards)

def assemble(text,plan):
    for e in reversed(plan['edits']):text=text[:e['span'][0]]+e['after']+text[e['span'][1]:]
    return text
