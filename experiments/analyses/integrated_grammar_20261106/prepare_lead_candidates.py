"""Source-based omissions found by the lead; explicitly interpreted input mapping."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent/'private/lead_candidates.json'
common={'status':'candidate','rule_type':'conversion','legacy_ids':[],
 'preserve':['어간·어휘 뜻','시제·부정','행동 주체·높임'],
 'limitations':'문헌 실현형의 존재와 표준 입력→실현형 매핑은 구별한다. 후자는 이번 연구의 해석이며 현대 자연스러움은 별도 사람 검토 대상이다.'}
rules=[
 {**common,'id':'INT_LEAD_DECL_PAST_DA','title':'반말 과거 사실을 -었다로 말하기','modules':[1,5,8],'packages':['F01','F04','F18'],'unit_kind':'predicate',
  'conditions':{'ending_tag':['EF'],'source_form':['어','아','다'],'prefinal_sequence':['eoss'],'predicate_class':['verb','adjective'],
    'speech_act':['statement'],'addressee_level':['plain'],'subject_honorific':['absent']},
  'instruction':'반말로 과거 사실을 전하는 절에서 해라체 -다 종결을 선택할 수 있다. 기존 -았/-었-과 어간은 그대로 보존한다. 어미만 바꾸며 현재 -는다로 바꾸지 않는다. 이는 표준어에도 있는 공통형이고 방언만의 고유형은 아니다.',
  'forms':['-았/었-다'],'source_refs':[{'doc':'D02','page':109,'quote':'표준형 -다,-ㄴ다,-아라/어라'}]},
 {**common,'id':'INT_LEAD_DECL_PRESENT_DA','title':'반말 현재 서술: 동사 -ㄴ다/는다, 형용사 -다','modules':[1,2,5],'packages':['F01','F04'],'unit_kind':'predicate',
  'conditions':{'ending_tag':['EF'],'source_form':['어','아','다','ㄴ다','는다'],'prefinal_sequence':['none'],'predicate_class':['verb','adjective'],
    'speech_act':['statement'],'addressee_level':['plain'],'subject_honorific':['absent'],'tense':['present']},
  'instruction':'현재 사실의 반말 서술을 해라체로 실현하는 선택지다. 동사는 현재 -ㄴ다/는다, 형용사는 -다로 구별한다. 문헌에서 공통형의 존재를 확인했으며 표준 입력의 말투 대응은 연구 해석이다. 질문·청유·약속으로 기능을 바꾸지 않는다.',
  'forms':['동사: -ㄴ다/는다','형용사: -다'],'source_refs':[{'doc':'D02','page':109,'quote':'표준형 -다,-ㄴ다,-아라/어라'}]},
 {**common,'id':'INT_LEAD_REQUEST_JU_AUX','title':'해 주세요의 보조 주다 → 해 주이소','modules':[5,6,9],'packages':['F05','F08','F21'],'unit_kind':'construction',
  'conditions':{'lemma':['주'],'source_form':['세요','으세요','십시오','으십시오'],'speech_act':['request'],'addressee_level':['polite','formal'],'auxiliary_kind':['benefactive']},
  'instruction':'높임 부탁의 보조 주다를 주이소로 실현하는 후보. 앞의 본동작과 연결어미는 보존한다. 주이소를 동사 어간 뒤에 바로 붙이지 말고 해 주다 구성 전체의 뜻을 유지한다.',
  'forms':['-아/어 주이소'],'source_refs':[{'doc':'D02','page':192,'quote':'터 하나 골\n라주이소.'}]},
 {**common,'id':'INT_LEAD_REQUEST_JU_MAIN','title':'물건을 주세요의 본동사 주다 → 주이소','modules':[1,5,6],'packages':['F05','F08'],'unit_kind':'predicate',
  'conditions':{'lemma':['주'],'ending_tag':['EF'],'source_form':['세요','으세요','십시오','으십시오'],'speech_act':['request'],'addressee_level':['polite','formal'],'auxiliary_kind':['none']},
  'instruction':'물건·시간 등을 달라는 높임 부탁의 본동사 주다를 주이소로 실현하는 후보. 주는 대상과 받는 사람을 보존한다. 보조용언 주다는 별도 구성 규칙을 사용한다.',
  'forms':['주이소'],'source_refs':[{'doc':'D02','page':218,'quote':'세 시간만 말미 주이소.'}]},
 {**common,'id':'INT_LEAD_PROHIB_PLAIN','title':'반말 금지 -지 마 → -지 마라','modules':[5,8,9],'packages':['F05','F19','F21'],'unit_kind':'construction',
  'conditions':{'lemma':['말'],'source_form':['어','아','라','어라'],'speech_act':['prohibition'],'addressee_level':['plain']},
  'instruction':'반말 금지의 말다를 마라로 실현할 수 있다. 앞의 행동과 -지, 부정 의미를 보존한다. 이 형태는 표준어에도 있는 공통형이며 방언 고유형으로 세지 않는다.',
  'forms':['-지 마라'],'source_refs':[{'doc':'D02','page':218,'quote':'겨정하지 마라.'},{'doc':'D02','page':218,'quote':'걱정하지 마.'}]},
]
P.parent.mkdir(parents=True,exist_ok=True)
P.write_text(json.dumps({'rules':rules},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Lead candidates',len(rules),'not independent facts or sentence-specific answers.')
