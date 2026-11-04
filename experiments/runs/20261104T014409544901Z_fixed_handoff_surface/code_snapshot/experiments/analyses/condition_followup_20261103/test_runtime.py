import unittest, json, copy, importlib.util, hashlib
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parents[2]
s=importlib.util.spec_from_file_location('followup_test_runtime',H/'runtime.py'); rt=importlib.util.module_from_spec(s);s.loader.exec_module(rt)
from kg_pipeline.io import unique_json_object,CallError

class FollowupTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.g=json.loads(rt.bridge.GRAPH.read_text('utf8'))
  cls.old=json.loads((R/'knowledge/authored/semantic_grammar_20261103_r2/private/graph.json').read_text('utf8'))
  cls.cases=json.loads((H/'private/six_cases.json').read_text('utf8'))
 def case(self,id,uid):
  c=next(x for x in self.cases if x['id']==id and x['target_id']==uid);raw=copy.deepcopy(c['raw'])
  raw['scope']['boundary_links']={x['word_id']:{k:v for k,v in x.items() if k!='word_id'} for x in raw['scope']['boundary_links']}
  return c,raw,c['target']['morph']
 def test_old_semantic_values_unchanged(self):
  ns={n['id']:n for n in self.g['nodes']}
  for n in self.old['nodes']:
   if n['type']=='Condition':
    for k in ('feature','operator','allowed'):self.assertEqual(n['properties'][k],ns[n['id']]['properties'][k])
   elif n['type']=='ProcessingScope':self.assertEqual(n['properties']['allowed'],ns[n['id']]['properties']['allowed'])
   else:self.assertEqual(n,ns[n['id']])
  self.assertTrue(all(e in self.g['edges'] for e in self.old['edges']))
 def test_unknown_auxiliary_not_fabricated(self):
  c,raw,m=self.case('DEV021','W3');a,t=rt.analyze_response(self.g,raw,m,'W3')
  self.assertIsNone(a['clauses'][0]['features']['predicate_class'])
  self.assertEqual(a['clauses'][0]['morphology']['terminal_host']['original_tag'],'VX')
  self.assertTrue(all(x['retrieval']['clauses'][0]['state']=='out_of_slice' for x in t['construction_queries']))
  self.assertEqual(t['packet']['clauses'][0]['readiness'],'out_of_slice')
 def test_bad_morphology_not_silently_rewritten(self):
  c,raw,m=self.case('ADVCE002A','W4');a,t=rt.analyze_response(self.g,raw,m,'W4')
  self.assertIn('auxiliary_structure_mismatch',t['diagnosis_axes']['structural_issues'])
  self.assertEqual(t['packet']['clauses'][0]['readiness'],'out_of_slice')
 def test_observed_boundary_contract_rejects_wrong_layer(self):
  for id,uid in [('LONG002','W7'),('NEW007','W7'),('QUAL002','W15')]:
   c,raw,m=self.case(id,uid)
   with self.assertRaises(Exception):rt.analyze_response(self.g,raw,m,uid)
 def test_corrected_relationship_fixture_unlocks_existing_rule(self):
  c,raw,m=self.case('LONG002','W7');raw['scope']['boundary_links']['W3']={'relation':'auxiliary','head_word_id':'W4'}
  a,t=rt.analyze_response(self.g,raw,m,'W7')
  self.assertEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
  self.assertIn('SEM_Q_V_POLAR',[x['rule_id'] for x in t['packet']['clauses'][0]['choices']])
  _,before=rt.analyze_response(self.old,raw,m,'W7')
  self.assertEqual(before['packet']['clauses'][0]['choices'],t['packet']['clauses'][0]['choices'])
 def test_unknown_relationship_still_blocks_eligible_rule(self):
  c,raw,m=self.case('LONG002','W7');raw['scope']['boundary_links']['W3']={'relation':'unknown','head_word_id':None}
  a,t=rt.analyze_response(self.g,raw,m,'W7');self.assertEqual(t['packet']['clauses'][0]['readiness'],'needs_analysis')
 def test_missing_and_extra_boundary_keys_rejected(self):
  c,raw,m=self.case('LONG002','W13')
  for extra in (False,True):
   b=copy.deepcopy(raw)
   if extra:b['scope']['boundary_links']['W999']={'relation':'unknown','head_word_id':None}
   else:b['scope']['boundary_links'].pop(next(iter(b['scope']['boundary_links'])))
   with self.assertRaises(Exception):rt.analyze_response(self.g,b,m,'W13')
 def test_unknown_kept_in_each_boundary_choice(self):
  for c in self.cases:
   s,_=rt.schema_and_payload(self.g,c['target']['morph'],c['target_id'],c['input'])
   for p in s['properties']['scope']['properties']['boundary_links']['properties'].values():self.assertIn('unknown',p['properties']['relation']['enum'])
 def test_duplicate_json_key_rejected(self):
  with self.assertRaises(CallError):json.loads('{"W3":1,"W3":2}',object_pairs_hook=unique_json_object)
 def test_provenance_references_and_nonfact_scope(self):
  ns={n['id']:n for n in self.g['nodes']}
  for e in self.g['edges']:self.assertIn(e['source'],ns);self.assertIn(e['target'],ns)
  for n in self.g['nodes']:
   if n['id'].startswith('COND_DECL_'):
    p=n['properties'];self.assertIn(p['decision_id'],ns)
    if p['feature']=='prefinal_sequence':self.assertEqual(p['evidence_ids'],[])
  cache=json.loads(Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit/D02.json').read_text('utf8'))
  for id in ('EV_DECL_CLASSIFICATION','EV_DECL_ADDRESSEE_DECL_SECTION'):
   p=ns[id]['properties'];text=cache[p['pdf_page']-1]['text'];self.assertEqual(text[p['start']:p['end']],p['quote']);self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),p['page_text_sha256'])
 def test_nonterminal_multiple_boundaries_are_not_fully_checked(self):
  for id,uid in [('QUAL003','W15'),('QUAL020','W20')]:
   td=R/'experiments/runs/20261103T093451123726Z_research_loop_followup50/private/records'/id/'targets'/uid
   raw=json.loads((td/'analysis_call/parsed.json').read_text('utf8'));target=json.loads((td/'target.json').read_text('utf8'))
   a,t=rt.analyze_response(self.g,raw,target['morph'],uid)
   self.assertIn('multiple_boundaries_in_word_unresolved',a['adapter_diagnostics'])
   self.assertEqual(t['packet']['clauses'][0]['readiness'],'needs_analysis')
 def test_multiple_boundary_does_not_hide_outside_scope(self):
  td=R/'experiments/runs/20261103T093451123726Z_research_loop_followup50/private/records/QUAL003/targets/W15'
  raw=json.loads((td/'analysis_call/parsed.json').read_text('utf8'));target=json.loads((td/'target.json').read_text('utf8'))
  raw['judgments']['speech_act']='상대의 행동을 요구하거나 재촉함'
  a,t=rt.analyze_response(self.g,raw,target['morph'],'W15')
  self.assertEqual(t['packet']['clauses'][0]['readiness'],'out_of_slice')
  self.assertIn('multiple_boundaries_in_word_unresolved',t['diagnosis_axes']['structural_issues'])
if __name__=='__main__':unittest.main()
