"""Versioned, bounded edits. Structural checks are not dialect-quality certification."""
import copy
import hashlib
import json
import re
import unicodedata as ud
from pathlib import Path
from itertools import product
from kg_pipeline.validation import validate_schema

VERSION='card_edits_v3_scoped'
from .scoped_operations import CONFIG_HASH as SCOPE_HASH,scoped_binding,scoped_edit_checks,realize_scoped
INTERPRETATION=json.loads(Path(__file__).with_name('card_interpretation.json').read_text(encoding='utf-8'))
S={'type':'string'}
def obj(p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def arr(x):return {'type':'array','items':x}
BINDING=obj({'card_id':S,'form_index':{'type':'integer','minimum':0},'source_word_id':S,'morph_index':{'type':'integer','minimum':0},'component':{'type':'string','enum':['particle','ending','construction']}})
EDIT=obj({'edit_id':S,'word_ids':arr(S),'bindings':arr(BINDING),'depends_on':arr(S),
          'action':{'type':'string','enum':['apply','keep','needs_review']},'instruction':S,'after':S,'reason':S})
DECISION=obj({'request_id':S,'edits':arr(EDIT),'reason':S})
WORKER=obj({'plan_id':S,'edits':arr(obj({'edit_id':S,'action':{'type':'string','enum':['apply','keep','needs_review']},'after':S,'reason':S})),'reason':S})

def sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def role(card):
    if card['id'] in INTERPRETATION['roles']:return INTERPRETATION['roles'][card['id']]
    if card.get('kind') in ('observation','classification') or not card.get('forms'):return 'reference'
    return 'candidate'  # candidate != certified rewrite

def context(morph,cards,analysis=None,input_id=None):
    ids=[c['id'] for c in cards]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate_card_id')
    data={'contract':VERSION,'interpretation':INTERPRETATION,'scope_operations':SCOPE_HASH,'input_id':input_id,'morphology':morph,'analysis':analysis,'cards':cards}
    return {'contract':VERSION,'request_id':sha(data),'input_id':input_id,
        'card_usage':[{'card_id':c['id'],'role':role(c)} for c in cards],
        'user_restrictions':(['이 입력의 샀어를 샀지/샀제로 바꾸지 않음'] if policy_active(morph['text'],input_id) else [])}

def policy_active(text,input_id):
    return input_id=='DEV002' and text=='집에 가는 길에 빵을 샀어.'

def words_checked(morph):
    by={};previous=0
    for w in morph['words']:
        a,b=w['start'],w['end']
        if w['uid'] in by or type(a)is not int or type(b)is not int or not 0<=a<b<=len(morph['text']) or a<previous or morph['text'][a:b]!=w['surface']:
            raise ValueError('invalid_source_span')
        by[w['uid']]=w;previous=b
    return by

def protected(text):
    return ''.join(c for c in text if c in '\r\n' or ud.category(c)[0] in ('P','S'))

def variants(form):
    """Only explicit literal alternatives; no guesses about unlisted allomorphs."""
    form=form.strip().strip('-')
    if not form:return []
    if re.search(r'[^가-힣ㄱ-ㅎㅏ-ㅣ /()\-]',form):return []
    pieces=form.split('/')
    out=[]
    for p in pieces:
        p=p.strip().strip('-')
        if '-' in p:return []
        m=re.search(r'\(([가-힣]+)\)',p)
        if m:
            if p.count('(')!=1:return []
            out.extend([p[:m.start()]+p[m.end():],p[:m.start()]+m[1]+p[m.end():]])
        elif '(' not in p and ')' not in p:out.append(p)
    return [p.strip() for p in out if p.strip()]

JONG=dict(zip('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ',map(chr,range(0x11a8,0x11c3))))
def decomposed(s):return ''.join(JONG.get(c,ud.normalize('NFD',c)) for c in s)
def form_match(after,form,component):
    options=variants(form)
    if not options:return 'unknown'
    text=decomposed(after)
    for option in options:
        target=decomposed(option)
        if component=='ending' and text.endswith(target):return 'literal_match'
        if component=='particle' and target in text:return 'literal_match'
        if component=='construction' and target in text:return 'literal_match'
    return 'unknown_realization' # contractions may be legitimate; never label mismatch a dialect error

def compose_selected_jamo(after,bindings,cards):
    """Compose only a coda explicitly selected in a literal ending, and log the repair."""
    cby={c['id']:c for c in cards};repairs=[]
    for b in bindings:
        if b['component']!='ending':continue
        for option in variants(cby[b['card_id']]['forms'][b['form_index']]):
            if not option or option[0] not in JONG or not after.endswith(option):continue
            i=len(after)-len(option)
            if i and '가'<=after[i-1]<='힣' and (ord(after[i-1])-0xac00)%28==0:
                old=after;after=after[:i-1]+chr(ord(after[i-1])+ord(JONG[option[0]])-0x11a7)+after[i+1:]
                repairs.append({'kind':'selected_coda_composition','before':old,'after':after,'card_id':b['card_id']})
    return after,repairs

FUNCTIONS={'assertion':['declarative'],'answer':['answer'],'confirmation_question':['confirmation_question'],
    'wh_question':['wh_question'],'polar_question':['polar_question'],'imperative':['request'],
    'request':['request'],'propositive':['propositive'],'prohibition':['prohibition'],
    'cause_or_sequence':['causal'],'contrast':['contrast'],'quotation':['quotation'],'progressive':['progressive'],
    'declarative':['declarative'],'interrogative':['polar_question','wh_question'],'hortative':['propositive']}
def condition_checks(card,units):
    checks=[]
    def walk(value,path='when'):
        if isinstance(value,dict):
            for k,v in value.items():walk(v,path+'.'+k)
        else:
            actual=sorted({f for u in units for f in [*u.get('functions',[]),u.get('discourse_function','unknown')]})
            expected=value if isinstance(value,list) else [value]
            state='not_evaluated'
            if any(v in ('required','resolved','not_yet_verified') for v in expected if isinstance(v,str)):state='missing_value'
            elif path.endswith(('.utterance_function','.construction_sense','.function','.mood_form')):
                known=[f for v in expected if isinstance(v,str) for f in FUNCTIONS.get(v,[])]
                if known:state=('analysis_support' if set(known)&set(actual) else 'analysis_not_supporting') if units else 'analysis_unavailable'
            checks.append({'field':path,'expected':value,'observed_functions':actual,'result':state,'basis':'Qwen_analysis_not_independent_truth'})
    walk(card.get('when',{}));return checks

def nested_values(value,key):
    if not isinstance(value,dict):return []
    out=[]
    for k,v in value.items():
        if k==key:out.extend(v if isinstance(v,list) else [v])
        elif isinstance(v,dict):out.extend(nested_values(v,key))
    return out

def project_edit(edit,morph,cards):
    """Build outputs from explicit source tokens; unknown composition remains unknown."""
    from .suffix_composition import project_suffix
    words={w['uid']:w for w in morph['words']};cby={c['id']:c for c in cards};options={};details=[];scopes=[];legacy_bindings=0
    for wid in edit['word_ids']:
        word=words[wid];bindings=[b for b in edit['bindings'] if b['source_word_id']==wid]
        if not bindings:options[wid]=[word['surface']];continue
        # Multiple changes inside one word require an explicit composition, not last-writer-wins.
        if len(bindings)>1:return {'candidates':[],'status':'compound_word_composition_unavailable'}
        b=bindings[0];card=cby[b['card_id']];forms=variants(card['forms'][b['form_index']]);idx=b['morph_index']
        scoped=scoped_binding(card,b,word,morph['text'])
        if scoped is not None:
            scopes.append(scoped);details.append(scoped);options[wid]=scoped['candidates'];continue
        legacy_bindings+=1
        if b['component']=='particle':
            tokens=word.get('tokens',[])
            t=tokens[idx] if idx<len(tokens) else None
            if not t or not word['start']<=t['start']<t['end']<=word['end']:return {'candidates':[],'status':'particle_span_unavailable'}
            a=t['start']-word['start'];z=t['end']-word['start']
            options[wid]=[word['surface'][:a]+f+word['surface'][z:] for f in forms]
        else:
            if idx!=len(word['morphs'])-1:return {'candidates':[],'status':'nonfinal_suffix_not_supported'}
            info=project_suffix(word,forms);details.append({'word_id':wid,**info});options[wid]=info['candidates']
    count=1
    for opts in options.values():count*=len(opts)
    if not count or count>128:return {'candidates':[],'status':'composition_unavailable_or_too_many','details':details}
    results=[]
    for values in product(*(options[w] for w in edit['word_ids'])):
        result=edit['before']
        for wid,replacement in reversed(list(zip(edit['word_ids'],values))):
            w=words[wid];a=w['start']-edit['span'][0];z=w['end']-edit['span'][0];result=result[:a]+replacement+result[z:]
        results.append(result)
    return {'candidates':list(dict.fromkeys(results)),'status':'source_token_composition','details':details,
            'exact_scoped':bool(scopes) and not legacy_bindings,'scope_operations':scopes}

def audit_edit(edit,morph,cards,analysis=None,input_id=None,realize=True):
    """Return all detected reasons, not just the first error. Never silently repair text."""
    issues=[];checks=[];by={c['id']:c for c in cards};units=[u for u in (analysis or {}).get('units',[]) if u['word_id'] in edit['word_ids']]
    def issue(code,basis='direct'):issues.append({'code':code,'basis':basis})
    before=edit['before'];after=edit['after'];action=edit['action']
    if action!='apply':return issues,checks
    scoped_issues,scoped_checks=scoped_edit_checks(edit,morph,cards,realize)
    issues.extend(scoped_issues);checks.extend(scoped_checks)
    if not edit['bindings']:issue('missing_target_binding')
    slots={}
    for b in edit['bindings']:
        c=by[b['card_id']];form=c['forms'][b['form_index']]
        checks.extend({'card_id':c['id'],**x} for x in condition_checks(c,units))
        if role(c)!='candidate':issue('reference_or_restriction_not_rewrite')
        if form.endswith('-'):issue('bound_form_needs_composition')
        key=(b['source_word_id'],b['morph_index'])
        if key in slots and slots[key]!=form:issue('conflicting_targets')
        slots[key]=form
        if realize:
            match=form_match(after,form,b['component'])
            checks.append({'card_id':c['id'],'form':form,'result':match,'basis':'literal_surface_check_not_grammar_validation'})
            projected=edit.get('suffix_projection',{}).get('candidates',[])
            if not variants(form):issue('card_form_unparsable')
            elif match!='literal_match' and after not in projected and after!=before:issue('target_realization_unverified')
        avoid=set(c.get('avoid',[]))&set(INTERPRETATION['unresolved_avoid'])
        if avoid:issue('unresolved_card_condition')
        if 'whole_word_used_as_suffix' in c.get('avoid',[]):issue('whole_word_not_suffix')
        required=INTERPRETATION['discourse_required'].get(c['id'])
        if required:
            support=[u for u in units if u['word_id']==b['source_word_id'] and u.get('discourse_function') in required and u.get('discourse_evidence','').strip() and u['discourse_evidence'] in morph['text']]
            checks.append({'card_id':c['id'],'field':'discourse','result':'model_evidence_present' if support else 'evidence_unavailable','basis':'model_inference_from_quoted_input_not_independent_confirmation'})
            if not support:issue('function_evidence_insufficient')
        w=next(w for w in morph['words'] if w['uid']==b['source_word_id']);tag=w['morphs'][b['morph_index']][1].split('-')[0]
        expected=[t for sense in nested_values(c.get('when',{}),'particle_sense') for t in INTERPRETATION['particle_tags'].get(sense,[])]
        if expected and tag not in expected:issue('particle_function_disagreement','Kiwi_tag_disagreement')
        kinds=nested_values(c.get('when',{}),'predicate_kind');tags={t.split('-')[0] for _,t in w['morphs']}
        accepted={'verb':{'VV','VX'},'action_verb':{'VV','VX'},'adjective':{'VA'},'copula':{'VCP'},'negative_copula':{'VCN'},'existential':{'VA','VV'}}
        allowed=set().union(*(accepted[k] for k in kinds if k in accepted)) if kinds else set()
        if allowed and not allowed&tags:issue('predicate_kind_disagreement','Kiwi_tag_disagreement')
    if any(c.get('result')=='analysis_not_supporting' for c in checks):issue('function_not_supported','analysis_disagreement')
    if policy_active(morph['text'],input_id) and edit['span'][0]<=12 and edit['span'][1]>=14:
        targets=[by[b['card_id']]['forms'][b['form_index']].strip('-') for b in edit['bindings']]
        if any(t in ('지','제') for t in targets) or any(t in after for t in ('샀지','샀제')):issue('user_restricted_conversion')
    projection=edit.get('suffix_projection',{})
    if len(edit['bindings'])>1 and not projection.get('candidates'):issue('compound_edit_composition_unverified')
    if len(edit['word_ids'])>1 and not projection.get('candidates'):issue('multiword_boundary_unproven')
    if not realize:return issues,checks
    if not after.strip():issue('empty_realization')
    if protected(before)!=protected(after):issue('protected_punctuation_changed')
    if any(ud.category(c)=='Cc' and c not in '\r\n\t' for c in after):issue('control_character_in_output')
    if after!=before:
        projected=edit.get('suffix_projection',{}).get('candidates',[])
        if projected and after not in projected:
            from .suffix_composition import preservation_check
            source_words=[w for w in morph['words'] if w['uid'] in edit['word_ids']]
            preservation=preservation_check(source_words,after)
            checks.append({'field':'lexical_and_prefinal_preservation',**preservation})
            if preservation['status']=='analysis_disagreement':issue('source_suffix_composition_disagreement','Kiwi_reanalysis_warning_not_semantic_truth')
            elif len(edit['word_ids'])>1:issue('multiword_composition_unverified')
            else:checks.append({'field':'suffix_spelling','result':'alternative_surface_unverified','basis':'does_not_equal_Kiwi_projection_not_necessarily_incorrect'})
        if len(edit['word_ids'])==1 and len(after.split())>1 and not any(' ' in by[b['card_id']]['forms'][b['form_index']] for b in edit['bindings']):issue('unlicensed_word_expansion')
        jamo=lambda s:[c for c in s if '\u3131'<=c<='\u318e' or '\u1100'<=c<='\u11ff']
        if jamo(after)!=jamo(before):issue('new_unjoined_jamo')
        source_words=[w for w in morph['words'] if w['uid'] in edit['word_ids']]
        # Common uncontracted joins, not an exhaustive morphological validator.
        for w in source_words:
            parts=w.get('morphs',[])
            for (stem,tag),(past,ptag) in zip(parts,parts[1:]):
                if tag.split('-')[0] in ('VV','VA') and ptag=='EP' and past in ('었','았') and stem and '가'<=stem[-1]<='힣':
                    n=ord(stem[-1])-0xac00;v=(n//28)%21
                    if n%28==0 and v in (0,4) and stem+past in after and stem+past not in before:
                        issue('uncontracted_join_suspected','morphology_based_warning')
            if any(tag.endswith('-I') and stem and (ord(stem[-1])-0xac00)%28==17 for stem,tag in parts if '가'<=stem[-1:]<='힣') and re.search('우[아어]',after):
                issue('irregular_join_suspected','morphology_based_warning')
        # Particle-only operations cannot replace the noun or its other particles.
        if edit['bindings'] and all(b['component']=='particle' for b in edit['bindings']) and len(source_words)==1:
            allowed=edit.get('suffix_projection',{}).get('candidates',[])
            if after not in allowed:issue('particle_edit_changes_other_material' if allowed else 'particle_span_unavailable')
        # Unambiguous separate negators must not vanish; contractions are not judged by EP presence.
        for term in ('안','못'):
            if term in before.split() and term not in after.split():issue('separate_negator_removed')
    return issues,checks

def finalize(plan):
    edits=plan['edits'];by={e['edit_id']:e for e in edits}
    # Dependencies form atomic connected groups (not only one-way prerequisites).
    links={k:set() for k in by}
    for e in edits:
        for dep in e['depends_on']:links[e['edit_id']].add(dep);links[dep].add(e['edit_id'])
    seen=set()
    for key in by:
        if key in seen:continue
        group=set();todo=[key]
        while todo:
            k=todo.pop()
            if k in group:continue
            group.add(k);todo.extend(links[k]-group)
        seen|=group
        if len(group)>1 and any(by[k]['outcome']=='needs_review' for k in group):
            for k in group:
                if by[k]['outcome']=='applied':by[k]['outcome']='needs_review';by[k]['issues'].append({'code':'dependency_group_not_applied','basis':'direct'})
    applied=sum(e['outcome']=='applied' for e in edits);held=sum(e['outcome']=='needs_review' for e in edits)
    plan['status']='partial' if applied and held else 'needs_review' if held else 'generated_requires_human_review' if applied else 'unchanged'
    plan['applied_edit_count']=applied;plan['held_edit_count']=held
    plan['held_by_model']=sum(e['outcome']=='needs_review' and e['action']=='needs_review' for e in edits)
    plan['held_by_program']=sum(e['outcome']=='needs_review' and bool(e['issues']) for e in edits)
    plan['dependency_basis']='model_declared_group; missing dependency is not independently detected; unchanged satisfies state-preservation dependency'
    plan['plan_id']=sha({k:v for k,v in plan.items() if k!='plan_id'})
    return plan

def bind_plan(value,morph,cards,realize=True,analysis=None,input_id=None):
    validate_schema(value,DECISION)
    ctx=context(morph,cards,analysis,input_id)
    if value['request_id']!=ctx['request_id']:raise ValueError('stale_request')
    by=words_checked(morph);order={w:i for i,w in enumerate(by)};cby={c['id']:c for c in cards};edits=[];ids=set()
    for source in value['edits']:
        e=copy.deepcopy(source);key=e['edit_id'];words=e['word_ids']
        if not key.strip() or key in ids:raise ValueError('duplicate_edit_id')
        ids.add(key)
        if not words or len(set(words))!=len(words) or any(w not in by for w in words):raise ValueError('invalid_edit_anchor')
        ix=[order[w] for w in words]
        if ix!=list(range(ix[0],ix[0]+len(ix))):raise ValueError('noncontiguous_edit_anchor')
        a=by[words[0]]['start'];z=by[words[-1]]['end'];before=morph['text'][a:z]
        if len(words)>1 and (protected(before) or len({by[w].get('sentence') for w in words})>1):raise ValueError('cross_boundary_edit')
        for b in e['bindings']:
            if b['card_id'] not in cby:raise ValueError('unretrieved_rule_reference')
            if b['form_index']>=len(cby[b['card_id']].get('forms',[])):raise ValueError('invalid_target_index')
            if b['source_word_id'] not in words or b['morph_index']>=len(by[b['source_word_id']].get('morphs',[])):raise ValueError('invalid_binding_source')
            tag=by[b['source_word_id']]['morphs'][b['morph_index']][1].split('-')[0]
            if b['component']=='particle' and not tag.startswith('J'):raise ValueError('binding_not_particle')
            if b['component'] in ('ending','construction') and tag not in ('EF','EC','ETM','ETN'):raise ValueError('binding_not_ending')
        if len({(b['card_id'],b['form_index'],b['component'],b['source_word_id'],b['morph_index']) for b in e['bindings']})!=len(e['bindings']):raise ValueError('duplicate_binding')
        if e['action']=='apply' and not e['instruction'].strip():raise ValueError('empty_instruction')
        e.update(before=before,span=[a,z],rule_ids=list(dict.fromkeys(b['card_id'] for b in e['bindings'])),surface_origin='qwen_composition',boundary_basis='contiguous_original_words_not_syntactic_proof')
        e['proposed_after']=e['after'];e['repairs']=[]
        if realize and e['action']=='apply':e['after'],e['repairs']=compose_selected_jamo(e['after'],e['bindings'],cards)
        e['analysis_evidence']={'origin':'Qwen_analysis','units':[u for u in (analysis or {}).get('units',[]) if u['word_id'] in words]}
        e['suffix_projection']=project_edit(e,morph,cards) if e['bindings'] else {'candidates':[],'status':'no_binding'}
        if realize and e['action']=='apply':realize_scoped(e)
        issues,checks=audit_edit(e,morph,cards,analysis,input_id,realize)
        candidates=e.get('suffix_projection',{}).get('candidates',[])
        mechanical={'uncontracted_join_suspected','irregular_join_suspected'}
        if realize and e['action']=='apply' and len(candidates)==1 and any(i['code'] in mechanical for i in issues):
            proposed=e['after'];e['after']=candidates[0]
            e['repairs'].append({'kind':'source_morph_suffix_composition','before':proposed,'after':e['after'],'basis':'Kiwi projection preserving source morph sequence; not meaning validation'})
            issues,checks=audit_edit(e,morph,cards,analysis,input_id,realize)
        e.update(issues=issues,condition_checks=checks,outcome='needs_review' if issues or e['action']=='needs_review' else 'kept' if e['action']=='keep' else 'unchanged' if realize and e['after']==before else 'applied' if realize else 'planned')
        edits.append(e)
    edits.sort(key=lambda e:e['span'][0])
    if any(a['span'][1]>b['span'][0] for a,b in zip(edits,edits[1:])):raise ValueError('overlap')
    for e in edits:
        if len(set(e['depends_on']))!=len(e['depends_on']) or any(d not in ids or d==e['edit_id'] for d in e['depends_on']):raise ValueError('invalid_dependency')
    plan={'contract':VERSION,'request_id':ctx['request_id'],'input_hash':sha(morph['text']),'edits':edits,'reason':value['reason'],'realized':realize}
    if realize:return finalize(plan)
    plan['plan_id']=sha(plan);return plan

def realize_plan(plan,answer,morph,cards,analysis=None,input_id=None):
    validate_schema(answer,WORKER)
    if plan['plan_id']!=sha({k:v for k,v in plan.items() if k!='plan_id'}):raise ValueError('mutated_plan')
    if answer['plan_id']!=plan['plan_id']:raise ValueError('stale_worker_plan')
    answers={e['edit_id']:e for e in answer['edits']}
    if len(answers)!=len(answer['edits']) or set(answers)!={e['edit_id'] for e in plan['edits']}:raise ValueError('worker_plan_mismatch')
    edits=[]
    for e in plan['edits']:
        a=answers[e['edit_id']];v={k:copy.deepcopy(e[k]) for k in EDIT['properties']}
        v['action']=e['action'] if e['action']!='apply' else a['action']
        v['after']=a['after'];v['reason']=a['reason'];edits.append(v)
    result=bind_plan({'request_id':plan['request_id'],'edits':edits,'reason':answer['reason']},morph,cards,analysis=analysis,input_id=input_id)
    previous={e['edit_id']:e for e in plan['edits']}
    for e in result['edits']:
        old=previous[e['edit_id']]
        if old['issues']:
            e['issues']=[*old['issues'],*e['issues']];e['outcome']='needs_review'
    return finalize(result)

def assemble(text,plan):
    if not plan.get('realized'):raise ValueError('unrealized_plan')
    if sha(text)!=plan['input_hash'] or plan['plan_id']!=sha({k:v for k,v in plan.items() if k!='plan_id'}):raise ValueError('mutated_or_stale_plan')
    result=text
    for e in reversed(plan['edits']):
        if text[e['span'][0]:e['span'][1]]!=e['before']:raise ValueError('stale_source_span')
        if e['outcome']=='applied':result=result[:e['span'][0]]+e['after']+result[e['span'][1]:]
    return result
