"""Test whether explicitly locating the preserved source prefix helps Qwen.
The prefix is copied from standard input; no completed dialect output is computed.
"""
from pathlib import Path
import importlib.util,copy
H=Path(__file__).resolve().parent;R=H.parents[2]
def load(name,file):
 s=importlib.util.spec_from_file_location(name,H/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=load('typed_baseline','typed_probe.py');p=t.p
def convert(packet):
 out=t.convert(packet)
 for a in out['actions']:
  if 'surface_edit' not in a:continue
  suffix=a['surface_edit']['source_suffix'];assert suffix and a['target'].endswith(suffix)
  a['preserved_source_prefix']=a['target'][:-len(suffix)]
  assert a['preserved_source_prefix']+suffix==a['target']
 return out
if __name__=='__main__':
 prompt=p.rt.GENERATION_PROMPT+t.delivery.PROMPT_SUFFIX+'\npreserved_source_prefix가 있으면 원문에서 그대로 떼어낸 보존 부분이다. 이를 한 글자도 바꾸지 말고 replacement_suffix를 이어 쓴다. 이것은 원문 일부이지 방언 완성 답안이 아니다.\n'
 p.EXPERIMENT='fixed_source_prefix';p.INDEX='latest_prefix.json';p.GRAPH_BY_ARM={'control':t.G,'surface':t.G};p.EXTRA_CODES=[Path(__file__),H/'typed_probe.py',H/'typed_delivery.py',H/'realization_probe.py'];p.COMPARISON='same typed instruction, KG, positions and original input; treatment additionally locates the preserved standard-language prefix; no completed dialect word sent';p.CONTROL_TRANSFORM=t.convert;p.SURFACE_PROMPT=prompt;p.rt.GENERATION_PROMPT=prompt;p.lean=convert;p.validate_packet=t.validate;p.main()
