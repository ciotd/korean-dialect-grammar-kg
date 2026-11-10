import unittest
import sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'local/python'),str(PROJECT/'src')]
from kg_runtime import card_pipeline as cp
from kg_runtime.cards import grammar_only,select_cards

class CardsTests(unittest.TestCase):
    def setUp(self):
        self.m={'text':'문 닫아 줘.','words':[{'uid':'W1','start':0,'end':1,'surface':'문','morphs':[['문','NNG']]},
            {'uid':'W2','start':2,'end':4,'surface':'닫아','morphs':[['닫','VV'],['어','EC']]},
            {'uid':'W3','start':5,'end':6,'surface':'줘','morphs':[['주','VX'],['어','EF']]}]}
        self.cards=[{'id':'EXISTING_CARD','module':'M05','kind':'design_rule','title':'명령','when':{'function':'imperative'},'forms':['-이소'],'avoid':[]}]
        self.v={'request_id':cp.context(self.m,self.cards)['request_id'],'edits':[{'edit_id':'E1','word_ids':['W3'],'bindings':[{'card_id':'EXISTING_CARD','form_index':0,'component':'ending','source_word_id':'W3','morph_index':1}],'depends_on':[],'action':'apply','instruction':'공손한 요청 어미로 활용','after':'주이소','reason':'요청'}],'reason':'계획'}
    def test_generic_new_id_without_python_operator(self):
        plan=cp.bind_plan(self.v,self.m,self.cards)
        self.assertEqual(cp.assemble(self.m['text'],plan),'문 닫아 주이소.')
    def test_unknown_rule_rejected(self):
        self.v['edits'][0]['bindings'][0]['card_id']='invented'
        with self.assertRaisesRegex(ValueError,'unretrieved'):cp.bind_plan(self.v,self.m,self.cards)
    def test_unknown_anchor_rejected(self):
        self.v['edits'][0]['word_ids']=['W99']
        with self.assertRaisesRegex(ValueError,'anchor'):cp.bind_plan(self.v,self.m,self.cards)
    def test_duplicate_edit_rejected(self):
        self.v['edits']*=2
        with self.assertRaisesRegex(ValueError,'duplicate_edit_id'):cp.bind_plan(self.v,self.m,self.cards)
    def test_worker_cannot_add_edit(self):
        plan=cp.bind_plan(self.v,self.m,self.cards,False)
        with self.assertRaisesRegex(ValueError,'worker_plan_mismatch'):
            cp.realize_plan(plan,{'plan_id':plan['plan_id'],'edits':[{'edit_id':'E99','action':'apply','after':'문','reason':'새 수정'}],'reason':''},self.m,self.cards)
    def test_worker_can_decline_change(self):
        plan=cp.bind_plan(self.v,self.m,self.cards,False)
        result=cp.realize_plan(plan,{'plan_id':plan['plan_id'],'edits':[{'edit_id':'E1','action':'keep','after':'줘','reason':'적용 불명'}],'reason':''},self.m,self.cards)
        self.assertEqual(cp.assemble(self.m['text'],result),self.m['text'])
    def test_spaces_are_not_blanket_rejected(self):
        self.v['edits'][0]['after']='기다려 주이소'
        plan=cp.bind_plan(self.v,self.m,self.cards)
        self.assertNotEqual(plan['status'],'unchanged') # structural allowance, not semantic certification
    def test_conditions_preserved_metadata_removed(self):
        x=grammar_only({'predicate_kind':'verb','source_level':'haiso','target_register':{'level':'polite','profile_id':'required'},'profile':'x'})
        self.assertEqual(x,{'predicate_kind':'verb','source_level':'haiso','target_register':{'level':'polite'}})
    def test_dotted_deployment_metadata_removed(self):
        self.assertEqual(grammar_only({'target_register.mapping_status':'approved','target_register.profile_id':'required','target_register.level_id':['hae']}),{'target_register.level_id':['hae']})
    def test_rank_has_no_legacy_allowlist(self):
        chosen,_=select_cards(self.cards,{'units':[{'functions':['request']}]},self.m)
        self.assertEqual(chosen,self.cards)
    def test_analysis_requires_actual_concept(self):
        a={'units':[{'word_id':'W3','functions':['request'],'politeness':'plain','tense':'present','subject_honorific':False,'concept_ids':['invented'],'reason':''}]}
        with self.assertRaisesRegex(ValueError,'concept'):cp.validate_analysis(a,self.m,{'real'})
    def test_analysis_span_is_program_bound(self):
        a={'units':[{'word_id':'W3','functions':['request'],'politeness':'plain','tense':'present','subject_honorific':False,'concept_ids':['real'],'reason':''}]}
        self.assertEqual(cp.validate_analysis(a,self.m,{'real'})[0]['span'],[5,6])
    def test_max_items_supported_and_enforced(self):
        from kg_pipeline.validation import validate_schema
        s={'type':'array','items':{'type':'string'},'maxItems':1}
        validate_schema(['x'],s)
        with self.assertRaisesRegex(ValueError,'maxItems'):validate_schema(['x','y'],s)

class RatingTests(unittest.TestCase):
    def setUp(self):
        self.tasks=[{'answers':[{'blind_id':'opaque'}]}]
        self.value={'reviewer':'tester','ratings':[{'blind_id':'opaque','naturalness':4,'meaning':'preserved','comment':''}]}
    def test_valid(self):
        from research_management.evaluation import validate_ratings
        self.assertEqual(validate_ratings(self.value,self.tasks)['reviewer'],'tester')
    def test_invalid_id(self):
        from research_management.evaluation import validate_ratings
        self.value['ratings'][0]['blind_id']='invented'
        with self.assertRaisesRegex(ValueError,'blind_id'):validate_ratings(self.value,self.tasks)
    def test_boolean_is_not_score(self):
        from research_management.evaluation import validate_ratings
        self.value['ratings'][0]['naturalness']=True
        with self.assertRaisesRegex(ValueError,'naturalness'):validate_ratings(self.value,self.tasks)
    def test_missing_score_preserved_as_missing(self):
        from research_management.evaluation import validate_ratings
        self.value['ratings'][0]['naturalness']=None
        self.assertIsNone(validate_ratings(self.value,self.tasks)['ratings'][0]['naturalness'])
    def test_http_persistence_and_key_not_exposed(self):
        import json, tempfile, threading, urllib.request, urllib.error
        from pathlib import Path
        from kg_pipeline.io import save,read
        from research_management.evaluation import ROOT
        from research_management.server import make_server
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);save(p/ROOT/'blind_review.json',self.tasks);save(p/ROOT/'blind_key.json',{'secret':'multi'})
            server=make_server(p,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{server.server_port}'
            try:
                with urllib.request.urlopen(url+'/api/info') as r:token=json.load(r)['csrf']
                req=urllib.request.Request(url+'/api/grammar-ratings',data=json.dumps(self.value).encode(),headers={'X-Research-Token':token,'Content-Type':'application/json'})
                with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['saved'],1)
                self.assertEqual(read(p/ROOT/'ratings.json')['ratings'][0]['naturalness'],4)
                self.assertEqual(len(list((p/ROOT/'rating_history').glob('*.json'))),1)
                with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(url+'/reports/grammar-cards/blind_key.json')
                self.assertEqual(ctx.exception.code,404)
                req=urllib.request.Request(url+'/api/grammar-ratings',data=b'{}',headers={'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code,403)
            finally:server.shutdown();thread.join();server.server_close()

if __name__=='__main__':unittest.main()
