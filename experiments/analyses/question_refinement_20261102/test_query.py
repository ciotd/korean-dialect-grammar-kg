import copy,unittest
from sources import HERE,ROOT,read,CACHE
from query import Reader
from development import cases

class QueryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.graph=read(HERE/'private/graph.json');cls.rows=cases()
 def setUp(self):self.r=Reader(self.graph);self.a=copy.deepcopy(self.rows[0]['analysis'])
 def packet(self,i):a=self.rows[i]['analysis'];return self.r.packet(a,self.r.query(a))['clauses'][0]
 def test_all_six_usage_forms(self):
  expect={0:'-나',1:'-노',4:'-가',6:'-고',8:'-나',9:'-노'}
  for i,v in expect.items():self.assertEqual(self.packet(i)['choices'][0]['forms'][0]['ending'],v)
 def test_nominal_coda_and_vowel(self):
  for i,v in ((4,'이가'),(5,'가'),(6,'이고'),(7,'고')):self.assertEqual(self.packet(i)['choices'][0]['forms'][0]['selected_combining_form'],v)
 def test_fused_predicate_is_not_split_at_char_boundary(self):
  for i in (9,10,11):
   p=self.packet(i);self.assertEqual(p['readiness'],'ready_for_generation_trial');self.assertEqual(p['morphology']['alignment'],'whole_predicate_recomposition')
  self.assertEqual(self.packet(10)['morphology']['prefinals'],['았'])
 def test_ambiguous_question_has_no_ready_choice(self):
  p=self.packet(12);self.assertEqual(p['choices'],[]);self.assertEqual(p['readiness'],'needs_analysis');self.assertIn('question_kind',p['needs_analysis'])
 def test_negative_marker_outside_target_preserved_in_plan(self):
  p=self.packet(13);self.assertEqual(p['preserve']['polarity'],'negative');self.assertEqual(p['target']['surface'],'먹었어')
 def test_request_is_outside_not_ungrammatical(self):self.assertEqual(self.packet(14)['readiness'],'out_of_slice')
 def test_coda_unknown_still_retrieves_knowledge(self):
  p=self.packet(15);self.assertEqual(len(p['choices']),1);self.assertEqual(p['readiness'],'needs_analysis');self.assertIsNone(p['choices'][0]['forms'][0]['selected_combining_form'])
 def test_old_24_candidate_contracts(self):
  rows=read(ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/private/easy_development.json')
  for row in rows:
   q=self.r.query(row['analysis'])
   for key in ('eligible','unresolved'):
    self.assertEqual(sorted({i['rule_id'] for c in q['clauses'] for i in c[key]}),sorted(row['expected_'+key]),row['id'])
 def test_absent_morphology_is_not_ready(self):
  self.a['clauses'][0].pop('morphology');p=self.r.packet(self.a)['clauses'][0];self.assertTrue(p['choices']);self.assertEqual(p['readiness'],'needs_analysis')
 def test_forged_realization_rejected(self):
  q=self.r.query(self.a);q['clauses'][0]['eligible'][0]['realization_edges']=self.r.links('SEM_Q_V_WH','REALIZES')
  with self.assertRaisesRegex(ValueError,'retrieval_content_mismatch'):self.r.packet(self.a,q)
 def test_missing_clause_in_retrieval_rejected(self):
  q=self.r.query(self.a);q['clauses']=[]
  with self.assertRaises(ValueError):self.r.packet(self.a,q)
 def test_reader_is_snapshot(self):
  g=copy.deepcopy(self.graph);r=Reader(g);g['nodes'][0]['properties']['x']=1;self.assertEqual(r.query(self.a),self.r.query(self.a))
 def test_reader_mutation_detected(self):
  self.r.graph['nodes'][0]['properties']['x']=1
  with self.assertRaisesRegex(ValueError,'reader_graph_modified'):self.r.query(self.a)
 def test_overlap_different_ids_rejected(self):
  c=copy.deepcopy(self.a['clauses'][0]);c.update(id='c2');c['predicate'].update(id='p2',clause_id='c2');c['ending_slot'].update(id='end2',predicate_id='p2',clause_id='c2')
  for b in c['feature_bindings'].values():b.update(clause_id='c2',predicate_id='p2' if b['predicate_id'] else None)
  self.a['clauses'].append(c)
  with self.assertRaisesRegex(ValueError,'overlapping_edit_targets'):self.r.query(self.a)
 def test_foreign_tense_owner_rejected(self):
  self.a['clauses'][0]['feature_bindings']['tense']['predicate_id']='p99'
  with self.assertRaises(ValueError):self.r.query(self.a)
 def test_bool_position_rejected(self):
  self.a['clauses'][0]['span'][0]=False
  with self.assertRaisesRegex(ValueError,'integers'):self.r.query(self.a)
 def test_question_variable_duplicate_id_rejected(self):
  a=copy.deepcopy(self.rows[1]['analysis']);a['clauses'][0]['question_variable']['id']='p1'
  with self.assertRaises(ValueError):self.r.query(a)
 def test_wrong_prefinals_need_analysis(self):
  self.a['clauses'][0]['morphology']['prefinals']=['었'];self.assertIn('prefinal_analysis_conflict',self.r.packet(self.a)['clauses'][0]['needs_analysis'])
 def test_unknown_tense_not_defaulted(self):
  self.a['clauses'][0]['features']['tense']=None;self.assertIn('tense',self.r.packet(self.a)['clauses'][0]['needs_analysis'])
 def test_dangling_graph_rejected(self):
  g=copy.deepcopy(self.graph);g['edges'][0]['target']='invented'
  with self.assertRaisesRegex(ValueError,'dangling_edge'):Reader(g)
 def test_condition_property_edge_disagreement(self):
  g=copy.deepcopy(self.graph);n=next(n for n in g['nodes'] if n['type']=='Condition');n['properties']['allowed']=['invalid']
  with self.assertRaisesRegex(ValueError,'condition_edges_disagree'):Reader(g)
 def test_construction_membership_required(self):
  g=copy.deepcopy(self.graph);g['edges']=[e for e in g['edges'] if e['relation']!='HAS_USAGE']
  with self.assertRaises(ValueError):Reader(g)
 def test_unrelated_policy_not_applied(self):
  g=copy.deepcopy(self.graph);g['nodes'].append({'id':'OTHER_SCOPE','type':'ProcessingScope','properties':{'allowed':{'speech_act':['statement']}}});r=Reader(g)
  self.assertEqual([i['rule_id'] for i in r.query(self.a)['clauses'][0]['eligible']],['SEM_Q_V_POLAR'])
 def test_index_narrows_before_branch_evaluation(self):
  q=self.r.query(self.a)['clauses'][0];self.assertEqual(q['evaluated_branch_count'],1);self.assertEqual(q['narrowing'][0]['before'],6)
  ids={e['id'] for e in self.graph['edges']}
  for step in q['narrowing']:self.assertTrue(set(step['entry_edges'])<=ids)
  self.assertTrue(set(q['eligible'][0]['path_edge_ids'])<=ids)
 def test_context_observations_are_not_choices(self):
  p=self.packet(6);self.assertIn('OBS_Q_COP_NO',p['context_note_ids']);self.assertTrue(all(x['rule_id'].startswith('SEM_Q_') for x in p['choices']))
 def test_past_wh_no_polar_example_as_direct_support(self):
  n=self.r.nodes['SEM_Q_C_PAST_WH']['properties'];self.assertNotIn('EV_COP_PAST',n['primary_evidence_ids']);self.assertIn('EV_COP_PREFINAL_RULE',n['primary_evidence_ids'])
 def test_evidence_quotes_exact(self):
  for n in self.graph['nodes']:
   if n['type']!='Evidence':continue
   p=n['properties'];t=read(CACHE/(p['document_id']+'.json'))[p['pdf_page']-1]['text'];self.assertEqual(t[p['start']:p['end']],p['quote'],n['id'])
 def test_supported_non_question_schema(self):
  for value in ('suggestion','exclamation','self_question'):
   a=copy.deepcopy(self.a);a['clauses'][0]['features']['speech_act']=value;self.assertEqual(self.r.query(a)['clauses'][0]['state'],'out_of_slice')
 def test_positive_two_separate_clauses(self):
  a=copy.deepcopy(self.a);c=copy.deepcopy(a['clauses'][0]);offset=len(a['text'])+1;a['text']+=' '+a['text']
  c['id']='c2';c['span']=[x+offset for x in c['span']];c['target_span']=[x+offset for x in c['target_span']]
  c['predicate'].update(id='p2',clause_id='c2',span=c['target_span']);c['ending_slot'].update(id='end2',clause_id='c2',predicate_id='p2');c['morphology']['predicate_id']='p2'
  c['morphology']['source_alignment']['target_span']=c['target_span'][:]
  for b in c['feature_bindings'].values():b.update(clause_id='c2',predicate_id='p2' if b['predicate_id'] else None)
  a['clauses'].append(c);packets=self.r.packet(a)['clauses'];self.assertEqual(len(packets),2);self.assertTrue(all(p['readiness']=='ready_for_generation_trial' for p in packets))
 def test_overlap_main_clause_without_overlap_target_rejected(self):
  a=copy.deepcopy(self.a);c=copy.deepcopy(a['clauses'][0]);offset=len(a['text'])+1;a['text']+=' '+a['text']
  c['id']='c2';c['span']=[0,len(a['text'])];c['target_span']=[x+offset for x in c['target_span']]
  c['predicate'].update(id='p2',clause_id='c2',span=c['target_span']);c['ending_slot'].update(id='end2',clause_id='c2',predicate_id='p2')
  for b in c['feature_bindings'].values():b.update(clause_id='c2',predicate_id='p2' if b['predicate_id'] else None)
  a['clauses'].append(c)
  with self.assertRaisesRegex(ValueError,'overlapping_main_clauses'):self.r.query(a)
 def test_nominal_changed_after_alignment(self):
  a=copy.deepcopy(self.rows[4]['analysis']);m=a['clauses'][0]['morphology'];m.update(nominal='의사',nominal_end='vowel_final_nominal')
  p=self.r.packet(a)['clauses'][0];self.assertEqual(p['readiness'],'needs_analysis');self.assertIn('nominal_source_mismatch',p['needs_analysis'])
 def test_stem_changed_after_alignment(self):
  self.a['clauses'][0]['morphology']['stem']='먹';p=self.r.packet(self.a)['clauses'][0];self.assertEqual(p['readiness'],'needs_analysis');self.assertIn('source_alignment_stem',p['needs_analysis'])
 def test_no_false_human_confirmation(self):
  self.a['clauses'][0]['morphology']['source_alignment']['checked_by']='qwen';self.assertIn('source_alignment_review',self.r.packet(self.a)['clauses'][0]['needs_analysis'])
 def test_past_surface_policy_is_in_packet(self):
  p=self.packet(9);self.assertIn('OBS_Q_PAST_SURFACE',p['context_note_ids']);self.assertTrue(any('이랐-' in x for x in p['choices'][0]['composition']));self.assertIn('not_generation_validated',p['linguistic_validation'])
 def test_irrelevant_existence_note_omitted(self):self.assertNotIn('OBS_Q_EXISTS',self.packet(0)['context_note_ids'])
 def test_actual_existence_note_included(self):
  from development import example
  a=example('TEMP','너 집에 있어?','있어',pc='adjective',lemma='있다',stem='있')['analysis'];self.assertIn('OBS_Q_EXISTS',self.r.query(a)['clauses'][0]['context_note_ids'])
 def test_primary_evidence_does_not_mix_polar_and_wh(self):
  polar=self.r.nodes['SEM_Q_V_POLAR']['properties']['primary_evidence_ids'];wh=self.r.nodes['SEM_Q_V_WH']['properties']['primary_evidence_ids']
  self.assertNotIn('EV_Q_V_PAST',polar);self.assertNotIn('EV_Q_V_EXAMPLES',wh);self.assertIn('EV_Q_V_WH_BODY',wh)
 def test_evidence_attributes_tamper_rejected(self):
  g=copy.deepcopy(self.graph);n=next(n for n in g['nodes'] if n['id']=='SEM_Q_V_POLAR');n['properties']['primary_evidence_ids']=['EV_COP_PAST']
  with self.assertRaisesRegex(ValueError,'evidence_properties_edges_disagree'):Reader(g)
 def test_spec_condition_evidence_matches_graph(self):
  spec=read(HERE/'private/spec.json')
  for n in self.r.conditions:
   p=n['properties'];record=next(x for x in spec['condition_evidence'] if x['feature']==p['feature'] and x['allowed']==p['allowed'])
   self.assertEqual(set(record['evidence_ids']),{e['target'] for e in self.r.links(n['id'],'SUPPORTED_BY')})

if __name__=='__main__':unittest.main()
