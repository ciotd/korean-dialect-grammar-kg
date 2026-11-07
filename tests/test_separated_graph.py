import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from kg_pipeline.separated_graph import separate, restore, compact_payload, lookup_audit


class SeparationTests(unittest.TestCase):
    def graph(self):
        return {'version': 'old', 'feature_schema': {}, 'gaps': ['unresolved'], 'nodes': [
            {'id': 'R', 'type': 'SemanticRule', 'properties': {
                'instruction': '과거를 보존한다.', 'meaning': '과거를 보존한다.',
                'limitations': '명령문에는 적용하지 않는다.', 'runtime_active': False,
                'source_refs': [{'doc': 'D01', 'page': 1}], 'unknown_future_field': 'keep'}},
            {'id': 'C', 'type': 'Condition', 'properties': {'feature': 'tense', 'allowed': ['past'],
                'operator': 'in', 'basis': 'source interpretation'}},
            {'id': 'E', 'type': 'Evidence', 'properties': {'quote': '원문'}}],
            'edges': [{'id': 'e1', 'source': 'R', 'target': 'C', 'relation': 'ALL',
                       'properties': {'origin': 'builder', 'mapping_kind': 'interpretation'}},
                      {'id': 'e2', 'source': 'R', 'target': 'E', 'relation': 'SUPPORTED_BY'}]}

    def test_exact_restore_and_external_lookup(self):
        source = self.graph(); before = copy.deepcopy(source)
        graph, archive = separate(source, 'new')
        self.assertEqual(source, before)
        self.assertEqual(restore(graph, archive), source)
        self.assertEqual([e['id'] for e in graph['edges']], ['e1'])
        self.assertEqual(lookup_audit(graph, archive, 'R')['linked_documentary_nodes'][0]['id'], 'E')

    def test_grammar_unknown_fields_and_qualifications_preserved(self):
        graph, _ = separate(self.graph(), 'new')
        p = graph['nodes'][0]['properties']
        self.assertEqual(p['limitations'], '명령문에는 적용하지 않는다.')
        self.assertEqual(p['unknown_future_field'], 'keep')
        self.assertIs(p['runtime_active'], False)
        self.assertNotIn('source_refs', p)
        self.assertNotIn('meaning', p)
        self.assertEqual(graph['nodes'][1]['properties']['allowed'], ['past'])
        self.assertEqual(graph['edges'][0]['properties']['mapping_kind'], 'interpretation')

    def test_changed_condition_or_archive_fails_restore(self):
        graph, archive = separate(self.graph(), 'new')
        corrupt = copy.deepcopy(graph); corrupt['nodes'][1]['properties']['allowed'] = ['present']
        with self.assertRaisesRegex(ValueError, 'Execution graph changed'): restore(corrupt, archive)
        archive['documentary_nodes'][0]['properties']['quote'] = 'tampered'
        with self.assertRaisesRegex(ValueError, 'Archive changed'): restore(graph, archive)

    def test_packet_only_removes_exact_repetition(self):
        p = {'instruction': '과거를 보존한다.', 'sources': [{'doc': 'D01'}],
             'forms': [{'form': '노', 'composition': '과거를 보존한다.'},
                       {'form': '나', 'composition': '다른 결합 조건'}], 'preserve': ['tense']}
        c = compact_payload(p)
        self.assertNotIn('sources', c)
        self.assertNotIn('composition', c['forms'][0])
        self.assertEqual(c['forms'][1]['composition'], '다른 결합 조건')
        self.assertEqual(c['preserve'], p['preserve'])
        self.assertIn('sources', p)

    def test_bad_graph_and_reseparation_rejected(self):
        source = self.graph(); source['edges'][0]['target'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'Dangling'): separate(source, 'new')
        graph, _ = separate(self.graph(), 'new')
        with self.assertRaisesRegex(ValueError, 'Already separated'): separate(graph, 'newer')


if __name__ == '__main__': unittest.main()
