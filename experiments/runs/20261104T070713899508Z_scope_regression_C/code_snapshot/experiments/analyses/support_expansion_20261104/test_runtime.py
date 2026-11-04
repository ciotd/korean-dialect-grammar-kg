import unittest,json,copy
from pathlib import Path
import runtime as rt
from kg_runtime.morphology import Morphology
from kg_pipeline.io import read
class SupportTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.m=Morphology();c.g=read(rt.bridge.GRAPH)
 def prepare(self,text,act='statement',q=None,tense='present'):
  m=self.m.analyze(text);uid=m['words'][-1]['uid'];schema,_=rt.schema_and_payload(self.g,m,uid,text)
  vals={'clause_role':'main','speech_act':act,'addressee_level':'polite','question_kind':q,'tense':tense,'subject_honorific':'absent','polarity':'positive'}
  raw={'target_word_id':uid,'question_word_id':None,'evidence_word_ids':[uid],'judgments':{k:rt.bridge.DEFINITIONS[k][1][vals[k]] if vals.get(k) is not None else None for k in schema['properties']['judgments']['properties']},'note':'test fixture, not model judgment','scope':{'boundary_links':{},'question_owner_id':None,'auxiliary_class':None}}
  return m,uid,raw
 def trace(self,text,**kw):
  m,u,r=self.prepare(text,**kw);a,t=rt.analyze_response(self.g,r,m,u);return a,t,m
 def test_present_noun_consonant(self):
  a,t,m=self.trace('저 사람은 연구원이에요.');self.assertEqual(t['packet']['clauses'][0]['choices'][0]['rule_id'],'SEM_SUP_COP_PRESENT');self.assertEqual(a['clauses'][0]['features']['source_final'],'에요')
 def test_present_noun_vowel(self):
  a,t,m=self.trace('저 사람은 가수예요.');self.assertEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial');_,p=rt.generation_payload(a,t,m);self.assertNotIn('expected_surface',p['actions'][0]);self.assertEqual(p['actions'][0]['nominal'],'가수')
 def test_past_copula_not_promoted(self):
  a,t,m=self.trace('저는 학생이었어요.',tense='past');self.assertNotEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_negative_copula_not_promoted(self):
  a,t,m=self.trace('그건 사실이 아니었어요.',tense='past');self.assertNotEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_bound_nominal_not_promoted(self):
  a,t,m=self.trace('그건 제 거예요.');self.assertEqual(a['clauses'][0]['features']['nominal_kind'],'bound_nominal');self.assertNotEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_polite_question(self):
  a,t,m=self.trace('벌써 끝났어요?',act='information_question',q='polar',tense='past');self.assertEqual(t['packet']['clauses'][0]['choices'][0]['rule_id'],'SEM_SUP_POLITE_Q_EO')
 def test_honorific_prefinals_preserved(self):
  a,t,m=self.trace('벌써 도착하셨어요?',act='information_question',q='polar',tense='past');_,p=rt.generation_payload(a,t,m);self.assertEqual(p['actions'][0]['prefinals'],['시','었'])
 def test_nayo_not_promoted(self):
  a,t,m=self.trace('벌써 끝났나요?',act='information_question',q='polar',tense='past');self.assertNotEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_request_not_polite_question(self):
  a,t,m=self.trace('어서 와요.',act='request');self.assertNotEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_unknown_not_admitted(self):
  m,u,r=self.prepare('저 사람은 가수예요.');r['judgments']['speech_act']=None;a,t=rt.analyze_response(self.g,r,m,u);self.assertNotEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_old_rules_preserved(self):
  old=read(rt.ROOT/'knowledge/authored/semantic_grammar_20261103_r4/private/graph.json');ns={n['id']:n for n in self.g['nodes']};self.assertTrue(all(ns[n['id']]==n for n in old['nodes']));self.assertTrue(all(e in self.g['edges'] for e in old['edges']))
 def test_evidence_quote_exact(self):
  from build_graph import C
  for n in self.g['nodes']:
   if n['type']=='Evidence' and n['id'].startswith('EV_SUP_'):
    p=n['properties'];text=read(C/(p['document_id']+'.json'))[p['pdf_page']-1]['text'];self.assertEqual(text[p['start']:p['end']],p['quote'])
 def test_explicit_copula_flag_independent_of_allomorphs(self):
  g=copy.deepcopy(self.g);a,t,m=self.trace('저 사람은 연구원이에요.');form=next(n for n in g['nodes'] if n['id']=='FORM_SUP_COP_PRESENT');form['properties'].update(allomorphs=[{'after':'consonant_final_nominal','surface':'라예'}],includes_copula=False)
  tr=rt.bridge.trace(g,a,m,construction='SEM_CX_SUP_COP_PRESENT');self.assertFalse(tr['packet']['clauses'][0]['choices'][0]['forms'][0]['includes_copula'])
 def test_unknown_nominal_is_unresolved(self):
  from unittest.mock import patch
  m,u,r=self.prepare('저 사람은 가수예요.')
  with patch.object(rt,'nominal_kind',return_value='unknown'):a,t=rt.analyze_response(self.g,r,m,u)
  self.assertIsNone(a['clauses'][0]['features']['nominal_kind']);self.assertEqual(t['retrieval']['clauses'][0]['state'],'unresolved')
 def test_condition_provenance_not_direct_fact(self):
  a,t,m=self.trace('저 사람은 연구원이에요.');checks=t['retrieval']['clauses'][0]['eligible'][0]['checks']
  self.assertTrue(all(x['interpretation_evidence_ids'] and x['decision_ids'] and not x['evidence_ids'] for x in checks))
 def test_copula_composition_and_observed_honorific(self):
  m,u,r=self.prepare('저분은 제 교수님이에요.');r['judgments']['subject_honorific']=rt.bridge.DEFINITIONS['subject_honorific'][1]['present'];a,t=rt.analyze_response(self.g,r,m,u);_,p=rt.generation_payload(a,t,m);act=p['actions'][0]
  self.assertEqual(act['preserve']['subject_honorific'],'not_marked_on_predicate');self.assertEqual(act['honorific_model_judgment'],'present');self.assertEqual(act['copula_surface_candidates'],['교수님이라예']);self.assertEqual(a['clauses'][0]['features']['subject_honorific'],'present')
 def test_gyeseyo_not_accepted_as_copula(self):
  m,u,r=self.prepare('선생님께서 읽고 계세요.');_,bounds,_=rt.parent.inventory(m);r['scope']['boundary_links']={b['id']:{'relation':'unknown','head_id':None} for b in bounds};a,t=rt.analyze_response(self.g,r,m,u);self.assertFalse(any(x['rule_id']=='SEM_SUP_COP_PRESENT' for x in t['packet']['clauses'][0]['choices']))
if __name__=='__main__':unittest.main(verbosity=2)
