import unittest,copy,json
import runtime as rt
from kg_runtime.morphology import Morphology
from kg_pipeline.io import read
import importlib.util
s=importlib.util.spec_from_file_location('boundary_runner_test',rt.H/'run.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner)
generation_check=runner.generation_check

class BoundaryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m=Morphology();cls.g=read(rt.bridge.GRAPH)
 def prepare(self,text):
  m=self.m.analyze(text);uid=m['words'][-1]['uid'];hosts,bs,_=rt.inventory(m)
  links={b['id']:{'relation':'unknown','head_id':None} for b in bs}
  raw={'target_word_id':uid,'question_word_id':None,'judgments':{'clause_role':'독립된 주절','speech_act':'사실을 서술함','addressee_level':'높임 종결','question_kind':None,'tense':'현재','subject_honorific':'주체를 높이지 않음','polarity':'긍정'},'evidence_word_ids':[uid],'note':'단위검사용 수작업 분석, 실제 모델 성능 아님','scope':{'boundary_links':links,'question_owner_id':None,'auxiliary_class':None}}
  return m,uid,hosts,bs,raw
 def test_internal_ec_ec_not_collapsed(self):
  m,uid,hs,bs,raw=self.prepare('종목을 선정해가지고 연습해요.')
  same=next(w['uid'] for w in m['words'] if w['surface']=='선정해가지고')
  self.assertEqual(len([b for b in bs if b['word_id']==same]),2)
  b1,b2=[b for b in bs if b['word_id']==same];vx=next(h for h in hs if h['word_id']==same and h['tag']=='VX');end=next(h for h in reversed(hs) if h['word_id']==uid and h['kind']=='predicate')
  raw['scope']['boundary_links'][b1['id']]={'relation':'auxiliary','head_id':vx['id']};raw['scope']['boundary_links'][b2['id']]={'relation':'linked','head_id':end['id']}
  a,t=rt.analyze_response(self.g,raw,m,uid);self.assertEqual(a['scope_links']['structural_issues'],[]);self.assertEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_internal_ec_etm_not_collapsed(self):
  m,uid,hs,bs,raw=self.prepare('높아지는 기온을 확인해요.')
  self.assertEqual([b['tag'] for b in bs],['EC','ETM'])
  vx=next(h for h in hs if h['tag']=='VX');noun=next(h for h in hs if h['form']=='기온')
  for b,r,h in [(bs[0],'auxiliary',vx),(bs[1],'adnominal',noun)]:raw['scope']['boundary_links'][b['id']]={'relation':r,'head_id':h['id']}
  a,t=rt.analyze_response(self.g,raw,m,uid);self.assertEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_omitted_internal_boundary_rejected(self):
  m,uid,hs,bs,raw=self.prepare('높아지는 기온을 확인해요.');raw['scope']['boundary_links'].pop(bs[0]['id'])
  with self.assertRaises(Exception):rt.analyze_response(self.g,raw,m,uid)
 def test_unknown_internal_boundary_kept(self):
  m,uid,hs,bs,raw=self.prepare('높아지는 기온을 확인해요.');a,t=rt.analyze_response(self.g,raw,m,uid)
  self.assertEqual(t['packet']['clauses'][0]['readiness'],'needs_analysis')
 def test_linked_to_vx_not_certified(self):
  m,uid,hs,bs,raw=self.prepare('책을 읽고 있어요.');vx=next(h for h in hs if h['tag']=='VX');raw['scope']['auxiliary_class']='adjective';raw['scope']['boundary_links'][bs[0]['id']]={'relation':'linked','head_id':vx['id']}
  
  with self.assertRaises(Exception):rt.analyze_response(self.g,raw,m,uid)
 def test_terminal_auxiliary_still_supported(self):
  m,uid,hs,bs,raw=self.prepare('책을 읽어봤어요.');raw['scope']['auxiliary_class']='verb';vx=next(h for h in hs if h['tag']=='VX');raw['scope']['boundary_links'][bs[0]['id']]={'relation':'auxiliary','head_id':vx['id']}
  a,t=rt.analyze_response(self.g,raw,m,uid);self.assertEqual(t['packet']['clauses'][0]['readiness'],'ready_for_generation_trial')
 def test_backward_reference_rejected(self):
  m,uid,hs,bs,raw=self.prepare('책을 읽고 있어요.');raw['scope']['boundary_links'][bs[0]['id']]={'relation':'linked','head_id':hs[0]['id']}
  with self.assertRaises(Exception):rt.analyze_response(self.g,raw,m,uid)
 def test_wh_inside_auxiliary_chain(self):
  m,uid,hs,bs,raw=self.prepare('뭐 읽고 있어?');raw['scope']['auxiliary_class']='adjective';raw['judgments'].update(speech_act='정보를 묻는 질문',addressee_level='비높임 종결',question_kind='누구 어디 왜 무엇 등의 구체적인 정보를 답함');raw['question_word_id']='W1'
  src=next(h for h in hs if h['form']=='읽');vx=next(h for h in hs if h['tag']=='VX');raw['scope'].update(question_owner_id=src['id']);raw['scope']['boundary_links'][bs[0]['id']]={'relation':'auxiliary','head_id':vx['id']}
  issues,*_=rt.structural_check(raw,m,uid);self.assertEqual(issues,[])
 def test_no_action_change_flagged(self):self.assertIn('changed_without_supported_action',generation_check('문 닫아.','문 닫아라.',[],self.m)['warnings'])
 def test_evidence_word_cannot_be_morpheme_id(self):
  m,uid,hs,bs,raw=self.prepare('책을 읽어요.');raw['evidence_word_ids']=[hs[-1]['id']]
  with self.assertRaises(Exception):rt.analyze_response(self.g,raw,m,uid)
 def test_multiple_action_full_sentence_check(self):
  actions=[{'span':[0,3],'target':'먹었어','target_id':'W1','source_morphs':[['먹','VV'],['었','EP'],['어','EF']],'stem':'먹','prefinals':['었'],'forms':[{'selected_combining_form':'나','includes_copula':False}]},{'span':[5,8],'target':'왔어요','target_id':'W2','source_morphs':[['오','VV'],['었','EP'],['어요','EF']],'stem':'오','prefinals':['었'],'forms':[{'selected_combining_form':'어예','includes_copula':False}],'expected_surface':'왔어예'}]
  x=generation_check('먹었어? 왔어요.','먹었나? 왔어예.',actions,self.m);self.assertNotIn('outside_supported_spans_changed',x['warnings']);self.assertEqual(len(x['pieces']),2)
  self.assertIn('outside_supported_spans_changed',generation_check('먹었어? 왔어요.','먹었나! 왔어예.',actions,self.m)['warnings'])
 def test_nominal_cannot_bypass_auxiliary_head(self):
  m,uid,hs,bs,raw=self.prepare('높아지는 기온을 확인해요.');vx=next(h for h in hs if h['tag']=='VX');raw['scope']['boundary_links'][bs[0]['id']]={'relation':'nominal','head_id':vx['id']}
  with self.assertRaises(Exception):rt.analyze_response(self.g,raw,m,uid)
 def test_diagnostic_failure_preserves_qwen_output(self):
  from unittest.mock import patch
  response={'output_text':'읽어예.','status':'generated','reason':''}
  with patch.object(runner,'generation_check',side_effect=ValueError('diagnostic test')):
   r=runner.inspect_generated('읽어요.',response,[],self.m)
  self.assertEqual(r['output_text'],response['output_text']);self.assertEqual(r['checks']['warnings'],['validation_failed'])
 def test_honorific_chain_and_adnominal_separated(self):
  m,uid,hs,bs,raw=self.prepare('선생님이 읽으시고 있어요.');raw['scope']['auxiliary_class']='adjective';vx=next(h for h in hs if h['tag']=='VX');raw['scope']['boundary_links'][bs[0]['id']]={'relation':'auxiliary','head_id':vx['id']}
  a,t=rt.analyze_response(self.g,raw,m,uid);self.assertEqual(a['clauses'][0]['features']['subject_honorific'],'present')
  m,uid,hs,bs,raw=self.prepare('선생님이 읽으시는 책을 봐요.');noun=next(h for h in hs if h['form']=='책');raw['scope']['boundary_links'][bs[0]['id']]={'relation':'adnominal','head_id':noun['id']}
  a,t=rt.analyze_response(self.g,raw,m,uid);self.assertEqual(a['clauses'][0]['features']['subject_honorific'],'absent')
 def test_ec_nominal_and_etn_stay_available(self):
  for text in ('누가 왔는지 알아요.','책을 읽기는 좋아요.'):
   m,uid,hs,bs,raw=self.prepare(text);head=next(h for h in reversed(hs) if h['word_id']==uid and h['kind']=='predicate')
   raw['scope']['boundary_links'][bs[0]['id']]={'relation':'nominal','head_id':head['id']}
   a,t=rt.analyze_response(self.g,raw,m,uid);self.assertEqual(a['scope_links']['structural_issues'],[])
if __name__=='__main__':unittest.main()
