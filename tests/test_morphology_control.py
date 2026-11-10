import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tests')]
from kg_pipeline.morphology_control import anchors,prepare,frozen_clauses,kiwi_rows
from kg_pipeline.multi_agent import run_sentence,bind_meaning
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline.validation import ValidationError
from test_qwen_multi import meaning_fixture

class ControlledMorphology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=json.loads((ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json').read_text(encoding='utf8'))
        cls.reader=IntegratedReader(json.loads((ROOT/p['graph']).read_text(encoding='utf8')))
    def fixture(self):
        text='물을 마셨어요.';w=anchors(text)
        raw={'words':[{'word_id':'W1','morphs':[{'form':'물','tag':'NNG'},{'form':'을','tag':'JKO'}]},
            {'word_id':'W2','morphs':[{'form':'마시','tag':'VV'},{'form':'었','tag':'EP'},{'form':'어','tag':'EF'},{'form':'요','tag':'JX'}]}],'uncertainties':[]}
        clauses=frozen_clauses(text,{'clauses':[{'id':'C1','parent_id':None,'start_word':'W1','end_word':'W2'}]})
        return text,w,raw,clauses
    def test_same_morphs_identical_units_independent_of_backend(self):
        t,w,r,c=self.fixture();a=prepare(t,w,r,c,'qwen');r['uncertainties']=['모델 자유 설명은 후속 지시로 전달하지 않는다'];b=prepare(t,w,r,c,'kiwi')
        self.assertEqual(a['units'],b['units']);self.assertEqual(a['clauses'],b['clauses'])
        self.assertEqual(a['uncertainties'],b['uncertainties']);self.assertTrue(b['diagnostic_uncertainties_not_sent'])
        u=next(x for x in a['units'] if x['kind']=='predicate')
        self.assertEqual(u['observed']['past_form'],'present');self.assertEqual(u['observed']['source_final'],'어요')
        self.assertNotIn('predicate_class',u['observed']);self.assertNotIn('subject_honorific',u['observed'])
    def test_duplicate_word_rejected(self):
        t,w,r,c=self.fixture();r['words'].append(r['words'][0])
        with self.assertRaises(ValidationError):prepare(t,w,r,c,'qwen')
    def test_unknown_morphology_not_absence(self):
        t,w,r,c=self.fixture();r['words'][1]['morphs'][1]['tag']='UNKNOWN'
        u=next(x for x in prepare(t,w,r,c,'qwen')['units'] if x['kind']=='predicate')
        self.assertIsNone(u['observed']['past_form']);self.assertIn('unknown_morphology_not_proof_of_absence',u['structure_issues'])
    def test_nested_scope_and_both_word_auxiliary(self):
        from kiwipiepy import Kiwi
        t='본 물건을 옮겨 주세요.';w=anchors(t)
        c=frozen_clauses(t,{'clauses':[{'id':'C1','parent_id':None,'start_word':'W1','end_word':'W4'},{'id':'C2','parent_id':'C1','start_word':'W1','end_word':'W1'}]})
        u=prepare(t,w,kiwi_rows(t,w,Kiwi(num_workers=1)),c,'kiwi')['units']
        self.assertTrue(all(x['clause_key']=='C2' for x in u if x['word_id']=='W1'))
        construction=next(x for x in u if x['kind']=='construction')
        self.assertEqual(construction['text'],'옮겨 주세요');self.assertEqual(construction['clause_key'],'C1')
    def test_clause_scope_and_parent_validation(self):
        t,w,r,c=self.fixture();c[0]['span']=[0,1]
        with self.assertRaises(ValidationError):prepare(t,w,r,c,'kiwi')
        with self.assertRaises(ValidationError):frozen_clauses(t,{'clauses':[{'id':'C1','parent_id':'C1','start_word':'W1','end_word':'W2'}]})
    def test_meaning_not_silently_replaced_by_morphology(self):
        t,w,r,c=self.fixture();units=prepare(t,w,r,c,'kiwi')['units'];schema,m=meaning_fixture(self.reader,units)
        bound=bind_meaning(t,units,m,schema)
        p=next(x for x in bound if x['kind']=='predicate')
        self.assertIsNone(p['features']['subject_honorific'])
        self.assertEqual(p['feature_origin']['past_form'],'shared_morphology_adapter')
    def test_same_payload_and_no_automatic_repairs(self):
        t,w,r,c=self.fixture();outer=self
        class Fake:
            def __init__(self):self.calls=[]
            def call(self,stage,prompt,payload,schema,out,tokens,seed):
                self.calls.append([stage,prompt,payload,schema,tokens,seed])
                if stage=='multi_meaning':return meaning_fixture(outer.reader,payload['units'])[1]
                if stage=='multi_writer':return {'decisions':[],'output_text':t,'used_action_ids':[],
                    'clause_coverage':[{'clause_id':'C1','output_quote':t}],'model_knowledge_changes':[],'warnings':[]}
                if stage=='multi_reviewer':return {'correction_required':False,'issues':[],'uncertainties':[]}
                raise AssertionError(stage)
        a,b=Fake(),Fake()
        for backend,client in [('qwen',a),('kiwi',b)]:
            with tempfile.TemporaryDirectory() as td:
                result=run_sentence(client,self.reader,t,Path(td),max_repairs=0,max_analysis_repairs=0,prepared_structure=prepare(t,w,r,c,backend))
                self.assertFalse(result['repaired']);self.assertEqual(result['call_count'],3)
        self.assertEqual(a.calls,b.calls)
    def test_real_kiwi_same_shared_sentence_anchor(self):
        from kiwipiepy import Kiwi
        t='오셨어요. 여기 있어요.';w=anchors(t);r=kiwi_rows(t,w,Kiwi(num_workers=1))
        self.assertEqual([x['sentence'] for x in w],[0,1,1]);self.assertEqual(len(r['words']),len(w))

if __name__=='__main__':unittest.main()
