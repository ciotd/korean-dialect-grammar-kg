"""Source-contract checks; synthetic fixtures do not certify dialect quality."""
import copy,json,sys,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src'),str(ROOT/'tests')]
from kg_runtime import card_pipeline as cp,edit_contract as ec
from kg_runtime.analysis_alignment import reconcile_analysis,predicate_kinds,source_conflicts
from kg_runtime.cards import FUNCTION_TERMS
from kg_runtime.morphology import Morphology
from kg_runtime.scoped_operations import scoped_binding
from kg_pipeline.validation import validate_schema
import test_edit_contract as contract_fixtures

class AlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.morph=Morphology()
        cls.cards={c['id']:c for c in json.loads((ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json').read_text(encoding='utf8'))['cards']}
    def case(self,text,functions,politeness='formal',concepts=None,target=None):
        m=self.morph.analyze(text);w=next((w for w in m['words'] if w['surface']==target),m['words'][-1])
        a={'units':[dict(word_id=w['uid'],functions=functions,politeness=politeness,tense='unknown',subject_honorific=False,
            concept_ids=concepts or [],reason='test',discourse_function='unknown',discourse_evidence='')]}
        return m,a
    def align(self,*args,**kw):
        m,a=self.case(*args,**kw);old=copy.deepcopy(a)
        b,r=reconcile_analysis(a,m,{'G_Q_WH':{}});self.assertEqual(a,old)
        return b['units'][0],r
    def test_enum_and_runtime_dictionary_agree(self):
        enum=cp.ANALYSIS['properties']['units']['items']['properties']['functions']['items']['enum']
        self.assertEqual(set(enum),set(FUNCTION_TERMS))
        m,a=self.case('공부하면서',['simultaneous','adverbial'])
        cp.validate_analysis(a,m,{})
        a['units'][0]['functions']=['invented']
        with self.assertRaises(ValueError):cp.validate_analysis(a,m,{})
    def test_request_schemas_are_independent(self):
        old=copy.deepcopy(cp.DECISION)
        with ThreadPoolExecutor(2) as pool:
            schemas=list(pool.map(lambda x:cp.request_schema(cp.DECISION,'request_id',x),['A','B']))
        self.assertEqual(cp.DECISION,old);self.assertEqual(cp.S,{'type':'string'})
        for i,s in enumerate(schemas):
            self.assertEqual(s['properties']['request_id']['enum'],[['A'],['B']][i])
            validate_schema({'request_id':['A','B'][i],'edits':[],'reason':''},s)
            with self.assertRaises(ValueError):validate_schema({'request_id':'wrong','edits':[],'reason':''},s)
            with self.assertRaisesRegex(ValueError,'maxLength'):validate_schema({'request_id':['A','B'][i],'edits':[],'reason':'x'*161},s)
    def test_observable_terminal_politeness(self):
        for text,level in [('샀어.','plain'),('좋아.','plain'),('설명했어요.','polite'),('설명했습니다.','formal')]:
            with self.subTest(text=text):self.assertEqual(self.align(text,['declarative'],'unknown')[0]['politeness'],level)
    def test_quote_and_connective_not_relabelled(self):
        self.assertEqual(self.align('그가 "샀어"라고 말했다.',['declarative'],target='샀어')[0]['politeness'],'formal')
        self.assertEqual(self.align('먹으면',['conditional'])[0]['politeness'],'formal')
    def test_unsupported_features_are_unverified_not_false(self):
        u,r=self.align('샀어.',['declarative','negation','progressive'],concepts=['G_NEG_SHORT','G_AUX_PROGRESS'])
        self.assertEqual(u['functions'],['declarative']);self.assertEqual(u['concept_ids'],[])
        self.assertEqual({x['status'] for x in r['unverified_functions']},{'unverified_not_false'})
    def test_supported_negative_and_progressive_preserved(self):
        for text,func in [('안 먹었어.','negation'),('먹지 마세요.','negation'),('먹고 있어.','progressive'),('읽고 계세요.','progressive')]:
            with self.subTest(text=text):self.assertIn(func,self.align(text,[func])[0]['functions'])
    def test_later_sentence_negation_not_propagated(self):
        u,r=self.align('샀어. 안 먹었어.',['negation'],target='샀어')
        self.assertNotIn('negation',u['functions'])
    def test_wh_question_only_simple_same_clause(self):
        self.assertIn('wh_question',self.align('왜 왔어?',['polar_question'])[0]['functions'])
        self.assertIn('polar_question',self.align('어디 갔는지 알아?',['polar_question'])[0]['functions'])
        self.assertIn('polar_question',self.align('왜 왔어? 먹었어?',['polar_question'])[0]['functions'])
    def test_terminal_derived_predicate_not_any_xsv(self):
        def k(p):return predicate_kinds({'morphs':p})
        self.assertEqual(k([['시작','NNG'],['하','XSV'],['었','EP'],['나요','EF']]),{'verb'})
        self.assertEqual(k([['시작','NNG']]),set())
        self.assertEqual(k([['시작','NNG'],['하','XSV'],['는','ETM'],['사람','NNG']]),set())
        self.assertEqual(k([['친구','NNG'],['이','VCP'],['야','EF']]),{'copula'})
        self.assertNotIn('existential',k([['좋','VA'],['아','EF']]))
    def test_kiwi_qwen_conflict_is_not_invented_correction(self):
        w={'uid':'W1','morphs':[['계','NNG'],['이','VCP'],['세요','EF']]}
        old=copy.deepcopy(w);r=source_conflicts(w,[{'word_id':'W1','functions':['progressive']}])
        self.assertEqual(r[0]['code'],'source_analysis_conflict');self.assertEqual(w,old)
    def test_normal_copula_progressive_not_conflict(self):
        u,r=self.align('공부 중이에요.',['progressive'])
        self.assertEqual(r['source_conflicts'],[]);self.assertIn('progressive',u['functions'])
    def test_homograph_and_connective_not_feature_evidence(self):
        self.assertNotIn('negation',self.align('그 말 들었어.',['negation'])[0]['functions'])
        self.assertNotIn('progressive',self.align('밥을 먹고 집에 갔어.',['progressive'])[0]['functions'])
    def test_unverified_reaches_condition_and_provenance(self):
        f=contract_fixtures.ContractTests();f.setUp()
        f.cards[0]['when']={'function':'progressive'}
        m,a=self.case('샀어.',['progressive'])
        aligned,r=reconcile_analysis(a,m,{})
        cp.validate_analysis(aligned,m,{},aligned=True)
        with self.assertRaises(ValueError):cp.validate_analysis(aligned,m,{})
        f.a={'units':[{'word_id':'W2','functions':['other']}],
             'source_alignment':{'version':'test','unverified_functions':[{'word_id':'W2','function':'progressive'}]}}
        p=f.bind();e=p['edits'][0]
        self.assertIn('function_unverified',[x['code'] for x in e['issues']])
        self.assertNotIn('function_not_supported',[x['code'] for x in e['issues']])
        self.assertEqual(e['analysis_evidence']['origin'],'program_aligned_Qwen_analysis')
        self.assertEqual(e['condition_checks'][0]['result'],'analysis_unverified')
    def test_registered_terminal_yo_only(self):
        c=self.cards['GS_ENDRULE_YO_COMPOSE'];text='하려고요'
        # Saved QUAL017 has EF+JX; isolated Kiwi text may instead return EC+JX.
        w={'uid':'W1','start':0,'end':4,'surface':text,'morphs':[['하','VV'],['려고','EF'],['요','JX']]}
        b=dict(card_id=c['id'],form_index=1,component='ending',source_word_id=w['uid'],morph_index=len(w['morphs'])-1)
        self.assertEqual(scoped_binding(c,b,w,text)['candidates'],['하려고예'])
        connective=copy.deepcopy(w);connective['morphs'][1][1]='EC'
        self.assertEqual(scoped_binding(c,b,connective,text)['status'],'scope_unavailable')
        wrong=copy.deepcopy(b);wrong['morph_index']=0
        self.assertEqual(scoped_binding(c,wrong,w,text)['status'],'scope_unavailable')
        fake=copy.deepcopy(c);fake['title']='changed'
        self.assertEqual(scoped_binding(fake,b,w,text)['status'],'scope_unavailable')
        noun={'uid':'W1','start':0,'end':2,'surface':'나요','morphs':[['나','NP'],['요','JX']]}
        b.update(morph_index=1)
        self.assertEqual(scoped_binding(c,b,noun,'나요')['status'],'scope_unavailable')
    def test_binding_error_is_local_and_dependency_is_atomic(self):
        f=contract_fixtures.ContractTests();f.setUp()
        bad=f.edit(edit_id='BAD',word_ids=['W1'],bindings=[dict(card_id='TEST_ENDING',form_index=0,component='ending',morph_index=0)],after='빵다')
        v=f.value([f.edit(),bad]);p=f.bind(v)
        self.assertEqual(ec.assemble(f.m['text'],p),'빵을 샀다.')
        v=f.value([f.edit(depends_on=['BAD']),bad]);p=f.bind(v)
        self.assertEqual(ec.assemble(f.m['text'],p),f.m['text'])
        v=f.value();v['request_id']='copied_wrong'
        with self.assertRaisesRegex(ValueError,'stale_request'):f.bind(v)

if __name__=='__main__':unittest.main()
