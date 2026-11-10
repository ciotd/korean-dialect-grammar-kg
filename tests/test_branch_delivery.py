"""Delivery must preserve constraints independently of condition eligibility."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kg_pipeline.integrated import IntegratedReader, delivery_limitations, bind_analysis, retrieve_packet
from kg_pipeline.delivery_normalization import normalize_delivery


def fixture():
    def n(i,t,**p):return {'id':i,'type':t,'properties':p}
    def e(a,r,b):return {'id':a+'-'+r+'-'+b,'source':a,'relation':r,'target':b}
    return {'nodes':[n('F','GrammarConstruction'),n('S','Scope',allowed={'clause_role':['main']}),
        n('R','SemanticRule',instruction='과거를 보존',limits=['요청에는 쓰지 않음'],
          generation_operation='replace_final',target='ending',surface_postcondition={'past':'preserve'},operation='generate'),
        n('B','ApplicabilityBranch'),n('C','Condition',feature='tense',operator='in',allowed=['past']),
        n('V','FeatureValue',value='past'),n('X','Realization',form='노',unit='ending',operation='keep_stem',surface_postcondition='keep_past')],
        'edges':[e('F','HAS_USAGE','R'),e('F','SUPPORTED_IN','S'),e('R','ANY_BRANCH','B'),
                 e('B','ALL','C'),e('C','ACCEPTS','V'),e('R','REALIZES','X')]}


class DeliveryTests(unittest.TestCase):
    def test_exact_note_removal_preserves_real_restrictions(self):
        p={'rule_id':'INT_END_PROHIB_MAISO','limitations':'-시- 결합형 미확인. | 조건 보완: construction에 lemma·어미 조건이 없어 높임 금지 판정만으로 걸림. 명사+말다는 별도 분기.',
           'forms':[{'form':'마이소'}]}
        result=normalize_delivery(p)
        self.assertNotIn('조건이 없어',result['limitations'])
        self.assertIn('-시- 결합형 미확인.',result['limitations'])
        self.assertIn('명사+말다는 별도 분기.',result['limitations'])
        self.assertIn('조건이 없어',p['limitations'])
        self.assertEqual(normalize_delivery({'rule_id':'unreviewed','limitations':p['limitations']})['limitations'],p['limitations'])

    def test_documentary_limit_removed_but_scope_kept(self):
        result=normalize_delivery({'limitations':['이번 직접 정보 질문 체계의 후보이며 모든 경상도 용법을 망라하지 않음.','완성형은 조합 결과이며 원문 인용과 구별','과거 보존']})
        self.assertEqual(result['limitations'],['실제 답을 묻는 주절 직접 질문의 후보 어미이며, 경상 방언 의문형 전부는 아니다.','과거 보존'])

    def test_alias_conflict_preserved_and_no_mutation(self):
        p={'limitations':'높임 유지','limits':['과거 유지']};old=copy.deepcopy(p)
        value=delivery_limitations(p)
        self.assertEqual(value,['높임 유지',['과거 유지']])
        value[1].append('changed');self.assertEqual(p,old)
        self.assertEqual(delivery_limitations({'limits':'A','limitations':'A'}),'A')
        self.assertEqual(delivery_limitations({'limitations':'','limits':['A']}),['A'])

    def test_scope_gate_trace_and_grammar_delivery(self):
        graph=fixture();old=copy.deepcopy(graph);reader=IntegratedReader(graph)
        unit={'id':'u','kind':'predicate','span':[0,3],'text':'먹었어','morphs':[['먹','VV'],['었','EP']]}
        features={'unit_kind':'predicate','clause_role':'main','tense':'past'}
        hit=reader.query(unit,features)['eligible'][0]
        self.assertIn('F-SUPPORTED_IN-S',hit['branches'][0]['path_edge_ids'])
        p=reader.payload(unit,hit)
        self.assertEqual(p['limitations'],['요청에는 쓰지 않음'])
        self.assertEqual(p['forms'][0]['unit'],'ending')
        self.assertEqual(p['forms'][0]['operation'],'keep_stem')
        self.assertEqual(p['forms'][0]['surface_postcondition'],'keep_past')
        for key in ('target','operation','generation_operation','surface_postcondition'):
            self.assertEqual(p[key],reader.nodes['R']['properties'][key])
        self.assertEqual(reader.query(unit,{**features,'clause_role':'embedded'})['rejected'][0]['state'],'condition_mismatch')
        self.assertEqual(reader.query(unit,{**features,'clause_role':None})['unresolved'][0]['state'],'unresolved')
        self.assertEqual(graph,old)

    def test_missing_required_relation_not_approved(self):
        graph=fixture();graph['nodes'][2]['properties']['required_relations']=['main_predicate']
        reader=IntegratedReader(graph)
        unit={'id':'u','kind':'predicate'}
        result=reader.query(unit,{'unit_kind':'predicate','clause_role':'main','tense':'past'})
        self.assertEqual(result['eligible'],[])
        self.assertEqual(result['unresolved'][0]['missing_relations'],['main_predicate'])

    def test_delivery_checker_detects_lost_fields(self):
        path=Path(__file__).resolve().parents[1]/'experiments/analyses/branch_validation_20261110/validate_branches.py'
        spec=importlib.util.spec_from_file_location('delivery_validator',path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        reader=IntegratedReader(fixture());u={'id':'u','kind':'predicate','span':[0,1],'text':'가','morphs':[]}
        hit=reader.query(u,{'unit_kind':'predicate','clause_role':'main','tense':'past'})['eligible'][0]
        payload=reader.payload(u,hit)
        self.assertTrue(all(mod.check_delivery(reader,'R',payload).values()))
        for mutate in ('limitations','forms','operation'):
            bad=copy.deepcopy(payload)
            if mutate=='operation':bad['forms'][0].pop('operation')
            else:bad.pop(mutate)
            self.assertFalse(all(mod.check_delivery(reader,'R',bad).values()),mutate)

    def test_boolean_logic_and_missing_values(self):
        graph=fixture()
        graph['nodes'].extend([{'id':'B2','type':'ApplicabilityBranch','properties':{}},
            {'id':'C2','type':'Condition','properties':{'feature':'question_kind','operator':'in','allowed':['wh']}},
            {'id':'V2','type':'FeatureValue','properties':{'value':'wh'}}])
        graph['edges'].extend([{'id':a+r+b,'source':a,'relation':r,'target':b} for a,r,b in
            [('R','ANY_BRANCH','B2'),('B2','ALL','C2'),('C2','ACCEPTS','V2')]])
        reader=IntegratedReader(graph);u={'id':'u','kind':'predicate'}
        def state(**f):
            q=reader.query(u,{'unit_kind':'predicate','clause_role':'main',**f})
            return next(k for k in ('eligible','unresolved','rejected') if q[k])
        self.assertEqual(state(tense='past',question_kind=None),'eligible')
        self.assertEqual(state(tense='present',question_kind=None),'unresolved')
        self.assertEqual(state(tense='present',question_kind='polar'),'rejected')
        for unknown in (None,'unknown'):
            self.assertEqual(state(tense=unknown,question_kind='polar'),'unresolved')
        self.assertEqual(state(question_kind='polar'),'unresolved')
        self.assertEqual(state(clause_role='embedded',tense=None,question_kind=None),'rejected')
        with self.assertRaisesRegex(ValueError,'binding mismatch'):reader.query(u,{'unit_kind':'nominal'})

    def test_invalid_relation_does_not_enable_query(self):
        graph=fixture();graph['nodes'][2]['properties']['required_relations']=['main_predicate']
        reader=IntegratedReader(graph)
        def unit(i,w):return {'id':i,'kind':'predicate','word_id':w,'sentence':0,'related_word_ids':['w1','w2'],
             'morphs':[['가','VV']],'observed':{'unit_kind':'predicate','predicate_class':'verb'}}
        units=[unit('u','w1'),unit('v','w2')]
        def raw(target,other_clause='c'):
            return {'units':[{'unit_id':i,'features':{'tense':'past','clause_role':'main','predicate_class':'verb'},
                'clause_key':'c' if i=='u' else other_clause,'related_unit_ids':[],
                'relations':[{'role':'main_predicate','target_id':target}] if i=='u' else []} for i in ('u','v')]}
        for target,clause in [('u','c'),('v','other')]:
            bound=bind_analysis(units,raw(target,clause))[0]
            self.assertTrue(bound['relation_issues'])
            self.assertTrue(reader.query(bound,bound['features'])['unresolved'])
        with self.assertRaisesRegex(ValueError,'Foreign named'):bind_analysis(units,raw('missing'))
        bound=bind_analysis(units,raw('v'))[0]
        self.assertTrue(reader.query(bound,bound['features'])['eligible'])

    def test_budget_omission_is_recorded(self):
        reader=IntegratedReader(fixture());u={'id':'u','kind':'predicate','span':[0,3],'text':'먹었어','morphs':[],
            'observed':{},'features':{'unit_kind':'predicate','clause_role':'main','tense':'past'}}
        packet,_=retrieve_packet(reader,'먹었어',[u],char_budget=0)
        self.assertEqual(packet['verified_scope_knowledge'],[])
        self.assertEqual(packet['delivery_omissions'][0]['rule_id'],'R')
        packet,_=retrieve_packet(reader,'먹었어',[u],char_budget=10000)
        self.assertEqual(packet['verified_scope_knowledge'][0]['forms'][0]['operation'],'keep_stem')


if __name__=='__main__':unittest.main()
