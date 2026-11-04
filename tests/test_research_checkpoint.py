import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'tools/research_checkpoint.py'
spec=importlib.util.spec_from_file_location('checkpoint',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class FakeFile:
    def __init__(self,text): self.text=text
    def read_text(self,**kwargs): return self.text
    def relative_to(self,root): return Path('sample.py')

class CheckpointTests(unittest.TestCase):
    def test_private_paths_denied(self):
        for p in ['test.py','x/private/graph.json','data/derived_private/a.jsonl','.claude/settings.local.json','work/draft.json','local/x.py','a.pdf','credentials.json']:
            self.assertTrue(m.denied(p),p)
    def test_code_and_summary_allowed(self):
        for p in ['src/kg_runtime/run.py','experiments/runs/run/config.json','knowledge/authored/r7/README.md']:
            self.assertFalse(m.denied(p),p)
    def test_literal_secret_location_only(self):
        value='sensitive_value_0123456789'
        result=m.scan(FakeFile('GATEWAY_TOKEN = "'+value+'"'))
        self.assertEqual(result,[{'file':'sample.py','line':1,'detector':'literal_credential'}])
        self.assertNotIn(value,str(result))
    def test_placeholder_not_secret(self):
        self.assertEqual(m.scan(FakeFile('api_key = "your_api_key_here"')),[])
    def test_provider_key(self):
        self.assertEqual(m.scan(FakeFile('token="ghp_'+'a'*30+'"'))[0]['detector'],'provider_key')
    def test_environment_lookup(self):
        self.assertEqual(m.scan(FakeFile('api_key = os.environ["TOKEN"]')),[])

if __name__=='__main__': unittest.main()
