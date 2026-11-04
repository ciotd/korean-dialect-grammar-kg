import copy,tempfile,unittest
from pathlib import Path
import runner as r
class ProbeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.cases={x['id']:r.compile_case(x) for x in r.load_jsonl(r.INPUT)}
 def test_all50(self):self.assertEqual(set(self.cases),set(r.REVIEW));self.assertEqual(len(self.cases),50)
 def test_missing_not_inserted(self):
  c=self.cases['LONG003'];self.assertEqual(len(c['missing_targets']),1)
  self.assertNotIn('GS_END_Q_HI_04',[b['card_id'] for e in c['arms']['reviewed']['decision']['edits'] for b in e['bindings']])
 def test_old_bad_index_not_repaired(self):
  c=self.cases['DEV012'];self.assertEqual(c['arms']['saved']['status'],'plan_validation_failed');self.assertEqual(c['arms']['saved']['error'],'invalid_target_index');self.assertEqual(c['arms']['reviewed']['status'],'ready')
 def test_same_common_inputs(self):
  for c in self.cases.values():
   a,b=[c['arms'][x].get('payload') for x in r.ARMS]
   if a and b:self.assertEqual({k:v for k,v in a.items() if k!='plan'},{k:v for k,v in b.items() if k!='plan'})
 def test_no_projection_or_free_instruction(self):
  for c in self.cases.values():
   for x in c['arms'].values():
    if 'payload' not in x:continue
    p=x['payload']['plan'];self.assertEqual(set(p),{'plan_id','edits'})
    for e in p['edits']:
     self.assertEqual(e['after'],'');self.assertEqual(e['instruction'],r.NOTE)
     self.assertEqual(set(e),{'edit_id','word_ids','bindings','depends_on','action','instruction','before','after'})
 def test_saved_structure_preserved(self):
  for c in self.cases.values():
   old=r.read(r.OLD/c['id']/'agent_call/parsed.json');new=c['arms']['saved']['decision']
   for a,b in zip(old['edits'],new['edits']):
    for key in ['edit_id','word_ids','bindings','depends_on','action']:self.assertEqual(a[key],b[key])
 def test_exclusion_not_no_change(self):
  c=self.cases['DEV002'];self.assertEqual(c['arms']['reviewed']['status'],'review_not_eligible')
  class Never:
   def call(self,*args):raise AssertionError('must not call')
  with tempfile.TemporaryDirectory() as d:
   x=r.execute(c,'reviewed',1,Path(d),Never(),123)
   self.assertEqual(x['worker_calls'],0);self.assertEqual(x['status'],'review_not_eligible')
 def test_worker_output_and_punctuation(self):
  c=self.cases['DEV003']
  class Fake:
   def call(self,stage,prompt,payload,schema,out,limit,seed):
    return {'plan_id':payload['plan']['plan_id'],'edits':[{'edit_id':e['edit_id'],'action':'apply','after':'맵네예','reason':'test'} for e in payload['plan']['edits']],'reason':'test'}
  with tempfile.TemporaryDirectory() as d:
   x=r.execute(c,'reviewed',1,Path(d),Fake(),123)
   self.assertEqual(x['output_text'],'이 음식은 생각보다 맵네예.');self.assertEqual(x['worker_calls'],1)
 def test_bad_worker_plan_rejected(self):
  c=self.cases['DEV003'];p=c['arms']['reviewed']['plan']
  with self.assertRaisesRegex(ValueError,'stale_worker_plan'):
   r.cp.realize_plan(p,{'plan_id':'bad','edits':[],'reason':''},c['morphology'],c['common']['cards'],analysis=c['common']['grammar'],input_id=c['id'])
 def test_no_source_mutation(self):
  before=r.source_files()
  for row in r.load_jsonl(r.INPUT):r.compile_case(row)
  self.assertEqual(before,r.source_files())
if __name__=='__main__':unittest.main(verbosity=2)
