"""Reusable suffix composition from source morphs. Kiwi is a helper, not a dialect oracle."""
import threading
_lock=threading.RLock()
_kiwi=None

def literal_vowel_join(edit,morph,cards):
    if len(edit['bindings'])!=1 or len(edit['word_ids'])!=1:return False
    b=edit['bindings'][0]
    if b['component'] not in ('ending','construction'):return False
    w=next(w for w in morph['words'] if w['uid']==b['source_word_id']);parts=w['morphs'];idx=b['morph_index']
    if idx!=len(parts)-1 or idx!=1 or parts[0][1].split('-')[0] not in ('VV','VA'):return False
    stem=parts[0][0];card=next(c for c in cards if c['id']==b['card_id'])
    target=card['forms'][b['form_index']].strip('-')
    if not stem or not target:return False
    return (stem[-1],target[0]) in (('오','아'),('우','어')) and edit['after']==stem+target

def preservation_check(source_words,after):
    """Compare only observable source lexical/prefinal analyses; absent tags are a warning."""
    global _kiwi
    def signature(parts):
        result=[]
        for form,tag in parts:
            tag=tag.split('-')[0]
            if tag in ('VV','VX','VA','VCP','VCN','XSV','XSA','NNG','NNP','NP','NR','NNB','EP') or (tag=='MAG' and form in ('안','못')):
                if tag=='EP':form={'았':'PAST','었':'PAST','시':'HON','으시':'HON'}.get(form,form)
                if tag in ('VV','VX'):tag='V'
                result.append((form,tag))
        return result
    before=signature([p for w in source_words for p in w.get('morphs',[])])
    try:
        with _lock:
            if _kiwi is None:
                from kiwipiepy import Kiwi
                _kiwi=Kiwi(num_workers=1)
            parsed=signature([(t.form,t.tag) for t in _kiwi.tokenize(after)])
        it=iter(parsed);missing=[]
        for item in before:
            if not any(item==x for x in it):missing.append(item)
        return {'status':'analysis_preserved' if not missing else 'analysis_disagreement','missing':missing,
                'before':before,'after':parsed,'basis':'Kiwi reanalysis warning, not semantic truth; ending-internal meaning not fully checked'}
    except (ImportError,ValueError,RuntimeError) as exc:return {'status':'unavailable','error_type':type(exc).__name__}

def project_suffix(word,targets):
    """Keep all source morphs except its last ending; return candidate spellings and provenance."""
    global _kiwi
    parts=word.get('morphs',[])
    indices=[i for i,(_,tag) in enumerate(parts) if tag.split('-')[0] in ('EF','EC','ETM','ETN')]
    if not indices or indices[-1]!=len(parts)-1:return {'candidates':[],'status':'source_not_suffix_edit'}
    idx=indices[-1];tag=parts[idx][1].split('-')[0]
    try:
        with _lock:
            if _kiwi is None:
                from kiwipiepy import Kiwi
                _kiwi=Kiwi(num_workers=1)
            candidates=[];allomorphs=[];unadjusted=[]
            jong=dict(zip('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ',map(chr,range(0x11a8,0x11c3))))
            for target in targets:
                if not target:continue
                # Kiwi expects a final jamo, not a compatibility jamo, for coda endings.
                target=jong.get(target[0],target[0])+target[1:]
                # Same conditional ending family: retain source 으 before the
                # dialect m-initial suffix; do not derive a new lexical stem.
                if parts[idx][0]=='으면' and target in ('머','먼','모','몬','마','만'):
                    unadjusted.append(_kiwi.join([tuple(p) for p in parts[:idx]]+[(target,tag)]))
                    allomorphs.append({'source':'으면','target_base':target,'target_with_source_vowel':'으'+target})
                    target='으'+target
                candidate=_kiwi.join([tuple(p) for p in parts[:idx]]+[(target,tag)])
                if candidate not in candidates:candidates.append(candidate)
            return {'candidates':candidates,'status':'kiwi_projection','source_morphs':parts,'source_allomorphs':allomorphs,'unadjusted_candidates':unadjusted,
                    'note':'Source morph analysis and suffix choice may be wrong; no contextual correctness claim.'}
    except (ImportError,ValueError,RuntimeError) as exc:
        return {'candidates':[],'status':'composition_unavailable','error_type':type(exc).__name__}
