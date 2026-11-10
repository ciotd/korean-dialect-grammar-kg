"""Frozen prompts: no native reference sentences or new dialect alternatives."""
def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
def nullable(values):return {'type':['string','null'],'enum':values+[None]}
ANALYSIS_PROMPT='''표준어 질문 한 문장을 분석한다. 방언 번역이나 어미 선택은 하지 않는다.
제공된 Kiwi 어절 ID와 형태소는 위치와 형태 분석의 보조 자료다. 문장의 문법 기능은 네가 판단한다.
target_word_id는 문장 끝 서술어가 있는 어절 ID, question_word_id는 구체적인 답을 요구하는 질문어가 있는 어절 ID다. 위치를 새로 만들지 말라.
question_kind: polar=예/아니오로 대답하는 질문, wh=누구/무엇/어디/왜 등 구체적인 답을 요구하는 질문. 의문사 문자열이 있다고 항상 wh인 것은 아니다.
문맥이 없어 여러 해석이 실질적으로 가능하면 해당 값을 null로 두고 ambiguity에 이유를 적어라. 확정할 수 있는 다른 특징까지 비우지 말라.
speech_act는 실제 발화 기능이다. 물음표가 있어도 재촉/요구면 request일 수 있다. 텍스트만으로 다른 의도를 확정하지 않는다.
prefinal_type은 실제 선어말 형태 종류이고 tense는 시간 의미다. 과거형 없음을 무조건 과거 없음으로 해석하지 않는다.
polarity는 안/못/아니다 등의 부정 구성 여부다. 반말은 plain, 높임말은 polite. 주체높임과 상대높임은 구별한다.
JSON만 출력한다. 분석 결과에 번역문이나 KG 규칙 ID를 넣지 않는다.'''
FEATURES={'clause_role':['main','embedded','quoted'],'speech_act':['information_question','statement','request','rhetorical_question','confirmation','suggestion','exclamation','self_question'],
 'addressee_level':['plain','polite'],'question_kind':['polar','wh'],'predicate_class':['verb','adjective','copula','negative_copula'],
 'prefinal_type':['none','eoss','gess','deo','other'],'tense':['past','present','future'],'subject_honorific':['absent','present'],'polarity':['positive','negative']}
ANALYSIS=obj({'target_word_id':{'type':['string','null']},'question_word_id':{'type':['string','null']},'features':obj({k:nullable(v) for k,v in FEATURES.items()}),
 'ambiguity':{'type':'array','items':{'type':'string'}},'reason':{'type':'string'}})
GENERATION_PROMPT='''한국어 문장을 주어진 경상도 질문 어미 규칙으로 고친다.
입력과 actions의 대상 구간, 어간/형태소, 선택된 어미를 사용한다. 문장 전체를 출력하되 대상 서술어 밖의 글자·조사·어휘·문장부호는 그대로 유지한다.
선택된 어미로 종결 부분을 조합한다. 활용의 축약/불규칙은 문법에 맞게 조합하고 단순 문자열 덧붙이기를 하지 않는다.
이가/이고/가/고 결합형에는 계사 부분이 포함되므로 이-를 중복해 붙이지 않는다. 과거 계사는 입력의 계사·과거 선어말을 보존한다.
뜻, 부정, 시간, 질문 유형, 높임은 유지한다. 어휘를 니/묵다/어데 등으로 새로 바꾸거나 조사를 생략하거나 과거 선어말을 추가하지 않는다.
완성형을 만들 수 없다면 status=needs_review와 이유를 적는다. 만들면 status=generated. JSON만 출력한다.'''
GENERATION=obj({'output_text':{'type':'string'},'status':{'type':'string','enum':['generated','needs_review']},'reason':{'type':'string'}})
