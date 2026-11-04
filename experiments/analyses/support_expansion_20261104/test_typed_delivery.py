import unittest,copy,json
from pathlib import Path
from typed_delivery import compile_action
class TypedTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  r=Path(__file__).resolve().parents[3];c.g=json.loads((r/'knowledge/authored/semantic_grammar_20261104_r9/private/graph.json').read_text('utf8'));c.old=json.loads((r/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json').read_text('utf8'));c.a={'target_id':'W1','target':'기록했어요','span':[0,5],'rule_id':'SEM_DECL_HAEYE_EO','preserve':{'tense':'past'},'source_final':'어요','stem':'기록하','prefinals':['었'],'forms':[{'selected_combining_form':'어예'}]}
 def test_typed_instruction_not_answer(self):
  b=compile_action(self.g,self.a);self.assertEqual(b['target'],'기록했어요');self.assertNotIn('forms',b);self.assertNotIn('stem',b);self.assertEqual(b['surface_edit']['source_suffix'],'요');self.assertEqual(b['surface_edit']['replacement_suffix'],'예');self.assertNotIn('기록했어예',json.dumps(b,ensure_ascii=False))
 def test_source_guard(self):
  a=copy.deepcopy(self.a);a['target']='기록했어'
  with self.assertRaises(ValueError):compile_action(self.g,a)
 def test_unchanged_other_rule(self):
  a=copy.deepcopy(self.a);a['rule_id']='SEM_Q_V_WH';self.assertEqual(compile_action(self.g,a),a)
 def test_same_conditions_edges(self):
  self.assertEqual(self.g['edges'],self.old['edges']);ns={n['id']:n for n in self.g['nodes']}
  for n in self.old['nodes']:
   if n['type'] in ('Condition','ProcessingScope','SemanticRule','GrammarConstruction'):self.assertEqual(n,ns[n['id']])
 def test_typed_form_agreement(self):
  g=copy.deepcopy(self.g);f=next(n for n in g['nodes'] if n['id']=='FORM_DECL_어예');f['properties']['form']='-네'
  with self.assertRaises(ValueError):compile_action(g,self.a)
if __name__=='__main__':unittest.main(verbosity=2)
