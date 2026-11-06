"""Transparent exclusions for unrefined references, not grammatical approval.

Whole-graph lexical matches remain in retrieval traces. These checks only reject
demonstrably mismatched generation references; unknown source conditions remain
unknown and cannot become an executable rule through this module.
"""
import re
import json

MODULE_KINDS={1:{'predicate','construction'},2:{'predicate','construction'},
              3:{'nominal'},4:{'particle'},5:{'predicate','construction'},
              6:{'predicate','construction'},7:{'connector'},
              8:{'predicate','connector','construction'},9:{'predicate','construction'}}
VOWELS='ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'

def exact_anchor(anchor,text):
    return bool(re.search(r'(?<![가-힣])'+re.escape(anchor)+r'(?![가-힣])',text))

def reference_exclusion(node,unit,reference):
    p=node['properties'];spec=p.get('original_spec',{});title=node.get('title','')
    condition=spec.get('documentary_condition_before_normalization',{})
    kinds=MODULE_KINDS.get(p.get('module'))
    # Module12 contains a regional inventory of different parts of speech.
    if p.get('module')==12:
        if title.startswith('조사/'):kinds={'particle'}
        elif title.startswith(('대명사/','수사/','명사/')):kinds={'nominal'}
    if kinds and unit['kind'] not in kinds:return 'module_unit_mismatch'
    observed=unit.get('observed',{})
    if unit['kind'] in ('nominal','particle','connector') and 'source_form' in observed:
        own={str(observed.get(k,'')).strip('-') for k in ('source_form','lemma')}
        if not own.intersection(reference['matched_anchors']):return 'anchor_belongs_to_other_morpheme'
    if '→' in title:
        input_side=title.split('→',1)[0]
        if not any(exact_anchor(a,input_side) for a in reference['matched_anchors']):
            return 'no_input_side_anchor'
    lemma=unit.get('observed',{}).get('lemma','')
    if lemma and 0xac00<=ord(lemma[-1])<=0xd7a3:
        index=ord(lemma[-1])-0xac00
        vowel=condition.get('stem_last_vowel')
        if isinstance(vowel,str) and len(vowel)==1 and vowel in VOWELS and vowel!=VOWELS[(index//28)%21]:
            return 'documented_stem_vowel_mismatch'
        if condition.get('stem_coda')=='NO_CODA' and index%28:
            return 'documented_stem_coda_mismatch'
        if condition.get('stem_coda')=='present' and not index%28:
            return 'documented_stem_coda_mismatch'
    return None

def select_references(reader,units,traces,actions,char_budget=24000):
    """Use complete recorded matches, then reject mismatches before top-three.

    The budget and top-three cap are held at the prior values. Unicode JSON
    compact serialization matches the existing packet builder's accounting.
    """
    compact=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    used=sum(len(compact(a)) for a in actions)
    selected=[];omitted=[];index={u['id']:u for u in units}
    for tr in traces:
        count=0;u=index[tr['unit_id']]
        for ref in tr['legacy_candidates']:
            # Edge/span hashes and repeated bookkeeping remain in retrieval.json.
            # They are not linguistic instructions for the generator.
            sources=[]
            for src in ref.get('document_refs',[]):
                sources.append({'doc':src.get('document_id',src.get('doc')),
                                'pages':src.get('pdf_pages',src.get('pdf_page',src.get('page')))})
            record={'unit_id':u['id'],'source_id':ref['source_id'],'title':ref['title'],
                    'matched_anchors':ref['matched_anchors'],'sources':sources}
            reason=reference_exclusion(reader.nodes[ref['source_id']],u,ref)
            if reason is None:
                count+=1
                if count>3:reason='unrefined_reference_top3_policy'
                elif used+len(compact(record))>char_budget:reason='delivery_character_budget'
            if reason:omitted.append({'unit_id':u['id'],'source_id':ref['source_id'],'reason':reason})
            else:selected.append(record);used+=len(compact(record))
    return selected,omitted
