import unittest,importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('minimal_probe',Path(__file__).with_name('run.py'));r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
class DesignTests(unittest.TestCase):
 def test_all_nine_and_AB_equal(self):
  rows=r.cases();self.assertEqual(len(rows),9)
  for x in rows:self.assertEqual(r.payload(x,'A'),r.payload(x,'B'))
 def test_C_only_adds_knowledge(self):
  for row in r.cases():
   a=r.payload(row,'A');c=r.payload(row,'C');self.assertEqual(a['text'],c['text'])
   for k,v in a['actions'][0].items():self.assertEqual(c['actions'][0][k],v)
   self.assertIn('rule_id',c['actions'][0]);self.assertNotIn('expected_surface',c['actions'][0])
 def test_full_output_preservation(self):
  row={'text':'저는 어제 기록했어요.','action':{'span':[6,11],'target':'기록했어요'}}
  self.assertTrue(r.evaluate(row,'저는 어제 기록했어예.')['instruction_match'])
  self.assertFalse(r.evaluate(row,'저는 어제 기록했예.')['instruction_match'])
  self.assertFalse(r.evaluate(row,'나는 어제 기록했어예.')['instruction_match'])
if __name__=='__main__':unittest.main(verbosity=2)
