import copy,importlib.util,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_pipeline.io import read,save,dumps,sha
from kg_runtime.card_content import CardContent
from kg_runtime.cards import VERSION
from kg_runtime import card_pipeline as cp
from kg_runtime.card_experiment import shared_analysis
spec=importlib.util.spec_from_file_location('card_builder',ROOT/'tools/build_generation_cards.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.version='kg_cards_test_v3'
        def card(i):return {'id':i,'module':'M','kind':'realization_inventory','title':i,'when':{'target_profile':'required'},'forms':['-요','-예'],'avoid':[]}
        self.base={'version':VERSION,'source_dataset':'KG','cards':[card('A'),card('B')]}
        self.path=self.root/'knowledge/authored'/self.version;self.basepath=self.root/'knowledge/authored'/VERSION/'cards.json'
        save(self.basepath,self.base);self.data=copy.deepcopy(self.base);self.data['version']=self.version
        self.data['cards'][0]['when']={'input_politeness':'polite'}
        self.data['cards'][0]['rewrite']={'source':'공손한 종결','target_form_index':1,'operation':'앞의 활용을 유지','preserve':[],'exclude':[]}
        self.write_version()
    def tearDown(self):self.tmp.cleanup()
    def write_version(self):
        save(self.path/'cards.json',self.data);save(self.path/'provenance.json',{})
        save(self.path/'manifest.json',{'parent':VERSION,'parent_cards_sha256':sha(self.basepath.read_bytes()),
            'cards_content_sha256':sha(dumps(self.data).encode()),'provenance_content_sha256':sha(dumps({}).encode())})
    def test_metadata_separation_retains_linguistic_conditions(self):
        original={'target_profile':'required','source_system':'D02','nested':{'target_register.level_id':['haeye'],
            'variant_profile':'allows_ni_deletion','addressee_profile':'close','coda_condition':'required'}}
        cleaned,moved=builder.separate(original)
        self.assertNotIn('target_profile',cleaned);self.assertEqual(cleaned['nested'],original['nested'])
        self.assertEqual(moved['when.target_profile'],'required')
    def test_same_selection_order_and_form_indices(self):
        content=CardContent(self.root,self.version);selected=list(reversed(self.base['cards']));before=copy.deepcopy(selected)
        cards,audit=content.project_cards(selected)
        self.assertEqual([c['id'] for c in cards],['B','A']);self.assertEqual(selected,before)
        self.assertEqual(cards[1]['forms'],['-요','-예']);self.assertTrue(audit['same_ids_and_order'])
    def test_changed_forms_rejected(self):
        self.data['cards'][0]['forms'].reverse();self.write_version()
        with self.assertRaisesRegex(ValueError,'structure_changed'):CardContent(self.root,self.version)
    def test_missing_or_duplicate_id_rejected(self):
        self.data['cards'][1]['id']='A';self.write_version()
        with self.assertRaisesRegex(ValueError,'ids_mismatch'):CardContent(self.root,self.version)
    def test_content_tampering_rejected(self):
        self.data['cards'][0]['when']={'new':'unsealed'};save(self.path/'cards.json',self.data)
        with self.assertRaisesRegex(ValueError,'hash_mismatch'):CardContent(self.root,self.version)
    def test_path_escape_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid_card_content'):CardContent(self.root,'../elsewhere')
    def test_old_request_cannot_be_used_with_new_cards(self):
        m={'text':'가요','words':[{'uid':'W1','start':0,'end':2,'surface':'가요','morphs':[['가','VV'],['어요','EF']]}]}
        a={'units':[]};old=cp.context(m,self.base['cards'],a,'T')
        cards,_=CardContent(self.root,self.version).project_cards(self.base['cards'])
        new=cp.context(m,cards,a,'T');self.assertNotEqual(old['request_id'],new['request_id'])
        with self.assertRaisesRegex(ValueError,'stale_request'):cp.bind_plan({'request_id':old['request_id'],'edits':[],'reason':'test'},m,cards,analysis=a,input_id='T')
    def test_shared_pipeline_projects_only_after_retrieval(self):
        a={'units':[{'word_id':'W1','functions':['declarative'],'politeness':'polite','tense':'present','subject_honorific':False,
            'concept_ids':['C'],'reason':'test','discourse_function':'unknown','discourse_evidence':''}]}
        class Client:
            def call(self,*args):return copy.deepcopy(a)
        outer=self
        class Graph:
            data={'concepts':[{'id':'C'}]};concepts={'C':{}}
            def retrieve(self,morph,analysis):return {'cards':copy.deepcopy(outer.base['cards']),'ranking':[],
                'retrieved_ids':['A','B'],'concept_ids':['C'],'paths':[]}
        morph={'text':'가요','words':[{'uid':'W1','start':0,'end':2,'surface':'가요','sentence':0,'morphs':[['가','VV'],['어요','EF']]}]}
        folder=self.root/'shared';result=shared_analysis({'id':'T','text':'가요'},morph,Client(),Graph(),folder,CardContent(self.root,self.version))
        self.assertTrue(result['ok'],result)
        raw=read(folder/'retrieval_raw.json');packet=read(folder/'reference_packet.json')
        self.assertEqual(raw['cards'],self.base['cards']);self.assertIn('rewrite',packet['cards'][0])
        self.assertEqual(packet['grammar']['units'],a['units'])
        self.assertIn('source_alignment',packet['grammar'])
        self.assertEqual(packet['contract_context'],cp.context(morph,packet['cards'],packet['grammar'],'T'))
        self.assertEqual([c['id'] for c in raw['cards']],[c['id'] for c in packet['cards']])

if __name__=='__main__':unittest.main()
