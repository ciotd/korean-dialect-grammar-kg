import unittest
from audit import inspect_case
class AuditTests(unittest.TestCase):
 def test_error_categories(self):
  c={'text':'기록했어요','action':{'span':[0,5],'target':'기록했어요'}}
  for text,kind in [('기록했어예','exact_instruction_followed'),('기록했예','pre_yo_syllable_deleted'),('기록했예요','pre_yo_syllable_replaced_yo_kept'),('기록했어요','unchanged'),(None,'call_or_output_failure')]:
   with self.subTest(text=text):self.assertEqual(inspect_case(c,{'output_text':text})['category'],kind)
 def test_model_status_is_not_success(self):
  c={'text':'기록했어요','action':{'span':[0,5],'target':'기록했어요'}}
  self.assertFalse(inspect_case(c,{'output_text':'기록했예','model_status':'generated'})['instruction_match'])
 def test_outside_span(self):
  c={'text':'나 기록했어요.','action':{'span':[2,7],'target':'기록했어요'}}
  self.assertEqual(inspect_case(c,{'output_text':'너 기록했어예.'})['category'],'outside_target_or_alignment_uncertain')
if __name__=='__main__':unittest.main(verbosity=2)
