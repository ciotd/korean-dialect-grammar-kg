"""One operational vocabulary for candidate and edit checks; not a grammar ontology."""
VERSION='function_contract_v1'
FUNCTIONS={
 'assertion':{'declarative'},'assert':{'declarative'},'declarative':{'declarative'},
 'answer':{'answer'},'confirmation_question':{'confirmation_question'},
 'wh_question':{'wh_question'},'polar_question':{'polar_question'},
 'interrogative':{'polar_question','wh_question'},'imperative':{'request'},
 'request':{'request'},'propositive':{'propositive'},'hortative':{'propositive'},
 'prohibition':{'prohibition'},'cause_or_sequence':{'causal'},'reason':{'causal'},
 'condition':{'conditional'},'contrast':{'contrast'},'quotation':{'quotation'},
 'progressive':{'progressive'},'simultaneous':{'simultaneous'},
 'intention':{'intention'},'intention_or_purpose':{'intention'},'promise':{'intention'},
 'speaker_intention_or_promise':{'intention'},'retrospective':{'retrospective'},
 'negation':{'negation'},'conjecture':{'conjecture'}}
FIELDS={'utterance_function','construction_sense','function','mood_form'}

def terminal_prohibitive(word):
    parts=[(f,t.split('-')[0]) for f,t in (word or {}).get('morphs',[])]
    endings=[i for i,(_,t) in enumerate(parts) if t=='EF']
    return bool(endings and ('말','VX') in parts[:endings[-1]])

def accepted(label,word=None):
    result=set(FUNCTIONS.get(label,()))
    # Only an ending on an observed prohibitive auxiliary. Not any negative clause.
    if label=='imperative' and terminal_prohibitive(word):result.add('prohibition')
    return result

def condition_checks(card,units,unverified=(),source_word=None):
    checks=[]
    actual=sorted({f for u in units for f in [*u.get('functions',[]),u.get('discourse_function','unknown')]})
    def walk(value,path='when'):
        if isinstance(value,dict):
            for k,v in value.items():walk(v,path+'.'+k)
            return
        expected=value if isinstance(value,list) else [value];state='not_evaluated'
        if any(v in ('required','resolved','not_yet_verified') for v in expected if isinstance(v,str)):state='missing_value'
        elif path.rsplit('.',1)[-1] in FIELDS:
            known=set().union(*(accepted(v,source_word) for v in expected if isinstance(v,str)))
            if known:
                unsupported=any(not isinstance(v,str) or v not in FUNCTIONS for v in expected)
                broad='intention_or_purpose' in expected
                state=('analysis_support' if known&set(actual) else 'analysis_undetermined' if unsupported or broad else 'analysis_unverified' if known&set(unverified) else 'analysis_not_supporting') if units else 'analysis_unavailable'
        checks.append({'field':path,'expected':value,'observed_functions':actual,'result':state,
                       'basis':'Qwen_analysis_and_observed_source_not_independent_truth'})
    walk(card.get('when',{}))
    return checks

def annotated_units(analysis):
    for unit in analysis.get('units',[]):
        uncertain=[x['function'] for x in analysis.get('source_alignment',{}).get('unverified_functions',[]) if x['word_id']==unit['word_id']]
        yield dict(unit,_unverified_functions=uncertain)
