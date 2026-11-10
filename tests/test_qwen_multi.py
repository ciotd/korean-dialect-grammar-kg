"""No live model calls: original-span, graph-ID and role-contract checks."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline import multi_agent as multi
from kg_pipeline.validation import ValidationError, validate_schema


def structure_fixture(text='언제 문 닫았어?'):
    words = multi.word_anchors(text)
    fields = {key: None for key in multi.STRUCTURE_FIELDS}
    fields.update(source_form='어', lemma='닫', source_final='어',
                  prefinal_type='eoss', prefinal_sequence='eoss',
                  past_form='present', ending_tag='EF', root_tag='VV')
    unit = {'id': 'U1', 'kind': 'predicate', 'start_word': words[-1]['id'],
            'end_word': words[-1]['id'], 'clause_id': 'C1',
            'morphs': [{'form': '닫', 'tag': 'VV', 'restored': False}, {'form': '았', 'tag': 'EP', 'restored': True}, {'form': '어', 'tag': 'EF', 'restored': False}],
            'features': fields}
    # Additional structure flags are part of the implementation contract, when present.
    schema = multi.structure_contract(words)
    for key, prop in schema['properties']['units']['items']['properties'].items():
        if key not in unit and prop.get('type') == 'boolean':
            unit[key] = False
    return words, {'clauses': [{'id': 'C1', 'parent_id': None,
                               'start_word': words[0]['id'], 'end_word': words[-1]['id']}],
                   'units': [unit], 'uncertainties': []}


def meaning_fixture(reader, units):
    schema = multi.meaning_contract(reader, units)
    variants = schema['properties']['units']['items']['anyOf']
    rows = []
    for u in units:
        variant = next(v for v in variants if u['id'] in v['properties']['unit_id']['enum'])
        rows.append({'unit_id': u['id'],
                     'features': {k: None for k in variant['properties']['features']['properties']},
                     'clause_key': u['clause_key'], 'related_unit_ids': [], 'relations': [],
                     'grammatical_role': None})
    return schema, {'units': rows, 'structural_corrections': [], 'analysis_issues': []}


class MultiContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pointer_path = ROOT / 'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json'
        if not pointer_path.exists():
            raise unittest.SkipTest('Separated KG fixture is not available')
        pointer = json.loads(pointer_path.read_text(encoding='utf-8'))
        path = ROOT / pointer['graph']
        if not path.exists():
            raise unittest.SkipTest('Private KG fixture is not available')
        cls.reader = IntegratedReader(json.loads(path.read_text(encoding='utf-8')))

    def test_repeated_words_and_unicode_keep_distinct_original_spans(self):
        text = '😀 먹어.\n먹어.'
        words = multi.word_anchors(text)
        self.assertEqual([text[slice(*w['span'])] for w in words], ['😀', '먹어.', '먹어.'])
        self.assertNotEqual(words[1]['span'], words[2]['span'])
        self.assertEqual(len({w['id'] for w in words}), 3)

    def test_original_surface_is_not_reconstructed_from_morphemes(self):
        text = '거기 뒀어.'
        words, raw = structure_fixture(text)
        raw['units'][0]['morphs'] = [{'form': '두', 'tag': 'VV', 'restored': True}, {'form': '었', 'tag': 'EP', 'restored': True}, {'form': '어', 'tag': 'EF', 'restored': False}]
        units, _ = multi.normalize_structure(text, words, raw)
        self.assertEqual(units[0]['text'], '뒀어.')
        self.assertEqual(text[slice(*units[0]['span'])], '뒀어.')
        self.assertEqual(units[0]['morphs'][0][0], '두')

    def test_reversed_word_range_is_rejected(self):
        words, raw = structure_fixture()
        raw['units'][0].update(start_word='W3', end_word='W1')
        with self.assertRaises(ValidationError):
            multi.normalize_structure('언제 문 닫았어?', words, raw)

    def test_missing_source_clause_coverage_is_rejected(self):
        words, raw = structure_fixture()
        raw['clauses'][0]['start_word'] = 'W2'
        with self.assertRaises(ValidationError):
            multi.normalize_structure('언제 문 닫았어?', words, raw)

    def test_unknown_clause_and_duplicate_unit_are_rejected(self):
        words, raw = structure_fixture()
        bad = copy.deepcopy(raw)
        bad['units'][0]['clause_id'] = 'invented'
        with self.assertRaises(ValidationError):
            multi.normalize_structure('언제 문 닫았어?', words, bad)
        raw['units'].append(copy.deepcopy(raw['units'][0]))
        with self.assertRaises(ValidationError):
            multi.normalize_structure('언제 문 닫았어?', words, raw)

    def test_clause_parent_cycle_is_rejected(self):
        words, raw = structure_fixture()
        raw['clauses'][0]['parent_id'] = 'C1'
        with self.assertRaises(ValidationError):
            multi.normalize_structure('언제 문 닫았어?', words, raw)

    def test_lemma_is_not_restricted_to_graph_vocabulary(self):
        fields = multi.STRUCTURE_FIELDS['lemma']
        self.assertNotIn('enum', fields)
        validate_schema('새로운어휘', fields)

    def test_nominal_question_character_is_separate_from_location_role(self):
        words, raw = structure_fixture('어디야?')
        raw['units'][0]['kind'] = 'nominal'
        units, _ = multi.normalize_structure('어디야?', words, raw)
        schema = multi.meaning_contract(self.reader, units)
        variant = schema['properties']['units']['items']['anyOf'][0]
        meaning = variant['properties']['features']['properties']['semantic_function']
        role = variant['properties']['grammatical_role']
        validate_schema('interrogative', meaning)
        validate_schema('location', role)
        with self.assertRaises(ValidationError):
            validate_schema('location', meaning)

    def test_actual_graph_rule_is_reached_from_model_unit_contract(self):
        words, raw = structure_fixture()
        units, _ = multi.normalize_structure('언제 문 닫았어?', words, raw)
        unit = units[0]
        features = {**unit['observed'], 'speech_act': 'information_question',
                    'question_kind': 'wh', 'predicate_class': 'verb', 'clause_role': 'main',
                    'addressee_level': 'plain', 'subject_honorific': 'absent',
                    'polarity': 'positive', 'tense': 'past'}
        result = self.reader.query(unit, features)
        self.assertIn('SEM_Q_V_WH', {h['rule_id'] for h in result['eligible']})
        self.assertTrue(all(h['rule_id'] in self.reader.rules for h in result['eligible']))

    def test_planner_cannot_invent_or_duplicate_actions(self):
        actions = [{'action_id': 'A1', 'rule_id': 'SEM_Q_V_WH', 'unit_id': 'U1'}]
        plan = {'selected': [{'action_id': 'invented', 'change': 'x', 'keep': []}],
                'not_selected': [], 'uncovered_units': [], 'uncertainties': []}
        with self.assertRaises(ValidationError):
            multi.validate_plan(plan, actions, [{'id': 'U1'}])
        plan['selected'][0]['action_id'] = 'A1'
        plan['not_selected'] = [{'action_id': 'A1', 'reason': 'duplicate'}]
        with self.assertRaises(ValidationError):
            multi.validate_plan(plan, actions, [{'id': 'U1'}])

    def test_empty_candidates_do_not_permit_fabricated_actions(self):
        plan = {'selected': [{'action_id': 'A1', 'change': 'x', 'keep': []}],
                'not_selected': [], 'uncovered_units': [], 'uncertainties': []}
        with self.assertRaises(ValidationError):
            multi.validate_plan(plan, [], [{'id': 'U1'}])

    def test_same_rule_at_two_locations_remains_two_actions(self):
        actions = [{'action_id': 'A1', 'rule_id': 'SEM_Q_V_WH', 'unit_id': 'U1'},
                   {'action_id': 'A2', 'rule_id': 'SEM_Q_V_WH', 'unit_id': 'U2'}]
        plan = {'selected': [{'action_id': 'A2', 'change': 'x', 'keep': ['past']}],
                'not_selected': [{'action_id': 'A1', 'reason': 'not chosen'}],
                'uncovered_units': [], 'uncertainties': []}
        chosen = multi.validate_plan(plan, actions, [{'id': 'U1'}, {'id': 'U2'}])
        self.assertEqual([x['unit_id'] for x in chosen], ['U2'])

    def test_structure_unit_cannot_cross_sentence_boundary(self):
        text = '먹어. 자.'
        words, raw = structure_fixture(text)
        raw['units'][0].update(start_word='W1', end_word='W2')
        with self.assertRaisesRegex(ValidationError, 'sentence_boundary'):
            multi.normalize_structure(text, words, raw)

    def test_writer_must_explain_each_action_and_match_usage(self):
        actions = [{'action_id': 'A1'}]
        clauses = [{'id': 'C1'}]
        draft = {'decisions': [{'action_id': 'A1', 'decision': 'not_used', 'reason': 'x', 'keep': []}],
                 'output_text': '문 닫았어.', 'used_action_ids': ['A1'],
                 'clause_coverage': [{'clause_id': 'C1', 'output_quote': '문 닫았어.'}],
                 'model_knowledge_changes': [], 'warnings': []}
        with self.assertRaisesRegex(ValidationError, 'decision_use_disagreement'):
            multi.check_writer(draft, actions, clauses)

    def test_structure_objection_is_recorded_without_overwriting(self):
        text = '언제 문 닫았어?'
        words, raw = structure_fixture(text)
        units, _ = multi.normalize_structure(text, words, raw)
        schema, meaning = meaning_fixture(self.reader, units)
        meaning['structural_corrections'] = [{'unit_id': 'U1', 'field': 'past_form',
                                             'value': 'absent', 'source_quote': '닫았어'}]
        bound = multi.bind_meaning(text, units, meaning, schema)
        self.assertEqual(bound[0]['features']['past_form'], 'present')
        self.assertEqual(bound[0]['structural_objections'][0]['value'], 'absent')

    def test_invalid_correction_quote_is_rejected(self):
        text = '언제 문 닫았어?'
        words, raw = structure_fixture(text)
        units, _ = multi.normalize_structure(text, words, raw)
        schema, meaning = meaning_fixture(self.reader, units)
        meaning['structural_corrections'] = [{'unit_id': 'U1', 'field': 'past_form',
                                             'value': 'absent', 'source_quote': '없는 원문'}]
        bound=multi.bind_meaning(text, units, meaning, schema)
        self.assertEqual(bound[0]['features']['past_form'],'present')
        self.assertEqual(bound[0]['rejected_structural_corrections'][0]['reason'],'correction_without_source_quote')
        self.assertIn('invalid_structural_correction',bound[0]['analysis_issues'])

    def test_auxiliary_cannot_be_bound_as_main_predicate(self):
        text = '하지 마.'
        words, raw = structure_fixture(text)
        main = raw['units'][0]
        main.update(start_word='W1', end_word='W1')
        main['features'].update(root_tag='VV', lemma='하')
        aux = copy.deepcopy(main)
        aux.update(id='U2', start_word='W2', end_word='W2')
        aux['features'].update(root_tag='VX', lemma='말')
        cx = copy.deepcopy(main)
        cx.update(id='U3', kind='construction', start_word='W1', end_word='W2')
        raw['units'] = [main, aux, cx]
        units, _ = multi.normalize_structure(text, words, raw)
        schema, meaning = meaning_fixture(self.reader, units)
        meaning['units'][2]['relations'] = [{'role': 'main_predicate', 'target_id': 'U2'},
                                            {'role': 'auxiliary_predicate', 'target_id': 'U1'}]
        bound = multi.bind_meaning(text, units, meaning, schema)
        self.assertFalse(bound[2]['relations'].get('main_predicate'))
        self.assertFalse(bound[2]['relations'].get('auxiliary_predicate'))
        self.assertEqual(len(bound[2]['relation_issues']), 2)

    def test_mock_client_connects_four_roles_to_actual_kg(self):
        class FakeClient:
            def __init__(self):
                self.roles = []
            def call(self, stage, prompt, payload, schema, out, tokens, seed):
                self.roles.append(stage)
                if stage == 'multi_structure':
                    return structure_fixture(payload['text'])[1]
                if stage == 'multi_meaning':
                    variants = schema['properties']['units']['items']['anyOf']
                    rows = []
                    for u in payload['units']:
                        variant = next(v for v in variants if u['id'] in v['properties']['unit_id']['enum'])
                        features = {k: None for k in variant['properties']['features']['properties']}
                        values = {'speech_act': 'information_question', 'question_kind': 'wh',
                                  'predicate_class': 'verb', 'clause_role': 'main', 'addressee_level': 'plain',
                                  'subject_honorific': 'absent', 'polarity': 'positive', 'tense': 'past'}
                        features.update({k: v for k, v in values.items() if k in features})
                        rows.append({'unit_id': u['id'], 'features': features, 'clause_key': 'C1',
                                     'related_unit_ids': [], 'relations': [], 'grammatical_role': None})
                    return {'units': rows, 'structural_corrections': [], 'analysis_issues': []}
                if stage == 'multi_writer':
                    actions = payload['knowledge']
                    return {'decisions': [{'action_id': a['action_id'], 'decision': 'applied', 'reason': 'mock fixture', 'keep': ['past']} for a in actions],
                            'output_text': '언제 문 닫았노?', 'used_action_ids': [a['action_id'] for a in actions],
                            'clause_coverage': [{'clause_id': 'C1', 'output_quote': '언제 문 닫았노?'}],
                            'model_knowledge_changes': [], 'warnings': []}
                if stage == 'multi_reviewer':
                    return {'correction_required': False, 'issues': [], 'uncertainties': []}
                raise AssertionError('Unexpected role ' + stage)
        client = FakeClient()
        with tempfile.TemporaryDirectory() as temp:
            result = multi.run_sentence(client, self.reader, '언제 문 닫았어?', Path(temp), max_repairs=0)
            self.assertEqual(client.roles, ['multi_structure', 'multi_meaning', 'multi_writer', 'multi_reviewer'])
            self.assertEqual(result['output_text'], '언제 문 닫았노?')
            self.assertIn('SEM_Q_V_WH', result['used_rule_ids'])
            self.assertFalse(result['kiwi_used'])
            self.assertEqual(result['call_count'], 4)

    def test_import_does_not_load_kiwi(self):
        code = """import sys,importlib.abc
sys.path.insert(0,sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.startswith(('kiwipiepy','kg_runtime.morphology')):raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
import kg_pipeline.multi_agent
"""
        result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT/'src')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_root_tag_conflict_is_preserved_for_deferral(self):
        words, raw = structure_fixture()
        raw['units'][0]['features']['root_tag'] = 'VX'
        units, _ = multi.normalize_structure('언제 문 닫았어?', words, raw)
        schema, meaning = meaning_fixture(self.reader, units)
        bound = multi.bind_meaning('언제 문 닫았어?', units, meaning, schema)
        self.assertIn('root_tag_morphology_disagreement', bound[0]['analysis_issues'])

    def test_meaning_cannot_silently_replace_clause(self):
        words, raw = structure_fixture()
        raw['clauses'].append({'id':'C2','parent_id':'C1','start_word':'W3','end_word':'W3'})
        units, _ = multi.normalize_structure('언제 문 닫았어?', words, raw)
        # Make C2 an existing target for the schema without changing the predicate's clause.
        extra = copy.deepcopy(units[0]); extra['id']='U2'; extra['kind']='connector'; extra['clause_key']='C2'; extra['structural_clause_id']='C2'; extra['observed']['unit_kind']='connector'
        units.append(extra)
        schema, meaning = meaning_fixture(self.reader, units)
        meaning['units'][0]['clause_key']='C2'
        bound=multi.bind_meaning('언제 문 닫았어?',units,meaning,schema)
        self.assertEqual(bound[0]['clause_key'],'C1')
        self.assertTrue(any(x['field']=='clause_key' for x in bound[0]['structural_objections']))

    def test_explicit_past_sequence_contradiction_is_flagged(self):
        words,raw=structure_fixture()
        raw['units'][0]['features'].update(prefinal_sequence='none',prefinal_type='none')
        units,_=multi.normalize_structure('언제 문 닫았어?',words,raw)
        self.assertIn('prefinal_sequence_morphology_disagreement',units[0]['structure_issues'])
        self.assertIn('prefinal_type_morphology_disagreement',units[0]['structure_issues'])

    def test_si_past_sequence_and_unknown_are_not_auto_corrected(self):
        words,raw=structure_fixture()
        u=raw['units'][0]
        u['morphs'].insert(1,{'form':'시','tag':'EP','restored':True})
        for value,expected in [('eoss',True),('si_eoss',False),('other',False)]:
            u['features']['prefinal_sequence']=value
            units,_=multi.normalize_structure('언제 문 닫았어?',words,raw)
            self.assertEqual('prefinal_sequence_morphology_disagreement' in units[0]['structure_issues'],expected)
            self.assertEqual(units[0]['observed']['prefinal_sequence'],value)

    def test_empty_candidate_contract_disallows_placeholder_ids(self):
        schema=multi.writer_contract([], [{'id':'C1'}])
        draft={'decisions':[], 'output_text':'문장', 'used_action_ids':[],
               'clause_coverage':[{'clause_id':'C1','output_quote':'문장'}],
               'model_knowledge_changes':[], 'warnings':[]}
        multi.validate_schema(draft,schema)
        for field,value in [('used_action_ids',['none']),('decisions',[{'action_id':'none','decision':'not_used','reason':'없음','keep':[]}])]:
            bad=copy.deepcopy(draft);bad[field]=value
            with self.assertRaises(multi.ValidationError):multi.validate_schema(bad,schema)
        self.assertEqual(multi.plan_contract([])['properties']['selected']['maxItems'],0)
        self.assertEqual(multi.plan_contract([])['properties']['not_selected']['maxItems'],0)
    def test_invalid_correction_value_isolated_not_applied(self):
        words,raw=structure_fixture();units,_=multi.normalize_structure('언제 문 닫았어?',words,raw)
        schema,meaning=meaning_fixture(self.reader,units)
        meaning['structural_corrections']=[{'unit_id':'U1','field':'prefinal_type','value':'connective','source_quote':'닫았어'}]
        with self.assertRaises(ValidationError):validate_schema(meaning,schema)
        bound=multi.bind_meaning('언제 문 닫았어?',units,meaning,schema)
        self.assertEqual(bound[0]['features']['prefinal_type'],'eoss')
        self.assertEqual(len(bound[0]['rejected_structural_corrections']),1)

    def test_analysis_cause_does_not_block_output_repair(self):
        issue={'stage':'analysis','repair_target':'output','category':'addressee_honorific_loss',
            'source_quote':'했어요','output_quote':'했어','problem':'높임 손실','suggestion':'상대 높임 복구'}
        review=multi.validate_review({'correction_required':True,'issues':[issue],'uncertainties':[]},'했어요',{'output_text':'했어'})
        self.assertEqual(multi.repair_issues(review),[issue])
        issue['repair_target']='analysis'
        self.assertEqual(multi.repair_issues(review),[issue])
        review['correction_required']=False
        self.assertEqual(multi.repair_issues(review),[issue])

    def test_false_added_word_does_not_trigger_repair(self):
        issue={'stage':'generation','repair_target':'output','category':'added_content',
            'source_quote':'그 종이','output_quote':'그','problem':'그 추가','suggestion':'삭제'}
        review=multi.validate_review({'correction_required':True,'issues':[issue],'uncertainties':[]},'그 종이',{'output_text':'그 종이'})
        self.assertEqual(multi.repair_issues(review),[])
        self.assertEqual(review['state'],'invalid')
        issue['category']='other'
        review=multi.validate_review({'correction_required':True,'issues':[issue],'uncertainties':[]},'그 종이',{'output_text':'그 종이'})
        self.assertEqual(multi.repair_issues(review),[])

    def test_review_context_explains_past_presence_without_present_tense(self):
        units=[{'id':'U1','kind':'predicate','text':'했어','features':{'past_form':'present','tense':'past','subject_honorific':'present'}}]
        row=multi.review_context(units)[0]['보존 정보(분석 추정)']
        self.assertEqual(row['과거 형태 유무'],'있음')
        self.assertEqual(row['시간 의미'],'과거')
        self.assertEqual(row['주체 높임'],'있음')

    def test_bounded_structure_repair_and_output_repair_are_model_calls(self):
        text='언제 문 닫았어?'; words,raw=structure_fixture(text); outer=self
        class Fake:
            def __init__(self):self.roles=[];self.structures=0;self.writes=0
            def call(self,stage,prompt,payload,schema,out,tokens,seed):
                self.roles.append(stage)
                if stage=='multi_structure':
                    self.structures+=1;result=copy.deepcopy(raw)
                    if self.structures==1:result['units'][0]['features']['prefinal_sequence']='none'
                    return result
                if stage=='multi_meaning':
                    _,result=meaning_fixture(outer.reader,payload['units']);result['structural_corrections']=[{'unit_id':[],'field':'past_form','value':'absent','source_quote':'닫았어'}];return result
                if stage=='multi_writer':
                    self.writes+=1;value='언제 문 닫아?' if self.writes==1 else '언제 문 닫았노?'
                    d={'decisions':[],'output_text':value,'used_action_ids':[],
                        'clause_coverage':[{'clause_id':'C1','output_quote':value}], 'model_knowledge_changes':[],'warnings':[]}
                    if 'previous_draft' in payload:d['feedback_decisions']=[{'issue_id':'R1','decision':'accepted','reason':'mock'}]
                    return d
                if stage=='multi_reviewer':
                    return {'correction_required':True,'issues':[{'stage':'analysis','repair_target':'output','category':'speech_act_changed',
                        'source_quote':'닫았어?','output_quote':'닫아?','problem':'모의 검토','suggestion':'모의 수정'}],'uncertainties':[]}
        client=Fake()
        with tempfile.TemporaryDirectory() as td:
            result=multi.run_sentence(client,self.reader,text,Path(td))
            self.assertEqual(result['call_count'],6)
            self.assertTrue(result['analysis_repaired']);self.assertTrue(result['repaired'])
            self.assertEqual(result['output_text'],'언제 문 닫았노?')
            self.assertTrue((Path(td)/'structure_initial_units.json').exists())
            self.assertFalse(result['post_repair_semantic_recheck'])
        class FailedSecond(Fake):
            def call(self,stage,*args):
                if stage=='multi_structure' and self.structures==1:
                    self.roles.append(stage);raise multi.CallError('simulated')
                return super().call(stage,*args)
        with tempfile.TemporaryDirectory() as td:
            result=multi.run_sentence(FailedSecond(),self.reader,text,Path(td),max_repairs=0)
            self.assertEqual(result['analysis_repair_status'],'failed_initial_analysis_retained')
            self.assertEqual(result['output_text'],'언제 문 닫아?')
            self.assertTrue((Path(td)/'structure_revision_failure.json').exists())


    def test_bad_unbound_proposals_do_not_block_every_unit(self):
        words,raw=structure_fixture();units,_=multi.normalize_structure('언제 문 닫았어?',words,raw)
        schema,meaning=meaning_fixture(self.reader,units)
        meaning['structural_corrections']=[{'unit_id':'missing','field':'past_form','value':'absent','source_quote':'문'}]
        bound=multi.bind_meaning('언제 문 닫았어?',units,meaning,schema)
        self.assertFalse(bound[0]['analysis_issues'])
        self.assertEqual(len(bound[0]['unbound_structural_corrections']),1)
        meaning['structural_corrections']=[{'unit_id':[],'field':'past_form','value':'absent','source_quote':'닫았어'},'not an object']
        bound=multi.bind_meaning('언제 문 닫았어?',units,meaning,schema)
        self.assertFalse(bound[0]['analysis_issues'])
        self.assertEqual(len(bound[0]['unbound_structural_corrections']),2)
        meaning['structural_corrections']=[{'unit_id':'U1','field':'past_form','value':'absent','source_quote':'닫았어','extra':'not allowed'}]
        bound=multi.bind_meaning('언제 문 닫았어?',units,meaning,schema)
        self.assertFalse(bound[0]['structural_objections'])
        self.assertEqual(len(bound[0]['rejected_structural_corrections']),1)

    def test_overlong_review_issue_isolated_not_truncated(self):
        issue={'stage':'analysis','repair_target':'output','category':'addressee_honorific_loss',
            'source_quote':'했어요','output_quote':'했어','problem':'높임 손실','suggestion':'높임 복구'}
        bad={**issue,'problem':'가'*181}
        review=multi.validate_review({'correction_required':True,'issues':[bad,issue],'uncertainties':[]},'했어요',{'output_text':'했어'})
        self.assertEqual(multi.repair_issues(review),[issue])
        self.assertEqual(review['state'],'partially_invalid')
        self.assertEqual(review['invalid_issues'][0]['issue']['problem'],'가'*181)

    def test_unchanged_quote_and_false_omission_do_not_route(self):
        base={'stage':'analysis','repair_target':'output','category':'tense_loss','source_quote':'인사한','output_quote':'인사한','problem':'모의','suggestion':'모의'}
        review=multi.validate_review({'correction_required':True,'issues':[base],'uncertainties':[]},'인사한 분',{'output_text':'인사한 분'})
        self.assertEqual(multi.repair_issues(review),[])
        self.assertEqual(review['invalid_issues'][0]['invalid_reason'],'unchanged_quote_not_evidence_of_change')
        missing={**base,'category':'missing_content','source_quote':'인사한 분','output_quote':''}
        review=multi.validate_review({'correction_required':True,'issues':[missing,missing],'uncertainties':[]},'인사한 분',{'output_text':'인사한 분'})
        self.assertEqual(multi.repair_issues(review),[])
        self.assertEqual(len(review['invalid_issues']),2)
        review=multi.validate_review({'correction_required':True,'issues':[missing],'uncertainties':[]},'인사한 분',{'output_text':'없음'})
        self.assertEqual(multi.repair_issues(review),[missing])

    def test_feedback_acceptance_is_report_not_an_edit_substitution(self):
        feedback=multi.feedback_request([{'category':'tense_loss'}])
        multi.check_feedback({'feedback_decisions':[{'issue_id':'R1','decision':'rejected','reason':'모의'}]},feedback)
        with self.assertRaises(ValidationError):multi.check_feedback({'feedback_decisions':[]},feedback)


if __name__ == '__main__':
    unittest.main()
