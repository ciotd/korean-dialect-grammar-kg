"""One morphology provider switch, shared units and downstream contracts.

This is a diagnostic adapter, not a replacement for the default pipeline.
Sentence/clause boundaries are frozen independently from the two providers.
"""
import copy
import re
from .integrated import observe_units
from .multi_agent import TAG_MEANINGS, STRUCTURE_FIELDS, obj, arr, string, word_anchors
from .validation import validate_schema, ValidationError

MORPH_PROMPT='''한국어 형태소 분석만 수행한다. 번역·문법 의미 판단·규칙 선택은 하지 않는다.
입력의 모든 어절 ID를 정확히 한 번씩 반환하고, 어절 안의 형태소를 순서대로 기본형(form)과 품사(tag)로 나눈다. 어미의 축약은 기본형으로 복원하고 선어말 어미를 누락하지 않는다. 어간은 -다를 붙이지 않은 형태다. 본용언·보조용언·파생 접미사·어근·명사·조사·어미를 구별한다. 동사 어간은 VV, 형용사 어간은 VA, 보조용언은 VX이며 어간이라는 이유만으로 XR로 쓰지 않는다. 연결/종결 어미를 임의의 음절별로 나누지 않는다. 이번 공통 표기 규약에서 아요/어요/에요/ㄹ게요는 각각 하나의 종결어미 EF로 둔다. 문장에 없는 형태소를 추가하지 않는다. 문장 전체를 문맥으로 읽되 새로운 어절이나 위치를 만들지 않는다. 모르겠으면 UNKNOWN 품사와 uncertainties에 이유를 남긴다. JSON만 반환한다.'''

def anchors(text):
    whitespace=word_anchors(text)
    result=[]
    for i,m in enumerate(re.finditer(r'[^\s.,!?…“”"\[\]()]+',text)):
        containing=[w for w in whitespace if w['span'][0]<=m.start()<m.end()<=w['span'][1]]
        if len(containing)!=1:raise ValidationError('word_anchor_ambiguity')
        result.append({'uid':f'W{i+1}','surface':m.group(),'start':m.start(),'end':m.end(),'sentence':containing[0]['sentence']})
    return result

def contract(words):
    return obj({'words':arr(obj({'word_id':string([w['uid'] for w in words]),
        'morphs':arr(obj({'form':string(),'tag':string(list(TAG_MEANINGS))}),minItems=1)}),minItems=1),
        'uncertainties':arr(string())})

def kiwi_rows(text,words,kiwi):
    tokens=kiwi.tokenize(text)
    rows=[]
    for w in words:
        parts=[{'form':t.form,'tag':t.tag.split('-')[0]} for t in tokens
               if w['start']<=t.start<w['end'] and t.tag.split('-')[0] not in ('SF','SP','SSO','SSC')]
        # Unsupported tags are recorded, not guessed as a known linguistic tag.
        rows.append({'word_id':w['uid'],'morphs':[dict(m,tag=m['tag'] if m['tag'] in TAG_MEANINGS else 'UNKNOWN') for m in parts]})
    raw={'words':rows,'uncertainties':[]}
    validate_schema(raw,contract(words))
    return raw

def frozen_clauses(text,raw):
    words={w['id']:w for w in word_anchors(text)}
    clauses=[{**c,'span':[words[c['start_word']]['span'][0],words[c['end_word']]['span'][1]]} for c in raw['clauses']]
    if not clauses or len({c['id'] for c in clauses})!=len(clauses):raise ValidationError('invalid_frozen_clauses')
    for c in clauses:
        if c['span'][0]>=c['span'][1]:raise ValidationError('reversed_frozen_clause')
        parent=c['parent_id'];seen={c['id']};index={x['id']:x for x in clauses}
        while parent is not None:
            if parent not in index or parent in seen:raise ValidationError('invalid_frozen_parent')
            seen.add(parent);p=index[parent]
            if not p['span'][0]<=c['span'][0]<c['span'][1]<=p['span'][1]:raise ValidationError('frozen_clause_outside_parent')
            parent=p['parent_id']
    if any(not any(c['span'][0]<=w['span'][0]<w['span'][1]<=c['span'][1] for c in clauses) for w in words.values()):raise ValidationError('uncovered_frozen_word')
    return clauses

def prepare(text,words,raw,clauses,backend):
    validate_schema(raw,contract(words))
    mapping={r['word_id']:r for r in raw['words']}
    if len(mapping)!=len(raw['words']) or set(mapping)!={w['uid'] for w in words}:raise ValidationError('word_missing_duplicate')
    assembled=[]
    for w in words:
        ts=[{'form':m['form'],'tag':m['tag'],'base_tag':m['tag']} for m in mapping[w['uid']]['morphs']]
        if any(not t['form'].strip() for t in ts):raise ValidationError('empty_morph')
        endings=[t for t in ts if t['base_tag'] in ('EF','EC','ETM','ETN')]
        ending=endings[-1] if endings else {}
        assembled.append({**w,'tokens':ts,'morphs':[[t['form'],t['tag']] for t in ts],
            'ending':ending.get('form'),'ending_tag':ending.get('base_tag')})
    units=observe_units({'text':text,'words':assembled})
    unknown_words={w['uid'] for w in assembled if any(t['tag']=='UNKNOWN' for t in w['tokens'])}
    clause_index={c['id']:c for c in clauses}
    def depth(c):
        result=0
        while c.get('parent_id') is not None:result+=1;c=clause_index[c['parent_id']]
        return result
    for u in units:
        containing=[c for c in clauses if c['span'][0]<=u['span'][0]<u['span'][1]<=c['span'][1]]
        if not containing:raise ValidationError('unit_outside_frozen_clause')
        priority=lambda c:(c['span'][1]-c['span'][0],-depth(c))
        containing.sort(key=lambda c:(*priority(c),c['id']));smallest=containing[0]
        scope_ambiguous=len(containing)>1 and priority(containing[0])==priority(containing[1])
        # Only surface morphology; predicate class and honorification stay with meaning worker.
        u['observed']={k:v for k,v in u['observed'].items() if k in STRUCTURE_FIELDS or k=='unit_kind'}
        for k in STRUCTURE_FIELDS:u['observed'].setdefault(k,None)
        u.update(clause_key=smallest['id'],structural_clause_id=smallest['id'],structure_issues=[],
            morphology_judgments=[{'form':f,'tag':t} for f,t in u['morphs']],
            feature_origin={k:'shared_morphology_adapter' for k in u['observed']})
        if unknown_words.intersection(u['related_word_ids']):
            u['structure_issues'].append('unknown_morphology_not_proof_of_absence')
            for k in ('past_form','prefinal_type','prefinal_sequence'):u['observed'][k]=None
        if scope_ambiguous:u['structure_issues'].append('ambiguous_frozen_clause_assignment')
    if not units:raise ValidationError('no_analyzable_units')
    return {'backend':backend,'units':units,'clauses':copy.deepcopy(clauses),'uncertainties':[],
        'diagnostic_uncertainties_not_sent':raw['uncertainties']}
