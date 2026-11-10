import copy,unittest,json
from pathlib import Path
from repair_feedback import build_feedback,retry_payload
R=Path(__file__).resolve().parents[3]
G=json.loads((R/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json').read_text('utf8'))
def packet(target,lead='그건 ',tail='.'):
 return {'text':lead+target+tail,'actions':[{'target_id':'p1','rule_id':'SEM_DECL_HAEYE_EO','target':target,'span':[len(lead),len(lead)+len(target)],'preserve':{'tense':'past'}}]}
class FeedbackTests(unittest.TestCase):
 def test_loss_of_past_is_feedback_not_silent_repair(self):
  p=packet('정리했어요');raw='그건 정리해예.';f=build_feedback(G,p,raw)
  self.assertEqual(f['status'],'feedback_available');self.assertEqual(f['original_output'],raw)
  self.assertEqual(f['findings'][0]['source_prefix_to_preserve'],'정리했어')
 def test_kept_past_but_deleted_eo_is_also_contract_failure(self):
  self.assertEqual(build_feedback(G,packet('정리했어요'),'그건 정리했예.')['status'],'feedback_available')
 def test_valid_surface_not_certified_as_quality(self):
  f=build_feedback(G,packet('정리했어요'),'그건 정리했어예.')
  self.assertEqual(f['status'],'declared_contract_satisfied');self.assertIn('not_semantic',f['scope'])
 def test_original_a_preserved_and_inner_yo_not_changed(self):
  p=packet('좋아요',lead='요금은 ')
  self.assertEqual(build_feedback(G,p,'요금은 좋아예.')['status'],'declared_contract_satisfied')
  self.assertEqual(build_feedback(G,p,'예금은 좋아예.')['status'],'needs_alignment_review')
 def test_unrelated_rule_is_not_forced_to_ye(self):
  p=packet('먹었어');p['actions'][0]['rule_id']='SEM_Q_V_WH'
  self.assertEqual(build_feedback(G,p,'그건 먹었노.')['status'],'not_inspected')
 def test_neutral_and_specific_only_add_failure_evidence(self):
  p=packet('정리했어요');before=copy.deepcopy(p);raw='그건 정리해예.';f=build_feedback(G,p,raw)
  neutral=retry_payload(G,p,raw,f,'neutral');specific=retry_payload(G,p,raw,f,'specific')
  self.assertEqual(specific.pop('failed_checks'),f['findings']);self.assertEqual(neutral,specific);self.assertEqual(p,before)
 def test_multiple_actions_not_guessed(self):
  p=packet('정리했어요');p['actions']*=2
  self.assertEqual(build_feedback(G,p,p['text'])['status'],'not_inspected')
 def test_invalid_offset_rejected(self):
  p=packet('정리했어요');p['actions'][0]['span']=[0,1]
  with self.assertRaises(ValueError):build_feedback(G,p,p['text'])
 def test_different_output_rejected(self):
  p=packet('정리했어요');raw='그건 정리해예.';f=build_feedback(G,p,raw)
  with self.assertRaisesRegex(ValueError,'output_mismatch'):retry_payload(G,p,raw+' ',f,'specific')
 def test_different_packet_rejected(self):
  p=packet('정리했어요');raw='그건 정리해예.';f=build_feedback(G,p,raw);p['actions'][0]['preserve']['tense']='present'
  with self.assertRaisesRegex(ValueError,'binding_mismatch'):retry_payload(G,p,raw,f,'specific')
 def test_different_graph_rejected(self):
  p=packet('정리했어요');raw='그건 정리해예.';f=build_feedback(G,p,raw);g=copy.deepcopy(G);g['version']='changed'
  with self.assertRaisesRegex(ValueError,'binding_mismatch'):retry_payload(g,p,raw,f,'specific')
 def test_tampered_findings_rejected(self):
  p=packet('정리했어요');raw='그건 정리해예.';f=build_feedback(G,p,raw);f['findings'][0]['source_prefix_to_preserve']='다른말'
  with self.assertRaisesRegex(ValueError,'content_mismatch'):retry_payload(G,p,raw,f,'specific')
 def test_payload_is_frozen_against_later_source_mutation(self):
  p=packet('정리했어요');raw='그건 정리해예.';f=build_feedback(G,p,raw);v=retry_payload(G,p,raw,f,'specific');frozen=copy.deepcopy(v)
  p['text']='바뀜';f['findings'][0]['message']='바뀜'
  self.assertEqual(v,frozen)
if __name__=='__main__':unittest.main()
