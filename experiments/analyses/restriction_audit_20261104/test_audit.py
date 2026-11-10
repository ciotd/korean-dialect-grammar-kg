"""Check audit boundaries and saved-record coverage; not dialect quality tests."""
import unittest,json
from pathlib import Path
from audit import extract_pieces
H=Path(__file__).resolve().parent
class AuditTests(unittest.TestCase):
 def test_multiple_actions_preserve_outside(self):
  a=[{'span':[0,1],'target':'가'},{'span':[2,3],'target':'나'}]
  self.assertEqual(extract_pieces('가 나!','가예 나예!',a),(['가예','나예'],False))
  self.assertEqual(extract_pieces('가 나!','가예 나예?',a),([],True))
 def test_no_action_change_detected(self):
  self.assertEqual(extract_pieces('원문','원문',[]),([],False))
  self.assertEqual(extract_pieces('원문','수정',[]),([],True))
 def test_bad_span_not_silently_accepted(self):
  with self.assertRaises(AssertionError):extract_pieces('가','가',[{'span':[0,1],'target':'나'}])
 def test_every_target_and_input_once(self):
  cases=json.loads((H/'private/cases.json').read_text('utf8'));ts=json.loads((H/'private/targets.json').read_text('utf8'))
  self.assertEqual(len({c['id'] for c in cases}),50);self.assertEqual(len({t['id'] for t in ts}),62)
  self.assertEqual({t['id'] for c in cases for t in c['targets']},{t['id'] for t in ts})
  self.assertTrue(all(len(t['all_constructions'])==4 for t in ts))
 def test_sentence_change_not_target_success(self):
  ts=json.loads((H/'private/targets.json').read_text('utf8'))
  self.assertEqual([t['id'] for t in ts if t['delivered'] and t['replacement']==t['target']],['LONG001__W12'])
 def test_report_includes_all_inputs(self):
  report=(H/'private/report.html').read_text('utf8');cases=json.loads((H/'private/cases.json').read_text('utf8'))
  self.assertEqual(report.count('class="case"'),50)
  self.assertTrue(all(c['id'] in report for c in cases))
if __name__=='__main__':unittest.main()
