import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tools'),str(ROOT/'tests')]
from kg_pipeline.kiwi_default import *
from kg_pipeline.morphology_control import *
from kg_pipeline.multi_agent import run_sentence
from kg_pipeline.integrated import IntegratedReader
from test_qwen_multi import meaning_fixture

class KiwiDefault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from kiwipiepy import Kiwi
        cls.kiwi=Kiwi(num_workers=1)
        latest=json.loads((ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json').read_text(encoding='utf8'))
        cls.reader=IntegratedReader(json.loads((ROOT/latest['graph']).read_text(encoding='utf8')))
    def prepared(self,text):
        words=anchors(text);raw=kiwi_rows(text,words,self.kiwi)
        sr={'clauses':[{'id':'C1','parent_id':None,'start_word':'W1','end_word':'W'+str(len(word_anchors(text)))}],'predicate_words':[],'uncertainties':[]}
        p=prepare(text,words,raw,frozen_clauses(text,sr),'kiwi')
        return dict(p,morphology_words=words,morphology_rows=raw,scope_response=sr)
    def test_unrecognized_prefinal_is_not_absence(self):
        p=self.prepared('들어가셨어요.')
        for u in p['units']:
            u['morphs']=[['들어가','VV'],['셨','EP'],['어요','EF']];u['observed']['past_form']='absent'
        a=enhance_structure('들어가셨어요.',p)
        self.assertIsNone(a['units'][0]['observed']['past_form']);self.assertIsNone(a['units'][0]['observed']['prefinal_sequence'])
        self.assertEqual(p['units'][0]['observed']['past_form'],'absent')
    def test_missing_scope_predicate_recorded_not_invented(self):
        p=self.prepared('인사한 분이에요.');p['units']=[u for u in p['units'] if u['word_id']!='W1'];p['scope_response']['predicate_words']=['W1','W2']
        a=enhance_structure('인사한 분이에요.',p)
        self.assertEqual(len(a['units']),len(p['units']));self.assertTrue(any(x['text']=='인사한' for x in a['missing_coverage']))
    def test_auxiliary_candidates_are_roles_not_decisions(self):
        for text in ['상자를 옮겨 주세요.','떠들지 마세요.','전화해 봤어요.']:
            p=self.prepared(text);rr=relation_candidates(p['units']);self.assertTrue(rr)
            self.assertTrue(rr[0]['main_predicate']);self.assertTrue(rr[0]['auxiliary_predicate'])
            self.assertTrue(all('relations' not in u for u in p['units']))
    def test_humble_surface_and_normal_pronoun(self):
        for text in ['제 물건이에요.','저는 가요.','저희 물건이에요.','제가 먼저 갈게요.']:
            p=enhance_structure(text,self.prepared(text));self.assertTrue(humble_hints(p['units']))
        p=enhance_structure('제 물건이에요.',self.prepared('제 물건이에요.'))
        self.assertFalse(next(u for u in p['units'] if u['kind']=='particle' and u['observed']['source_form']=='의')['source_form_literal'])
        self.assertFalse(humble_hints(self.prepared('내 우산이야.')['units']))
        self.assertFalse(humble_hints(self.prepared('저 사람은 누구야?')['units']))
    def test_scope_contract_and_all_words(self):
        t='제가 가요. 너는 쉬어.';p=self.prepared(t)
        bad={'clauses':[{'id':'C1','parent_id':None,'start_word':'W1','end_word':'W2'}]}
        with self.assertRaises(Exception):frozen_clauses(t,bad)
        self.assertIn('predicate_words',scope_contract(t)['required'])
    def test_crossing_and_multisentence_scope_rejected(self):
        text='친구가 보는 책을 읽어요.'
        c=frozen_clauses(text,{'clauses':[{'id':'C1','parent_id':None,'start_word':'W1','end_word':'W4'},
            {'id':'C2','parent_id':'C1','start_word':'W1','end_word':'W2'},
            {'id':'C3','parent_id':'C1','start_word':'W2','end_word':'W3'}]})
        with self.assertRaises(Exception):validate_scope(text,c)
        c=frozen_clauses('가요. 쉬어요.',{'clauses':[{'id':'C1','parent_id':None,'start_word':'W1','end_word':'W2'}]})
        with self.assertRaises(Exception):validate_scope('가요. 쉬어요.',c)
    def test_new_data_expectations_not_writer_answers(self):
        from kg_pipeline.io import load_jsonl
        rows=load_jsonl(ROOT/'experiments/analyses/kiwi_default_20261107/development.jsonl')
        self.assertEqual(len(rows),12);self.assertTrue(all('check' in r and 'answer' not in r for r in rows))
    def test_same_final_writer_and_no_hidden_rewrite(self):
        text='저는 가요.';p=self.prepared(text);outer=self
        class Fake:
            def __init__(self):self.calls=[]
            def call(self,stage,prompt,payload,schema,out,tokens,seed):
                self.calls.append((stage,payload))
                if stage=='multi_meaning':return meaning_fixture(outer.reader,payload['units'])[1]
                if stage=='multi_writer':return {'decisions':[],'output_text':text,'used_action_ids':[],
                    'clause_coverage':[{'clause_id':'C1','output_quote':text}],'model_knowledge_changes':[],'warnings':[]}
                if stage=='multi_reviewer':return {'correction_required':False,'issues':[],'uncertainties':[]}
                raise AssertionError(stage)
        fake=Fake()
        with tempfile.TemporaryDirectory() as td:
            r=run_sentence(fake,self.reader,text,Path(td),max_repairs=0,max_analysis_repairs=0,prepared_structure=p,connection_policy='kiwi_improved')
        self.assertEqual(r['output_text'],text);self.assertEqual(len(fake.calls),3);self.assertFalse(r['repaired'])
        self.assertIn('relation_candidates',fake.calls[0][1]);self.assertTrue(any('겸양' in str(h) for h in fake.calls[1][1]['preservation_hints']))
    def test_cli_default_is_kiwi_old_option_remains(self):
        from run_qwen_multi import parser
        base=['--execute','--inputs','x','--phase','development','--deadline','2027-01-01T00:00:00Z','--max-calls','4']
        self.assertEqual(parser().parse_args(base).analysis_backend,'kiwi')
        self.assertEqual(parser().parse_args(base+['--analysis-backend','qwen']).analysis_backend,'qwen')

if __name__=='__main__':unittest.main()
