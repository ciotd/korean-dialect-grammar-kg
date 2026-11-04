import unittest,sys,json
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
from easy_pilot import render,restore,payloads,SYSTEM,wire_content,Qwen,read,dumps
class PilotTest(unittest.TestCase):
 def test_roundtrip_nested(self):
  for v in [{},[],{'가':[],'b':[None,True,False,2,2.5,{},'줄\n = 값']},{'조건':{'past':'었','x':[1,2]}}]:self.assertEqual(restore(render(v)),v)
 def test_only_knowledge_varies(self):
  p,proof=payloads('원문',[],{'text':'원문','actions':[{'rule_id':'R','forms':['예'],'preserve':{'tense':'past'}}],'unsupported_or_unresolved':[],'instruction':'forced copy forbidden here'})
  self.assertEqual(p['N']['grammar_reference'],'');self.assertNotIn('instruction',p['J']['grammar_reference']);self.assertEqual(restore(p['T']['grammar_reference']),json.loads(p['J']['grammar_reference']))
  for a in ['N','T','J']:self.assertEqual(p[a]['analysis'],[]);self.assertEqual(p[a]['text'],'원문')
 def test_expected_output_rejected(self):
  with self.assertRaises(AssertionError):payloads('x',[],{'actions':[{'expected_surface':'x'}]})
 def test_real_transport_preserves_string_and_dict(self):
  from unittest.mock import patch
  import tempfile,io
  class Response(io.BytesIO):status=200
  c=Qwen.__new__(Qwen);c.url='http://test.invalid';c.key='test';c.timeout=1;c.model='test'
  p,_=payloads('원문',[],{'actions':[{'forms':['예']}],'unsupported_or_unresolved':[]})
  for user in [wire_content(p['T']),wire_content(p['J']),{'legacy':'dict'}]:
   with tempfile.TemporaryDirectory() as tmp:
    response=Response(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}).encode())
    with patch('urllib.request.urlopen',return_value=response):c.call('test','system',user,{},Path(tmp),10,1)
    request=read(Path(tmp)/'request.json');content=request['messages'][1]['content']
    self.assertEqual(content,user if isinstance(user,str) else dumps(user))
    if isinstance(user,str):self.assertIn('\n\n문법 참고 정보:\n',content)
 def test_dataset_frozen_unique(self):
  rows=[json.loads(l) for l in (H/'private/easy30.jsonl').read_text('utf8').splitlines()];self.assertEqual(len(rows),30);self.assertEqual(len({r['text'] for r in rows}),30);self.assertTrue(all(r['role']=='reviewer_authored_development_pilot' for r in rows))
if __name__=='__main__':unittest.main()
