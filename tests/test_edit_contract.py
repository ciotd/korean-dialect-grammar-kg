"""Synthetic fixtures test contracts, not attested dialect translations."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime import edit_contract as ec
from kg_runtime import card_pipeline as cp

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.m={'text':'빵을 샀어.','words':[
            {'uid':'W1','start':0,'end':2,'surface':'빵을','sentence':0,'morphs':[['빵','NNG'],['을','JKO']],
             'tokens':[{'form':'빵','base_tag':'NNG','start':0,'end':1},{'form':'을','base_tag':'JKO','start':1,'end':2}]},
            {'uid':'W2','start':3,'end':5,'surface':'샀어','sentence':0,'morphs':[['사','VV'],['었','EP'],['어','EF']]}]}
        self.cards=[{'id':'TEST_ENDING','kind':'design_rule','when':{},'forms':['-다','-ㄴ가','-지','-아 가지고']},
                    {'id':'TEST_PARTICLE','kind':'realization_inventory','when':{},'forms':['-를']},
                    {'id':'TEST_OBSERVATION','kind':'observation','when':{},'forms':['-다']}]
        self.a={'units':[{'word_id':'W2','functions':['declarative']}]}
    def edit(self,**kw):
        e=dict(edit_id='E1',word_ids=['W2'],bindings=[dict(card_id='TEST_ENDING',form_index=0,component='ending')],depends_on=[],action='apply',instruction='종결형 교체',after='샀다',reason='검사 예시')
        e.update(kw);return e
    def value(self,edits=None,m=None,cards=None,a=None,input_id=None):
        edits=copy.deepcopy([self.edit()] if edits is None else edits)
        for e in edits:
            for b in e['bindings']:
                b.setdefault('source_word_id',e['word_ids'][-1]);w=next((w for w in (m or self.m)['words'] if w['uid']==b['source_word_id']),{'morphs':[]})
                b.setdefault('morph_index',max(0,len(w['morphs'])-1))
        return dict(request_id=ec.context(m or self.m,cards or self.cards,self.a if a is None else a,input_id)['request_id'],edits=edits,reason='시험')
    def bind(self,v=None,**kw):return ec.bind_plan(v or self.value(),self.m,self.cards,analysis=self.a,**kw)
    def test_basic_splice(self):self.assertEqual(ec.assemble(self.m['text'],self.bind()),'빵을 샀다.')
    def test_keep_cannot_modify(self):
        p=self.bind(self.value([self.edit(action='keep',after='거짓말')]))
        self.assertEqual(ec.assemble(self.m['text'],p),self.m['text']);self.assertEqual(p['applied_edit_count'],0)
    def test_noop_is_not_counted(self):self.assertEqual(self.bind(self.value([self.edit(after='샀어')]))['applied_edit_count'],0)
    def test_missing_target(self):self.assertEqual(self.bind(self.value([self.edit(bindings=[])]))['status'],'needs_review')
    def test_wrong_target_surface_held(self):self.assertEqual(self.bind(self.value([self.edit(after='샀노')]))['status'],'needs_review')
    def test_particle_cannot_replace_noun(self):
        e=self.edit(word_ids=['W1'],bindings=[dict(card_id='TEST_PARTICLE',form_index=0,component='particle')],after='차를')
        p=self.bind(self.value([e]));self.assertIn('particle_edit_changes_other_material',[x['code'] for x in p['edits'][0]['issues']])
    def test_literal_particle_change(self):
        e=self.edit(word_ids=['W1'],bindings=[dict(card_id='TEST_PARTICLE',form_index=0,component='particle')],after='빵를')
        p=self.bind(self.value([e]));self.assertEqual(p['status'],'generated_requires_human_review') # checks provenance, not phonological correctness
    def test_observation_not_rewrite(self):
        e=self.edit(bindings=[dict(card_id='TEST_OBSERVATION',form_index=0,component='ending')])
        self.assertEqual(self.bind(self.value([e]))['status'],'needs_review')
    def test_reference_keep_allowed(self):
        e=self.edit(action='keep',bindings=[dict(card_id='TEST_OBSERVATION',form_index=0,component='ending')])
        self.assertEqual(self.bind(self.value([e]))['status'],'unchanged')
    def test_stale_card_order(self):
        v=self.value();self.cards[0]['forms'].reverse()
        with self.assertRaisesRegex(ValueError,'stale_request'):self.bind(v)
    def test_stale_analysis(self):
        v=self.value();self.a['units'][0]['functions']=['request']
        with self.assertRaisesRegex(ValueError,'stale_request'):self.bind(v)
    def test_bad_target_index(self):
        v=self.value();v['edits'][0]['bindings'][0]['form_index']=99
        with self.assertRaisesRegex(ValueError,'target_index'):self.bind(v)
    def test_bool_not_index(self):
        v=self.value();v['edits'][0]['bindings'][0]['form_index']=True
        with self.assertRaises(ValueError):self.bind(v)
    def test_overlap_different_ids(self):
        with self.assertRaisesRegex(ValueError,'overlap'):self.bind(self.value([self.edit(),self.edit(edit_id='E2')]))
    def test_reversed_word_ids(self):
        with self.assertRaisesRegex(ValueError,'noncontiguous'):self.bind(self.value([self.edit(word_ids=['W2','W1'])]))
    def test_multiword_span_allowed(self):
        e=self.edit(word_ids=['W1','W2'],after='빵을 샀다')
        self.assertEqual(ec.assemble(self.m['text'],self.bind(self.value([e]))),'빵을 샀다.')
    def test_punctuation_not_injected(self):self.assertEqual(self.bind(self.value([self.edit(after='샀다!')]))['status'],'needs_review')
    def test_cross_sentence_group_rejected(self):
        self.m['words'][1]['sentence']=1
        with self.assertRaisesRegex(ValueError,'boundary'):self.bind(self.value([self.edit(word_ids=['W1','W2'])]))
    def test_independent_good_edit_survives(self):
        bad=self.edit(edit_id='E2',word_ids=['W1'],bindings=[dict(card_id='TEST_PARTICLE',form_index=0,component='particle')],after='차를')
        p=self.bind(self.value([self.edit(),bad]));self.assertEqual(p['status'],'partial');self.assertEqual(ec.assemble(self.m['text'],p),'빵을 샀다.')
    def test_dependent_group_is_atomic(self):
        bad=self.edit(edit_id='E2',word_ids=['W1'],bindings=[],after='차를')
        p=self.bind(self.value([self.edit(depends_on=['E2']),bad]));self.assertEqual(p['applied_edit_count'],0)
    def test_unknown_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError,'dependency'):self.bind(self.value([self.edit(depends_on=['ghost'])]))
    def test_selected_coda_composed_and_logged(self):
        p=self.bind(self.value([self.edit(after='되ㄴ가',bindings=[dict(card_id='TEST_ENDING',form_index=1,component='ending')])]))
        e=p['edits'][0];self.assertEqual(e['after'],'된가');self.assertEqual(e['proposed_after'],'되ㄴ가');self.assertEqual(len(e['repairs']),1)
    def test_unselected_jamo_held(self):self.assertEqual(self.bind(self.value([self.edit(after='되ㄴ다')]))['status'],'needs_review')
    def test_vowel_past_join_flagged(self):
        p=self.bind(self.value([self.edit(after='사었지',bindings=[dict(card_id='TEST_ENDING',form_index=2,component='ending')])]))
        self.assertEqual(p['edits'][0]['after'],'샀지');self.assertTrue(p['edits'][0]['repairs'])
    def test_no_blanket_space_rejection(self):
        e=self.edit(after='사 가지고',bindings=[dict(card_id='TEST_ENDING',form_index=3,component='construction')])
        # Structural space allowed; the unmatched literal still needs a human/realizer judgment.
        p=self.bind(self.value([e]));self.assertNotIn('after_not_single_word',str(p))
    def test_worker_cannot_change_target(self):
        plan=self.bind(realize=False);answer=dict(plan_id=plan['plan_id'],edits=[dict(edit_id='E1',action='apply',after='샀노',reason='')],reason='')
        self.assertEqual(ec.realize_plan(plan,answer,self.m,self.cards,self.a)['status'],'needs_review')
    def test_worker_missing_id(self):
        plan=self.bind(realize=False)
        with self.assertRaisesRegex(ValueError,'worker_plan_mismatch'):ec.realize_plan(plan,dict(plan_id=plan['plan_id'],edits=[],reason=''),self.m,self.cards,self.a)
    def test_mutated_plan_rejected(self):
        p=self.bind();p['edits'][0]['after']='거짓말'
        with self.assertRaisesRegex(ValueError,'mutated'):ec.assemble(self.m['text'],p)
    def test_wrong_input_rejected(self):
        with self.assertRaisesRegex(ValueError,'stale'):ec.assemble('다른 문장',self.bind())
    def test_user_policy_exact_scope(self):
        self.assertTrue(ec.policy_active('집에 가는 길에 빵을 샀어.','DEV002'))
        self.assertFalse(ec.policy_active('집에 가는 길에 빵을 샀어.','OTHER'))
        self.assertFalse(ec.policy_active('샀어.','DEV002'))
    def test_placeholders_not_true(self):
        checks=ec.condition_checks({'when':{'x':'required'}},[])
        self.assertEqual(checks[0]['result'],'missing_value')
    def test_function_disagreement_not_hidden(self):
        self.cards[0]['when']={'function':'imperative'}
        self.assertEqual(self.bind()['status'],'needs_review')
    def test_suffix_cannot_drop_past(self):
        p=self.bind(self.value([self.edit(after='산다')]))
        self.assertEqual(p['status'],'needs_review')
        self.assertIn('source_suffix_composition_disagreement',[i['code'] for i in p['edits'][0]['issues']])
    def test_suffix_cannot_replace_verb(self):
        self.assertEqual(self.bind(self.value([self.edit(after='먹었다')]))['status'],'needs_review')
    def test_kiwi_projection_accepts_contracted_multisyllable_ending(self):
        from kg_runtime.suffix_composition import project_suffix
        p=project_suffix({'morphs':[['재밌','VA'],['어서','EC']]},['아 가지고'])
        self.assertIn('재밌어 가지고',p['candidates'])
    def test_kiwi_projection_irregular_join(self):
        from kg_runtime.suffix_composition import project_suffix
        self.assertIn('미끄러워가',project_suffix({'morphs':[['미끄럽','VA-I'],['으니까','EC']]},['아가'])['candidates'])
    def test_judge_alternative_spelling_not_kiwi_string_only(self):
        from kg_runtime.suffix_composition import preservation_check
        self.assertEqual(preservation_check([{'morphs':[['두','VV'],['었','EP'],['어','EF']]}],'두었노')['status'],'analysis_preserved')
    def test_jamo_repair_does_not_license_verb_change(self):
        p=self.bind(self.value([self.edit(after='되ㄴ가',bindings=[dict(card_id='TEST_ENDING',form_index=1,component='ending')])]))
        self.assertEqual(p['status'],'needs_review');self.assertEqual(p['edits'][0]['after'],'된가')
    def test_no_added_verb_for_simple_suffix(self):
        self.assertEqual(self.bind(self.value([self.edit(after='기다리다 샀다')]))['status'],'needs_review')
    def test_explicit_source_morpheme_is_required(self):
        v=self.value();v['edits'][0]['bindings'][0]['morph_index']=0
        p=self.bind(v)
        self.assertEqual(ec.assemble(self.m['text'],p),self.m['text'])
        self.assertIn('binding_not_ending',[i['code'] for i in p['edits'][0]['issues']])
    def test_combined_edits_cannot_swap_noun(self):
        e=self.edit(word_ids=['W1','W2'],after='차를 샀다',bindings=[
            dict(card_id='TEST_PARTICLE',form_index=0,component='particle',source_word_id='W1',morph_index=1),
            dict(card_id='TEST_ENDING',form_index=0,component='ending',source_word_id='W2',morph_index=2)])
        self.assertEqual(self.bind(self.value([e]))['status'],'needs_review')
    def test_same_component_different_targets_not_conflict(self):
        e=self.edit(word_ids=['W1','W2'],after='빵를 샀다',bindings=[
            dict(card_id='TEST_PARTICLE',form_index=0,component='particle',source_word_id='W1',morph_index=1),
            dict(card_id='TEST_ENDING',form_index=0,component='ending',source_word_id='W2',morph_index=2)])
        self.assertEqual(self.bind(self.value([e]))['status'],'generated_requires_human_review')
    def test_dependency_keep_is_not_failure(self):
        keep=self.edit(edit_id='E2',word_ids=['W1'],bindings=[],action='keep',after='빵을')
        p=self.bind(self.value([self.edit(depends_on=['E2']),keep]));self.assertEqual(p['applied_edit_count'],1)
    def test_ji_needs_discourse_not_just_declarative(self):
        self.cards[0]['id']='GS_ENDRULE_JI_ASSERT'
        e=self.edit(after='샀지',bindings=[dict(card_id='GS_ENDRULE_JI_ASSERT',form_index=2,component='ending')])
        p=self.bind(self.value([e]));self.assertIn('function_evidence_insufficient',[i['code'] for i in p['edits'][0]['issues']])
    def test_other_restriction_card_not_a_rewrite(self):
        self.cards[0]['id']='GS_GEORO_BLOCK_GUESS'
        e=self.edit(bindings=[dict(card_id='GS_GEORO_BLOCK_GUESS',form_index=0,component='ending')])
        self.assertEqual(self.bind(self.value([e]))['status'],'needs_review')
    def test_unresolved_avoid_not_ignored(self):
        self.cards[0]['avoid']=['unresolved_final_georo_register_policy']
        self.assertEqual(self.bind()['status'],'needs_review')
    def test_profile_classification_not_a_rewrite(self):
        self.cards[0]['kind']='classification'
        self.assertEqual(self.bind()['status'],'needs_review')
    def test_explicit_hyphen_alternatives(self):
        self.assertEqual(ec.variants('-요/-소'),['요','소'])
    def test_bound_form_is_not_a_complete_replacement(self):
        self.cards[0]['forms']=['-겠-']
        self.assertEqual(self.bind()['status'],'needs_review')
    def test_particle_function_tag_must_match(self):
        self.cards[1]['when']={'particle_sense':'nominative'}
        e=self.edit(word_ids=['W1'],after='빵를',bindings=[dict(card_id='TEST_PARTICLE',form_index=0,component='particle')])
        self.assertEqual(self.bind(self.value([e]))['status'],'needs_review')

if __name__=='__main__':unittest.main()
