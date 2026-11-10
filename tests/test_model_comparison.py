import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kg_pipeline.model_comparison import freeze, preflight, ProfiledClient, summarize, execute, comparison_protocol, main
from research_management.core import Registry
from kg_pipeline.io import Qwen, save, dumps

PROFILE={'name':'example','model':'example-model','base_url_env':'TEST_ENDPOINT','api_key_env':'TEST_TOKEN',
         'temperature':0,'top_p':1,'max_tokens':512,'seed':1,'timeout_seconds':3,
         'chat_template_kwargs':None,'max_failures':2,'repeats':1}
SCHEMA={'type':'object','properties':{'output_text':{'type':'string'},'status':{'type':'string'}},
        'required':['output_text','status'],'additionalProperties':False}


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.source=self.root/'source'; self.bundle=self.root/'bundle'
        save(self.source/'config.json',{'arms':['N','T','J'],'model_id':'analysis-model'})
        save(self.source/'private/graph.json',{'version':'test'})
        self.rows=[{'id':'X1','text':'테스트 문장.'},{'id':'X2','text':'다른 문장.'}]
        (self.source/'private/inputs.jsonl').write_text(''.join(dumps(r)+'\n' for r in self.rows),encoding='utf8')
        for row in self.rows:
            p=self.source/'private/records'/row['id']
            save(p/'analysis/parsed.json',{'features':{}});save(p/'traces.json',{})
            save(p/'packet.json',{'text':row['text'],'actions':[]})
            request={'messages':[{'role':'system','content':'test'}, {'role':'user','content':dumps({'text':row['text'],'analysis':[]})+'\n\n문법 참고 정보:\n{}'}],
                     'response_format':{'json_schema':{'name':'generation','schema':SCHEMA}}}
            save(p/'J/generation_call/request.json',request)

    def tearDown(self): self.tmp.cleanup()

    def test_freeze_all_empty_action_inputs_offline(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
            self.assertEqual(freeze(self.source,'J',self.bundle)['inputs'],2)
            b,c=preflight(self.bundle,PROFILE)
        self.assertEqual(c['planned_generation_calls'],2)
        self.assertTrue(all(x['supported_targets']==0 for x in b['items']))

    def test_missing_request_fails_no_partial_bundle(self):
        (self.source/'private/records/X2/J/generation_call/request.json').unlink()
        with self.assertRaises(FileNotFoundError): freeze(self.source,'J',self.bundle)
        self.assertFalse(self.bundle.exists())

    def test_input_mismatch(self):
        p=self.source/'private/records/X1/J/generation_call/request.json'
        q=json.loads(p.read_text());q['messages'][1]['content']=q['messages'][1]['content'].replace('테스트','잘못된');save(p,q)
        with self.assertRaisesRegex(ValueError,'mismatch'): freeze(self.source,'J',self.bundle)

    def test_tampering(self):
        freeze(self.source,'J',self.bundle)
        save(self.bundle/'evidence/private/graph.json',{'version':'changed'})
        with self.assertRaisesRegex(ValueError,'hash mismatch'):preflight(self.bundle,PROFILE)

    def test_no_overwrite(self):
        freeze(self.source,'J',self.bundle)
        with self.assertRaises(ValueError):freeze(self.source,'J',self.bundle)

    def test_bad_span_blocked(self):
        p=self.source/'private/records/X1/packet.json'
        save(p,{'text':self.rows[0]['text'],'actions':[{'target_id':'W1','span':[0,2],'target':'틀린 위치'}]})
        with self.assertRaisesRegex(ValueError,'span mismatch'):freeze(self.source,'J',self.bundle)

    def test_new_model_options_no_qwen_default(self):
        with patch.dict(os.environ,{'TEST_ENDPOINT':'http://example.invalid/v1','TEST_TOKEN':'dummy'}):
            c=ProfiledClient(PROFILE)
        req=c.build_request('generation','system','user',SCHEMA,512,None)
        self.assertNotIn('chat_template_kwargs',req);self.assertNotIn('seed',req)
        self.assertEqual(req['model'],'example-model')

    def test_legacy_request_unchanged(self):
        c=Qwen.__new__(Qwen);c.model='legacy'
        q=c.build_request('generation','s',{'text':'x'},SCHEMA,22,7)
        self.assertEqual(q['chat_template_kwargs'],{'enable_thinking':False})
        self.assertEqual(q['messages'][1]['content'],dumps({'text':'x'}))

    def test_missing_usage_not_zero(self):
        m=summarize([{'status':'failed','usage':None}],2)
        self.assertIsNone(m['usage']['total_tokens']['observed_sum'])
        self.assertEqual(m['usage']['total_tokens']['missing_calls'],1)

    def test_expired_deadline_never_accesses_server(self):
        freeze(self.source,'J',self.bundle)
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')):
            with self.assertRaisesRegex(ValueError,'deadline'):execute(self.bundle,PROFILE,'2020-01-01T00:00:00+09:00',2,comparison_protocol(self.bundle,[PROFILE]))

    def test_transport_logs_failure_and_no_retry(self):
        with patch.dict(os.environ,{'TEST_ENDPOINT':'http://example.invalid/v1','TEST_TOKEN':'dummy'}):c=ProfiledClient(PROFILE)
        with patch('urllib.request.urlopen',side_effect=OSError('offline')) as mock:
            with self.assertRaises(Exception):c.call('generation','s','u',SCHEMA,self.root/'call',20,1)
        self.assertEqual(mock.call_count,1)
        self.assertEqual(json.loads((self.root/'call/meta.json').read_text())['status'],'failed')

    def test_execute_full_flow_mock_no_analysis(self):
        freeze(self.source,'J',self.bundle)
        def call(client,stage,prompt,user,schema,out,max_tokens,seed):
            save(out/'request.json',client.build_request(stage,prompt,user,schema,max_tokens,seed))
            save(out/'meta.json',{'usage':None,'seconds':0.1,'model':client.model})
            return {'output_text':'출력 문장.','status':'needs_review'}
        with patch.dict(os.environ,{'TEST_ENDPOINT':'http://example.invalid/v1','TEST_TOKEN':'dummy'}), \
             patch('kg_pipeline.model_comparison.ROOT',self.root), \
             patch.object(ProfiledClient,'check_model',return_value={'requested_model':'example-model'}), \
             patch.object(ProfiledClient,'call',call):
            # Code snapshot sources live under ROOT, copy only needed source files.
            original=Path(__file__).resolve().parents[1]
            import shutil
            for name in ('io.py','validation.py'):
                dest=self.root/'src/kg_pipeline'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original/'src/kg_pipeline'/name,dest)
            # module __file__ must be relative to the same root for snapshotting.
            dest=self.root/'src/kg_pipeline/model_comparison.py';shutil.copy2(original/'src/kg_pipeline/model_comparison.py',dest)
            with patch('kg_pipeline.model_comparison.__file__',str(dest)):
                result=execute(self.bundle,PROFILE,'2099-01-01T00:00:00+09:00',2,comparison_protocol(self.bundle,[PROFILE]))
        self.assertEqual(result['attempted_generation_calls'],2)
        self.assertEqual(result['statuses'],{'model_review_requested':2})
        indexed=Registry(self.root).get(Path(result['directory']).name)
        self.assertEqual(indexed['integrity']['mismatches'],[])
        self.assertEqual(indexed['state'],'completed')

    def test_protocol_rejects_different_settings_and_qwen_implicit_thinking(self):
        freeze(self.source,'J',self.bundle)
        p={**PROFILE,'name':'second','temperature':0.5}
        with self.assertRaisesRegex(ValueError,'settings differ'):comparison_protocol(self.bundle,[PROFILE,p])
        with self.assertRaisesRegex(ValueError,'disable thinking'):comparison_protocol(self.bundle,[{**PROFILE,'model':'Qwen-test'}])

    def integration(self, profile, values, setup_failure=False, deadline_after_first=False, mismatch_first=False):
        import shutil
        import datetime as dt
        from contextlib import ExitStack
        freeze(self.source,'J',self.bundle)
        original=Path(__file__).resolve().parents[1]
        for name in ('io.py','validation.py','model_comparison.py'):
            dest=self.root/'src/kg_pipeline'/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(original/'src/kg_pipeline'/name,dest)
        count=[0]
        def call(client,stage,prompt,user,schema,out,max_tokens,seed):
            count[0]+=1
            value=values[(count[0]-1)%len(values)]
            if isinstance(value,Exception):raise value
            save(out/'meta.json',{'model':'other-model' if mismatch_first and count[0]==1 else client.model,'usage':None,'seconds':0})
            return value
        class Clock(dt.datetime):
            @classmethod
            def now(cls,tz=None):
                return cls(2100 if deadline_after_first and count[0] else 2026,1,1,tzinfo=dt.timezone.utc)
        with ExitStack() as s:
            s.enter_context(patch.dict(os.environ,{'TEST_ENDPOINT':'http://example.invalid/v1','TEST_TOKEN':'dummy'}))
            s.enter_context(patch('kg_pipeline.model_comparison.ROOT',self.root))
            s.enter_context(patch('kg_pipeline.model_comparison.__file__',str(dest)))
            s.enter_context(patch('kg_pipeline.model_comparison.dt.datetime',Clock))
            s.enter_context(patch.object(ProfiledClient,'check_model',side_effect=OSError('offline') if setup_failure else None,return_value={}))
            s.enter_context(patch.object(ProfiledClient,'call',call))
            result=execute(self.bundle,profile,'2099-01-01T00:00:00+09:00',2*profile['repeats'],comparison_protocol(self.bundle,[profile]))
        record=Registry(self.root).get(Path(result['directory']).name)
        self.assertEqual(record['integrity']['mismatches'],[])
        # Archived evidence alone remains sufficient even without the source run.
        shutil.rmtree(self.source)
        preflight(Path(result['directory'])/'private/frozen_bundle',profile)
        return result,record

    def test_repeats_real_registry_counts_nonempty_not_quality(self):
        r,idx=self.integration({**PROFILE,'repeats':2},[
            {'output_text':'테스트 문장.','status':'ok'}, {'output_text':'보류 문장.','status':'needs_review'},
            {'output_text':'','status':'ok'}, OSError('offline')])
        self.assertEqual(r['records'],4);self.assertEqual(r['valid_output_records'],2)
        self.assertEqual(idx['state'],'completed');self.assertEqual(r['cli_exit_code'],2)

    def test_failure_limit_is_interrupted(self):
        r,idx=self.integration({**PROFILE,'max_failures':1},[OSError('offline')])
        self.assertEqual(idx['state'],'interrupted');self.assertEqual(r['unattempted_records'],1)
        self.assertEqual(r['cli_exit_code'],2)

    def test_deadline_after_first_is_interrupted(self):
        r,idx=self.integration(PROFILE,[{'output_text':'출력.','status':'ok'}],deadline_after_first=True)
        self.assertEqual(idx['state'],'interrupted');self.assertEqual(r['stop_reason'],'deadline')

    def test_setup_failure_is_failed(self):
        r,idx=self.integration(PROFILE,[],setup_failure=True)
        self.assertEqual(idx['state'],'failed');self.assertEqual(r['records'],0)
        self.assertEqual(r['server_check_calls'],1)

    def test_empty_and_model_mismatch_count_as_one_failed_call(self):
        r,idx=self.integration(PROFILE,[{'output_text':'','status':'ok'},{'output_text':'출력.','status':'ok'}],mismatch_first=True)
        self.assertEqual(r['records'],2);self.assertEqual(r['unattempted_records'],0)
        self.assertIsNone(r['stop_reason']);self.assertEqual(r['cli_exit_code'],2)
        rows=json.loads((Path(r['directory'])/'private/results.json').read_text(encoding='utf-8'))
        self.assertEqual(rows[0]['failure_reasons'],['empty_output','model_identity_mismatch'])
        self.assertEqual(rows[1]['failure_reasons'],[])

    def test_cli_failure_exit(self):
        save(self.root/'profile.json',PROFILE);save(self.root/'protocol.json',{})
        args=['tool','run','--execute','--bundle',str(self.bundle),'--profile',str(self.root/'profile.json'),
              '--protocol',str(self.root/'protocol.json'),'--deadline','2099-01-01T00:00:00+09:00','--max-calls','2']
        with patch.object(sys,'argv',args),patch('kg_pipeline.model_comparison.execute',return_value={'cli_exit_code':2}):
            with self.assertRaises(SystemExit) as e:main()
        self.assertEqual(e.exception.code,2)


if __name__=='__main__':unittest.main()
