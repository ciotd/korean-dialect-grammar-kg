"""Offline interruption accounting: no server, credentials, or real output runs."""
import datetime as dt,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tools')]
import run_morphology_control as runner
from kg_pipeline.io import save,read,sha

class InterruptionAccounting(unittest.TestCase):
    def test_first_and_downstream_interrupt_are_attempted_not_unattempted(self):
        for stop_at in (1,2):
            with self.subTest(stop_at=stop_at),tempfile.TemporaryDirectory() as td:
                root=Path(td);source=root/'source';(source/'private').mkdir(parents=True)
                (source/'private/inputs.jsonl').write_text('\n'.join('{"id":"I%d","text":"가."}'%i for i in range(6)),encoding='utf8')
                save(source/'private/records/I0/structure/parsed.json',{'clauses':[{'id':'C1','parent_id':None,'start_word':'W1','end_word':'W1'}]})
                graph=root/'graph/graph.json';save(graph,{'nodes':[],'edges':[]});save(graph.parent/'audit.json',{})
                save(graph.parent/'manifest.json',{'graph_sha256':sha(graph.read_bytes()),'audit_sha256':sha((graph.parent/'audit.json').read_bytes())})
                save(root/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json',{'graph':'graph/graph.json'})
                for rel in ['tools/run_morphology_control.py','tools/run_qwen_multi.py','src/kg_pipeline/morphology_control.py','src/kg_pipeline/multi_agent.py','src/kg_pipeline/integrated.py','src/kg_pipeline/io.py','src/kg_pipeline/validation.py','src/kg_pipeline/separated_graph.py','src/kg_pipeline/runner.py','src/research_management/core.py','src/research_management/work.py']:
                    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# isolated fixture',encoding='utf8')
                class Fake:
                    timeout=120;models={'data':[]}
                    def __init__(self,*a,**kw):self.n=0
                    def call(self,stage,prompt,user,schema,out,max_tokens,seed):
                        self.n+=1;save(out/'meta.json',{'stage':stage,'usage':{},'seconds':0})
                        if self.n==stop_at:raise KeyboardInterrupt()
                        return {'words':[{'word_id':'W1','morphs':[{'form':'가','tag':'VV'},{'form':'어','tag':'EF'}]}],'uncertainties':[]}
                def downstream(client,reader,text,rd,**kw):return client.call('multi_writer','',{}, {},rd/'writer',1,1)
                args=SimpleNamespace(execute=True,source=str(source),model='fake',deadline=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=1)).isoformat())
                with patch.object(runner,'ROOT',root),patch.object(runner,'Qwen',Fake),patch.object(runner,'register_run'),patch.object(runner,'WorkStore'),patch.object(runner,'run_sentence',downstream),patch('kiwipiepy.Kiwi',return_value=object()),patch('kg_pipeline.separated_graph.restore'):
                    runner.execute(args)
                out=next((root/'experiments/runs').iterdir());m=read(out/'metrics.json');rr=read(out/'private/results.json')
                self.assertEqual(len(rr),1);self.assertEqual(rr[0]['status'],'interrupted');self.assertFalse(rr[0]['pipeline_completed'])
                self.assertEqual(m['unattempted_records'],11);self.assertEqual(m['complete_pairs'],0)
                self.assertEqual(m['api_attempts'],stop_at);self.assertEqual(m['by_backend']['qwen']['api_attempts'],stop_at)
                manifest=read(out/'artifact_hashes.json')
                self.assertTrue(all(sha((out/name).read_bytes())==h for name,h in manifest.items()))

if __name__=='__main__':unittest.main()
