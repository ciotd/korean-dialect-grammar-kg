"""Same prompt, same analysis/selection: only graph REALIZES content differs."""
from pathlib import Path
import importlib.util,copy
H=Path(__file__).resolve().parent;R=H.parents[2]
s=importlib.util.spec_from_file_location('fixed_runner',H/'handoff_probe.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
G=R/'knowledge/authored/semantic_grammar_20261104_r8/private/graph.json'
def convert(packet):
 out=copy.deepcopy(packet);graph=p.read(G);ns={n['id']:n for n in graph['nodes']}
 for a in out['actions']:
  if a['rule_id'] not in ('SEM_DECL_HAEYE_EO','SEM_SUP_POLITE_Q_EO'):continue
  assert a['target'].endswith('요') and a['source_final'] in ('아요','어요')
  ids=[e['target'] for e in graph['edges'] if e['source']==a['rule_id'] and e['relation']=='REALIZES'];assert len(ids)==1
  f=ns[ids[0]]['properties'];a['forms']=[{'ending':f['form'],'selected_combining_form':f['form'].lstrip('-'),'includes_copula':f['includes_copula']}];a['composition']=[f['composition']]
 return out
def validate(packet,original):
 assert len(packet['actions'])==len(original['actions'])
 for a,b in zip(packet['actions'],original['actions']):
  assert {k:v for k,v in a.items() if k not in ('forms','composition')}=={k:v for k,v in b.items() if k not in ('forms','composition')}
 assert {k:v for k,v in packet.items() if k!='actions'}=={k:v for k,v in original.items() if k!='actions'}
if __name__=='__main__':
 p.EXPERIMENT='fixed_realization';p.INDEX='latest_realization.json';p.GRAPH_BY_ARM={'surface':G};p.EXTRA_CODES=[Path(__file__),H/'build_realization_r8.py'];p.COMPARISON='same system prompt and all packet fields except forms/composition from two r8 Realization nodes; source analysis and selected rules fixed';p.SURFACE_PROMPT=p.rt.GENERATION_PROMPT;p.lean=convert;p.validate_packet=validate;p.main()
