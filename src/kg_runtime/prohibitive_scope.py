"""Keep the observed prohibitive auxiliary and any adjacent -지 in place."""
from .function_semantics import terminal_prohibitive

def guard(edits,morph,analysis,cards,realize):
    units={u['word_id']:u for u in (analysis or {}).get('units',[])}
    words=morph['words'];by={w['uid']:w for w in words};cs={c['id']:c for c in cards}
    def values(x):
        if isinstance(x,dict):return [v for item in x.values() for v in values(item)]
        if isinstance(x,list):return [v for item in x for v in values(item)]
        return [x]
    for edit in edits:
        if edit['action']!='apply':continue
        for b in edit['bindings']:
            word=by[b['source_word_id']];unit=units.get(word['uid'],{})
            if 'prohibition' not in unit.get('functions',[]) or not terminal_prohibitive(word) or 'imperative' not in values(cs[b['card_id']].get('when',{})):continue
            issues=[];parts=word['morphs'];idx=b['morph_index']
            if edit['word_ids']!=[word['uid']] or len(edit['bindings'])!=1 or b['component']!='ending' or idx!=len(parts)-1 or parts[idx][1].split('-')[0]!='EF':issues.append('prohibitive_scope_unverified')
            # Prefix-preserving projection or the existing lexical preservation check
            # supports 말; an arbitrary string that drops it is not authorized.
            if realize and edit['after']!=edit['before']:
                projected=edit.get('suffix_projection',{}).get('candidates',[])
                preserved=any(c.get('field')=='lexical_and_prefinal_preservation' and c.get('status')=='analysis_preserved' for c in edit.get('condition_checks',[]))
                if edit['after'] not in projected and not preserved:issues.append('prohibitive_auxiliary_not_preserved')
            wi=next(i for i,w in enumerate(words) if w['uid']==word['uid']);previous=words[wi-1] if wi else None
            companion=previous if previous and previous['sentence']==word['sentence'] and previous.get('morphs',[])[-1]==['지','EC'] else None
            if companion:
                for other in edits:
                    if other is edit or other['action']!='apply' or companion['uid'] not in other['word_ids']:continue
                    if realize and other['after']==other['before']:continue
                    issues.append('prohibitive_companion_edit_unverified')
                    other['issues'].append({'code':'prohibitive_companion_edit_unverified','basis':'observed_ji_mal_scope'})
                    other['outcome']='needs_review'
            edit.setdefault('condition_checks',[]).append({'field':'prohibitive_scope','result':'unverified' if issues else 'source_structure_preserved',
                'auxiliary_word_id':word['uid'],'companion_word_id':companion['uid'] if companion else None,
                'basis':'original 말/VX + terminal ending; surface naturalness not certified'})
            if issues:
                edit['issues'].extend({'code':c,'basis':'observed_ji_mal_scope'} for c in sorted(set(issues)))
                edit['outcome']='needs_review'
