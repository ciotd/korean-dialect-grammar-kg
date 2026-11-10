from pathlib import Path
import copy,json,sys,unittest
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path[:0]=[str(H),str(R/'src')]
import candidate_runtime as rt
from build_past_graph import make,CX,RULE
BASE=R/'experiments/runs/20261104T013633051461Z_support_expansion_full50/private/records'
def read(p):return json.loads(p.read_text('utf8'))

class CandidateTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.g,cls.ledger=make();cls.a=read(BASE/'NEW012/targets/W12/analysis.json')
 def query(self,a):return rt.bridge.Reader(self.g,CX).query(a)['clauses'][0]
 def test_four_saved_targets(self):
  for id,uid in [('DEV028','W7'),('NEW012','W6'),('NEW012','W12'),('QUAL005','W8')]:
   a=read(BASE/id/'targets'/uid/'analysis.json');self.assertEqual(self.query(a)['state'],'eligible')
 def test_present_not_admitted(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['prefinal_sequence']='none';self.assertEqual(self.query(a)['state'],'out_of_slice')
 def test_unknown_not_admitted(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['speech_act']=None;self.assertEqual(self.query(a)['state'],'unresolved')
 def test_negative_positive_mismatch(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['polarity']='negative';self.assertEqual(self.query(a)['state'],'no_matching_usage')
 def test_question_not_admitted(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['speech_act']='information_question';self.assertEqual(self.query(a)['state'],'out_of_slice')
 def test_honorific_not_silently_extended(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['prefinal_sequence']='si_eoss';self.assertEqual(self.query(a)['state'],'out_of_slice')
 def test_old_graph_retained(self):self.assertTrue(self.ledger['old_nodes_unchanged']);self.assertTrue(self.ledger['old_edges_preserved'])
 def test_implementation_conditions_not_false_citations(self):
  for n in self.g['nodes']:
   if n['id'].startswith('COND_EXT_'):self.assertEqual(n['properties']['evidence_ids'],[])
 def test_bound_nominal_rejected(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['nominal_kind']='bound_nominal';self.assertEqual(self.query(a)['state'],'no_matching_usage')
 def test_honorific_present_rejected(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['subject_honorific']='present';self.assertEqual(self.query(a)['state'],'out_of_slice')
 def test_other_final_rejected(self):
  a=copy.deepcopy(self.a);a['clauses'][0]['features']['source_final']='네요';self.assertEqual(self.query(a)['state'],'no_matching_usage')
 def test_negative_unknown_polarity(self):
  a=read(BASE/'NEW012/targets/W6/analysis.json');a['clauses'][0]['features']['polarity']=None;self.assertEqual(self.query(a)['state'],'unresolved')
 def test_full_packets_exclude_expected_surface(self):
  from paired_kg import packet_from_targets
  for id,uid in [('DEV028','W7'),('NEW012','W6'),('NEW012','W12'),('QUAL005','W8')]:
   d=BASE/id;t=read(d/'targets'/uid/'target.json');raw=read(d/'targets'/uid/'analysis_call/parsed.json');text=read(d/'generation_packet.json')['text']
   packet,traces,internal=packet_from_targets(text,[t],[raw],self.g)
   self.assertEqual(len(packet['actions']),1);self.assertEqual(packet['actions'][0]['rule_id'],RULE)
   self.assertNotIn('expected_surface',json.dumps(packet));self.assertIn('expected_surface',internal[0])
   self.assertEqual(sum(t['packet']['clauses'][0]['readiness']=='ready_for_generation_trial' for t in traces[0]['trace']['construction_queries']),1)
 def test_all_constructions_validate(self):
  for n in self.g['nodes']:
   if n['type']=='GrammarConstruction':rt.bridge.Reader(self.g,n['id'])

if __name__=='__main__':unittest.main()
