import datetime as dt
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_pipeline.integrated import compile_overlay
from kg_pipeline.io import save,read

spec=importlib.util.spec_from_file_location('integrated_runner',ROOT/'tools/run_integrated_grammar.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class FakeQwen:
    fail=False
    interrupt=False
    def __init__(self,*a,**kw):self.models={'data':[{'id':'fake'}]}
    def call(self,stage,prompt,user,schema,out,max_tokens,seed):
        save(out/'request.json',{'messages':[{'content':prompt},{'content':json.dumps(user,ensure_ascii=False)}]})
        save(out/'meta.json',{'stage':stage,'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
        if self.interrupt:raise KeyboardInterrupt()
        if self.fail:raise RuntimeError('mock_failure')
        if stage=='integrated_analysis':
            rows=[]
            for u in user['units']:
                v=next(v for v in schema['properties']['units']['items']['anyOf'] if u['id'] in v['properties']['unit_id']['enum'])
                rows.append({'unit_id':u['id'],'features':{k:None for k in v['properties']['features']['properties']},'clause_key':'C1','related_unit_ids':[],'relations':[]})
            result={'units':rows}
        else:result={'output_text':'  틀린 현재 문장.  ','used_rule_ids':[],'status':'generated'}
        save(out/'parsed.json',result);save(out/'response.json',{'choices':[{'message':{'content':json.dumps(result,ensure_ascii=False)}}]})
        return result


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for rel in ['tools/run_integrated_grammar.py','src/kg_pipeline/integrated.py','src/kg_pipeline/io.py','src/kg_pipeline/validation.py','src/kg_runtime/morphology.py']:
            p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
        save(self.root/'graph.json',compile_overlay({'rules':[]}))
        self.args=SimpleNamespace(graph=str(self.root/'graph.json'),inputs=str(self.root/'inputs.jsonl'),phase='smoke',
            deadline=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5)).isoformat(),max_calls=10,model='fake',seed=1,char_budget=24000)
    def tearDown(self):self.tmp.cleanup()
    def run_fixture(self,rows,fail=False):
        (self.root/'inputs.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows),encoding='utf8')
        with patch.object(runner,'ROOT',self.root),patch.object(runner,'Qwen',FakeQwen),patch.object(runner,'register_run'),patch.object(FakeQwen,'fail',fail):
            return runner.execute(self.args)
    def test_full_wire_preserves_even_bad_raw_output(self):
        out,m=self.run_fixture([{'id':'T1','text':'어제 설명했어.'}])
        result=read(out/'private/results.json')[0]
        self.assertEqual(result['output_text'],'  틀린 현재 문장.  ')
        self.assertEqual(result['output_text'],read(out/'private/records/T1/generation/parsed.json')['output_text'])
        self.assertEqual(m['api_attempts'],2);self.assertEqual(m['changed_records'],1)
        self.assertTrue(read(out/'postflight.json')['code_unchanged'])

    def test_analysis_prompt_override_is_frozen_and_sent(self):
        prompt=self.root/'custom_analysis.txt';prompt.write_text('분석 정의 보완 시험',encoding='utf8')
        self.args.analysis_prompt=str(prompt)
        out,m=self.run_fixture([{'id':'T1','text':'어제 설명했어.'}])
        self.assertEqual((out/'analysis_prompt.txt').read_text(encoding='utf8'),'분석 정의 보완 시험')
        wire=read(out/'private/records/T1/analysis/request.json')
        self.assertEqual(wire['messages'][0]['content'],'분석 정의 보완 시험')
        self.assertEqual((out/'generation_prompt.txt').read_text(encoding='utf8'),runner.GENERATION_PROMPT)
        self.assertEqual(m['api_attempts'],2)
    def test_three_failures_stop_and_preserve_unattempted(self):
        out,m=self.run_fixture([{'id':f'T{i}','text':'책을 읽어.'} for i in range(5)],fail=True)
        self.assertEqual(m['api_attempts'],3);self.assertEqual(m['unattempted_inputs'],2)
        self.assertEqual(m['generation_calls'],0);self.assertEqual(m['stop_reason'],'consecutive_failures')
        self.assertTrue(all(r['output_text'] is None for r in read(out/'private/results.json')))

    def test_interrupt_retains_attempt_and_not_completed(self):
        with patch.object(FakeQwen,'interrupt',True):
            out,m=self.run_fixture([{'id':'I1','text':'책을 읽어.'},{'id':'I2','text':'옷을 입어.'}])
        self.assertEqual(m['api_attempts'],1);self.assertEqual(m['records'],1);self.assertEqual(m['unattempted_inputs'],1)
        self.assertEqual(m['stop_reason'],'interrupted');self.assertTrue((out/'interruption.json').exists())
        self.assertFalse((out/'failure.json').exists())

if __name__=='__main__':unittest.main()
