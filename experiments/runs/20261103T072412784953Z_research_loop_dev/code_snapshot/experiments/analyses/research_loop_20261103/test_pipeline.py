import unittest,copy,json
from pipeline import *
from kg_runtime.morphology import Morphology
class TestPipeline(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m=Morphology();cls.g=bridge.read(bridge.GRAPH)
 def test_sentence_target_offsets(self):
  text='나는 먼저 간다. 너는 어디 가?';m=self.m.analyze(text);ts=sentence_targets(m)
  self.assertEqual(len(ts),2)
  for t in ts:
   w=next(w for w in t['morph']['words'] if w['uid']==t['uid'])
   a,b=t['original_span'];self.assertEqual(text[a:b],w['surface']);self.assertEqual(w['start']+t['offset'],a)
   self.assertTrue(all(w['sentence']==next(x for x in t['morph']['words'] if x['uid']==t['uid'])['sentence'] for w in t['morph']['words']))
 def test_target_enum(self):
  m=self.m.analyze('누가 왔어?');s,p=schema_and_payload(self.g,m,'W2',m['text'])
  self.assertEqual(s['properties']['target_word_id']['enum'],['W2'])
  self.assertNotIn('reference',p)
 def test_outside_preservation(self):
  text='아까 문을 닫았어?';a={'span':[6,9],'target':'닫았어'}
  self.assertEqual(apply_piece(text,a,'닫았나'),'아까 문을 닫았나?')
  with self.assertRaises(ValueError):apply_piece(text,a,'닫았나?')
  with self.assertRaises(ValueError):apply_piece(text,a,'문 닫았나')
 def test_stale_span(self):
  with self.assertRaises(ValueError):apply_piece('아까 왔어?',{'span':[3,5],'target':'갔어'},'왔나')
 def test_past_loss_detected(self):
  p={'text':'뭘 먹었어?','actions':[{'span':[2,5],'target':'먹었어','source_morphs':[['먹','VV'],['었','EP'],['어','EF']], 'nominal':None,'forms':[{'selected_combining_form':'노','includes_copula':False}]}]}
  self.assertIn('prefinal_observation_changed_or_kiwi_uncertain',preservation_check(self.m,'뭘 먹노?',p)['warnings'])
  self.assertNotIn('prefinal_observation_changed_or_kiwi_uncertain',preservation_check(self.m,'뭘 먹었노?',p)['warnings'])
 def test_copula_duplicate_detected(self):
  p={'text':'누가 의사야?','actions':[{'span':[3,6],'target':'의사야','source_morphs':[['의사','NNG'],['이','VCP'],['야','EF']], 'nominal':'의사','forms':[{'selected_combining_form':'고','includes_copula':True}]}]}
  self.assertIn('integrated_copula_composition_mismatch',preservation_check(self.m,'누가 의사이고?',p)['warnings'])
 def test_actual_paths_and_unknown(self):
  m=self.m.analyze('누가 왔어?');schema,_=bridge.contract(self.g)
  js={'clause_role':'독립된 주절','speech_act':'정보를 묻는 질문','addressee_level':'비높임 종결','question_kind':'누구 어디 왜 무엇 등의 구체적인 정보를 답함','subject_honorific':'주체를 높이지 않음','tense':'과거','polarity':'긍정'}
  raw={'target_word_id':'W2','question_word_id':'W1','judgments':js,'evidence_word_ids':['W1','W2'],'note':'시험'}
  a,t=analyze_response(self.g,raw,m,'W2');self.assertEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
  ids={e['id'] for e in self.g['edges']}
  for b in t['retrieval']['clauses'][0]['branches']:
   self.assertTrue(set(b['path_edge_ids'])<=ids)
  raw['judgments']['speech_act']=None
  a,t=analyze_response(self.g,raw,m,'W2');self.assertNotEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_complex_remains_visible(self):
  m=self.m.analyze('네가 읽던 책을 봤어?')
  self.assertTrue(any(t['base_tag']=='ETM' for t in m['tokens']))
  self.assertTrue(sentence_targets(m))
if __name__=='__main__':unittest.main(verbosity=2)
