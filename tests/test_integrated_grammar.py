import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_pipeline.integrated import (compile_overlay,IntegratedReader,observe_units,bind_analysis,
    retrieve_packet,analysis_contract)
from kg_pipeline.validation import validate_schema
from kg_runtime.morphology import Morphology


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=compile_overlay({'rules':[],'gaps':[]});cls.reader=IntegratedReader(cls.graph);cls.m=Morphology()

    def test_whole_graph_reachable_and_original_preserved(self):
        self.assertEqual(len(self.reader.legacy),721)
        self.assertIn('GS_PART_ACC_01',self.reader.nodes)
        self.assertEqual(len(self.reader.rules),12)

    def test_target_kinds_beyond_sentence_final(self):
        units=observe_units(self.m.analyze('친구한테 문을 열어 주세요.'))
        self.assertEqual(set(u['kind'] for u in units),{'nominal','particle','predicate','connector','construction'})
        for u in units:self.assertEqual('친구한테 문을 열어 주세요.'[slice(*u['span'])],u['text'])
        cx=next(u for u in units if u['kind']=='construction')
        self.assertEqual(cx['text'],'열어 주세요')
        self.assertEqual(len(cx['related_word_ids']),2)

    def test_main_ju_not_auxiliary_construction(self):
        units=observe_units(self.m.analyze('물을 주세요.'))
        self.assertFalse(any(u['kind']=='construction' for u in units))

    def test_compound_derived_verb_does_not_overwrite_auxiliary_lemma(self):
        path=ROOT/'experiments/runs/20261106T052943610843Z_integrated_grammar_regression/private/records/QUAL003/morphology.json'
        if not path.exists():self.skipTest('Private observed regression fixture not available')
        morph=json.loads(path.read_text(encoding='utf8'));units=observe_units(morph)
        targets=[u for u in units if u['text']=='선정해가지고']
        cx=next(u for u in targets if u['kind']=='construction')
        self.assertEqual(cx['observed']['lemma'],'가지')
        connectors=[u for u in targets if u['kind']=='connector']
        self.assertEqual([(u['observed']['source_form'],u['observed']['lemma']) for u in connectors],[('어','선정하'),('고','가지')])

    def test_observed_past_not_overwritten_by_model(self):
        units=observe_units(self.m.analyze('벌써 먹었어요.'))
        raw={'units':[{'unit_id':u['id'],'features':{'past_form':'absent','tense':'present'},'clause_key':'C1','related_unit_ids':[]} for u in units]}
        bound=bind_analysis(units,raw)
        u=next(u for u in bound if u['kind']=='predicate')
        self.assertEqual(u['features']['past_form'],'present')
        self.assertEqual(u['features']['prefinal_sequence'],'eoss')
        self.assertEqual(u['features']['tense'],'present')  # observed form != interpreted time

    def test_analysis_duplicate_or_missing_rejected(self):
        units=observe_units(self.m.analyze('밥 먹었어?'))
        row={'unit_id':units[0]['id'],'features':{},'clause_key':'C1','related_unit_ids':[]}
        with self.assertRaises(ValueError):bind_analysis(units,{'units':[row,row]})

    def test_unknown_not_eligible_and_false_not_unknown(self):
        u=next(u for u in observe_units(self.m.analyze('먹었어?')) if u['kind']=='predicate')
        unknown=self.reader.query(u,{**u['observed'],'speech_act':'information_question'})
        self.assertFalse(unknown['eligible']);self.assertTrue(unknown['unresolved'])
        no=self.reader.query(u,{**u['observed'],'speech_act':'suggestion'})
        self.assertFalse(no['eligible']);self.assertFalse(no['unresolved'])

    def test_matched_question_uses_real_edges(self):
        u=next(u for u in observe_units(self.m.analyze('먹었어?')) if u['kind']=='predicate')
        features={**u['observed'],'clause_role':'main','speech_act':'information_question','addressee_level':'plain',
                  'question_kind':'polar','subject_honorific':'absent','tense':'past','polarity':'positive'}
        tr=self.reader.query(u,features)
        self.assertTrue(tr['eligible'])
        edges={e['id'] for e in self.graph['edges']}
        self.assertTrue(all(e in edges for b in tr['eligible'][0]['branches'] for e in b['path_edge_ids']))

    def test_legacy_reference_reachable_without_executable_rule(self):
        u=next(u for u in observe_units(self.m.analyze('책을 줘.')) if u['kind']=='particle')
        tr=self.reader.query(u,u['observed'])
        self.assertFalse(tr['eligible']);self.assertTrue(tr['legacy_candidates'])
        self.assertTrue(all(x['status']=='related_source_not_refined_application_rule' for x in tr['legacy_candidates']))

    def test_packet_preserves_input_and_records_budget_omissions(self):
        text='책을 줘.';us=observe_units(self.m.analyze(text))
        for u in us:u['features']=u['observed']
        packet,traces=retrieve_packet(self.reader,text,us,char_budget=1)
        self.assertEqual(packet['text'],text);self.assertTrue(packet['delivery_omissions'])
        self.assertEqual(packet['verified_scope_knowledge'],[])

    def test_new_rule_source_quote_must_match(self):
        r={'id':'INT_TEST','title':'test','modules':[4],'packages':['F09'],'unit_kind':'particle',
           'conditions':{'source_form':['한테']},'instruction':'test','forms':['test'],'preserve':[],
           'source_refs':[{'doc':'D04','page':1,'quote':'FAKE_NONEXISTENT_QUOTE_987654'}],
           'legacy_ids':[],'limitations':'test'}
        with self.assertRaisesRegex(ValueError,'Quote mismatch'):compile_overlay({'rules':[r]})

    def test_analysis_schema_all_unit_ids(self):
        units=observe_units(self.m.analyze('책을 읽어 주세요.'));s=analysis_contract(self.reader,units)
        allowed=[i for v in s['properties']['units']['items']['anyOf'] for i in v['properties']['unit_id']['enum']]
        self.assertEqual(set(allowed),{u['id'] for u in units})
        with self.assertRaises(Exception):validate_schema({'units':[]},s)

    def test_derivative_and_same_word_auxiliary_keep_both_predicates(self):
        a=observe_units(self.m.analyze('설명했어.'))
        self.assertEqual(next(u['observed']['lemma'] for u in a if u['kind']=='predicate'),'설명하')
        b=observe_units(self.m.analyze('먹어봐.'))
        self.assertEqual([u['observed']['lemma'] for u in b if u['kind']=='predicate'],['먹','보'])

    def test_jamo_normalization_and_wrong_relation_diagnostic(self):
        us=observe_units(self.m.analyze('내가 할게.'))
        self.assertEqual(next(u['observed']['source_form'] for u in us if u['kind']=='predicate'),'ㄹ게')
        raw={'units':[{'unit_id':u['id'],'features':{},'clause_key':'C1','related_unit_ids':[],
              'relations':[{'role':'nominal_host','target_id':us[-1]['id']}]} for u in us]}
        self.assertTrue(all(u['relation_issues'] for u in bind_analysis(us,raw)))

    def test_repeated_nominals_keep_distinct_ids_and_locations(self):
        us=observe_units(self.m.analyze('책은 책으로 막아.'))
        ns=[u for u in us if u['kind']=='nominal']
        self.assertEqual(len(ns),2);self.assertNotEqual(ns[0]['id'],ns[1]['id']);self.assertNotEqual(ns[0]['span'],ns[1]['span'])

    def test_array_minimum_rejects_missing_analysis_without_other_failure(self):
        with self.assertRaisesRegex(Exception,'minItems'):
            validate_schema([],{'type':'array','items':{'type':'string'},'minItems':1})

    def test_internal_ec_cannot_receive_final_question_rule(self):
        us=observe_units(self.m.analyze('먹어봤어?'))
        predicates=[u for u in us if u['kind']=='predicate']
        semantic={'clause_role':'main','speech_act':'information_question','addressee_level':'plain',
                  'question_kind':'polar','subject_honorific':'absent','tense':'past','polarity':'positive','predicate_class':'verb'}
        for u in predicates:
            hits=self.reader.query(u,{**u['observed'],**semantic})['eligible']
            self.assertEqual(bool(hits),u['observed']['ending_tag']=='EF')

    def test_aux_relation_same_host_rejected_but_two_roles_pass(self):
        us=observe_units(self.m.analyze('먹어봤어.'));ps=[u for u in us if u['kind']=='predicate'];cx=next(u for u in us if u['kind']=='construction')
        def bound(main,aux):
            return bind_analysis(us,{'units':[{'unit_id':u['id'],'features':{},'clause_key':'C1','related_unit_ids':[],
               'relations':[{'role':'main_predicate','target_id':main},{'role':'auxiliary_predicate','target_id':aux}] if u['id']==cx['id'] else []} for u in us]})
        bad=next(u for u in bound(ps[-1]['id'],ps[-1]['id']) if u['id']==cx['id'])
        self.assertNotIn('main_predicate',bad['relations']);self.assertTrue(bad['relation_issues'])
        good=next(u for u in bound(ps[0]['id'],ps[-1]['id']) if u['id']==cx['id'])
        self.assertEqual(good['relations']['main_predicate'],[ps[0]['id']]);self.assertFalse(good['relation_issues'])

    def test_all_reference_matches_kept_in_trace_before_top3(self):
        text='친구한테 책을 줬어.';us=observe_units(self.m.analyze(text))
        for u in us:u['features']=u['observed']
        packet,traces=retrieve_packet(self.reader,text,us)
        u=next(u for u in us if u['observed']['source_form']=='한테')
        tr=next(t for t in traces if t['unit_id']==u['id'])
        self.assertGreater(len(tr['legacy_candidates']),3)
        self.assertEqual(sum(x['unit_id']==u['id'] for x in packet['related_unprocessed_sources']),3)
        self.assertEqual(sum(x['unit_id']==u['id'] and x['reason']=='unrefined_reference_top3_policy' for x in packet['delivery_omissions']),len(tr['legacy_candidates'])-3)

    def test_internal_auxiliary_does_not_capture_previous_clause(self):
        us=observe_units(self.m.analyze('빨리 와서 도와주세요.'))
        cx=next(u for u in us if u['kind']=='construction')
        self.assertEqual(cx['text'],'도와주세요');self.assertEqual(len(cx['related_word_ids']),1)

    def test_root_tags_distinguish_main_and_aux_ju(self):
        aux=next(u for u in observe_units(self.m.analyze('열어주세요.')) if u['kind']=='predicate' and u['observed']['lemma']=='주')
        main=next(u for u in observe_units(self.m.analyze('물을 주세요.')) if u['kind']=='predicate' and u['observed']['lemma']=='주')
        self.assertEqual(aux['observed']['root_tag'],'VX');self.assertEqual(main['observed']['root_tag'],'VV')

    def test_adopted_candidate_does_not_force_auxiliary_present_nda(self):
        p=ROOT/'knowledge/authored/semantic_grammar_20261106_integrated_r2/private/graph.json'
        if not p.exists():self.skipTest('private candidate absent')
        rd=IntegratedReader(json.loads(p.read_text(encoding='utf8')))
        u=next(u for u in observe_units(self.m.analyze('가고 싶어.')) if u['kind']=='predicate' and u['observed']['lemma']=='싶')
        f={**u['observed'],'predicate_class':'verb','speech_act':'statement','clause_role':'main','addressee_level':'plain','subject_honorific':'absent','tense':'present'}
        self.assertNotIn('INT_LEAD_DECL_PRESENT_DA',[h['rule_id'] for h in rd.query(u,f)['eligible']])


if __name__=='__main__':unittest.main()
