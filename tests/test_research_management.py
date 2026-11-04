import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research_management.core import Registry,write,digest,guard_dataset,FROZEN
from research_management.server import make_server

def fixture(project,run_id='run_a',validator='v1',text='새 문장',completed=True):
    root=project/'experiments/runs'/run_id
    inputs=(json.dumps({'id':'S1','text':text},ensure_ascii=False)+'\n').encode()
    (root/'private').mkdir(parents=True);(root/'private/inputs.jsonl').write_bytes(inputs)
    write(root/'config.json',{'phase':'smoke','input_count':1,'input_sha256':digest(inputs),'version':'test','workers':2})
    write(root/'code_hashes.json',{'validation.py':validator,'contracts.py':validator})
    write(root/'analysis.schema.json',{'type':'object'})
    write(root/'generation.schema.json',{'type':'object'})
    write(root/'kg_hashes.json',{'nodes':'kg1'})
    rows=[{'id':'S1','input_text':text,'output_text':text,'status':'unchanged','calls':[],'total_seconds':1}]
    write(root/'private/results.json',rows)
    write(root/'private/records/S1/input.json',{'id':'S1','text':text})
    if completed:
        write(root/'metrics.json',{'records':1,'valid_output_records':1,'changed_records':0,'api_attempts':0,'wall_seconds':1,'reported_usage':{'total_tokens':0},'calls_with_usage':0,'calls_without_usage':0})
        seal(root)
    return root

def seal(root):
    write(root/'artifact_hashes.json',{str(p.relative_to(root)):digest(p.read_bytes()) for p in root.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})

class ManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.project=Path(self.tmp.name);self.registry=Registry(self.project)
    def tearDown(self):self.tmp.cleanup()
    def test_reference_status_requires_matching_manifest_hash(self):
        root=self.project/'data/derived_private/gyeongsang_reference50_20261030_v1'
        root.mkdir(parents=True)
        content=b'{}\n';(root/'references.jsonl').write_bytes(content)
        write(root/'manifest.json',{'count':1,'references_sha256':digest(content)})
        self.registry.status_document()
        doc=self.project/'docs/research/RESEARCH_STATUS.md'
        self.assertIn('사용자 승인 정답 1개 등록',doc.read_text(encoding='utf-8'))
        (root/'references.jsonl').write_bytes(b'changed')
        self.registry.status_document()
        self.assertIn('등록 미확인',doc.read_text(encoding='utf-8'))
    def test_runtime_validation_contract_support(self):
        a=fixture(self.project);b=fixture(self.project,'run_b')
        for f in (a,b):
            write(f/'code_hashes.json',{'kg_runtime/graph.py':'same'})
            write(f/'validation_contract.json',{'plan_validator':'same','schemas':'same'})
            seal(f)
        self.registry.sync();self.assertTrue(self.registry.compare('run_a','run_b')['validation_contract_equal'])
    def test_runtime_plan_stage_is_available(self):
        f=fixture(self.project);write(f/'private/records/S1/transformation_plan.json',{'edits':[]});seal(f)
        self.registry.sync();self.assertEqual(self.registry.trace('run_a','S1','plan')['data'],{'edits':[]})
    def test_idempotent_index_preserves_files(self):
        f=fixture(self.project);before={p:digest(p.read_bytes()) for p in f.rglob('*') if p.is_file()}
        self.registry.sync();self.assertEqual(self.registry.sync()['indexed'][0]['action'],'unchanged')
        self.assertEqual(before,{p:digest(p.read_bytes()) for p in f.rglob('*') if p.is_file()})
    def test_completed_change_is_detected(self):
        f=fixture(self.project);self.registry.sync();write(f/'metrics.json',{'records':9});self.registry.sync()
        self.assertEqual(self.registry.get('run_a')['integrity']['status'],'mismatch')
        self.assertTrue(self.registry.get('run_a')['integrity']['original_completed_run_changed'])
    def test_incomplete_is_visible(self):
        fixture(self.project,completed=False);self.registry.sync();self.assertEqual(self.registry.get('run_a')['state'],'incomplete')
    def test_preflight_failure_is_visible(self):
        f=fixture(self.project,completed=False);write(f/'preflight_failure.json',{'error_type':'ConnectionError'});self.registry.sync()
        self.assertEqual(self.registry.get('run_a')['state'],'preflight_failed')
    def test_fatal_failure_is_not_success_even_with_sealed_metrics(self):
        f=fixture(self.project);write(f/'failure.json',{'stage':'schedule_serialization','error_type':'TypeError'})
        seal(f);before={str(p):digest(p.read_bytes()) for p in f.rglob('*') if p.is_file()}
        self.registry.register('run_a')
        self.assertEqual(self.registry.get('run_a')['state'],'failed')
        self.assertEqual(before,{str(p):digest(p.read_bytes()) for p in f.rglob('*') if p.is_file()})
    def test_corrupt_run_does_not_hide_other_runs(self):
        fixture(self.project);f=fixture(self.project,'run_b');(f/'config.json').write_text('{')
        result=self.registry.sync();self.assertEqual(result['total_runs'],1);self.assertIn('index_error',result['indexed'][1])
    def test_compare_different_inputs_blocks_deltas(self):
        fixture(self.project);fixture(self.project,'run_b',text='다른 문장');self.registry.sync()
        result=self.registry.compare('run_a','run_b');self.assertFalse(result['same_evaluation_inputs'])
        self.assertTrue(all(r['delta'] is None for r in result['metrics']))
    def test_compare_same_inputs_has_descriptive_delta(self):
        fixture(self.project);fixture(self.project,'run_b');self.registry.sync();r=self.registry.compare('run_a','run_b')
        self.assertTrue(r['same_evaluation_inputs']);self.assertEqual(r['metrics'][0]['delta'],0);self.assertFalse(r['causal_claim_allowed'])
    def test_changed_validator_blocks_pass_count(self):
        fixture(self.project);fixture(self.project,'run_b',validator='v2');self.registry.sync();r=self.registry.compare('run_a','run_b')
        self.assertTrue(r['same_evaluation_inputs']);self.assertIsNone(r['metrics'][0]['delta'])
    def test_missing_validator_blocks_pass_count(self):
        f=fixture(self.project);write(f/'code_hashes.json',{});seal(f);fixture(self.project,'run_b');self.registry.sync()
        self.assertIsNone(self.registry.compare('run_a','run_b')['metrics'][0]['delta'])
    def test_no_quality_score_invented(self):
        fixture(self.project);self.registry.sync();r=self.registry.compare('run_a','run_a')
        self.assertFalse(r['quality_comparison']['allowed'])
    def test_verify_checks_unindexed_trace(self):
        f=fixture(self.project);self.registry.sync();(f/'private/records/S1/input.json').write_text('{}')
        self.assertEqual(self.registry.verify('run_a')['status'],'failed')
    def test_path_escape_rejected(self):
        with self.assertRaises(ValueError):self.registry.folder('../test.py')
    def test_artifact_manifest_path_escape_rejected(self):
        f=fixture(self.project);write(f/'artifact_hashes.json',{'../secret':'bad'})
        with self.assertRaises(ValueError):self.registry.verify('run_a')
    def test_trace_is_exact_original(self):
        f=fixture(self.project);self.registry.sync();t=self.registry.trace('run_a','S1','input')
        self.assertEqual(t['sha256'],digest((f/'private/records/S1/input.json').read_bytes()))
    def test_trace_unreached_stage(self):
        fixture(self.project);self.registry.sync();self.assertFalse(self.registry.trace('run_a','S1','generation')['available'])
    def test_arbitrary_trace_file_rejected(self):
        fixture(self.project);self.registry.sync()
        with self.assertRaises(ValueError):self.registry.trace('run_a','S1','../../test.py')
    def test_review_bundle_is_separate(self):
        f=fixture(self.project);self.registry.sync();p=self.registry.review_bundle('run_a')
        self.assertTrue(p.is_relative_to(self.registry.root));self.assertFalse(p.is_relative_to(f))
    def test_source_directory_missing_reported(self):
        f=fixture(self.project);self.registry.sync();f.rename(self.project/'moved')
        self.assertEqual(self.registry.sync()['missing_run_directories'],['run_a'])
        self.assertFalse(self.registry.compare('run_a','run_a')['same_evaluation_inputs'])
    def test_automatic_comparison_selects_prior_same_inputs(self):
        fixture(self.project);fixture(self.project,'run_b',text='다른 문장');fixture(self.project,'run_c');self.registry.sync()
        summary=json.loads((self.registry.root/'summaries/run_c.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['comparison']['left'],'run_a')
    def test_metrics_recalculated_count_mismatch(self):
        f=fixture(self.project);write(f/'metrics.json',{'records':1,'valid_output_records':99,'changed_records':0});seal(f)
        self.registry.sync();self.assertIn('metrics.valid_output_records',self.registry.get('run_a')['integrity']['mismatches'])
    def test_dataset_normalized_overlap_blocks_development(self):
        f=self.project/FROZEN;write_dummy=f.parent.mkdir(parents=True)
        f.write_text(json.dumps({'id':'E1','text':'안녕 친구'},ensure_ascii=False)+'\n',encoding='utf-8')
        inp=self.project/'dev.jsonl';inp.write_text(json.dumps({'id':'D1','text':'안녕  친구'},ensure_ascii=False)+'\n',encoding='utf-8')
        with patch('research_management.core.FROZEN_SHA',digest(f.read_bytes())):
            with self.assertRaisesRegex(ValueError,'development_overlaps'):guard_dataset(self.project,inp,'development')
            self.assertEqual(guard_dataset(self.project,inp,'evaluation')['frozen_overlap_ids'],['D1'])
    def test_changed_frozen_reference_blocks_execution(self):
        f=self.project/FROZEN;f.parent.mkdir(parents=True);f.write_text('{}')
        with self.assertRaisesRegex(ValueError,'missing_or_changed'):guard_dataset(self.project,f,'evaluation')

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.project=Path(self.tmp.name);fixture(self.project)
        self.server=make_server(self.project,0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def get(self,path):
        with urllib.request.urlopen(self.url+path) as response:return response.read()
    def test_runs_and_trace(self):
        self.assertEqual(len(json.loads(self.get('/api/runs'))),1)
        self.assertTrue(json.loads(self.get('/api/trace?run=run_a&input=S1&stage=input'))['available'])
    def test_secret_file_not_served(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.get('/test.py')
        self.assertEqual(e.exception.code,404)
    def test_new_report_allows_review_sheet_but_not_blinding_key(self):
        root=self.project/'experiments/analyses/search_execution_20261025/private'
        write(root/'blind_review.json',[{'id':'S1','output':'sample'}])
        write(root/'blind_review_key.json',{'A':'single'})
        self.assertEqual(json.loads(self.get('/reports/search-execution/blind_review.json'))[0]['id'],'S1')
        with self.assertRaises(urllib.error.HTTPError) as e:self.get('/reports/search-execution/blind_review_key.json')
        self.assertEqual(e.exception.code,404)
    def test_rerun_report_serves_only_html_and_css(self):
        root=self.project/'experiments/analyses/qwen_rerun_20261030/private'
        root.mkdir(parents=True)
        (root/'report.html').write_text('<h1>Report</h1>',encoding='utf-8')
        (root/'report.css').write_text('body{color:black}',encoding='utf-8')
        (root/'cases.json').write_text('[]',encoding='utf-8')
        self.assertIn(b'Report',self.get('/reports/qwen-rerun-20261030/report.html'))
        self.assertIn(b'color:black',self.get('/reports/qwen-rerun-20261030/report.css'))
        for name in ('cases.json','../cases.json','%2e%2e/cases.json'):
            with self.assertRaises(urllib.error.HTTPError) as e:self.get('/reports/qwen-rerun-20261030/'+name)
            self.assertEqual(e.exception.code,404)
    def test_claude_comparison_report_serves_only_html_and_css(self):
        root=self.project/'experiments/analyses/claude_comparison_20261030/private'
        root.mkdir(parents=True)
        (root/'report.html').write_text('<h1>Report</h1>',encoding='utf-8')
        (root/'report.css').write_text('body{color:black}',encoding='utf-8')
        (root/'cases.json').write_text('[]',encoding='utf-8')
        self.assertIn(b'Report',self.get('/reports/claude-comparison-20261030/report.html'))
        self.assertIn(b'color:black',self.get('/reports/claude-comparison-20261030/report.css'))
        for name in ('cases.json','../cases.json','%2e%2e/cases.json'):
            with self.assertRaises(urllib.error.HTTPError) as e:self.get('/reports/claude-comparison-20261030/'+name)
            self.assertEqual(e.exception.code,404)
    def test_card_delivery_report_serves_only_html_and_css(self):
        root=self.project/'experiments/analyses/card_delivery_20261030/private'
        root.mkdir(parents=True)
        (root/'report.html').write_text('<h1>Report</h1>',encoding='utf-8')
        (root/'report.css').write_text('body{color:black}',encoding='utf-8')
        (root/'cases.json').write_text('[]',encoding='utf-8')
        self.assertIn(b'Report',self.get('/reports/card-delivery-20261030/report.html'))
        self.assertIn(b'color:black',self.get('/reports/card-delivery-20261030/report.css'))
        for name in ('cases.json','../cases.json','%2e%2e/cases.json'):
            with self.assertRaises(urllib.error.HTTPError) as e:self.get('/reports/card-delivery-20261030/'+name)
            self.assertEqual(e.exception.code,404)
    def test_card_revision_report_serves_only_html_and_css(self):
        root=self.project/'experiments/analyses/card_revision_20261030/private'
        root.mkdir(parents=True)
        (root/'report.html').write_text('<h1>Report</h1>',encoding='utf-8')
        (root/'report.css').write_text('body{color:black}',encoding='utf-8')
        (root/'cases.json').write_text('[]',encoding='utf-8')
        self.assertIn(b'Report',self.get('/reports/card-revision-20261030/report.html'))
        self.assertIn(b'color:black',self.get('/reports/card-revision-20261030/report.css'))
        for name in ('cases.json','../cases.json','%2e%2e/cases.json'):
            with self.assertRaises(urllib.error.HTTPError) as e:self.get('/reports/card-revision-20261030/'+name)
            self.assertEqual(e.exception.code,404)
    def test_rebinding_host_rejected(self):
        req=urllib.request.Request(self.url+'/api/runs',headers={'Host':'evil.example'})
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
    def test_refresh_without_token_rejected(self):
        req=urllib.request.Request(self.url+'/api/sync',data=b'',method='POST')
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
    def test_refresh_valid_token(self):
        token=json.loads(self.get('/api/info'))['csrf']
        req=urllib.request.Request(self.url+'/api/sync',data=b'',headers={'X-Research-Token':token},method='POST')
        with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['total_runs'],1)
    def test_cross_origin_post_rejected(self):
        token=json.loads(self.get('/api/info'))['csrf']
        req=urllib.request.Request(self.url+'/api/sync',data=b'',headers={'X-Research-Token':token,'Origin':'https://evil.example'},method='POST')
        with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)

class RunnerIntegrationTests(unittest.TestCase):
    def test_completed_run_automatically_registered_without_model_calls(self):
        from kg_pipeline import runner
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp);f=project/FROZEN;f.parent.mkdir(parents=True);f.write_text('{"id":"X1","text":"새 문장"}\n',encoding='utf-8')
            kg=project/'knowledge/authored'/runner.DATASET
            for name in ('graph/nodes.jsonl','graph/edges.jsonl','schema/schema.json'):
                path=kg/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}',encoding='utf-8')
            client=type('FakeQwen',(),{'model':'fixture_only','models':{'data':[]}})()
            result={'id':'X1','input_text':'새 문장','output_text':'새 문장','status':'unchanged','calls':[],'total_seconds':0.1}
            with patch('research_management.core.FROZEN_SHA',digest(f.read_bytes())),patch.object(runner,'Qwen',return_value=client),patch.object(runner,'Neo4j'),patch.object(runner,'load_catalog',return_value={}),patch.object(runner,'execute_record',return_value=result),patch('kg_pipeline.report.render_report'):
                runner.main(['--project',str(project),'--inputs',str(f),'--credentials','unused','--qwen-config','unused','--phase','evaluation'])
            runs=Registry(project).runs();self.assertEqual(len(runs),1);self.assertEqual(runs[0]['state'],'completed');self.assertEqual(runs[0]['metrics']['api_attempts'],0)
            self.assertEqual(runs[0]['version_manifest']['management_version'],'1.0.0')

if __name__=='__main__':unittest.main(verbosity=2)
