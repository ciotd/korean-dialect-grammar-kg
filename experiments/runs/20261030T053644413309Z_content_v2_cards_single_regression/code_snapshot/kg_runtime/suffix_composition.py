"""Reusable suffix composition from source morphs. Kiwi is a helper, not a dialect oracle."""
import threading
_lock=threading.RLock()
_kiwi=None

def preservation_check(source_words,after):
    """Compare only observable source lexical/prefinal analyses; absent tags are a warning."""
    global _kiwi
    def signature(parts):
        result=[]
        for form,tag in parts:
            tag=tag.split('-')[0]
            if tag in ('VV','VX','VA','VCP','VCN','NNG','NNP','NP','NR','NNB','EP') or (tag=='MAG' and form in ('안','못')):
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
            candidates=[]
            jong=dict(zip('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ',map(chr,range(0x11a8,0x11c3))))
            for target in targets:
                if not target:continue
                # Kiwi expects a final jamo, not a compatibility jamo, for coda endings.
                target=jong.get(target[0],target[0])+target[1:]
                candidate=_kiwi.join([tuple(p) for p in parts[:idx]]+[(target,tag)])
                if candidate not in candidates:candidates.append(candidate)
            return {'candidates':candidates,'status':'kiwi_projection','source_morphs':parts,
                    'note':'Source morph analysis and suffix choice may be wrong; no contextual correctness claim.'}
    except (ImportError,ValueError,RuntimeError) as exc:
        return {'candidates':[],'status':'composition_unavailable','error_type':type(exc).__name__}
