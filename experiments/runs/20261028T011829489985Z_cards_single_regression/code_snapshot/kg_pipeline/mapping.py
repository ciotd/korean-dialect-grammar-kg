"""Explicit linguistic feature -> existing concept mapping. Scores are ordering, not probabilities."""
from .io import load_jsonl
from pathlib import Path

CONSTRUCTION_IDS={
 'trial':'G_AUX_TRIAL','benefactive':'G_AUX_BENEFACTIVE','completion':'G_AUX_COMPLETE',
 'aux_become':'G_AUX_BECOME','main_become':'G_MAIN_BECOME','desire':'G_AUX_DESIRE',
 'obligation':'G_AUX_OBLIGATION','inference':'G_AUX_INFER','passive_derived':'G_PASS_DERIVE',
 'passive_analytic':'G_PASS_ANALYTIC','causative':'G_GE_CAUSATIVE_HA',
 'quote_indirect':'G_QUOTE_INDIRECT','quote_direct':'G_QUOTE_DIRECT','quote_rago_hada':'G_QUOTE_CONTRACTION',
 'retrospective':'G_TAM_RETROSPECT','prospective':'G_TAM_PROSPECTIVE'}
RELATION_IDS={'reason':'G_END_CAUSE','condition':'G_END_CONDITIONAL','purpose':'G_GE_PURPOSE',
 'degree':'G_GE_DEGREE','contrast':'G_END_CONCESSION','concessive':'G_END_CONCESSION',
 'sequence':'G_END_SEQUENCE','simultaneous':'G_END_SIMULTANEOUS','relative':'G_CLAUSE_RELATIVE',
 'nominal':'G_CLAUSE_NOMINAL','quote':'G_QUOTE_BOUNDARY','coordinate':'G_CLAUSE_COORD'}
PARTICLE_IDS={'subject':'G_PARTICLE_SUBJECT','object':'G_PARTICLE_OBJECT','topic':'G_PARTICLE_TOPIC',
 'comparison':'G_PARTICLE_COMPARE','similarity':'G_PARTICLE_COMPARE','dative':'G_PARTICLE_DATIVE',
 'instrument':'G_PARTICLE_INSTRUMENT','coordination':'G_PARTICLE_COORD','focus':'G_PARTICLE_FOCUS',
 'vocative':'G_PARTICLE_VOCATIVE','locative':'G_CASE_ROLE','genitive':'G_CASE_ROLE'}

def map_concepts(analysis,catalog):
    clauses={c['cid']:c for c in analysis['clauses']};rows=[];unknown=[]
    for u in analysis['units']:
        f=u['features'];c=clauses[u['cid']];hits={}
        def add(cid,reason,priority=50):
            if cid not in catalog or catalog[cid]['type'] not in ('AnalysisConcept','GrammarFeature','Construction'):
                raise ValueError('missing_or_invalid_concept:'+cid)
            h=hits.setdefault(cid,{'unit_id':u['uid'],'concept_id':cid,'title':catalog[cid]['title'],'priority':priority,'reasons':[],'origin':'implemented_feature_mapping'})
            h['priority']=max(h['priority'],priority);h['reasons'].append(reason)
        if u['kind']=='predicate':
            add('G_PRED_KIND','predicate unit',10);add('G_VERB_STEM','lemma/stem analysis',10)
            if f.get('predicate_kind')=='verb':add('G_VERB_INFLECTION','predicate_kind=verb',20)
            if f.get('predicate_kind')=='adjective':add('G_ADJ_STATE','predicate_kind=adjective',60)
            if f.get('predicate_kind')=='negative_copula':add('G_NEG_COPULA','negative copula',90)
            if c['parent_cid'] is None:
                add('G_END_FINAL','outer clause predicate',30);add('G_MOOD_FUNCTION','outer clause mood/function',30)
                add('G_REALIZATION_ALLOWLIST','check lexical restrictions on endings',20)
            if c['relation'] in RELATION_IDS:add(RELATION_IDS[c['relation']], 'clause relation='+c['relation'],90)
            for tag in f.get('constructions',[]):
                if tag in CONSTRUCTION_IDS:add(CONSTRUCTION_IDS[tag],'construction='+tag,100)
            q=f.get('question_type')
            if q in ('polar','wh'):
                add('G_Q_POLAR' if q=='polar' else 'G_Q_WH','question_type='+q,90)
                add('G_Q_SCOPE','question scope',80)
            if f.get('politeness') in ('informal','polite'):
                add('G_HON_ADDRESSEE','input politeness='+f['politeness'],40)
            if f.get('subject_honorific')=='yes':add('G_HON_SUBJECT','subject honorific=yes',80)
            if f.get('tense')=='past':add('G_TAM_PAST','tense=past',70)
            if f.get('prefinal_tam')=='present':add('G_TAM_SLOTS','TAM prefinal present',60)
            if f.get('aspect')=='progressive':add('G_AUX_PROGRESS','progressive aspect',90)
            if f.get('aspect')=='result':add('G_AUX_STATE','result aspect',90)
            if f.get('aspect')=='completion':add('G_AUX_COMPLETE','completion aspect',90)
            if f.get('speech_act') in ('intention','promise'):add('G_TAM_MODALITY','speech_act='+f['speech_act'],75)
            neg=f.get('negation');target={'an':'G_NEG_SHORT','mot':'G_NEG_SHORT','long_an':'G_NEG_LONG','long_mot':'G_NEG_LONG','malda':'G_NEG_PROHIBITIVE'}.get(neg)
            if target:add(target,'negation='+neg,90)
        elif u['kind']=='particle':
            tag=f.get('particle_function')
            if tag in PARTICLE_IDS:add(PARTICLE_IDS[tag],'particle_function='+tag,90)
        elif u['kind']=='pronoun':add('G_PRON_PERSON','pronoun person/number',80)
        elif u['kind'] in ('noun','adverb'):add('G_LEX_SENSE','lexical sense lookup',30)
        for k,v in f.items():
            if v=='unknown':unknown.append({'unit_id':u['uid'],'feature':k})
        rows.extend(sorted(hits.values(),key=lambda h:(-h['priority'],h['concept_id'])))
    return {'candidates':rows,'selected_concept_ids':sorted({r['concept_id'] for r in rows}),
      'ranking':'exact construction 100 > specific feature 60-90 > generic concept 10-40; all supported IDs retained',
      'ambiguities':unknown,'mapping_failures':[u['uid'] for u in analysis['units'] if not any(r['unit_id']==u['uid'] for r in rows)]}
