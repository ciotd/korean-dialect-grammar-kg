import unittest,copy,json
from experiment import request_parts,checks,SOURCE,read,DEV,validate_packet,dependency_check
class ScopeTests(unittest.TestCase):
 def test_counterfactual_changes_policy_not_knowledge(self):
  for row in read(SOURCE/'private/results.json'):
   p=read(SOURCE/'private/records'/row['id']/'generation_packet.json')
   a,pa=request_parts(p,'A');b,pb=request_parts(p,'B');c,pc=request_parts(p,'C')
   self.assertEqual(pa,p)
   for x in (pb,pc):
    x=copy.deepcopy(x);x['instruction']=p['instruction'];self.assertEqual(x,p)
   if p['actions']:self.assertEqual((a,pa),(b,pb));self.assertNotEqual(b,c)
   else:self.assertEqual((b,pb),(c,pc));self.assertNotEqual(a,b)
 def test_no_forced_copy_in_open_policy(self):
  p={'text':'아침을 먹었어.','actions':[],'instruction':'old'}
  for arm in ('B','C'):
   prompt,_=request_parts(p,arm);self.assertNotIn('원문 전체를 그대로 출력하고',prompt);self.assertIn('학습한 경상도 방언 지식',prompt)
   self.assertNotIn('새로운 방언 규칙은 만들지 않는다',prompt)
 def test_v1_archived_policy_is_reproducible(self):
  p={'text':'아침을 먹었어.','actions':[],'instruction':'old'}
  old,_=request_parts(p,'B',version='v1');new,_=request_parts(p,'B',version='v2')
  self.assertIn('새로운 방언 규칙은 만들지 않는다',old);self.assertNotEqual(old,new)
 def test_development_unique_and_absent_from_source(self):
  self.assertEqual(len(DEV),12);self.assertEqual(len({x[1] for x in DEV}),12)
  self.assertFalse({x[1] for x in DEV}&{r['input_text'] for r in read(SOURCE/'private/results.json')})
 def test_no_action_change_is_observation_not_error(self):
  d=checks({'text':'왔어.','packet':{'actions':[]}},'왔다.')
  self.assertTrue(d['changed']);self.assertTrue(d['outside_original_actions']);self.assertEqual(d['suffix_contracts'],[])
 def test_unalignable_is_not_failed_suffix(self):
  p=read(SOURCE/'private/records/ADVCE006A/generation_packet.json');d=checks({'text':p['text'],'packet':p},'저, 그 내용을 설명했어예.')
  self.assertTrue(d['outside_original_actions']);self.assertIsNone(d['suffix_contracts'][0]['match'])
 def test_bad_packet_rejected_before_call(self):
  for p in [{'text':'가','actions':[{'span':[0,1],'target':'나','target_id':'W1'}]},{'text':'가나','actions':[{'span':[0,2],'target':'가나','target_id':'W1'},{'span':[1,2],'target':'나','target_id':'W2'}]}]:
   with self.assertRaises(AssertionError):validate_packet(p)
 def test_source_dependencies_verified(self):
  rows=dependency_check();self.assertTrue(rows);self.assertTrue(all(r['equal'] or r['allowed_progress_only_difference'] for r in rows))
if __name__=='__main__':unittest.main()
