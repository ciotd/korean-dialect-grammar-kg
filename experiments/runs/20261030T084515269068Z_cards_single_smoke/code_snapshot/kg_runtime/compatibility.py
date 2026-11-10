"""Observable source/card compatibility, not a complete Korean grammar validator.

Reads existing card attributes and explicit source→target titles. Unknown register
levels stay unknown. This research policy preserves broad politeness, not an
assertion that standard and dialect speech-level systems are identical.
"""
import re,unicodedata
from .analysis_alignment import PLAIN,FORMAL,predicate_kinds
VERSION='register_connective_v1'
LEVELS={'hae':'plain','haera':'plain','haiso':'polite','haeye':'polite'}
SENSES={'declarative':{'declarative'},'assertion':{'declarative'},'assert':{'declarative'},
 'interrogative':{'polar_question','wh_question'},'imperative':{'request','prohibition'},
 'request':{'request'},'propositive':{'propositive'},'hortative':{'propositive'},
 'contrast':{'contrast'},'cause_or_sequence':{'causal'},'reason':{'causal'},'condition':{'conditional'},
 'quotation':{'quotation'},'intention_or_purpose':{'intention'},'simultaneous':{'simultaneous'},
 'retrospective':{'retrospective'},'promise':{'intention'},'intention':{'intention'}}

def values(obj,keys):
    out=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in keys:out.extend(v if isinstance(v,list) else [v])
            elif isinstance(v,dict):out.extend(values(v,keys))
    return out

def norm(form):
    form=unicodedata.normalize('NFC',form.strip().strip('-').rstrip('?'))
    return form.replace('ㄴ','ᆫ').replace('ㄹ','ᆯ').replace('ㅂ','ᆸ')

def alternatives(label):
    out=[]
    for part in label.split('/'):
        m=re.search(r'\(([^()]*)\)',part)
        out.extend([part[:m.start()]+part[m.end():],part[:m.start()]+m[1]+part[m.end():]] if m else [part])
    return {norm(x) for x in out}

def source_forms(card):
    # Titles explicitly state these correspondences; no title keyword inference.
    title=card.get('title','')
    if card.get('module')=='M07' and ' → ' in title:
        left=title.split(' → ',1)[0]
        if re.fullmatch(r'[-가-힣ㄱ-ㅎ()/ ]+',left):return alternatives(left)
    return set()

def equivalent(form):
    n=norm(form)
    # Orthographic allomorphs of the SAME source ending; never equate 는데 and 지만.
    families=[{'아서','어서','여서'},{'아도','어도','여도'},{'니까','으니까'},{'면','으면'},
              {'려고','으려고'},{'려','으려'},{'면서','으면서'}]
    for family in families:
        if n in family:return family
    return {n}

def source_level(word,unit):
    parts=[(f,t.split('-')[0]) for f,t in word.get('morphs',[])]
    ef=[f for f,t in parts if t=='EF']
    if not ef:return 'unknown'
    if parts[-1][1]!='EF' and parts[-1]!=('요','JX'):return 'unknown'
    if ef[-1] in FORMAL:return 'polite'
    if word['surface'].endswith('요'):return 'polite'
    if ef[-1] in PLAIN:return 'plain'
    return {'formal':'polite','polite':'polite','plain':'plain'}.get(unit.get('politeness'),'unknown')

def assess(card,word,unit):
    checks=[];blocks=[];score=0;when=card.get('when',{});parts=word.get('morphs',[])
    def check(field,state,observed,expected):checks.append(dict(field=field,result=state,observed=observed,expected=expected))
    expected=source_forms(card)
    if expected:
        ends=[f for f,t in parts if t.split('-')[0]=='EC']
        match=bool(ends) and bool(equivalent(ends[-1])&expected)
        check('source_connective','match' if match else 'mismatch',ends,sorted(expected))
        if not match:blocks.append('source_connective_mismatch')
        else:score+=40
    levels=values(when,{'target_register.level_id','target_level','source_level'})
    # In this catalog documentary source_level is the attested dialect register.
    target={LEVELS[x] for x in levels if isinstance(x,str) and x in LEVELS}
    source=source_level(word,unit)
    if levels:
        state='unknown' if source=='unknown' or not target else 'match' if source in target else 'mismatch'
        check('politeness',state,source,levels)
        if state=='mismatch':blocks.append('politeness_mismatch')
        elif state=='match':score+=12
    explicit=values(when,{'input_politeness'})
    if explicit and source!='unknown':
        matched=source in explicit
        check('input_politeness','match' if matched else 'mismatch',source,explicit)
        if not matched:blocks.append('politeness_mismatch')
        else:score+=12
    kinds=values(when,{'predicate_kind'});known={k for k in kinds if isinstance(k,str)}&{'verb','action_verb','adjective','copula','negative_copula'}
    if known:
        known={'verb' if k=='action_verb' else k for k in known};observed=predicate_kinds(word)
        if not known&observed:blocks.append('predicate_kind_disagreement')
        else:score+=3
    functions=set(unit.get('functions',[]));wanted=values(when,{'mood_form','utterance_function','construction_sense'})
    for want in wanted:
        mapped=SENSES.get(want) if isinstance(want,str) else None
        if not mapped:continue
        matched=bool(mapped&functions)
        check('function','match' if matched else 'unknown',sorted(functions),want)
        if matched:score+=8
        # Source spelling is binding evidence for connectors; function analysis alone is not.
    return {'word_id':word['uid'],'card_id':card['id'],'status':'incompatible' if blocks else 'candidate',
            'blocks':sorted(set(blocks)),'checks':checks,'score':score,'source_forms':sorted(expected)}

def select_compatible(cards,original,analysis,morph,limit=48):
    """Reserve per-target compatible alternatives from the SAME actual query results."""
    by={w['uid']:w for w in morph['words']};perword=[];chosen={};audit=[]
    for unit in analysis['units']:
        w=by[unit['word_id']]
        if not any(t.split('-')[0] in ('EF','EC') for _,t in w['morphs']):continue
        evaluations=[assess(c,w,unit) for c in cards if c.get('forms') and c.get('kind') in ('design_rule','realization_inventory')]
        good=[e for e in evaluations if not e['blocks'] and any(x['field'] in ('function','source_connective') and x['result']=='match' for x in e['checks'])]
        # Do not rank general endings over exact connector source correspondences.
        if any(t.split('-')[0]=='EC' for _,t in w['morphs']) and not any(t.split('-')[0]=='EF' for _,t in w['morphs']):
            good=[e for e in good if e['source_forms']]
        good.sort(key=lambda e:(-e['score'],e['card_id']))
        ids=[e['card_id'] for e in good[:3]];perword.append({'word_id':w['uid'],'source':w['surface'],'alternatives':ids,
            'status':'candidates_found_not_certified' if ids else 'no_compatible_alternative_identified'})
        audit.extend(evaluations)
    cby={c['id']:c for c in cards}
    # Round-robin, so a long sentence cannot consume the budget at its first word.
    for i in range(3):
        for item in perword:
            if i<len(item['alternatives']) and len(chosen)<limit:
                cid=item['alternatives'][i];chosen.setdefault(cid,cby[cid])
    for c in original:
        if len(chosen)>=limit:break
        chosen.setdefault(c['id'],cby[c['id']])
    return list(chosen.values()),{'version':VERSION,'limit':limit,'per_word':perword,'assessments':audit,
        'scope':'same retrieved graph nodes; candidate is not fully validated; unknown register not forced into a class',
        'original_ids':[c['id'] for c in original],'delivered_ids':list(chosen)}

def guidance(cards,analysis,morph):
    by={w['uid']:w for w in morph['words']};out=[]
    for unit in analysis['units']:
        w=by[unit['word_id']];bad=[];good=[]
        if not any(t.split('-')[0] in ('EF','EC') for _,t in w['morphs']):continue
        for c in cards:
            if not c.get('forms'):continue
            info=assess(c,w,unit)
            if info['blocks']:bad.append({'card_id':c['id'],'reasons':info['blocks']})
            elif info['score']>0:good.append(info)
        good.sort(key=lambda e:(-e['score'],e['card_id']))
        if good or bad:out.append({'word_id':w['uid'],'surface':w['surface'],'source_politeness':source_level(w,unit),
            'candidate_card_ids':[e['card_id'] for e in good[:3]],'incompatible_examples':bad[:6],'incompatible_count':len(bad)})
    return out
