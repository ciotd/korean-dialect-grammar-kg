"""Exact operation and negative scope tests, not a dialect quality score."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime import edit_contract as ec
from kg_runtime.scoped_operations import scoped_binding
from kg_runtime.morphology import Morphology

class ScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer=Morphology()
        cls.cards={c['id']:c for c in json.loads((ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json').read_text(encoding='utf-8'))['cards']}
    def case(self,text,after,card_id='GS_END_DECL_YE_01',action='apply',index=0):
        m=self.analyzer.analyze(text);w=m['words'][-1];c=self.cards[card_id]
        a={'units':[{'word_id':w['uid'],'functions':['declarative'],'politeness':'polite'}]}
        e={'edit_id':'E1','word_ids':[w['uid']],'bindings':[{'card_id':card_id,'form_index':index,'source_word_id':w['uid'],'morph_index':len(w['morphs'])-1,'component':'ending'}],
            'action':action,'after':after,'reason':'test','instruction':'카드에 지정한 범위만 교체','depends_on':[]}
        value={'request_id':ec.context(m,[c],a,'TEST')['request_id'],'edits':[e],'reason':'test'}
        return m,[c],a,value
    def bound(self,*args,**kwargs):
        m,c,a,v=self.case(*args,**kwargs)
        return m,ec.bind_plan(v,m,c,analysis=a,input_id='TEST')
    def test_past_negative_honorific_derivation_and_stems_preserved(self):
        for source,wrong,expected in [('나왔어요','나왔예','나왔어예'),('아니었어요','아니었예','아니었어예'),
             ('계셨어요','계셨예','계셨어예'),('설명했어요','설명했예','설명했어예'),('좋아요','좋예','좋아예')]:
            with self.subTest(source=source):
                m,p=self.bound(source,wrong);e=p['edits'][0]
                self.assertEqual(ec.assemble(m['text'],p),expected)
                self.assertEqual(e['proposed_after'],wrong);self.assertEqual(e['repairs'][0]['kind'],'scoped_surface_tail')
                self.assertEqual(e['surface_origin'],'deterministic_card_scope_composition')
                self.assertNotIn(wrong,e['suffix_projection']['candidates'])
    def test_model_correct_answer_is_not_marked_as_repair(self):
        _,p=self.bound('말했어요','말했어예');self.assertEqual(p['edits'][0]['repairs'],[])
    def test_whole_ending_card_keeps_legacy_composition(self):
        m,p=self.bound('말했어요','말했네예','GS_END_DECL_YE_02')
        self.assertFalse(p['edits'][0]['suffix_projection']['exact_scoped'])
        self.assertFalse(any(x['kind']=='scoped_surface_tail' for x in p['edits'][0]['repairs']))
    def test_keep_and_model_defer_are_not_promoted(self):
        for action in ['keep','needs_review']:
            m,p=self.bound('말했어요','말했예',action=action)
            self.assertEqual(ec.assemble(m['text'],p),m['text']);self.assertEqual(p['edits'][0]['repairs'],[])
    def test_source_outside_registered_scope_is_held(self):
        for source in ['친구예요','책이에요','제출하셨죠','좋아','맵네요']:
            with self.subTest(source=source):
                m,p=self.bound(source,'틀린예');self.assertEqual(ec.assemble(m['text'],p),source)
                self.assertIn('scoped_operation_source_unavailable',[x['code'] for x in p['edits'][0]['issues']])
    def test_composition_card_index_and_source_guard(self):
        m,p=self.bound('맵네요','맵예','GS_ENDRULE_YO_COMPOSE',index=1)
        self.assertEqual(ec.assemble(m['text'],p),'맵네예')
        m,p=self.bound('맵네요','맵요','GS_ENDRULE_YO_COMPOSE',index=0)
        self.assertEqual(ec.assemble(m['text'],p),'맵네요')
    def test_card_content_mismatch_cannot_silently_execute(self):
        m,c,a,v=self.case('나왔어요','나왔예');c=copy.deepcopy(c);c[0]['rewrite']['operation']='다른 뜻'
        v['request_id']=ec.context(m,c,a,'TEST')['request_id']
        p=ec.bind_plan(v,m,c,analysis=a,input_id='TEST')
        self.assertEqual(ec.assemble(m['text'],p),'나왔어요')
    def test_multi_worker_respects_plan_keep(self):
        m,c,a,v=self.case('나왔어요','',action='keep')
        plan=ec.bind_plan(v,m,c,realize=False,analysis=a,input_id='TEST')
        answer={'plan_id':plan['plan_id'],'edits':[{'edit_id':'E1','action':'apply','after':'나왔예','reason':'test'}],'reason':'test'}
        final=ec.realize_plan(plan,answer,m,c,analysis=a,input_id='TEST')
        self.assertEqual(ec.assemble(m['text'],final),'나왔어요')
    def test_multi_worker_scoped_repair(self):
        m,c,a,v=self.case('나왔어요','');plan=ec.bind_plan(v,m,c,realize=False,analysis=a,input_id='TEST')
        answer={'plan_id':plan['plan_id'],'edits':[{'edit_id':'E1','action':'apply','after':'나왔예','reason':'test'}],'reason':'test'}
        final=ec.realize_plan(plan,answer,m,c,analysis=a,input_id='TEST')
        self.assertEqual(ec.assemble(m['text'],final),'나왔어예');self.assertEqual(final['edits'][0]['proposed_after'],'나왔예')
    def test_direct_audit_rejects_unfixed_deletion(self):
        m,c,a,v=self.case('나왔어요','나왔예');p=ec.bind_plan(v,m,c,analysis=a,input_id='TEST')
        e=copy.deepcopy(p['edits'][0]);e['after']='나왔예';issues,_=ec.audit_edit(e,m,c,analysis=a,realize=True)
        self.assertIn('scoped_operation_preservation_violation',[x['code'] for x in issues])
    def test_explicit_quotation_is_not_rewritten(self):
        for text in ['그가 "먹었어요"라고 말했어.','그가 “먹었어요”라고 말했어.']:
            m=self.analyzer.analyze(text);w=next(w for w in m['words'] if w['surface']=='먹었어요')
            c=self.cards['GS_END_DECL_YE_01'];b={'card_id':c['id'],'form_index':0,'source_word_id':w['uid'],'morph_index':len(w['morphs'])-1,'component':'ending'}
            info=scoped_binding(c,b,w,text);self.assertEqual(info['reason'],'explicit_quotation_out_of_scope')
    def test_quote_elsewhere_does_not_block_final_ending(self):
        m,p=self.bound('"메모"를 읽었어요','읽었예')
        self.assertEqual(ec.assemble(m['text'],p),'"메모"를 읽었어예')

if __name__=='__main__':unittest.main()
