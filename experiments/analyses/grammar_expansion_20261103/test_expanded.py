import unittest,importlib.util,copy,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]
s=importlib.util.spec_from_file_location('expanded_test_runtime',H/'expanded_runtime.py');rt=importlib.util.module_from_spec(s);s.loader.exec_module(rt)
from kg_runtime.morphology import Morphology
from kg_runtime.realization import compose
class ExpandedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.g=json.loads(rt.bridge.GRAPH.read_text('utf8'));cls.m=Morphology()
 def test_preserves_all_prior_nodes_edges(self):
  old=json.loads((R/'knowledge/authored/semantic_questions_20261102_r3/private/graph.json').read_text('utf8'));ns={n['id']:n for n in self.g['nodes']}
  self.assertTrue(all(ns[n['id']]==n for n in old['nodes']));self.assertTrue(all(e in self.g['edges'] for e in old['edges']))
 def test_all_construction_readers_validate(self):
  for n in self.g['nodes']:
   if n['type']=='GrammarConstruction':rt.bridge.Reader(self.g,n['id'])
 def test_conditional_haeye_not_blanket_replacement(self):
  m=self.m.analyze('책을 읽어요.');uid=m['words'][-1]['uid'];schema,user=rt.schema_and_payload(self.g,m,uid,m['text'])
  raw={'target_word_id':uid,'question_word_id':None,'judgments':{'clause_role':'독립된 주절','speech_act':'사실을 서술함','addressee_level':'높임 종결','question_kind':None,'tense':'현재','subject_honorific':'주체를 높이지 않음','polarity':'긍정'},'evidence_word_ids':[uid],'note':'검사용 의미 조건','scope':{'question_owner_word_id':None,'boundary_links':[],'question_scope':'none','auxiliary_class':None}}
  a,tr=rt.analyze_response(self.g,raw,m,uid);self.assertEqual(tr['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
  _,p=rt.generation_payload(a,tr,m);self.assertEqual(compose(self.m.kiwi,p['actions'][0])[0],'읽어예')
  for key,value in [('speech_act','상대의 행동을 요구하거나 재촉함'),('addressee_level','비높임 종결')]:
   bad=copy.deepcopy(raw);bad['judgments'][key]=value;a,t=rt.analyze_response(self.g,bad,m,uid)
   self.assertFalse(any(x['packet']['clauses'][0]['readiness']=='ready_for_generation_trial' for x in t['construction_queries']))
 def test_source_surface_postcondition_rejects_disagreement(self):
  a={'source_morphs':[['춥','VA'],['어요','EF']],'forms':[{'selected_combining_form':'어예','includes_copula':False}],'expected_surface':'추워예'}
  with self.assertRaisesRegex(ValueError,'postcondition'):compose(self.m.kiwi,a)
 def test_subject_and_past_parts_preserved(self):
  a={'source_morphs':[['오','VV'],['시','EP'],['었','EP'],['어요','EF']],'forms':[{'selected_combining_form':'어예','includes_copula':False}],'expected_surface':'오셨어예'}
  out,op=compose(self.m.kiwi,a);self.assertEqual(out,'오셨어예');self.assertEqual(op['join_morphs'][:-1],a['source_morphs'][:-1])
 def test_unknown_prefinal_sequence_excluded(self):
  reader=rt.bridge.Reader(self.g,'SEM_CX_HAEYE_DECLARATIVE')
  self.assertNotIn('other',reader.policy['prefinal_sequence'])
  for bid,links in reader.branch_checks.items():
   seq=[reader.nodes[e['target']]['properties'] for e in links if reader.nodes[e['target']]['properties']['feature']=='prefinal_sequence']
   self.assertEqual(len(seq),1);self.assertNotIn('other',seq[0]['allowed'])
 def test_auxiliary_chain_si_excludes_plain_question_scope(self):
  m=self.m.analyze('선생님이 읽으시고 있어?');uid=m['words'][-1]['uid']
  raw={'target_word_id':uid,'question_word_id':None,'judgments':{'clause_role':'독립된 주절','speech_act':'정보를 묻는 질문','addressee_level':'비높임 종결','question_kind':'사실 여부를 예 아니오로 답함','tense':'현재','subject_honorific':'주체를 높이지 않음','polarity':'긍정'},'evidence_word_ids':[uid],'note':'검사용 잘못된 높임값','scope':{'question_owner_word_id':None,'boundary_links':[{'word_id':'W2','head_word_id':'W3','relation':'auxiliary'}],'question_scope':'none','auxiliary_class':'adjective'}}
  a,tr=rt.analyze_response(self.g,raw,m,uid)
  self.assertEqual(a['clauses'][0]['features']['subject_honorific'],'present')
  self.assertEqual(a['clauses'][0]['feature_bindings']['predicate_class']['origin'],'qwen_auxiliary_semantic_class_with_observed_VX_host')
  self.assertFalse(any(t['packet']['clauses'][0]['readiness']=='ready_for_generation_trial' for t in tr['construction_queries']))
if __name__=='__main__':unittest.main()
