"""Check isolation and real query provenance; no model requests."""
import unittest,tempfile,copy
from pathlib import Path
import experiment as x

class Isolation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows=x.load_jsonl(x.INPUT);cls.catalog=x.CardContent(x.R,'kg_cards_20261030_v3')
 def test_all_fifty_same_inputs_analysis_and_query(self):
  self.assertEqual(50,len(self.rows))
  for r in self.rows:
   a=x.read(x.P/'prepared/filtered'/r['id']/'reference_packet.json');b=x.read(x.P/'prepared/unfiltered'/r['id']/'reference_packet.json')
   raw=x.read(x.SOURCE/r['id']/'retrieval_raw.json')
   self.assertEqual({c['id'] for c in b['cards']},set(raw['retrieved_ids']))
   self.assertEqual([c['id'] for c in b['cards']],sorted(raw['retrieved_ids']))
   self.assertTrue({c['id'] for c in a['cards']}<=set(raw['retrieved_ids']))
   self.assertEqual(48,len(a['cards']));self.assertEqual([],b['candidate_guidance'])
   for k in a:
    if k not in ('cards','candidate_guidance','contract_context'):self.assertEqual(a[k],b[k])
   for c in a['cards']+b['cards']:self.assertEqual(c,self.catalog.by[c['id']])
   self.assertFalse({'approved_reference','reviewed_targets','reference_translation'} & a.keys())
 def test_previously_excluded_card_is_delivered_without_answer(self):
  a=x.read(x.P/'prepared/filtered/DEV021/reference_packet.json');b=x.read(x.P/'prepared/unfiltered/DEV021/reference_packet.json')
  self.assertNotIn('GS_END_DECL_YE_08',[c['id'] for c in a['cards']])
  self.assertIn('GS_END_DECL_YE_08',[c['id'] for c in b['cards']])
  self.assertNotIn('plan',b)
 def test_all_cards_bound_to_actual_graph_paths(self):
  for r in self.rows:
   raw=x.read(x.SOURCE/r['id']/'retrieval_raw.json')
   self.assertEqual(set(raw['retrieved_ids']),{p['rule_id'] for p in raw['paths']})
 def test_existing_runtime_empty_plan_is_identical(self):
  class Client:
   def call(self,stage,prompt,payload,schema,out,*args):
    self.prompt=prompt
    return {'request_id':payload['contract_context']['request_id'],'edits':[],'reason':'테스트: 적용 없음'}
  for arm in x.ARMS:
   with tempfile.TemporaryDirectory() as td:
    client=Client();row=self.rows[0]
    r=x.generate(row,'multi',client,x.P/'prepared'/arm/row['id'],Path(td))
    self.assertEqual('unchanged',r['status']);self.assertEqual(row['text'],r['output_text'])
    self.assertTrue(r['generation_call_skipped']);self.assertEqual(x.cp.PLANNER,client.prompt)
 def test_invalid_model_selection_stays_failure_not_fallback_success(self):
  class Client:
   def call(self,*args):return {'request_id':'invented','edits':[],'reason':''}
  with tempfile.TemporaryDirectory() as td:
   row=self.rows[0];r=x.generate(row,'multi',Client(),x.P/'prepared/unfiltered'/row['id'],Path(td))
   self.assertEqual('planning_failed',r['status']);self.assertIsNone(r['output_text'])

if __name__=='__main__':unittest.main()
