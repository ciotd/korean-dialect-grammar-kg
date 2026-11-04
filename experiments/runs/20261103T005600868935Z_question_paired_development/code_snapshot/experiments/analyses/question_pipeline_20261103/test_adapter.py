import copy,json,unittest
from adapter import ROOT,GRAPH,RuntimeReader,adapt,compact_packet,check_output,read
from kg_runtime.morphology import Morphology
class AdapterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m=Morphology();cls.g=read(GRAPH);cls.rows=read(ROOT/'experiments/analyses/question_refinement_20261102/private/development.json')
 def setup_case(self,index=0):
  a=copy.deepcopy(self.rows[index]['analysis']);m=self.m.analyze(a['text']);w=next(w for w in m['words'] if w['surface']==a['clauses'][0]['target_text']);q=a['clauses'][0]['question_variable'];qid=next((w['uid'] for w in m['words'] if q and w['surface']==q['surface']),None)
  raw={'target_word_id':w['uid'],'question_word_id':qid,'features':a['clauses'][0]['features'],'ambiguity':[],'reason':'test'};return a,m,raw
 def test_normal_machine_alignment_is_not_human_claim(self):
  a,m,raw=self.setup_case();x=adapt(raw,m);r=RuntimeReader(self.g,m);p=r.packet(x);self.assertEqual(p['clauses'][0]['readiness'],'ready_for_generation_trial');self.assertEqual(x['clauses'][0]['morphology']['source_alignment']['checked_by'],'kiwi_token_projection')
 def test_same_semantics_yield_same_generator_payload(self):
  for i in range(12):
   a,m,raw=self.setup_case(i);x=adapt(raw,m);r=RuntimeReader(self.g,m)
   self.assertEqual(compact_packet(a,r.packet(a),m),compact_packet(x,r.packet(x),m),i)
 def test_machine_morphology_tamper_is_detected(self):
  a,m,raw=self.setup_case();x=adapt(raw,m);x['clauses'][0]['morphology']['stem']='먹';p=RuntimeReader(self.g,m).packet(x);self.assertIn('kiwi_projection_mismatch',p['clauses'][0]['needs_analysis'])
 def test_wrong_model_predicate_is_not_overwritten(self):
  a,m,raw=self.setup_case();raw['features']['predicate_class']='copula';x=adapt(raw,m);p=RuntimeReader(self.g,m).packet(x);self.assertIn('qwen_kiwi_predicate_disagreement',p['clauses'][0]['needs_analysis'])
 def test_unknown_question_stays_unresolved(self):
  a,m,raw=self.setup_case(12);p=RuntimeReader(self.g,m).packet(adapt(raw,m));self.assertEqual(p['clauses'][0]['readiness'],'needs_analysis');self.assertFalse(p['clauses'][0]['choices'])
 def test_technical_missing_field_stays_missing(self):
  a,m,raw=self.setup_case(15);p=RuntimeReader(self.g,m).packet(a);self.assertIn('nominal_end',p['clauses'][0]['needs_analysis'])
 def test_unknown_word_id_fails(self):
  a,m,raw=self.setup_case();raw['target_word_id']='W999'
  with self.assertRaises(ValueError):adapt(raw,m)
 def test_outside_edit_is_warning_not_hidden_repair(self):
  a,m,raw=self.setup_case();r=RuntimeReader(self.g,m);payload=compact_packet(a,r.packet(a),m);self.assertIn('outside_target_changed',check_output(a['text'],'니 지금 웃나?',payload)['warnings'])
 def test_native_reference_never_in_packet(self):
  a,m,raw=self.setup_case();p=compact_packet(a,RuntimeReader(self.g,m).packet(a),m);self.assertNotIn('reference',p);self.assertEqual(set(p),{'text','actions'})
if __name__=='__main__':unittest.main()
