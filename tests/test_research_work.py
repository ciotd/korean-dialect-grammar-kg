import json
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research_management.work import WorkStore
from research_management.server import make_server
from research_management.live import BatchProgress

def proposal(key='P1',version=1):
    return dict(id=key,version=version,title='검토안',before='현재',after='변경',reason='근거',scope='범위',verification='시험')

def decision(key='P1',version=1,revision=0,action='approved'):
    return dict(id=key,version=version,revision=revision,action=action,comment='')

class WorkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.project=Path(self.tmp.name);self.store=WorkStore(self.project)
    def tearDown(self):self.tmp.cleanup()
    def test_versioned_approval_and_explicit_application(self):
        self.store.proposal(proposal());self.store.decide({'items':[decision()]})
        self.assertEqual(self.store.state()['proposals'][0]['state'],'approved')
        self.store.proposal(proposal(version=2))
        with self.assertRaisesRegex(ValueError,'current_version'):self.store.applied(dict(id='P1',version=1,revision=1,artifacts=['a'],verification='pass'))
        self.assertEqual(self.store.state()['proposals'][0]['state'],'pending')
        self.store.decide({'items':[decision(version=2)]})
        self.store.applied(dict(id='P1',version=2,revision=1,artifacts=['a'],verification='pass'))
        with self.assertRaisesRegex(ValueError,'already_applied'):self.store.decide({'items':[decision(version=2,revision=2)]})
        self.assertEqual(len(self.store.state()['events']),5)
    def test_batch_rollback_and_stale_browser(self):
        self.store.proposal(proposal());self.store.proposal(proposal('P2'))
        with self.assertRaisesRegex(ValueError,'stale'):self.store.decide({'items':[decision(),decision('P2',version=9)]})
        self.assertTrue(all(p['state']=='pending' for p in self.store.state()['proposals']))
        self.store.decide({'items':[decision(),decision('P2')]})
        with self.assertRaisesRegex(ValueError,'stale'):self.store.decide({'items':[decision()]})
    def test_change_request_and_chat_need_explanation(self):
        self.store.proposal(proposal())
        with self.assertRaises(ValueError):self.store.decide({'items':[decision(action='changes_requested')]})
        with self.assertRaises(ValueError):self.store.decide({'items':[decision()]},channel='chat')
        self.store.decide({'items':[decision()],'reference':'chat 2026','quote':'구현해줘'},channel='chat')
        self.assertEqual(self.store.state()['events'][0]['body']['channel'],'chat')
    def test_progress_eta_only_comparable_and_fresh(self):
        data=dict(id='T1',title='테스트',actor='tester',stage='반복 작업',status='running',total=10,unit_key='same-test')
        for t,n in [(100,0),(110,1),(125,2),(145,3)]:
            with patch('research_management.work.time.time',return_value=t):self.store.task({**data,'done':n})
        with patch('research_management.work.time.time',return_value=146):
            task=self.store.state()['tasks'][0];self.assertEqual(task['eta']['low_seconds'],70);self.assertEqual(task['eta']['high_seconds'],140)
        with patch('research_management.work.time.time',return_value=250):
            task=self.store.state()['tasks'][0];self.assertTrue(task['stale']);self.assertIsNone(task['eta'])
        with patch('research_management.work.time.time',return_value=251):self.store.task({**data,'stage':'새 작업','done':0})
        self.assertIsNone(self.store.state()['tasks'][0]['eta'])
    def test_unknown_count_and_finished_clock(self):
        with patch('research_management.work.time.time',return_value=100):self.store.task(dict(id='T',title='작업',actor='총괄',stage='구현',status='running'))
        with patch('research_management.work.time.time',return_value=120):self.store.task(dict(id='T',title='작업',actor='총괄',stage='구현',status='completed'))
        self.assertEqual(self.store.state()['tasks'][0]['elapsed_seconds'],20)
    def test_bad_counts_rejected(self):
        with self.assertRaises(ValueError):self.store.task(dict(id='T',title='작업',actor='총괄',stage='구현',status='completed',done=2,total=3))
    def test_existing_review_is_read_only(self):
        root=self.project/'experiments/analyses/full_review_20261029/private';root.mkdir(parents=True)
        p=root/'casebook.json';p.write_text(json.dumps({'cases':[{'id':'DEV002','input':'샀어','reviewers':{},'lead_observations':['근거']}]}),encoding='utf-8');before=p.read_bytes()
        self.assertEqual(self.store.review()['cases'][0]['id'],'DEV002');self.assertEqual(before,p.read_bytes())
    def test_runner_progress_includes_failed_inputs_without_quality_claim(self):
        with BatchProgress(self.project,'test-batch',2) as progress:
            for stage in ('analysis','single','multi'):
                progress.start(stage)
                progress.completed_item(stage,'X1','failed')
                progress.completed_item(stage,'X2','completed')
            progress.start('finalize');progress.completed_item('finalize','batch','saved')
        state=self.store.state()
        self.assertEqual(len(state['tasks']),4)
        self.assertTrue(all(t['done']==t['total'] and t['status']=='completed' for t in state['tasks']))
        self.assertFalse(progress.thread.is_alive())
    def test_runner_exception_marks_unfinished_tasks_failed(self):
        with self.assertRaises(RuntimeError):
            with BatchProgress(self.project,'broken-batch',2) as progress:
                progress.start('analysis');raise RuntimeError('test interruption')
        self.assertTrue(all(t['status']=='failed' for t in self.store.state()['tasks']))

class WorkServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.project=Path(self.tmp.name)
        self.server=make_server(self.project,0);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}';self.store=WorkStore(self.project);self.store.proposal(proposal())
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,payload=None,token=None,origin=None):
        headers={}
        if token:headers['X-Research-Token']=token
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.url+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        with urllib.request.urlopen(req) as response:return response.read()
    def test_ui_and_read_api(self):
        self.assertIn('연구 진행'.encode(),self.request('/work'))
        self.assertEqual(json.loads(self.request('/api/work'))['proposals'][0]['id'],'P1')
        self.assertIn(b'setInterval(refresh,2000)',self.request('/work.js'))
    def test_authenticated_decision_and_origin_guard(self):
        payload={'items':[decision()]};token=json.loads(self.request('/api/info'))['csrf']
        for tok,origin in [(None,None),(token,'http://evil.example')]:
            with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/work/decisions',payload,tok,origin)
            self.assertEqual(e.exception.code,403)
        self.assertEqual(json.loads(self.request('/api/work/decisions',payload,token,self.url))['saved'],1)
        self.assertEqual(self.store.state()['proposals'][0]['state'],'approved')
    def test_invalid_json_shape_rejected(self):
        token=json.loads(self.request('/api/info'))['csrf']
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('/api/work/decisions',[],token)
        self.assertEqual(e.exception.code,400)

if __name__=='__main__':unittest.main()
