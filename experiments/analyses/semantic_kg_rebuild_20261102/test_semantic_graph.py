import copy,json,unittest
from pathlib import Path
from semantic_graph import GraphReader,compile_graph
HERE=Path(__file__).resolve().parent
def load(name):return json.loads((HERE/'private'/name).read_text(encoding='utf8'))
class SemanticGraphTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=load('graph.json');cls.reader=GraphReader(cls.g);cls.data=load('easy_development.json');cls.spec=load('foundation.json')
    def a(self,i):return copy.deepcopy(self.data[i-1]['analysis'])
    def ids(self,a,kind='eligible'):
        return {i['rule_id'] for c in self.reader.query(a)['clauses'] for i in c[kind]}
    def test_development_contracts(self):
        for d in self.data:
            with self.subTest(id=d['id']):
                self.assertEqual(self.ids(d['analysis']),set(d['expected_eligible']))
                self.assertEqual(self.ids(d['analysis'],'unresolved'),set(d['expected_unresolved']))
    def test_clauses_do_not_leak_question_kind(self):
        a=self.a(1);b=self.a(2);n=len(a['text'])+1
        c=b['clauses'][0];c['id']='c2';c['span']=[x+n for x in c['span']];c['target_span']=[x+n for x in c['target_span']]
        c['predicate'].update(id='p2',clause_id='c2',span=c['target_span']);c['ending_slot'].update(id='end2',predicate_id='p2',clause_id='c2')
        for x in c['feature_bindings'].values():
            x['clause_id']='c2'
            if x['predicate_id']:x['predicate_id']='p2'
        c['question_variable'].update(id='w2',clause_id='c2',scope_clause_id='c2',span=[x+n for x in c['question_variable']['span']])
        a['text']+=' '+b['text'];a['clauses'].append(c)
        r=self.reader.query(a)['clauses']
        self.assertEqual([x['rule_id'] for x in r[0]['eligible']],['SEM_Q_V_POLAR'])
        self.assertEqual([x['rule_id'] for x in r[1]['eligible']],['SEM_Q_V_WH'])
    def test_no_string_wh_detection(self):
        a=self.a(17);a['clauses'][0]['features']['question_kind']='polar'
        self.assertEqual(self.ids(a),{'SEM_Q_V_POLAR'})
        a['clauses'][0]['features']['question_kind']='wh';a['clauses'][0]['question_variable']={'id':'w1','clause_id':'c1','scope_clause_id':'c1','span':[0,2],'surface':'어디','role':'asked_information'}
        self.assertEqual(self.ids(a),{'SEM_Q_V_WH'})
    def test_past_meaning_without_marker_is_not_marker(self):
        a=self.a(11);a['clauses'][0]['features']['tense']='past'
        self.assertEqual(self.ids(a),{'SEM_Q_C_POLAR'})
    def test_copula_past_marker_changes_family(self):
        a=self.a(11);a['clauses'][0]['features']['prefinal_type']='eoss'
        self.assertEqual(self.ids(a),{'SEM_Q_C_PAST_POLAR'})
    def test_unknown_is_not_permission(self):
        a=self.a(1);del a['clauses'][0]['features']['predicate_class']
        self.assertEqual(self.ids(a),set());self.assertTrue(self.ids(a,'unresolved'))
    def test_conflicting_analysis_values_not_randomly_selected(self):
        a=self.a(1);a['clauses'][0]['features']['question_kind']=['polar','wh']
        self.assertEqual(self.ids(a),set());self.assertEqual(len(self.ids(a,'unresolved')),2)
    def test_false_and_unknown_remains_false(self):
        a=self.a(22);a['clauses'][0]['features']['question_kind']=None
        self.assertEqual(self.ids(a),set());self.assertEqual(self.ids(a,'unresolved'),set())
    def test_invalid_span(self):
        a=self.a(1);a['clauses'][0]['target_span']=[0,999]
        with self.assertRaises(ValueError):self.reader.query(a)
    def test_target_text_mismatch(self):
        a=self.a(1);a['clauses'][0]['target_text']='샀어'
        with self.assertRaises(ValueError):self.reader.query(a)
    def test_duplicate_clause_id(self):
        a=self.a(1);a['clauses'].append(copy.deepcopy(a['clauses'][0]))
        with self.assertRaises(ValueError):self.reader.query(a)
    def test_graph_edges_drive_lookup(self):
        g=copy.deepcopy(self.g)
        f=next(n['id'] for n in g['nodes'] if n['type']=='FeatureValue' and n['properties']=={'feature':'question_kind','value':'polar'})
        g['edges']=[e for e in g['edges'] if not (e['relation']=='ACCEPTS' and e['target']==f)]
        r=GraphReader(g).query(self.a(1))
        self.assertEqual(r['clauses'][0]['eligible'],[])
    def test_module_edges_do_not_grant_eligibility(self):
        g=copy.deepcopy(self.g);g['edges']=[e for e in g['edges'] if e['relation']!='IN_MODULE']
        self.assertEqual(GraphReader(g).query(self.a(1))['clauses'],self.reader.query(self.a(1))['clauses'])
    def test_new_lexeme_needs_no_rule_code(self):
        a=self.a(1);a['text']='너 지금 코딩해?';c=a['clauses'][0];c['span']=[0,len(a['text'])];c['target_span']=[5,8];c['target_text']='코딩해'
        c['predicate'].update(span=[5,8],surface='코딩해')
        self.assertEqual(self.ids(a),{'SEM_Q_V_POLAR'})
    def test_packet_contains_selected_only_with_evidence(self):
        a=self.a(13);r=self.reader.query(a);p=self.reader.packet(a,r)
        self.assertEqual(len(p['clauses'][0]['choices']),1)
        self.assertEqual(p['clauses'][0]['choices'][0]['forms'][0]['form'],'-나')
        self.assertTrue(p['clauses'][0]['choices'][0]['evidence_ids'])
        self.assertNotIn('quote',json.dumps(p,ensure_ascii=False))
    def test_flat_equivalent_knowledge_matches_graph(self):
        # This checks semantic equivalence, not a KG performance advantage.
        for d in self.data:
            f=d['analysis']['clauses'][0]['features']
            flat={r['id'] for r in self.spec['rules'] if any(all(isinstance(f.get(k),str) and f[k] in vals for k,vals in b.items()) for b in r['any_branches'])}
            self.assertEqual(flat,self.ids(d['analysis']))
    def test_stale_analysis_packet_rejected(self):
        a=self.a(1);r=self.reader.query(a);a['clauses'][0]['features']['question_kind']=None
        with self.assertRaisesRegex(ValueError,'stale_analysis'):self.reader.packet(a,r)
    def test_stale_graph_packet_rejected(self):
        a=self.a(1);r=self.reader.query(a);g=copy.deepcopy(self.g);g['nodes'][0]['properties']['title']='changed'
        with self.assertRaisesRegex(ValueError,'stale_graph'):GraphReader(g).packet(a,r)
    def test_target_is_bound_to_predicate(self):
        a=self.a(2);a['clauses'][0].update(target_span=[0,1],target_text='너')
        with self.assertRaisesRegex(ValueError,'predicate_binding'):self.reader.query(a)
    def test_foreign_question_scope_rejected(self):
        a=self.a(2);a['clauses'][0]['question_variable']['scope_clause_id']='embedded_clause'
        with self.assertRaisesRegex(ValueError,'question_scope'):self.reader.query(a)
    def test_foreign_predicate_feature_rejected(self):
        a=self.a(2);a['clauses'][0]['feature_bindings']['prefinal_type']['predicate_id']='other_predicate'
        with self.assertRaisesRegex(ValueError,'feature_predicate'):self.reader.query(a)
    def test_unknown_string_is_invalid_input(self):
        a=self.a(1);a['clauses'][0]['features']['question_kind']='unknown'
        with self.assertRaisesRegex(ValueError,'invalid_feature_value'):self.reader.query(a)
    def test_typo_not_silent_rejection(self):
        a=self.a(1);a['clauses'][0]['features']['question_kind']='pollarr'
        with self.assertRaisesRegex(ValueError,'invalid_feature_value'):self.reader.query(a)
    def test_outside_scope_is_not_bad_grammar(self):
        for i in (19,20,21,22,23,24):
            r=self.reader.query(self.a(i))['clauses'][0]
            self.assertTrue(r['out_of_slice']);self.assertFalse(r['not_matching_usage']);self.assertTrue(r['scope_failures'])
    def test_or_branch_true_beats_unknown(self):
        g=copy.deepcopy(self.g)
        b=next(n for n in g['nodes'] if n['id']=='SEM_Q_V_POLAR/branch/0');b=copy.deepcopy(b);b['id']='OR_EXTRA';g['nodes'].append(b)
        g['edges'].append({'id':'OR_OWNER','source':'SEM_Q_V_POLAR','relation':'ANY_BRANCH','target':'OR_EXTRA'})
        pred=next(n for n in g['nodes'] if n['type']=='Condition' and n['properties']['feature']=='predicate_class' and 'verb' in n['properties']['allowed'])
        g['edges'].append({'id':'OR_COND','source':'OR_EXTRA','relation':'ALL','target':pred['id']})
        a=self.a(1);a['clauses'][0]['features']['question_kind']=None
        r=GraphReader(g).query(a)['clauses'][0]
        self.assertIn('SEM_Q_V_POLAR',[x['rule_id'] for x in r['eligible']])
if __name__=='__main__':unittest.main()
