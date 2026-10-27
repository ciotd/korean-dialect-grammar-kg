import copy
import unittest
from pathlib import Path
import sys
import json
import tempfile
import urllib.error
import io
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kg_pipeline.contracts import ANALYSIS,GENERATION
from kg_pipeline.validation import validate_schema,validate_analysis,validate_generation,locate,ValidationError
from kg_pipeline.mapping import map_concepts
from kg_pipeline.selection import decision,select_evidence
from kg_pipeline.io import load_jsonl,Qwen,CallError

def sample():
    return {'input_id':'SMOKE_UNIT','clauses':[{'cid':'C1','anchor':{'surface':'민수야, 여기로 와.','occurrence':1},'parent_cid':None,'relation':'main'}],
     'units':[{'uid':'P1','kind':'predicate','cid':'C1','anchor':{'surface':'와','occurrence':1},'lemma':'오다','morphemes':['오-','-아'],
       'features':{'predicate_kind':'verb','stem':'오-','mood':'imperative','speech_act':'command','politeness':'informal','subject_honorific':'no','prefinal_tam':'absent',
        'question_type':'none','tense':'present','aspect':'none','negation':'none','constructions':[],'wh_scope_cid':'','agent':'addressee'}}],
     'uncertainties':[]}
class IntegrityTests(unittest.TestCase):
    def setUp(self):self.a=sample();self.text='민수야, 여기로 와.'
    def test_contract(self):validate_schema(self.a,ANALYSIS)
    def test_required_predicate_features(self):
        del self.a['units'][0]['features']['predicate_kind']
        with self.assertRaises(ValidationError):validate_schema(self.a,ANALYSIS)
    def test_anchor_occurrence(self):self.assertEqual(locate('가 가',{'surface':'가','occurrence':2}),[2,3])
    def test_no_anchor_normalization(self):
        with self.assertRaises(ValidationError):locate('가 봐',{'surface':'가봐','occurrence':1})
    def test_boolean_not_integer(self):
        with self.assertRaises(ValidationError):validate_schema(True,{'type':'integer'})
    def test_unknown_schema_keyword(self):
        with self.assertRaises(ValidationError):validate_schema('x',{'type':'string','pattern':'x'})
    def test_extra_field(self):
        a=copy.deepcopy(self.a);a['invented']='x'
        with self.assertRaises(ValidationError):validate_schema(a,ANALYSIS)
    def test_duplicate_ids(self):
        self.a['units'].append(copy.deepcopy(self.a['units'][0]))
        with self.assertRaises(ValidationError):validate_analysis(self.a,self.text,'SMOKE_UNIT',ANALYSIS)
    def test_clause_cycle(self):
        self.a['clauses'][0]['parent_cid']='C1'
        with self.assertRaises(ValidationError):validate_analysis(self.a,self.text,'SMOKE_UNIT',ANALYSIS)
    def test_wrong_clause(self):
        self.a['units'][0]['cid']='missing'
        with self.assertRaises(ValidationError):validate_analysis(self.a,self.text,'SMOKE_UNIT',ANALYSIS)
    def test_invalid_concept_not_invented(self):
        with self.assertRaises(ValueError):map_concepts(self.a,{})
    def test_real_concept_ids(self):
        root=Path(__file__).resolve().parents[1];p=root/'knowledge/authored/kg_v3_evidence_20261019_r2/graph/nodes.jsonl'
        catalog={n['id']:n for n in load_jsonl(p)};m=map_concepts(self.a,catalog)
        self.assertIn('G_END_FINAL',m['selected_concept_ids'])
    def test_nna_not_generalized(self):
        u=self.a['units'][0];c=self.a['clauses'][0]
        self.assertTrue(decision('C_D02_03',{},u,c)[0]);u['lemma']='가다'
        self.assertFalse(decision('C_D02_03',{},u,c)[0])
    def test_politeness_not_ignored(self):
        u=self.a['units'][0];u['features']['politeness']='polite'
        self.assertFalse(decision('C_D02_03',{},u,self.a['clauses'][0])[0])
    def test_unknown_deferred(self):
        u=self.a['units'][0];u['features']['mood']='unknown'
        self.assertFalse(decision('C_D02_03',{},u,self.a['clauses'][0])[0])
    def test_hortative_claim_form_conflict(self):self.assertFalse(decision('C_D02_06',{},self.a['units'][0],self.a['clauses'][0])[0])
    def test_promise_missing_prior_command(self):self.assertFalse(decision('C_D02_05',{},self.a['units'][0],self.a['clauses'][0])[0])
    def test_question_scope_and_tam(self):
        u=self.a['units'][0];u['features'].update(mood='interrogative',speech_act='question',question_type='wh',wh_scope_cid='C1')
        self.assertTrue(decision('C_D02_02',{'id':'GS_ENDRULE_Q_WH_V'},u,self.a['clauses'][0])[0])
        u['features']['prefinal_tam']='present'
        self.assertFalse(decision('C_D02_02',{'id':'GS_ENDRULE_Q_WH_V'},u,self.a['clauses'][0])[0])
        u['features'].update(prefinal_tam='absent',wh_scope_cid='C_OTHER')
        self.assertFalse(decision('C_D02_02',{'id':'GS_ENDRULE_Q_WH_V'},u,self.a['clauses'][0])[0])
    def make_output(self):
        packet={'evidence':[{'evidence_id':'E1','target_uid':'P1','role':'realization_reference'}]}
        g={'input_id':'SMOKE_UNIT','output_text':'민수야, 여기로 온나.','edits':[{'target_uid':'P1','before':'와','after':'온나','evidence_ids':['E1'],'reason':'source reference'}],'unresolved':[]}
        return g,packet,validate_analysis(self.a,self.text,'SMOKE_UNIT',ANALYSIS)
    def test_exact_reconstruction(self):
        g,p,c=self.make_output();self.assertTrue(validate_generation(g,self.text,'SMOKE_UNIT',self.a,p,c,GENERATION)['changed'])
    def test_untracked_change_rejected(self):
        g,p,c=self.make_output();g['output_text']='철수야, 여기로 온나.'
        with self.assertRaises(ValidationError):validate_generation(g,self.text,'SMOKE_UNIT',self.a,p,c,GENERATION)
    def test_constraint_not_permission(self):
        g,p,c=self.make_output();p['evidence'][0]['role']='constraint'
        with self.assertRaises(ValidationError):validate_generation(g,self.text,'SMOKE_UNIT',self.a,p,c,GENERATION)
    def test_fabricated_evidence(self):
        g,p,c=self.make_output();g['edits'][0]['evidence_ids']=['made_up']
        with self.assertRaises(ValidationError):validate_generation(g,self.text,'SMOKE_UNIT',self.a,p,c,GENERATION)
    def test_unchanged_valid_not_change(self):
        g={'input_id':'SMOKE_UNIT','output_text':self.text,'edits':[],'unresolved':['no evidence']};c=validate_analysis(self.a,self.text,'SMOKE_UNIT',ANALYSIS)
        self.assertFalse(validate_generation(g,self.text,'SMOKE_UNIT',self.a,{'evidence':[]},c,GENERATION)['changed'])
    def test_unsupported_claim_preserved(self):self.assertFalse(decision('C_D04_03',{},self.a['units'][0],self.a['clauses'][0])[0])
    def selection_fixture(self):
        def node(id,p):return {'id':id,'properties_json':json.dumps(p)}
        row={'concept_id':'G_END_FINAL','claim':node('C_D02_03',{'claim_text':'오다만 결합','scope_note':'source scope'}),
          'span':node('SPAN_C_D02_03',{'quote_kind':'curated_exact_span','quote':'동사 오다와만 결합','pdf_page':169}),
          'atom':node('GS_ENDRULE_NNA_O',{'runtime_active':False,'original_spec':{'output':{'forms':['-ㄴ나']}}}),
          'document_id':'D02','concept_edge':'E1','span_edge':'E2','document_edge':'E3','atom_edge':'E4'}
        mapping={'candidates':[{'unit_id':'P1','concept_id':'G_END_FINAL','priority':30}]}
        return {'claim_paths':[row,row],'unreviewed_neighborhood':[]},mapping
    def test_selection_deduplicates_paths(self):
        raw,m=self.selection_fixture();packet,_=select_evidence(raw,self.a,m)
        self.assertEqual(len(packet['evidence']),1);self.assertFalse(packet['evidence'][0]['runtime_rule_approved'])
    def test_automatic_excerpt_not_evidence(self):
        raw,m=self.selection_fixture();raw['claim_paths'][0]['span']['properties_json']=json.dumps({'quote_kind':'automatic_context_not_semantic_evidence','quote':'text','pdf_page':1})
        packet,_=select_evidence(raw,self.a,m);self.assertEqual(packet['evidence'],[])
    def test_uncertainty_blocks_realization(self):
        raw,m=self.selection_fixture();self.a['uncertainties']=[{'target_id':'P1','field':'mood','note':'ambiguous'}]
        packet,_=select_evidence(raw,self.a,m);self.assertEqual(packet['evidence'],[])
    def test_budget_omission_recorded(self):
        raw,m=self.selection_fixture();packet,_=select_evidence(raw,self.a,m,max_items=0)
        self.assertEqual(packet['evidence'],[]);self.assertEqual(len(packet['omitted_due_to_budget']),1)
    def test_http_failure_redacts_secret(self):
        client=Qwen.__new__(Qwen);client.model='test';client.url='http://example.invalid';client.key='TEST_SECRET';client.timeout=1
        error=urllib.error.HTTPError(client.url,401,'Unauthorized',{},io.BytesIO(b'TEST_SECRET'))
        with tempfile.TemporaryDirectory() as t:
            with patch('urllib.request.urlopen',side_effect=error):
                with self.assertRaises(CallError):client.call('analysis','prompt',{},ANALYSIS,Path(t),10,1)
            written=''.join(p.read_text(encoding='utf-8') for p in Path(t).glob('*.json'))
            self.assertNotIn('TEST_SECRET',written);self.assertIn('401',written)
    def test_overlap_rejected(self):
        g,p,c=self.make_output();self.a['units'].append({**copy.deepcopy(self.a['units'][0]),'uid':'P2'})
        c['spans']['P2']=c['spans']['P1'];p['evidence'].append({'evidence_id':'E2','target_uid':'P2','role':'realization_reference'})
        g['edits'].append({'target_uid':'P2','before':'와','after':'온나','evidence_ids':['E2'],'reason':'test'})
        with self.assertRaises(ValidationError):validate_generation(g,self.text,'SMOKE_UNIT',self.a,p,c,GENERATION)
if __name__=='__main__':unittest.main(verbosity=2)
