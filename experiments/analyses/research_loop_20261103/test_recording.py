import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from research_management.core import metric_mismatches,Registry
class Counts(unittest.TestCase):
 def test_legacy_unchanged(self):
  self.assertEqual(metric_mismatches({}, {'valid_output_records':1,'changed_records':0},[{'status':'needs_review'}]),[])
 def test_new_candidate_is_not_legacy_success(self):
  result=[{'status':'completed','input_text':'a','output_text':'b','generated_targets':1,'targets':[{'generation':{'piece':{'status':'generated','output_text':'b'}}}]}]
  m={'actual_generated_outputs':1,'generated_records':1,'target_count':1,'changed_records':1,'output_records_with_patch':1,'generation_failures':0}
  self.assertEqual(metric_mismatches({'metric_contract':'research_loop_target_preservation_v2'},m,result),[])
  m['actual_generated_outputs']=2
  self.assertIn('metrics.actual_generated_outputs',metric_mismatches({'metric_contract':'research_loop_target_preservation_v2'},m,result))
 def test_replay_excludes_no_candidate(self):
  r=[{'status':'generated','output_text':'x','checks':{'warnings':['flag']}},{'status':'no_ready_target','output_text':'y'}]
  m={'actual_generated_outputs':1,'schema_valid_generated_records':1,'surface_warning_records':1}
  self.assertEqual(metric_mismatches({'metric_contract':'composition_replay_v1'},m,r),[])
 def test_all_saved_runs(self):
  import json
  audit=json.loads((Path(__file__).parent/'private/audit.json').read_text('utf8'))
  for a in audit['runs']:
   d=ROOT/'experiments/runs'/a['run_id'];read=lambda p:json.loads(p.read_text('utf8'))
   self.assertEqual(metric_mismatches(read(d/'config.json'),read(d/'metrics.json'),read(d/'private/results.json')),[])
if __name__=='__main__':unittest.main(verbosity=2)
