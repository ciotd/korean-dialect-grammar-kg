"""Bounded semantic retrieval using real graph edges; no LLM or sentence rewriting.

Reuse the previous input contract, but isolate each construction, validate graph
invariants and separate a retrieved usage from a complete generation instruction.
"""
import collections,copy,importlib.util
from sources import ROOT
s=importlib.util.spec_from_file_location('prior',ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/semantic_graph.py')
prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
stable=prior.stable
CONSTRUCTION='SEM_CX_HAERA_INFORMATION_QUESTION'

class Reader(prior.GraphReader):
 def __init__(self,graph,construction=CONSTRUCTION):
  super().__init__(copy.deepcopy(graph));self.family=construction
  if len(self.nodes)!=len(graph['nodes']):raise ValueError('duplicate_node_id')
  if len({e['id'] for e in graph['edges']})!=len(graph['edges']):raise ValueError('duplicate_edge_id')
  for e in self.graph['edges']:
   if e['source'] not in self.nodes or e['target'] not in self.nodes:raise ValueError('dangling_edge')
  if self.nodes.get(construction,{}).get('type')!='GrammarConstruction':raise ValueError('invalid_construction')
  contracts={'HAS_USAGE':('GrammarConstruction','SemanticRule'),'SUPPORTED_IN':('GrammarConstruction','ProcessingScope'),
   'ANY_BRANCH':('SemanticRule','ApplicabilityBranch'),'ALL':('ApplicabilityBranch','Condition'),
   'ACCEPTS':('Condition','FeatureValue'),'REALIZES':('SemanticRule','Realization'),
   'HAS_CONTEXT_NOTE':('SemanticRule','UsageObservation')}
  for e in self.graph['edges']:
   if e['relation'] in contracts and tuple(self.nodes[e[k]]['type'] for k in ('source','target'))!=contracts[e['relation']]:raise ValueError('invalid_edge_type')
   if e['relation']=='SUPPORTED_BY' and self.nodes[e['target']]['type']!='Evidence':raise ValueError('invalid_evidence_edge')
  self.usages=sorted(e['target'] for e in self.links(construction,'HAS_USAGE'))
  self.scope_edges=self.links(construction,'SUPPORTED_IN')
  if not self.usages or len(self.scope_edges)!=1:raise ValueError('missing_construction_membership_or_scope')
  self.policy=self.nodes[self.scope_edges[0]['target']]['properties']['allowed']
  for key,vals in self.policy.items():
   if not vals or any(v not in self.graph['feature_schema'].get(key,[]) for v in vals):raise ValueError('invalid_policy')
  self.branch_owner={};self.branch_checks={};self.required=collections.defaultdict(set);self.matches=collections.defaultdict(set)
  for rid in self.usages:
   if not self.links(rid,'REALIZES') or not self.links(rid,'SUPPORTED_BY'):raise ValueError('incomplete_usage')
   rp=self.nodes[rid]['properties'];declared=set(rp['primary_evidence_ids']+rp['supporting_evidence_ids'])
   if declared!={e['target'] for e in self.links(rid,'SUPPORTED_BY')}:raise ValueError('evidence_properties_edges_disagree')
   for e in self.links(rid,'SUPPORTED_BY'):
    if e.get('evidence_role')!=('primary' if e['target'] in rp['primary_evidence_ids'] else 'supporting'):raise ValueError('evidence_role_disagrees')
   branches=self.links(rid,'ANY_BRANCH')
   if not branches:raise ValueError('empty_usage')
   for b in branches:
    bid=b['target'];checks=self.links(bid,'ALL');self.branch_owner[bid]=rid;self.branch_checks[bid]=checks
    if len([e for e in self.inc[bid] if e['relation']=='ANY_BRANCH'])!=1 or not checks:raise ValueError('invalid_branch')
    keys=set()
    for c in checks:
     cid=c['target'];p=self.nodes[cid]['properties'];key=p['feature'];accept=self.links(cid,'ACCEPTS')
     if key in keys:raise ValueError('duplicate_branch_feature')
     keys.add(key)
     if p['operator']!='in' or not p['allowed'] or not accept:raise ValueError('invalid_condition')
     actual=[]
     for edge in accept:
      f=self.nodes[edge['target']]['properties']
      if f['feature']!=key or f['value'] not in self.graph['feature_schema'].get(key,[]):raise ValueError('invalid_feature_edge')
      actual.append(f['value']);self.matches[(key,f['value'])].add(bid)
     if set(actual)!=set(p['allowed']):raise ValueError('condition_edges_disagree')
     self.required[key].add(bid)

 def validate(self,a):
  if not isinstance(a.get('text'),str) or not isinstance(a.get('origin'),str) or not a['origin']:raise ValueError('missing_analysis_origin')
  if not isinstance(a.get('clauses'),list) or not a['clauses']:raise ValueError('missing_clauses')
  spans=[];main_spans=[];variables=[];all_ids=[]
  for c in a['clauses']:
   for key in ('span','target_span'):
    v=c.get(key)
    if not isinstance(v,list) or len(v)!=2 or any(type(x)!=int for x in v):raise ValueError('span_must_be_two_integers')
   spans.append(c['target_span']);all_ids.extend([c['id'],c['predicate']['id'],c['ending_slot']['id']])
   if c['features'].get('clause_role')=='main':main_spans.append(c['span'])
   q=c.get('question_variable')
   if q and q.get('id'):all_ids.append(q['id'])
   if q:
    if not isinstance(q.get('span'),list) or len(q['span'])!=2 or any(type(x)!=int for x in q['span']):raise ValueError('invalid_question_span')
    variables.append(tuple(q['span']))
   for k,b in c['feature_bindings'].items():
    if b.get('predicate_id') not in (None,c['predicate']['id']):raise ValueError('foreign_predicate_binding')
   if any(isinstance(v,list) and (not v or any(x is None for x in v)) for v in c['features'].values()):raise ValueError('invalid_ambiguity_list')
  if any(not isinstance(x,str) or not x for x in all_ids) or len(all_ids)!=len(set(all_ids)):raise ValueError('duplicate_or_invalid_instance_id')
  for left,right in zip(sorted(spans),sorted(spans)[1:]):
   if right[0]<left[1]:raise ValueError('overlapping_edit_targets')
  for left,right in zip(sorted(main_spans),sorted(main_spans)[1:]):
   if right[0]<left[1]:raise ValueError('overlapping_main_clauses')
  if len(variables)!=len(set(variables)):raise ValueError('question_variable_shared_between_clauses')
  super().validate(a)

 def query(self,a):
  if stable(self.graph)!=self.graph_hash:raise ValueError('reader_graph_modified')
  self.validate(a);results=[]
  for c in a['clauses']:
   f=c['features'];remaining=set(self.branch_owner);steps=[]
   for key in sorted(self.required,key=lambda k:(len(self.matches.get((k,f.get(k)),())) if isinstance(f.get(k),str) else len(remaining)+1,k)):
    value=f.get(key)
    if not isinstance(value,str):continue
    before=set(remaining);remaining-=(self.required[key]-self.matches.get((key,value),set()))
    fid=self.feature_index.get((key,value));entry=[e['id'] for e in self.inc.get(fid,[]) if e['relation']=='ACCEPTS']
    steps.append({'feature':key,'value':value,'feature_node':fid,'entry_edges':entry,'before':len(before),'after':len(remaining),'removed_branches':sorted(before-remaining)})
   fails=[{'feature':k,'observed':f.get(k),'supported':v} for k,v in self.policy.items() if isinstance(f.get(k),str) and f[k] not in v]
   missing=[k for k in self.policy if not isinstance(f.get(k),str)]
   eligible=[];unresolved=[];details=[]
   for bid in sorted(remaining):
    checks=[]
    for e in self.branch_checks[bid]:
     cid=e['target'];p=self.nodes[cid]['properties'];v=f.get(p['feature']);known=isinstance(v,str)
     checks.append({'condition_id':cid,'feature':p['feature'],'observed':v,'allowed':p['allowed'],'state':'true' if known else 'unknown',
      'basis':p['basis'],'edge_id':e['id'],'evidence_ids':[x['target'] for x in self.links(cid,'SUPPORTED_BY')]})
    rid=self.branch_owner[bid];state='out_of_slice' if fails else 'unresolved' if missing or any(x['state']=='unknown' for x in checks) else 'eligible'
    item={'rule_id':rid,'branch_id':bid,'state':state,'checks':checks,
     'path_edge_ids':[e['id'] for e in self.links(self.family,'HAS_USAGE') if e['target']==rid]+[e['id'] for e in self.links(rid,'ANY_BRANCH') if e['target']==bid]+[e['id'] for e in self.branch_checks[bid]],
     'realization_edges':self.links(rid,'REALIZES'),'evidence_edges':self.links(rid,'SUPPORTED_BY')}
    details.append(item)
    if state=='eligible':eligible.append(item)
    elif state=='unresolved':unresolved.append(item)
   notes=sorted({e['target'] for rid in {x['rule_id'] for x in details} for e in self.links(rid,'HAS_CONTEXT_NOTE')})
   notes=[nid for nid in notes if not self.nodes[nid]['properties'].get('applies_to_lemmas') or (c.get('morphology') or {}).get('lemma') in self.nodes[nid]['properties']['applies_to_lemmas']]
   results.append({'clause_id':c['id'],'target_span':c['target_span'],'target_text':c['target_text'],'eligible':eligible,'unresolved':unresolved,
    'state':'out_of_slice' if fails else 'eligible' if eligible else 'unresolved' if unresolved else 'no_matching_usage',
    'scope_failures':fails,'scope_unknown':missing,'scope_edge_id':self.scope_edges[0]['id'],
    'narrowing':steps,'evaluated_branch_count':len(remaining),'branches':details,'context_note_ids':notes})
  return copy.deepcopy({'graph_version':self.graph['version'],'graph_hash':self.graph_hash,'analysis_hash':stable(a),'analysis_origin':a['origin'],'construction_id':self.family,'clauses':results})

 def morphology_status(self,c):
  m=c.get('morphology');needs=[]
  if not isinstance(m,dict):return ['morphology'],None
  for key in ('lemma','stem','source_final','origin','alignment'):
   if not isinstance(m.get(key),str) or not m[key]:needs.append(key)
  if m.get('predicate_id')!=c['predicate']['id']:needs.append('morphology_predicate_binding')
  if m.get('alignment')!='whole_predicate_recomposition':needs.append('surface_alignment')
  # This is an explicit manual alignment record, not a new morphological parser.
  # A future model output cannot call itself manually verified; its adapter must
  # supply independently checked alignment or keep the handoff unresolved.
  alignment=m.get('source_alignment')
  if not isinstance(alignment,dict):needs.append('source_alignment')
  else:
   if alignment.get('target_span')!=c['target_span'] or alignment.get('surface')!=c['target_text']:needs.append('source_alignment_target')
   if alignment.get('checked_by')!='builder_manual_review' or alignment.get('status')!='manually_aligned':needs.append('source_alignment_review')
   for key in ('lemma','stem','prefinals','source_final','nominal'):
    if alignment.get(key)!=m.get(key):needs.append('source_alignment_'+key)
  if not isinstance(m.get('prefinals'),list) or any(not isinstance(x,str) or not x for x in m.get('prefinals',[])):needs.append('prefinals')
  else:
   pf=c['features'].get('prefinal_type')
   if (pf=='none' and m['prefinals']) or (pf=='eoss' and (len(m['prefinals'])!=1 or m['prefinals'][0] not in ('었','았','였'))):needs.append('prefinal_analysis_conflict')
  for key in ('tense','polarity'):
   if not isinstance(c['features'].get(key),str):needs.append(key)
  if c['features'].get('predicate_class')=='copula':
   nominal=m.get('nominal')
   if not isinstance(nominal,str) or not nominal:needs.append('nominal')
   else:
    cp=ord(nominal[-1]);expected=('consonant_final_nominal' if (cp-0xac00)%28 else 'vowel_final_nominal') if 0xac00<=cp<=0xd7a3 else None
    if expected is None or m.get('nominal_end')!=expected:needs.append('nominal_end')
    if not c['target_text'].startswith(nominal):needs.append('nominal_source_mismatch')
  return sorted(set(needs)),m

 def packet(self,a,retrieval=None):
  fresh=self.query(a)
  if retrieval is not None and retrieval!=fresh:raise ValueError('retrieval_content_mismatch')
  clauses=[]
  for c,r in zip(a['clauses'],fresh['clauses']):
   needs,m=self.morphology_status(c);choices=[]
   for item in r['eligible']:
    rid=item['rule_id'];rp=self.nodes[rid]['properties'];forms=[]
    for edge in item['realization_edges']:
     p=self.nodes[edge['target']]['properties'];surface=None
     if not p['allomorphs']:surface=p['form'].lstrip('-')
     elif m and 'nominal_end' not in needs and 'nominal' not in needs:
      surface=next((x['surface'] for x in p['allomorphs'] if x['after']==m.get('nominal_end')),None)
     forms.append({'form_id':edge['target'],'ending':p['form'],'selected_combining_form':surface,
      'includes_copula':bool(p['allomorphs']),'edge_id':edge['id']})
    sources=[]
    for e in item['evidence_edges']:
     eid=e['target'];ep=self.nodes[eid]['properties'];sources.append({'id':eid,'doc':ep['document_id'],'page':ep['pdf_page'],'kind':ep['evidence_kind'],'family':ep['source_family'],'role':e['evidence_role']})
    choices.append({'rule_id':rid,'meaning':rp['meaning'],'forms':forms,'basis':rp['realization_basis'],'sources':sources,
     'conditions':[{'feature':x['feature'],'value':x['observed'],'basis':x['basis'],'evidence_ids':x['evidence_ids']} for x in item['checks']],
     'composition':[self.nodes[e['target']]['properties']['composition'] for e in item['realization_edges']]})
   state='ready_for_generation_trial' if choices and not needs else 'needs_analysis' if choices or r['unresolved'] else r['state']
   clauses.append({'clause_id':c['id'],'target':{'span':c['target_span'],'surface':c['target_text'],'predicate_id':c['predicate']['id']},
    'readiness':state,'needs_analysis':needs+sorted(set(r['scope_unknown']+ [x['feature'] for i in r['unresolved'] for x in i['checks'] if x['state']=='unknown'])),
    'morphology':m,'preserve':{k:c['features'].get(k) for k in ('tense','polarity','subject_honorific','addressee_level','question_kind')},
    'choices':choices,'context_note_ids':r['context_note_ids'],
    'context_notes':[{'id':nid,**{k:self.nodes[nid]['properties'][k] for k in ('title','meaning','status')},
      'sources':[{'id':e['target'],'doc':self.nodes[e['target']]['properties']['document_id'],'page':self.nodes[e['target']]['properties']['pdf_page']} for e in self.links(nid,'SUPPORTED_BY')]} for nid in r['context_note_ids']],
    'linguistic_validation':'not_generation_validated; ready means aligned fields for a controlled trial, not attested full surface form',
    'scope_failures':r['scope_failures']})
  return {'graph_version':self.graph['version'],'analysis_hash':fresh['analysis_hash'],'graph_hash':self.graph_hash,'text':a['text'],
   'instruction':'ready인 위치만 종결형을 조합한다. 선택한 이가/이고/가/고에는 계사 부분이 포함되므로 이-를 다시 붙이지 않는다. 어휘·선어말·질문 뜻·부정·높임을 보존한다. 지정 위치 밖은 유지한다. 완성된 방언 문장을 예시에서 복사하지 않는다.',
   'status_meaning':'ready는 전달 필드가 채워졌다는 뜻이며 문장 자연스러움 검증이 아님.', 'clauses':clauses}
