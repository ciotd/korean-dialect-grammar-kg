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
        with self.assertRaisesRegex(ValidationError, 'correction_without_source_quote'):
            multi.bind_meaning(text, units, meaning, schema)

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

if __name__ == '__main__':
    unittest.main()
