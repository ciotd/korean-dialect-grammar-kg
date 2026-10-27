"""Source-bounded reference selection, not activation of the KG's disabled Rule blueprints.

Every selector below is an explicit implementation interpretation of existing Claim/SourceAtom
data. The original constraints, status and source scope remain in the audit trace.
"""
import json
from .io import dumps

def decoded(node):
    if not node:return {}
    p=node.get('properties_json','{}')
    return json.loads(p) if isinstance(p,str) else p

def decision(claim_id,atom,u,c):
    f=u['features'];tags=f.get('constructions',[]);kind=f.get('predicate_kind');mood=f.get('mood')
    final=c['parent_cid'] is None;informal=f.get('politeness')=='informal';polite=f.get('politeness')=='polite'
    reason=[]
    def gate(test,why):reason.append({'condition':why,'matched':bool(test)});return bool(test)
    def all_gates(*pairs):return all([gate(t,w) for t,w in pairs])
    ok=False;role='realization_reference';forms=None
    if claim_id=='C_D01_01':
        expected='purpose' if atom.get('id')=='GS_GEORO_PURPOSE' else 'degree'
        ok=all_gates((c['relation']==expected,'clause semantic relation='+expected),(not final,'non-final clause'),('aux_become' not in tags,'not auxiliary become'))
    elif claim_id=='C_D01_02':ok=gate('aux_become' in tags,'auxiliary become');role='constraint'
    elif claim_id=='C_D01_03':
        ok=all_gates((final,'outer final'),(f.get('speech_act')=='intention','speaker intention'),(f.get('agent')=='speaker','speaker agent'),(informal,'preserve informal politeness'))
    elif claim_id in ('C_D02_01','C_D02_02'):
        aid=atom.get('id','');expected='wh' if '_WH_' in aid else 'polar'
        allowed=('copula','negative_copula') if claim_id=='C_D02_01' else ('verb','adjective')
        ok=all_gates((final,'outer final'),(mood=='interrogative','interrogative form'),(f.get('speech_act')=='question','information question'),
          (kind in allowed,'predicate class '+str(allowed)),(f.get('question_type')==expected,'question type='+expected),
          (f.get('prefinal_tam')=='absent','no TAM prefinal; narrow source scope'),(informal,'coarse input politeness compatibility'),
          (expected!='wh' or f.get('wh_scope_cid')==u['cid'],'WH variable bound to current clause'))
    elif claim_id=='C_D02_03':
        ok=all_gates((final,'outer final'),(u['lemma']=='오다','lexeme=오다'),(mood=='imperative','imperative form'),(informal,'coarse informal compatibility'),(f.get('subject_honorific')=='no','no subject honorific'))
    elif claim_id=='C_D02_04':
        ok=all_gates((final,'outer final'),(kind=='adjective','adjective'),(f.get('speech_act')=='exclamation','exclamative use'),(informal,'coarse informal compatibility'));forms=['-래이']
    elif claim_id=='C_D02_05':gate(False,'prior command context and promise relation not resolved; defer')
    elif claim_id=='C_D02_06':gate(False,'Claim attests -제이 while linked atom lists -자/-제; do not silently equate');role='constraint'
    elif claim_id=='C_D03_02':
        ok=all_gates(('quote_indirect' in tags or c['relation']=='quote','indirect quotation'),('quote_direct' not in tags,'not protected direct quotation'),
         (any(s in u['anchor']['surface'] for s in ('다고','라고','자고')),'quoted ending within exact target span'))
    elif claim_id=='C_D05_01':
        ok=all_gates((final,'outer final'),(mood=='interrogative','interrogative form'),(f.get('speech_act')=='question','information question'),
          (kind in ('verb','adjective'),'verb or adjective'),(polite,'coarse polite compatibility'),(f.get('prefinal_tam')=='absent','TAM interaction left out in first release'))
    elif claim_id=='C_D05_02':
        ok=all_gates((final,'outer final'),(mood=='declarative','declarative form'),(kind=='adjective','adjective'),(polite,'coarse polite compatibility'),(f.get('prefinal_tam')=='absent','no unverified TAM combination'))
    elif claim_id=='C_D06_03':
        ok=all_gates(('quote_rago_hada' in tags,'exact -라고 하다 construction'),('라고' in u['anchor']['surface'],'whole construction in editable span'));forms=['-라카다']
    elif claim_id=='C_D07_01':ok=all_gates((u['kind']=='particle','particle'),(f.get('particle_function')=='similarity','similarity, not comparison'))
    elif claim_id=='C_D07_02':ok=gate(f.get('particle_function')=='topic','topic particle');role='constraint'
    elif claim_id=='C_D07_03':ok=gate('passive_derived' in tags,'derived passive');role='constraint'
    elif claim_id=='C_D07_04':
        aid=atom.get('id','')
        if aid=='GS_HAM_AUX_COMPLETE':ok=gate(f.get('aspect')=='completion' or 'completion' in tags,'completion construction')
        elif aid=='GS_HAM_AUX_PROGRESS':ok=gate(f.get('aspect')=='progressive','progressive');role='constraint'
        elif aid=='GS_HAM_AUX_SERVICE':ok=gate('benefactive' in tags,'benefactive');role='constraint'
    elif claim_id=='C_D07_05':
        lemmas={'GS_HAM_ADV_MAI':('많이',),'GS_HAM_ADV_LITTLE':('조금','조금만'),'GS_HAM_ADV_BARE':('간신히','겨우'),'GS_HAM_ADV_FULL':('가득',)}
        ok=all_gates((u['kind']=='adverb','adverb'),(u['lemma'] in lemmas.get(atom.get('id'),()),'lexeme-specific semantic mapping'))
    elif claim_id=='C_D07_06':
        ok=all_gates((u['kind']=='pronoun','pronoun'),(f.get('person')=='second','second person'),(f.get('number')=='singular','singular'),(u['lemma']=='너','plain 너; do not demote honorific pronouns'));forms=['니']
    else:gate(False,'source fact exists but no sufficiently narrow implementation selector in this release')
    # Unknown in fields used above cannot accidentally become true. Uncertainty overrides selected units.
    return ok,role,forms,reason

def select_evidence(raw,analysis,mapping,max_chars=24000,max_items=16):
    clauses={c['cid']:c for c in analysis['clauses']}
    unit_concepts={u['uid']:{r['concept_id']:r['priority'] for r in mapping['candidates'] if r['unit_id']==u['uid']} for u in analysis['units']}
    uncertain={x['target_id'] for x in analysis['uncertainties']}
    groups={}
    for row in raw['claim_paths']:
        key=(row['claim']['id'],(row['atom'] or {}).get('id'))
        entry=groups.setdefault(key,{'row':row,'concepts':set(),'paths':[]})
        entry['concepts'].add(row['concept_id']);entry['paths'].append({k:row[k] for k in ('concept_id','concept_edge','span_edge','document_edge','atom_edge')})
    candidates=[];audit=[]
    for (cid,aid),g in sorted(groups.items(),key=lambda x:str(x[0])):
        row=g['row'];cp=decoded(row['claim']);sp=decoded(row['span']);atom=row['atom'] or {};ap=decoded(atom);spec=ap.get('original_spec',{})
        for u in analysis['units']:
            shared=g['concepts'] & unit_concepts[u['uid']].keys()
            if not shared:continue
            ok,role,forms,conditions=decision(cid,atom,u,clauses[u['cid']])
            if u['uid'] in uncertain or u['cid'] in uncertain:
                ok=False;conditions.append({'condition':'Qwen flagged uncertainty for this unit/clause','matched':False})
            if sp.get('quote_kind')!='curated_exact_span' or not sp.get('quote'):
                ok=False;conditions.append({'condition':'requires curated exact source span','matched':False})
            audit.append({'claim_id':cid,'atom_id':aid,'target_uid':u['uid'],'decision':'selected_candidate' if ok else 'deferred',
              'conditions':conditions,'original_match':spec.get('match'),'original_block':spec.get('block'),
              'original_runtime_active':ap.get('runtime_active'),'original_review_status':ap.get('semantic_review_status')})
            if not ok:continue
            card={'evidence_id':cid+':'+(aid or 'claim')+':'+u['uid'],'claim_id':cid,'atom_id':aid,'target_uid':u['uid'],'role':role,
             'source_fact':cp.get('claim_text'),'source_quote':sp['quote'],'source':{'document_id':row['document_id'],'pdf_page':sp['pdf_page'],'span_id':row['span']['id'],'document_sha256':sp.get('document_sha256')},
             'scope_note':cp.get('scope_note'),'claim_kind':cp.get('claim_kind'),'interpretation_origin':cp.get('interpretation_origin'),
             'forms':forms if forms is not None else spec.get('output',{}).get('forms',[]),
             'source_profile':spec.get('profile',{}),'inherited_match':spec.get('match',{}),
             'runtime_rule_approved':False,'use_mode':'scoped_document_reference',
             'implementation_conditions':conditions,'paths':g['paths'],
             'priority':max(unit_concepts[u['uid']][i] for i in shared)}
            candidates.append(card)
    # Deduplicate by claim+atom+unit, preserve constraints first, then exact-feature relevance.
    candidates.sort(key=lambda x:(x['role']!='constraint',-x['priority'],x['claim_id'],str(x['atom_id']),x['target_uid']))
    selected=[];omitted=[]
    for card in candidates:
        if len(selected)>=max_items or len(dumps(selected+[card]))>max_chars:omitted.append(card['evidence_id'])
        else:selected.append(card)
    # Never give transformation permissions with a known applicable constraint dropped by a budget.
    if any(c['role']=='constraint' and c['evidence_id'] in omitted for c in candidates):
        omitted.extend(c['evidence_id'] for c in selected if c['role']=='realization_reference')
        selected=[c for c in selected if c['role']=='constraint']
    packet={'mode':'source_reference_pilot','evidence':selected,
      'policy':{'region_period':'preserve provenance; no region/age-specific filter; no claim of a unified modern variety',
       'politeness':'coarse input compatibility is an implementation choice, not approved regional register mapping',
       'missing_or_conflicting_evidence':'preserve input; no autonomous dialect invention',
       'unreviewed_design':'retrieved for audit, not authorized for realization',
       'max_items':max_items,'max_chars':max_chars},'omitted_due_to_budget':omitted}
    return packet,{'decisions':audit,'unreviewed_paths_not_forwarded':len(raw['unreviewed_neighborhood']),
      'raw_chars':len(dumps(raw)),'packet_chars':len(dumps(packet)),'budget_omitted':omitted}
