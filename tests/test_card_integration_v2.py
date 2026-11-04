"""Offline module integration using an explicit fake client, never Qwen."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime import card_pipeline as cp
from kg_runtime.card_experiment import generate
from kg_pipeline.io import save,read
from kg_pipeline.runner import metrics

class FakeClient:
    def __init__(self,empty=False,fail=False):self.empty=empty;self.fail=fail;self.stages=[]
    def call(self,stage,prompt,payload,schema,out,*rest):
        self.stages.append(stage)
        if self.fail:raise ValueError('injected_model_failure')
        if stage=='agent':
            v={'request_id':payload['contract_context']['request_id'],'reason':'stub',
              'edits':[] if self.empty else [{'edit_id':'E1','word_ids':['W1'],'bindings':[{'card_id':'TEST_CARD','form_index':0,'component':'ending','source_word_id':'W1','morph_index':2}],
                'depends_on':[],'action':'apply','instruction':'테스트 종결형','after':'샀다' if prompt==cp.SINGLE else '', 'reason':'stub'}]}
        else:v={'plan_id':payload['plan']['plan_id'],'edits':[{'edit_id':'E1','action':'apply','after':'샀다','reason':'stub'}],'reason':'stub'}
        save(out/'parsed.json',v);return v

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.shared=self.root/'shared';self.record={'id':'TEST01','text':'샀어.'}
        self.m={'text':'샀어.','words':[{'uid':'W1','surface':'샀어','start':0,'end':2,'morphs':[['사','VV'],['었','EP'],['어','EF']]}]}
        self.cards=[{'id':'TEST_CARD','kind':'design_rule','forms':['-다'],'when':{}}]
        self.a={'units':[{'word_id':'W1','functions':['declarative']}]}
        save(self.shared/'shared.json',{'ok':True,'seconds':0.1,'stage_seconds':{'analysis':0.05,'retrieval':0.05}})
        save(self.shared/'morphology.json',self.m)
        save(self.shared/'reference_packet.json',{'cards':self.cards,'grammar':self.a,'contract_context':cp.context(self.m,self.cards,self.a,'TEST01')})
        save(self.shared/'retrieval_raw.json',{'retrieved_ids':['TEST_CARD']})
    def tearDown(self):self.tmp.cleanup()
    def run_arm(self,arm,client):return generate(self.record,arm,client,self.shared,self.root/arm)
    def test_single_and_multi_same_splice_and_counts(self):
        for arm,stages in [('single',['agent']),('multi',['agent','generation'])]:
            c=FakeClient();r=self.run_arm(arm,c)
            self.assertEqual(r['output_text'],'샀다.');self.assertEqual(r['edit_count'],1);self.assertEqual(c.stages,stages)
            self.assertEqual(r['applied_rules'],['TEST_CARD'])
    def test_noop_multi_skips_worker(self):
        c=FakeClient(empty=True);r=self.run_arm('multi',c)
        self.assertEqual(c.stages,['agent']);self.assertEqual(r['status'],'unchanged');self.assertEqual(r['edit_count'],0)
    def test_call_failure_is_not_unchanged(self):
        r=self.run_arm('single',FakeClient(fail=True));self.assertEqual(r['status'],'planning_failed');self.assertIsNone(r['output_text'])
    def test_metrics_distinguish_partial_and_held(self):
        base={'calls':[],'total_seconds':1}
        m=metrics([dict(base,status='partial'),dict(base,status='needs_review'),dict(base,status='planning_failed')],3)
        self.assertEqual(m['valid_output_records'],2);self.assertEqual(m['changed_records'],1);self.assertEqual(m['held_records'],2)
    def test_analysis_failure_skips_all_generation(self):
        save(self.shared/'shared.json',{'ok':False,'failed_stage':'analysis','error':'bad_parse','seconds':0.1,'stage_seconds':{}})
        c=FakeClient();r=self.run_arm('multi',c);self.assertEqual(c.stages,[]);self.assertEqual(r['status'],'analysis_failed')
    def test_request_specific_contract_checked_locally(self):
        for invalid_stage in ('agent','generation'):
            for fault in ('id','length'):
                class InvalidClient(FakeClient):
                    def call(client,stage,prompt,payload,schema,out,*rest):
                        v=super().call(stage,prompt,payload,schema,out,*rest)
                        if stage==invalid_stage:
                            if fault=='length':v['reason']='x'*161
                            else:v['request_id' if stage=='agent' else 'plan_id']='wrong'
                        return v
                r=generate(self.record,'multi',InvalidClient(),self.shared,self.root/(invalid_stage+fault))
                self.assertIsNone(r['output_text']);self.assertEqual(r['status'],'planning_failed' if invalid_stage=='agent' else 'generation_failed')
                self.assertIn('maxLength' if fault=='length' else 'enum',r['error'])

if __name__=='__main__':unittest.main()
