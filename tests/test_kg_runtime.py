import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime.morphology import Morphology
from kg_runtime.rules import RULES,forms_for,seed_concepts
from kg_runtime.graph import make_plan,apply_plan,GraphTool
from kg_runtime.prompts import DECISION
from kg_pipeline.validation import validate_schema,ValidationError

class MorphologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.a=Morphology()
    def forms(self,text,rid):
        m=self.a.analyze(text)
        return [f for w in m['words'] for f in forms_for(rid,w,m,self.a)]
    def test_past_question_is_not_blocked(self):
        self.assertEqual(self.forms('언제 갔어?','GS_ENDRULE_Q_WH_V'),['갔노'])
    def test_question_not_declaration(self):
        self.assertEqual(self.forms('학교에 갔어.','GS_ENDRULE_Q_POLAR_V'),[])
    def test_polite_question_not_downgraded(self):
        self.assertEqual(self.forms('집에 갔어요?','GS_ENDRULE_Q_POLAR_V'),[])
    def test_copula_tense_different_rule(self):
        self.assertEqual(self.forms('동료였어?','GS_ENDRULE_Q_POLAR_C'),[])
        self.assertEqual(self.forms('동료였어?','GS_ENDRULE_Q_TAM_C'),['동료였나','동료였노'])
    def test_copula_polite_composition(self):
        self.assertEqual(self.forms('선생님이에요. 동료예요.','GS_ENDRULE_YO_COMPOSE'),['선생님이라예','동료라예'])
    def test_command_not_any_verb(self):
        self.assertEqual(self.forms('여기로 와.','GS_ENDRULE_NNA_O'),['온나'])
        self.assertEqual(self.forms('사과 먹어.','GS_ENDRULE_NNA_O'),[])
    def test_quote_not_sleep_connective(self):
        self.assertEqual(self.forms('만나자고 했어.','GS_CONNECT_QUOTE_02'),['만나자꼬'])
        self.assertEqual(self.forms('먼저 자고 가.','GS_CONNECT_QUOTE_02'),[])
    def test_condition_not_noun(self):
        self.assertEqual(self.forms('괜찮으면 가.','GS_CONNECT_COND_03'),['괜찮으모'])
        self.assertEqual(self.forms('이 면은 넓어.','GS_CONNECT_COND_03'),[])
    def test_little_no_added_restriction(self):
        self.assertEqual(self.forms('조금만 기다려.','GS_HAM_ADV_LITTLE'),['쪼께만'])
        self.assertEqual(self.forms('조금 기다려.','GS_HAM_ADV_LITTLE'),[])
    def test_preserve_tense_in_polite(self):
        self.assertEqual(self.forms('닫았어요.','GS_ENDRULE_YO_COMPOSE'),['닫았어예'])
    def test_subject_honorific_kiwi_error_not_command(self):
        self.assertEqual(self.forms('선생님이 읽고 계세요.','GS_ENDRULE_ISO_IMP'),[])
    def test_negation_not_final_ji(self):
        self.assertEqual(self.forms('먹지 않아.','GS_ENDRULE_JI_ASSERT'),[])
    def test_overlapping_morph_offsets_remain_exact_word(self):
        m=self.a.analyze('출발했나요?');w=m['words'][0]
        self.assertEqual(m['text'][w['start']:w['end']],w['surface'])
        self.assertIn(['하','XSV'],w['morphs'])
        self.assertTrue(any(a['start']==b['start'] for a,b in zip(w['tokens'],w['tokens'][1:])))
    def test_source_atom_id_exists(self):
        ns=[json.loads(x) for x in (ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/graph/nodes.jsonl').read_text(encoding='utf8').splitlines()]
        by={x['id']:x for x in ns}
        for rid in RULES:self.assertEqual(by[rid]['type'],'SourceAtom')
        for cid in seed_concepts(self.a.analyze('조금만 기다리면 될까요?')):self.assertIn(cid,by)

class PlanTests(unittest.TestCase):
    def setUp(self):
        self.text='가. 가.'
        self.c={'candidate_id':'a','span':[3,4],'before':'가','after':'가예'}
        self.raw={'candidates':[self.c]}
    def test_exact_position_not_global_replacement(self):
        plan=make_plan(['a'],self.raw,self.text)
        self.assertEqual(apply_plan(self.text,plan),'가. 가예.')
        self.assertEqual(plan['preserved_spans'],[[0,3],[4,5]])
    def test_conflicting_candidates_rejected(self):
        self.raw['candidates'].append({**self.c,'candidate_id':'b','after':'가라'})
        with self.assertRaisesRegex(ValueError,'overlapping'):make_plan(['a','b'],self.raw,self.text)
    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):make_plan(['a','a'],self.raw,self.text)
    def test_unknown_rule_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown'):make_plan(['invented'],self.raw,self.text)
    def test_changed_source_rejected(self):
        with self.assertRaisesRegex(ValueError,'binding'):make_plan(['a'],self.raw,'나. 나.')
    def test_multiple_edits_do_not_shift_offsets(self):
        self.raw['candidates'].append({**self.c,'candidate_id':'b','span':[0,1],'after':'가겠어'})
        self.assertEqual(apply_plan(self.text,make_plan(['a','b'],self.raw,self.text)),'가겠어. 가예.')
    def test_bad_agent_schema_rejected(self):
        with self.assertRaises(ValidationError):validate_schema({'action':'finish'},DECISION)

class RunnerInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.a=Morphology()
    def execute(self,condition,mode='valid'):
        import tempfile
        from kg_runtime.experiment import run_record
        class Graph:
            by={'G_END_FINAL':{'title':'종결어미','type':'AnalysisConcept'}}
            def remaining_modules(self,result):return [{'id':'M12','title':'변이'}]
            def retrieve(self,m,a,concepts=None):
                return {'concept_ids':['G_END_FINAL'],'paths':[],'candidates':[
                  {'candidate_id':'GS_ENDRULE_YO_COMPOSE:W1:0','rule_id':'GS_ENDRULE_YO_COMPOSE','target_uid':'W1',
                   'before':'예쁘네요','after':'예쁘네예','span':[0,4],'condition':'종결형','source_refs':[{'doc':'D02','page':203}]}]}
        class Client:
            def call(self,stage,prompt,payload,schema,folder,*args):
                if stage=='agent' and mode=='lookup':
                    return {'action':'lookup','lookup_concepts':['M12'],'selected_candidate_ids':[],'output_text':'','reason':'추가 확인'}
                if stage=='generation':
                    ids=['invented'] if mode=='unplanned' else [] if mode=='omit' else ['GS_ENDRULE_YO_COMPOSE:W1:0']
                    return {'applied_candidate_ids':ids,'output_text':'예쁘네요.' if mode in ('omit','mismatch') else '예쁘네예.','reason':'test'}
                return {'action':'finish','lookup_concepts':[],'selected_candidate_ids':['GS_ENDRULE_YO_COMPOSE:W1:0'],'output_text':'예쁘네예.','reason':'test'}
        with tempfile.TemporaryDirectory() as d:
            return run_record({'id':'T1','text':'예쁘네요.'},condition,Client(),Graph(),self.a,{},Path(d),1)
    def test_single_stage_contract(self):self.assertEqual(self.execute('single')['output_text'],'예쁘네예.')
    def test_multi_stage_contract(self):self.assertEqual(self.execute('multi')['output_text'],'예쁘네예.')
    def test_worker_may_omit(self):self.assertEqual(self.execute('multi','omit')['status'],'unchanged')
    def test_worker_may_not_invent(self):self.assertEqual(self.execute('multi','unplanned')['error'],'worker_added_unplanned_edit')
    def test_reported_edit_must_match_output(self):self.assertEqual(self.execute('multi','mismatch')['error'],'output_differs_from_authorized_edits')
    def test_agent_requested_lookup_is_executed(self):self.assertEqual(self.execute('single','lookup')['kg_queries'],2)

if __name__=='__main__':unittest.main()
