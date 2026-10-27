import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime.graph import GraphTool,QUERY,LOOKUP_QUERY,compact_context
from kg_runtime.catalog import route_concepts,CONCEPT_TYPES
from kg_runtime.morphology import Morphology

class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.a=Morphology()
    def graph(self,rows=None):
        class Neo:
            def query(self,query,params):
                if query==LOOKUP_QUERY:return [{'id':x} for x in params['ids']]
                assert 'rules' not in params
                return rows or []
        return GraphTool(ROOT,Neo())
    def test_all_original_ids_and_edges_retained(self):
        g=self.graph();original=ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/graph'
        ns=[json.loads(l) for l in (original/'nodes.jsonl').read_text(encoding='utf8').splitlines()]
        es=[json.loads(l) for l in (original/'edges.jsonl').read_text(encoding='utf8').splitlines()]
        self.assertEqual(set(g.by),{n['id'] for n in ns});self.assertEqual(g.edgeids,{e['id'] for e in es})
    def test_inactive_item_direct_lookup_is_available(self):
        g=self.graph();ids=[n['id'] for n in g.by.values() if n['type']=='SourceAtom']
        self.assertEqual(len(g.lookup(ids)),721)
        self.assertEqual(sum(g.by[x]['properties']['executable'] for x in ids),17)
    def test_knowledge_conditions_not_lost(self):
        g=self.graph();p=g.by['GS_ENDRULE_Q_INDEF']['properties']
        self.assertEqual(p['documentary_condition_before_normalization']['wh_role'],'indefinite')
        self.assertNotIn('scope_profile',p)
        self.assertTrue(g.provenance['GS_ENDRULE_Q_INDEF']['source_refs'])
    def test_particle_and_relative_clause_routes_exist(self):
        g=self.graph();ids=route_concepts(self.a.analyze('아이에게 읽던 책을 주었어요.'))
        self.assertIn('G_CASE_ROLE',ids);self.assertIn('G_CLAUSE_RELATIVE',ids)
        for x in ids:self.assertIn(g.by[x]['type'],CONCEPT_TYPES)
    def test_non_executable_retrieved_but_not_applied(self):
        g=self.graph();rid=next(x for x,n in g.by.items() if n['type']=='SourceAtom' and x not in g.rules)
        e=next(e for e in g.runtime['edges'] if e['source']==rid and e['relation']=='in_module')
        rows=[{'concept_id':e['target'],'rule_id':rid,'edge_ids':[e['id']],'via':e['target']}]
        g=self.graph(rows);r=g.retrieve(self.a.analyze('책을 보아요.'),self.a)
        self.assertEqual(r['items'][0]['id'],rid);self.assertFalse(r['items'][0]['executable'])
        self.assertEqual(r['candidates'],[])
    def test_unknown_id_and_unknown_edge_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid'):self.graph().lookup(['invented'])
        rows=[{'rule_id':'GS_CONNECT_COND_03','edge_ids':['invented']}]
        with self.assertRaisesRegex(ValueError,'non_snapshot'):self.graph(rows).retrieve(self.a.analyze('가면 와.'),self.a)
    def test_query_has_no_runtime_activation_or_id_allowlist(self):
        for banned in ('runtime_active','activation','profile_not_selected','$rules'):self.assertNotIn(banned,QUERY)

if __name__=='__main__':unittest.main()
