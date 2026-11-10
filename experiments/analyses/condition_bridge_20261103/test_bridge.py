import copy
import unittest
from bridge import HERE,GRAPH,DEFINITIONS,contract,assemble,trace,inventory,projected
from kg_pipeline.io import read

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.graph=read(GRAPH);cls.rows={r['id']:r for r in read(HERE/'private/cases.json')};cls.morphs=read(HERE/'private/kiwi_inputs.json')
 def raw(self,qid):
  row=self.rows[qid];m=self.morphs[qid];word=next(w for w in m['words'] if w['surface']==row['target'])
  fields=contract(self.graph)[0]['properties']['judgments']['properties']
  judgments={k:DEFINITIONS[k][1][row['accepted_features'][k][0]] if row['accepted_features'][k][0] is not None else None for k in fields}
  wh=next((w['uid'] for w in m['words'] if w['surface'] in ('왜','어디','누가','뭐')),None)
  return {'target_word_id':word['uid'],'question_word_id':wh,'judgments':judgments,'evidence_word_ids':[word['uid']],'note':'검사 입력'}
 def test_all_seven_conditions_have_real_edges(self):
  a=inventory(self.graph);self.assertEqual(len(a['conditions']),7)
  for c in a['conditions']:self.assertTrue(any(e['source']==c['id'] and e['relation']=='ACCEPTS' for e in self.graph['edges']))
 def test_twelve_new_core_cases_retrieve(self):
  for i in range(1,13):
   q=f'N{i:02d}';a=assemble(self.graph,self.raw(q),self.morphs[q]);t=trace(self.graph,a,self.morphs[q])
   self.assertEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial',q)
 def test_unknown_does_not_mean_false(self):
  r=self.raw('N07');r['judgments']['question_kind']=None
  t=trace(self.graph,assemble(self.graph,r,self.morphs['N07']),self.morphs['N07'])
  self.assertEqual(t['retrieval']['clauses'][0]['state'],'unresolved')
  self.assertEqual({x['rule_id'] for x in t['retrieval']['clauses'][0]['unresolved']},{'SEM_Q_C_POLAR','SEM_Q_C_WH'})
 def test_missing_speech_act_keeps_candidates(self):
  r=self.raw('N01');r['judgments']['speech_act']=None
  t=trace(self.graph,assemble(self.graph,r,self.morphs['N01']),self.morphs['N01'])
  self.assertTrue(t['retrieval']['clauses'][0]['unresolved'])
  self.assertFalse(t['retrieval']['clauses'][0]['scope_failures'])
 def test_boundary_not_linguistic_prohibition(self):
  for q in ('N13','N14','N15','N16'):
   t=trace(self.graph,assemble(self.graph,self.raw(q),self.morphs[q]),self.morphs[q])
   self.assertEqual(t['retrieval']['clauses'][0]['state'],'out_of_slice',q)
 def test_derivational_verb_is_recomposed_from_morphology(self):
  a=assemble(self.graph,self.raw('N12'),self.morphs['N12']);m=a['clauses'][0]['morphology']
  self.assertEqual(m['stem'],'도착하');self.assertEqual(m['prefinals'],['었']);self.assertTrue(m['source_morphs'])
 def test_lexical_honorific_is_not_overwritten_by_missing_si(self):
  a=assemble(self.graph,self.raw('N14'),self.morphs['N14'])
  self.assertFalse(a['fusion_log']['observed_si']);self.assertEqual(a['clauses'][0]['features']['subject_honorific'],'present')
 def test_wrong_word_id_is_rejected(self):
  r=self.raw('N01');r['target_word_id']='W999'
  with self.assertRaises(ValueError):assemble(self.graph,r,self.morphs['N01'])
 def test_new_feature_does_not_silently_disappear(self):
  g=copy.deepcopy(self.graph);g['feature_schema']['new_dimension']=['x']
  next(n for n in g['nodes'] if n['type']=='ProcessingScope')['properties']['allowed']['new_dimension']=['x']
  self.assertTrue(any(r['state']=='definition_required' for r in inventory(g)['rows']))
  with self.assertRaises(ValueError):contract(g)
 def test_all_candidates_have_failure_or_unknown_trace(self):
  t=trace(self.graph,assemble(self.graph,self.raw('N01'),self.morphs['N01']),self.morphs['N01'])
  self.assertEqual(len(t['all_condition_checks']),7);self.assertEqual(len(t['all_branch_checks']),6)
  self.assertEqual(sum(x['condition_state']=='true' for x in t['all_branch_checks']),1)
 def test_mapping_does_not_contain_sentence_id_or_translation(self):
  schema,questions=contract(self.graph)
  self.assertNotIn('predicate_class',schema['properties']['judgments']['properties'])
  self.assertNotIn('prefinal_type',schema['properties']['judgments']['properties'])
  self.assertNotIn('rules',schema['properties'])
 def test_graph_and_morphology_are_unchanged(self):
  g=copy.deepcopy(self.graph);m=copy.deepcopy(self.morphs['N12'])
  trace(self.graph,assemble(self.graph,self.raw('N12'),m),m)
  self.assertEqual(g,self.graph);self.assertEqual(m,self.morphs['N12'])
 def test_new_usage_is_discovered_without_whitelist_edit(self):
  # Synthetic clone validates plumbing only, not new linguistic knowledge.
  g=copy.deepcopy(self.graph);rid='SEM_Q_V_POLAR';newid='TEST_EXTRA_USAGE';bid=rid+'/branch/0';nbid=newid+'/branch/0'
  for source,dest in ((rid,newid),(bid,nbid)):
   n=copy.deepcopy(next(n for n in g['nodes'] if n['id']==source));n['id']=dest;g['nodes'].append(n)
  additions=[]
  for edge in g['edges']:
   if edge['source'] in (rid,bid) or (edge['relation']=='HAS_USAGE' and edge['target']==rid):
    x=copy.deepcopy(edge);x['id']='TEST_'+x['id']
    x['source']={rid:newid,bid:nbid}.get(x['source'],x['source']);x['target']={rid:newid,bid:nbid}.get(x['target'],x['target']);additions.append(x)
  g['edges']+=additions
  a=assemble(g,self.raw('N01'),self.morphs['N01']);t=trace(g,a,self.morphs['N01'])
  self.assertEqual({x['rule_id'] for x in t['retrieval']['clauses'][0]['eligible']},{rid,newid})

if __name__=='__main__':unittest.main(verbosity=2)
