"""Conservative, auditable alignment of model features to observable source form.

No sentence IDs, reference translations, or inferred replacement morphs. Lack of
surface evidence means unverified, not a proven negative linguistic judgment.
"""
import copy,re
from .scoped_operations import inside_explicit_quote

VERSION='source_feature_alignment_v1'
PLAIN={'아','어','야','지','자','다','냐','나','니','라','더라','거든','네','ᆯ게','을게'}
FORMAL={'습니다','ㅂ니다','ᆸ니다','습니까','ㅂ니까','ᆸ니까','십시오','ㅂ시오','ᆸ시오'}
FUNCTION_CONCEPTS={'negation':{'G_NEG_COPULA','G_NEG_LONG','G_NEG_SCOPE','G_NEG_SHORT','G_NEG_PROHIBITIVE'},
                   'progressive':{'G_AUX_PROGRESS'}}

def predicate_kinds(word):
    parts=[(f,t.split('-')[0]) for f,t in word.get('morphs',[])]
    # Only a terminal predicate chain, not a noun with a relative clause inside it.
    boundary=next((i for i in range(len(parts)-1,-1,-1) if parts[i][1] in ('EF','EC','ETM','ETN')),None)
    if boundary is None:return set()
    if any(t not in ('JX',) for _,t in parts[boundary+1:]):return set()
    stem=boundary-1
    while stem>=0 and parts[stem][1]=='EP':stem-=1
    if stem<0:return set()
    tag=parts[stem][1]
    if tag in ('VV','VX'):return {'verb'}
    if tag=='VA':return {'adjective','existential'} if parts[stem][0] in ('있','없') else {'adjective'}
    if tag=='VCP':return {'copula'}
    if tag=='VCN':return {'negative_copula'}
    if tag in ('XSV','XSA') and stem>0 and parts[stem-1][1] in ('NNG','NNP','XR'):
        return {'verb'} if tag=='XSV' else {'adjective'}
    return set()

def source_conflicts(word,units):
    # Report a conflict; never silently replace Kiwi's analysis with an invented one.
    functions={f for u in units if u['word_id']==word['uid'] for f in u.get('functions',[])}
    parts=word.get('morphs',[])
    # Narrow parser disagreement seen in 계세요. 중+이다 is a legitimate
    # progressive construction and must not be blocked merely for containing VCP.
    signature=[(f,t.split('-')[0]) for f,t in parts]
    if 'progressive' in functions and signature[:2]==[('계','NNG'),('이','VCP')]:
        return [{'code':'source_analysis_conflict','basis':'Qwen_progressive_vs_Kiwi_copula','word_id':word['uid']}]
    return []

def sentence_words(morph,w):
    # A punctuation-delimited source window avoids spreading a later negation backwards.
    start=max([m.end() for m in re.finditer(r'[.!?\n]',morph['text'][:w['start']])]+[0])
    stop=re.search(r'[.!?\n]',morph['text'][w['end']:]);end=w['end']+stop.start() if stop else len(morph['text'])
    return [x for x in morph['words'] if start<=x['start'] and x['end']<=end]

def feature_support(w,window):
    """Local overt anchors only; existence is not semantic validation of scope."""
    own=[(f,t.split('-')[0]) for f,t in w['morphs']]
    neg=any((f in ('안','못') and t=='MAG') or (f in ('않','말') and t=='VX') or t=='VCN' or (f=='없' and t=='VA') or (f in ('모르','못하') and t=='VV') for f,t in own)
    i=next(i for i,x in enumerate(window) if x['uid']==w['uid'])
    if i and predicate_kinds(w):
        prev=[(f,t.split('-')[0]) for f,t in window[i-1]['morphs']]
        neg=neg or prev in ([('안','MAG')],[('못','MAG')])
    nearby=window[max(0,i-1):i+2]
    ps=[(f,t.split('-')[0],x['uid']) for x in nearby for f,t in x['morphs']]
    progress=any(f=='고' and t=='EC' and nf in ('있','계시') and nt in ('VV','VX','VA') and w['uid'] in (wid,nwid)
        for (f,t,wid),(nf,nt,nwid) in zip(ps,ps[1:]))
    progress=progress or any(f=='중' and t=='NNB' for f,t in own) and any(t=='VCP' for f,t in own)
    return neg,progress

def reconcile_analysis(value,morph,concepts):
    result=copy.deepcopy(value);by={w['uid']:w for w in morph['words']};changes=[];unverified=[];conflicts=[]
    for u in result['units']:
        w=by[u['word_id']];parts=[(f,t.split('-')[0]) for f,t in w['morphs']]
        conflicts.extend(source_conflicts(w,[u]))
        if inside_explicit_quote(morph['text'],w['start']):continue
        endings=[f for f,t in parts if t=='EF']
        terminal=bool(endings) and (parts[-1][1]=='EF' or parts[-1]==('요','JX'))
        if terminal:
            level='formal' if endings[-1] in FORMAL else 'polite' if w['surface'].endswith('요') else 'plain' if endings[-1] in PLAIN else None
            if level is not None and u.get('politeness')!=level:
                changes.append({'word_id':w['uid'],'field':'politeness','before':u.get('politeness'),'after':level,'basis':'explicit_terminal_form','surface':w['surface']})
                u['politeness']=level
        window=sentence_words(morph,w);negative,progress=feature_support(w,window)
        for function,supported in [('negation',negative),('progressive',progress)]:
            if function not in u['functions'] or supported:continue
            # An observed parser conflict needs explicit repair, not removal of the opposing interpretation.
            if function=='progressive' and source_conflicts(w,[u]):continue
            removed=[c for c in u['concept_ids'] if c in FUNCTION_CONCEPTS[function]]
            unverified.append({'word_id':w['uid'],'function':function,'status':'unverified_not_false','basis':'no_local_explicit_marker',
                               'original_concept_ids':removed,'source_window':[x['uid'] for x in window]})
            u['functions']=[f for f in u['functions'] if f!=function] or ['other']
            u['concept_ids']=[c for c in u['concept_ids'] if c not in removed]
        # Only a simple unembedded question. Do not generalize a wh word through relative/quoted clauses.
        if terminal and 'polar_question' in u['functions']:
            anchors=[x for x in window if any(f in ('왜','어디','언제','어떻게','몇') for f,t in x.get('morphs',[])) and x['start']<=w['start']]
            tail=morph['text'][w['end']:].lstrip()
            if anchors and tail.startswith('?'):
                between=[x for x in window if anchors[-1]['start']<=x['start']<w['start']]
                embedded=any(t.split('-')[0] in ('EC','ETM','ETN') for x in between for f,t in x['morphs'])
                if not embedded:
                    u['functions']=list(dict.fromkeys('wh_question' if f=='polar_question' else f for f in u['functions']))
                    u['concept_ids']=[c for c in u['concept_ids'] if c!='G_Q_POLAR']
                    if 'G_Q_WH' in concepts and 'G_Q_WH' not in u['concept_ids']:
                        if len(u['concept_ids'])<3:u['concept_ids'].append('G_Q_WH')
                    changes.append({'word_id':w['uid'],'field':'functions','before':'polar_question','after':'wh_question','basis':'unembedded_wh_in_same_question'})
    result['source_alignment']={'version':VERSION,'unverified_functions':unverified,'changes':changes,'source_conflicts':conflicts}
    report={'version':VERSION,'changes':changes,'unverified_functions':unverified,'source_conflicts':conflicts,
            'origin':'program_alignment_of_saved_model_analysis; not new Qwen analysis','concept_policy':'only directly associated unsupported IDs removed; other concepts not semantically certified'}
    return result,report
