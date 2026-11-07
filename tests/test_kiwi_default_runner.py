"""Isolated interruption tests: no model/server/real research files."""
import datetime as dt,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tools')]
import run_kiwi_default as runner
from kg_pipeline.io import save,read,sha

class KiwiRunnerFailureAccounting(unittest.TestCase):
    def test_scope_and_branch_interrupts_preserve_attempts_and_manifest(self):
        for stop_at,records in [(1,2),(2,1),(5,2)]:
            with self.subTest(stop_at=stop_at),tempfile.TemporaryDirectory() as td:
                root=Path(td);graph=root/'graph/graph.json';save(graph,{'nodes':[],'edges':[]});save(graph.parent/'audit.json',{})
                save(graph.parent/'manifest.json',{'graph_sha256':sha(graph.read_bytes()),'audit_sha256':sha((graph.parent/'audit.json').read_bytes())})
                inputs=root/'inputs.jsonl';inputs.write_text('{"id":"I0","text":"가."}\n',encoding='utf8')
                for rel in ['tools/run_kiwi_default.py','tools/run_qwen_multi.py','src/kg_pipeline/kiwi_default.py','src/kg_pipeline/morphology_control.py','src/kg_pipeline/multi_agent.py','src/kg_pipeline/integrated.py','src/kg_pipeline/io.py','src/kg_pipeline/validation.py','src/kg_pipeline/separated_graph.py','src/kg_pipeline/runner.py','src/research_management/core.py','src/research_management/work.py']:
                    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# isolated',encoding='utf8')
                class Fake:
                    timeout=120;models={}
                    def __init__(self,*a,**kw):self.n=0
                    def call(self,stage,prompt,payload,schema,out,tokens,seed):
                        self.n+=1;save(out/'meta.json',{'stage':stage,'usage':{},'seconds':0})
                        if self.n==stop_at:raise KeyboardInterrupt()
                        return {}
                def initial(client,text,kiwi,out,seed):client.call('scope','',{}, {},out/'scope',10,seed);return {'units':[]}
                def downstream(client,reader,text,rd,**kwargs):
                    for name in ['meaning','writer','reviewer']:client.call(name,'',{}, {},rd/name,10,1)
                    save(rd/'writer/parsed.json',{'output_text':text})
                    return {'output_text':text,'status':'generated_requires_human_review'}
                args=SimpleNamespace(execute=True,inputs=str(inputs),graph=str(graph),paired=True,
                    deadline=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5)).isoformat(),
                    max_calls=7,phase='development',model='fake',seed=1,char_budget=18000)
                with patch.object(runner,'ROOT',root),patch.object(runner,'HERE',root/'analysis'),patch.object(runner,'restore'),patch.object(runner,'Qwen',Fake),patch.object(runner,'register_run'),patch.object(runner,'WorkStore'),patch.object(runner,'initial_structure',initial),patch.object(runner,'run_sentence',downstream),patch('kiwipiepy.Kiwi',return_value=object()):
                    out,m=runner.execute(args)
                rr=read(out/'private/results.json')
                self.assertEqual(m['api_attempts'],stop_at);self.assertEqual(m['records'],records)
                self.assertEqual(m['scope_calls']+sum(r['api_attempts'] for r in rr),stop_at)
                self.assertTrue((out/'failure.json').exists());self.assertEqual(m['stop_reason'],'interrupted')
                self.assertTrue(all(sha((out/f).read_bytes())==h for f,h in read(out/'artifact_hashes.json').items()))

if __name__=='__main__':unittest.main()
