"""r8 meaning fixed: old EF interface vs explicit surface-edit interface."""
from pathlib import Path
import importlib.util,copy
H=Path(__file__).resolve().parent;R=H.parents[2]
def load(name,file):
 s=importlib.util.spec_from_file_location(name,H/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('typed_runner','handoff_probe.py');r8=load('r8_convert','realization_probe.py');delivery=load('typed_delivery','typed_delivery.py')
G=R/'knowledge/authored/semantic_grammar_20261104_r9/private/graph.json'
def convert(packet):
 out=copy.deepcopy(packet);g=p.read(G);out['actions']=[delivery.compile_action(g,a) for a in packet['actions']];return out
def validate(packet,original):
 assert len(packet['actions'])==len(original['actions'])
 for a,b in zip(packet['actions'],original['actions']):assert all(a[k]==b[k] for k in ('target_id','target','span','rule_id','preserve'))
 assert {k:v for k,v in packet.items() if k!='actions'}=={k:v for k,v in original.items() if k!='actions'}
if __name__=='__main__':
 p.EXPERIMENT='fixed_typed_delivery';p.INDEX='latest_typed.json';p.GRAPH_BY_ARM={'control':G,'surface':G};p.EXTRA_CODES=[Path(__file__),H/'typed_delivery.py',H/'realization_probe.py',H/'build_realization_r9.py'];p.COMPARISON='r8 linguistic meaning fixed; explicit edit-unit interface and instruction vs old EF interface; original diagnostics fixed; composer not called';p.CONTROL_TRANSFORM=r8.convert;p.SURFACE_PROMPT=p.rt.GENERATION_PROMPT+delivery.PROMPT_SUFFIX;p.lean=convert;p.validate_packet=validate;p.main()
