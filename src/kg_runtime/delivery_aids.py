"""Independent, opt-in delivery interventions. Never edit KG cards or approved references."""
import copy
from .compatibility import assess,ranked_candidates
from .function_semantics import annotated_units
from .edit_contract import project_edit

VERSION='delivery_aids_v1'
VARIANTS=('control','explanation','composition')
PROMPTS={
 'control':'',
 'explanation':'''\ncondition_explanations는 이번 실행에서 계산한 원문/카드 조건의 대조 결과다.
말높임 결과가 match면 원문의 공손함과 이 후보의 넓은 말높임 범주가 일치한다는 뜻이다. 이를 화계 코드의 이름만 보고 반말이라고 뒤집지 않는다.
unknown은 확인되지 않았다는 뜻이며, match가 모든 문맥·활용을 보장하지는 않는다. 어휘·시제·금지·뜻은 계속 보존한다.
when의 required/resolved/not_yet_verified는 설계 기록용 표시다. 구체적인 조건값 자체가 아니므로 이 단어를 문법 기능처럼 해석하거나 반복 설명하지 않는다.
기록에 적힌 실제 원형·문법 기능·화계 조건은 그대로 검토한다. 설명은 짧게 하고 각 편집을 한 번만 반환한다.''',
 'composition':'''\ncomposition_aids는 원문 형태소와 선택 가능한 어미를 조합한 보조 자료다. source_prefix_morphs는 선택한 마지막 어미 앞까지 보존할 재료다.
형태 설명의 -ㅂ/-ㅁ 같은 표기를 그대로 붙이지 말고 앞 형태소와 결합된 완성형을 쓴다. 어미 교체 때 원래 어미를 덧붙여 이중으로 만들지 않는다.
candidate_spellings는 기존 조합기가 계산한 후보일 뿐 자연스러움의 정답이 아니다. 카드 조건과 원문 뜻을 확인하고, 맞지 않으면 그대로 복사하지 않는다.
카드에 명시되지 않은 새 어미나 어휘는 만들지 않는다. 조합 도움 자료가 없어도 기존에 전달된 카드를 사용할 수 있다.'''}

def prepare(payload,morph,variant,plan=None):
    if variant not in VARIANTS:raise ValueError('unknown_delivery_variant')
    result=copy.deepcopy(payload)
    if variant=='control':return result
    by={w['uid']:w for w in morph['words']};cards=result['cards'];cby={c['id']:c for c in cards}
    units={u['word_id']:u for u in annotated_units(result['grammar'])};targets=[]
    if plan is not None:
        for edit in plan['edits']:
            for b in edit['bindings']:
                if b['card_id'] in cby:targets.append((b['source_word_id'],b['card_id'],b['form_index'],b['morph_index'],b['component']))
    else:
        for uid,unit in units.items():
            word=by[uid]
            if not any(t.split('-')[0] in ('EF','EC') for _,t in word['morphs']):continue
            ranked,_=ranked_candidates(cards,word,unit)
            for item in ranked[:3]:
                card=cby[item['card_id']]
                for fi in range(min(3,len(card['forms']))):targets.append((uid,card['id'],fi,len(word['morphs'])-1,'ending'))
    if variant=='explanation':
        rows=[];seen=set()
        for uid,cid,fi,idx,component in targets:
            if (uid,cid) in seen:continue
            seen.add((uid,cid));info=assess(cby[cid],by[uid],units.get(uid,{}))
            rows.append({'word_id':uid,'source':by[uid]['surface'],'card_id':cid,
                         'politeness_meanings':{'polite':'공손한 말','plain':'높이지 않는 말','unknown':'미확인'},
                         'checks':info['checks'],'blocks':info['blocks']})
        result['condition_explanations']={'origin':'program_condition_comparison','items':rows,
            'placeholder_meaning':'required/resolved/not_yet_verified are design metadata, not a grammatical value',
            'scope':'Only the displayed conditions; not complete correctness.'}
    else:
        rows=[]
        for uid,cid,fi,idx,component in dict.fromkeys(targets):
            word=by[uid];b={'card_id':cid,'form_index':fi,'source_word_id':uid,'morph_index':idx,'component':component}
            edit={'word_ids':[uid],'bindings':[b],'span':[word['start'],word['end']],'before':word['surface']}
            projection=project_edit(edit,morph,cards)
            rows.append({'word_id':uid,'source':word['surface'],'card_id':cid,'form_index':fi,
                         'source_prefix_morphs':word['morphs'][:idx],'target_form':cby[cid]['forms'][fi],
                         'candidate_spellings':projection['candidates'],'origin':projection['status'],'certified':False})
        result['composition_aids']={'items':rows,'selection':'agent: first3 eligible cards x first3 forms per ending; worker: exact selected bindings',
                                   'scope':'Spelling aids only; no new permission, no gold sentences.'}
    assert result['cards']==payload['cards'] and result['grammar']==payload['grammar'] and result['words']==payload['words']
    return result
