import unittest,importlib.util
from pathlib import Path
p=Path(__file__).with_name('scope_runtime.py');s=importlib.util.spec_from_file_location('scope_rt_test',p);rt=importlib.util.module_from_spec(s);s.loader.exec_module(rt)
from kg_runtime.morphology import Morphology
from kg_runtime.realization import compose
class ScopeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.a=Morphology()
 def raw(self,links,q=None,kind='사실 여부를 예 아니오로 답함',where='none',owner=None):
  return {'scope':{'question_owner_word_id':owner,'boundary_links':[{'word_id':w,'relation':r,'head_word_id':h} for w,r,h in links],'question_scope':where,'auxiliary_class':None},'question_word_id':q,'judgments':{'question_kind':kind}}
 def test_adnominal_main_question(self):
  m=self.a.analyze('아까 산 책을 어디에 뒀어?');r=self.raw([('W2','adnominal','W3')],'W4','누구 어디 왜 무엇 등의 구체적인 정보를 답함','target',owner='W5')
  self.assertEqual(rt.scope_check(r,m,'W5'),[])
 def test_missing_boundary_rejected(self):
  self.assertIn('boundary_coverage_mismatch',rt.scope_check(self.raw([]),self.a.analyze('책을 읽고 있어?'),'W3'))
 def test_false_auxiliary_head_rejected(self):
  self.assertIn('auxiliary_structure_mismatch',rt.scope_check(self.raw([('W2','auxiliary','W1')]),self.a.analyze('책을 읽고 있어?'),'W3'))
 def test_embedded_wh_not_borrowed(self):
  m=self.a.analyze('누가 왔는지 알아?');r=self.raw([('W2','nominal','W3')],'W1','누구 어디 왜 무엇 등의 구체적인 정보를 답함','target',owner='W2')
  self.assertIn('question_owner_not_target_or_unknown',rt.scope_check(r,m,'W3'))
 def test_embedded_polar_possible(self):
  self.assertEqual(rt.scope_check(self.raw([('W2','nominal','W3')]),self.a.analyze('누가 왔는지 알아?'),'W3'),[])
 def test_auxiliary_space(self):
  m=self.a.analyze('책을 읽고 있어?');w=m['words'][-1];p,pc,pf=rt.projector_for('adjective')(w)
  self.assertEqual((pc,pf),('adjective','none'));self.assertEqual(p['source_morphs'],w['morphs'])
 def test_combined_auxiliary_preserves_inner_components(self):
  m=self.a.analyze('국을 먹어봤어?');w=m['words'][-1];p,pc,pf=rt.projector_for('verb')(w)
  a={'source_morphs':w['morphs'],'forms':[{'selected_combining_form':'나','includes_copula':False}]}
  self.assertEqual(compose(self.a.kiwi,a)[0],'먹어봤나');self.assertEqual((p['stem'],pf),('보','eoss'))
 def test_auxiliary_class_unknown_rejected(self):
  with self.assertRaises(ValueError):rt.projector_for(None)(self.a.analyze('책을 읽고 있어?')['words'][-1])
 def test_duplicate_boundary_rejected(self):
  self.assertIn('boundary_coverage_mismatch',rt.scope_check(self.raw([('W2','auxiliary','W3')]*2),self.a.analyze('책을 읽고 있어?'),'W3'))
 def test_internal_noun_and_multiple_boundaries_rejected(self):
  m=self.a.analyze('먹고밥먹어봤어?');uid=m['words'][0]['uid']
  self.assertIn('internal_clause_alignment_unresolved',rt.scope_check(self.raw([(uid,'auxiliary',uid)]),m,uid))
 def test_outer_wh_before_quote_allowed_with_explicit_owner(self):
  m=self.a.analyze('누가 철수가 왔다고 말했어?');r=self.raw([('W3','quoted','W4')],'W1','누구 어디 왜 무엇 등의 구체적인 정보를 답함','target',owner='W4')
  self.assertEqual(rt.scope_check(r,m,'W4'),[])
if __name__=='__main__':unittest.main()
