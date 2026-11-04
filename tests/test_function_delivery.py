import copy,json,sys,unittest,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'local/python'),str(R/'src')]
from kg_runtime import edit_contract as ec
from kg_runtime.function_semantics import condition_checks,terminal_prohibitive
from kg_runtime.compatibility import assess
from kg_runtime.delivery_aids import prepare
from kg_runtime.morphology import Morphology

class FunctionDeliveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=Morphology();cls.cards={c['id']:c for c in json.loads((R/'knowledge/authored/kg_cards_20261030_v3/cards.json').read_text('utf8'))['cards']}
 def checks(self,label,functions,text='가세요',extra=None):
  w=self.m.analyze(text)['words'][-1];u={'word_id':w['uid'],'functions':functions,**(extra or {})};c={'id':'T','when':{'mood_form':label}}
  return condition_checks(c,[u],source_word=w),assess(c,w,u)
 def test_request_and_prohibition_only_on_observed_auxiliary(self):
  for text,func,expected in [('마세요',['prohibition'],'analysis_support'),('가세요',['prohibition'],'analysis_not_supporting'),('가세요',['request'],'analysis_support')]:
   c,a=self.checks('imperative',func,text);self.assertEqual(c[0]['result'],expected)
   self.assertEqual('function_not_supported' in a['blocks'],expected=='analysis_not_supporting')
 def test_noun_mal_is_not_prohibitive(self):
  self.assertFalse(terminal_prohibitive({'morphs':[['말','NNG'],['이다','EF']]}))
 def test_purpose_not_forced_into_intention(self):
  c,a=self.checks('intention_or_purpose',['other']);self.assertEqual(c[0]['result'],'analysis_undetermined');self.assertNotIn('function_not_supported',a['blocks'])
 def test_unknown_alternative_not_false(self):
  c,a=self.checks(['request','unsupported_function'],['declarative']);self.assertEqual(c[0]['result'],'analysis_undetermined');self.assertFalse(a['blocks'])
 def test_disjunctive_known_alternatives(self):
  c,a=self.checks(['request','declarative'],['declarative']);self.assertEqual(c[0]['result'],'analysis_support');self.assertFalse(a['blocks'])
 def test_placeholder_not_treated_as_function(self):
  c,a=self.checks('required',['request']);self.assertEqual(c[0]['result'],'missing_value');self.assertFalse(a['blocks'])
 def test_discourse_is_not_lost(self):
  c,a=self.checks('confirmation_question',['polar_question'],extra={'discourse_function':'confirmation_question'})
  self.assertEqual(c[0]['result'],'analysis_support');self.assertEqual(a['checks'][0]['result'],'match')
 def test_unverified_kept_distinct(self):
  w=self.m.analyze('가세요')['words'][-1];u={'functions':['request']};c={'id':'T','when':{'function':'negation'}}
  self.assertEqual(condition_checks(c,[u],['negation'],w)[0]['result'],'analysis_unverified')
  self.assertIn('function_unverified',assess(c,w,u,['negation'])['blocks'])
 def test_unknown_alternative_still_open_with_unverified_known_value(self):
  w=self.m.analyze('가세요')['words'][-1];u={'functions':['other']};c={'id':'T','when':{'function':['negation','unsupported_function']}}
  self.assertEqual(condition_checks(c,[u],['negation'],w)[0]['result'],'analysis_undetermined')
  self.assertFalse(assess(c,w,u,['negation'])['blocks'])
 def test_jimal_scope_terminal_edit_and_deletion(self):
  m=self.m.analyze('움직이지 마세요.');w=m['words'][-1];c=self.cards['GS_END_IMP_HI_02'];a={'units':[{'word_id':w['uid'],'functions':['prohibition'],'politeness':'polite'}]}
  e={'edit_id':'E','word_ids':[w['uid']],'bindings':[{'card_id':c['id'],'form_index':0,'source_word_id':w['uid'],'morph_index':len(w['morphs'])-1,'component':'ending'}],
    'depends_on':[],'action':'apply','instruction':'종결어미만 교체','after':'마시소','reason':'test'}
  ctx=ec.context(m,[c],a,'SYNTH');p=ec.bind_plan({'request_id':ctx['request_id'],'edits':[e],'reason':'test'},m,[c],analysis=a,input_id='SYNTH')
  self.assertNotIn('function_not_supported',[x['code'] for x in p['edits'][0]['issues']]);self.assertEqual(ec.assemble(m['text'],p),'움직이지 마시소.')
  e['after']='가시소';p=ec.bind_plan({'request_id':ctx['request_id'],'edits':[e],'reason':'test'},m,[c],analysis=a,input_id='SYNTH')
  self.assertEqual(ec.assemble(m['text'],p),m['text'])
 def test_companion_change_blocks_prohibitive_group(self):
  from kg_runtime.prohibitive_scope import guard
  m=self.m.analyze('움직이지 마세요.');w=m['words'][-1];p=m['words'][0];c=self.cards['GS_END_IMP_HI_02']
  e={'action':'apply','word_ids':[w['uid']],'bindings':[{'card_id':c['id'],'source_word_id':w['uid'],'component':'ending','morph_index':1}],'before':'마세요','after':'마시소','suffix_projection':{'candidates':['마시소']},'issues':[],'outcome':'applied'}
  other={'action':'apply','word_ids':[p['uid']],'bindings':[],'before':'움직이지','after':'움직여','issues':[],'outcome':'applied'}
  guard([e,other],m,{'units':[{'word_id':w['uid'],'functions':['prohibition']}]},[c],True)
  self.assertEqual(e['outcome'],'needs_review');self.assertEqual(other['outcome'],'needs_review')
 def test_delivery_interventions_preserve_shared_material(self):
  folder=R/'experiments/batches/20261030T085346443103Z/private/shared/DEV017'
  p=json.loads((folder/'reference_packet.json').read_text('utf8'));m=json.loads((folder/'morphology.json').read_text('utf8'));old=copy.deepcopy(p)
  for variant,key in [('explanation','condition_explanations'),('composition','composition_aids')]:
   augmented=prepare(p,m,variant);self.assertEqual({k:v for k,v in augmented.items() if k!=key},p)
   self.assertTrue(augmented[key]['items']);self.assertEqual(p,old)
  self.assertEqual(prepare(p,m,'control'),p)
 def test_single_multi_actual_delivery_interfaces_without_network(self):
  from kg_runtime import card_experiment as ce
  from kg_pipeline.io import save
  from kg_runtime.delivery_aids import PROMPTS
  m=self.m.analyze('받았어요.');w=m['words'][0];a={'units':[{'word_id':w['uid'],'functions':['declarative'],'politeness':'polite'}]}
  c={'id':'SYNTHETIC_CARD','kind':'design_rule','module':'M05','title':'test only','forms':['-어예'],'when':{'mood_form':'declarative','source_level':'haeye'}}
  packet={'input':m['text'],'words':[{'id':w['uid'],'text':w['surface'],'morphs':w['morphs']}],'grammar':a,'cards':[c],'contract_context':ec.context(m,[c],a,'SYNTHETIC')}
  class Fake:
   def __init__(self,arm):self.arm=arm;self.seen=[]
   def call(self,stage,prompt,user,schema,out,*args):
    self.seen.append((stage,prompt,copy.deepcopy(user)))
    if stage=='generation':return {'plan_id':user['plan']['plan_id'],'edits':[{'edit_id':'E','action':'apply','after':'받았어예','reason':'fixture'}],'reason':'fixture'}
    return {'request_id':user['contract_context']['request_id'],'edits':[{'edit_id':'E','word_ids':[w['uid']],
     'bindings':[{'card_id':c['id'],'form_index':0,'source_word_id':w['uid'],'morph_index':len(w['morphs'])-1,'component':'ending'}],
     'depends_on':[],'action':'apply','instruction':'어미 교체','after':'받았어예' if self.arm=='single' else '', 'reason':'fixture'}],'reason':'fixture'}
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);shared=root/'shared';save(shared/'morphology.json',m);save(shared/'reference_packet.json',packet)
   save(shared/'shared.json',{'ok':True,'stage_seconds':{},'seconds':0});save(shared/'retrieval_raw.json',{'retrieved_ids':[c['id']]})
   for v in ('control','explanation','composition'):
    for arm in ('single','multi'):
     fake=Fake(arm);result=ce.generate({'id':'SYNTHETIC','text':m['text']},arm,fake,shared,root/(v+arm),delivery_variant=v)
     self.assertEqual(result['output_text'],'받았어예.');self.assertEqual(len(fake.seen),1 if arm=='single' else 2)
     self.assertEqual(result['delivery_variant'],v)
     for _,prompt,payload in fake.seen:
      self.assertTrue(prompt.endswith(PROMPTS[v]));self.assertEqual(payload['cards'],[c]);self.assertEqual(payload['grammar'],a)
      self.assertEqual('condition_explanations' in payload,v=='explanation');self.assertEqual('composition_aids' in payload,v=='composition')

if __name__=='__main__':unittest.main()
