"""Conditions and counterexamples, independent of approved reference translations."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime.compatibility import assess,select_compatible,source_forms,guidance
from kg_runtime import edit_contract as ec
from kg_runtime.morphology import Morphology

class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=Morphology();cls.cards={c['id']:c for c in json.loads((ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json').read_text('utf8'))['cards']}
    def word(self,text):return self.m.analyze(text)['words'][-1]
    def test_polite_question_cannot_use_plain(self):
        w=self.word('도착했나요?');a={'functions':['polar_question'],'politeness':'polite'}
        self.assertIn('politeness_mismatch',assess(self.cards['GS_ENDRULE_Q_POLAR_V'],w,a)['blocks'])
        self.assertNotIn('politeness_mismatch',assess(self.cards['GS_END_Q_HI_03'],w,a)['blocks'])
    def test_plain_question_cannot_be_made_polite_without_authorization(self):
        self.assertIn('politeness_mismatch',assess(self.cards['GS_END_Q_HI_03'],self.word('도착했어?'),{'functions':['polar_question'],'politeness':'plain'})['blocks'])
    def test_unknown_register_not_invented(self):
        c={'id':'X','when':{'source_level':'hage'},'forms':['-가'],'title':'test'}
        r=assess(c,self.word('왔나요?'),{'politeness':'polite','functions':['polar_question']})
        self.assertEqual(r['checks'][0]['result'],'unknown');self.assertEqual(r['blocks'],[])
    def test_connector_source_not_replaced_by_broad_function(self):
        c=self.cards['GS_CONNECT_CONTRAST_01'];a={'functions':['contrast','causal']}
        self.assertIn('source_connective_mismatch',assess(c,self.word('오는데'),a)['blocks'])
        self.assertNotIn('source_connective_mismatch',assess(c,self.word('오지만'),a)['blocks'])
    def test_same_ending_allomorph_allowed_not_different_ending(self):
        c=self.cards['GS_CONNECT_CAUSE_01'];a={'functions':['causal']}
        self.assertFalse(assess(c,self.word('먹어서'),a)['blocks'])
        self.assertIn('source_connective_mismatch',assess(c,self.word('먹으니까'),a)['blocks'])
    def test_reselection_uses_only_available_cards_and_keeps_limit(self):
        m=self.m.analyze('열차가 출발했나요?');w=m['words'][-1];a={'units':[{'word_id':w['uid'],'functions':['polar_question'],'politeness':'polite'}]}
        cs=[self.cards[x] for x in ('GS_ENDRULE_Q_POLAR_V','GS_END_Q_HI_03')]
        chosen,info=select_compatible(cs,cs[:1],a,m,1)
        self.assertEqual([c['id'] for c in chosen],['GS_END_Q_HI_03'])
        self.assertEqual(info['per_word'][0]['alternatives'],['GS_END_Q_HI_03'])
    def test_connective_no_exact_candidate_is_reported(self):
        m=self.m.analyze('오는데');w=m['words'][0];a={'units':[{'word_id':w['uid'],'functions':['contrast']}]}
        cs=[self.cards['GS_CONNECT_CONTRAST_01']];chosen,info=select_compatible(cs,cs,a,m)
        self.assertEqual(info['per_word'][0]['alternatives'],[])
        self.assertEqual([c['id'] for c in chosen],[cs[0]['id']]) # still visible as evidence; not permission to apply
    def test_confirmation_source_ending_not_any_polite_question(self):
        c=self.cards['GS_END_Q_YE_05'];u={'functions':['polar_question'],'politeness':'polite'}
        for text in ('출발했나요?','시작했나요?','닫힐까요?'):
            self.assertIn('explicit_source_ending_mismatch',assess(c,self.word(text),u)['blocks'])
        self.assertFalse(assess(c,self.word('제출하셨죠?'),u)['blocks'])
    def test_connective_and_final_guidance_matches_selection(self):
        m=self.m.analyze('닫아 주세요.');a={'units':[{'word_id':w['uid'],'functions':['request'],'politeness':'polite'} for w in m['words']]}
        cs=[self.cards['GS_ENDRULE_ISO_IMP']]
        chosen,info=select_compatible(cs,cs,a,m);g={x['word_id']:x for x in guidance(cs,a,m)}
        for x in info['per_word']:self.assertEqual(x['alternatives'],g[x['word_id']]['candidate_card_ids'])
        self.assertEqual(info['per_word'][0]['alternatives'],[])
        self.assertEqual(info['per_word'][1]['alternatives'],['GS_ENDRULE_ISO_IMP'])
    def bind(self,text,card_id,after):
        m=self.m.analyze(text);w=m['words'][-1];c=self.cards[card_id]
        a={'units':[{'word_id':w['uid'],'functions':['contrast'],'politeness':'unknown'}]}
        e={'edit_id':'E','word_ids':[w['uid']],'bindings':[dict(card_id=card_id,form_index=0,source_word_id=w['uid'],morph_index=len(w['morphs'])-1,component='ending')],
           'depends_on':[],'action':'apply','instruction':'test','after':after,'reason':'test'}
        v={'request_id':ec.context(m,[c],a,'SYNTH')['request_id'],'edits':[e],'reason':'test'}
        return m,ec.bind_plan(v,m,[c],analysis=a,input_id='SYNTH')
    def test_vowel_composition_does_not_license_wrong_source_card(self):
        m,p=self.bind('오는데','GS_CONNECT_CONTRAST_01','오아도')
        self.assertEqual(ec.assemble(m['text'],p),'오는데')
        self.assertIn('source_connective_mismatch',[i['code'] for i in p['edits'][0]['issues']])
    def test_literal_vowel_join_repaired_when_card_source_matches(self):
        m,p=self.bind('오지만','GS_CONNECT_CONTRAST_01','오아도')
        self.assertEqual(ec.assemble(m['text'],p),'와도')
        self.assertEqual(p['edits'][0]['proposed_after'],'오아도')
        self.assertEqual(p['edits'][0]['repairs'][0]['kind'],'literal_vowel_contraction')
    def test_legitimate_uncontracted_surface_not_blanket_rewritten(self):
        m,p=self.bind('되지만','GS_CONNECT_CONTRAST_01','되어도')
        self.assertFalse(any(r['kind']=='literal_vowel_contraction' for r in p['edits'][0]['repairs']))
    def test_conditional_source_vowel_preserved(self):
        from kg_runtime.suffix_composition import project_suffix
        self.assertIn('남으머',project_suffix(self.word('남으면'),['머'])['candidates'])
        self.assertIn('가머',project_suffix(self.word('가면'),['머'])['candidates'])
    def test_derived_predicate_suffix_cannot_disappear(self):
        from kg_runtime.suffix_composition import preservation_check
        self.assertEqual(preservation_check([self.word('운동하자')],'운동아')['status'],'analysis_disagreement')

if __name__=='__main__':unittest.main()
