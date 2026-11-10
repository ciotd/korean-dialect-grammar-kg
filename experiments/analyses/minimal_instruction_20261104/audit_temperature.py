from pathlib import Path
import json,collections,sys
from audit import inspect_case
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import read,save,sha
runs={};by={}
for arm,p in read(H/'private/latest_temperature.json').items():
 d=Path(p);rs=read(d/'private/results.json');cases={r['id']:r for r in read(d/'private/cases.json')};metrics=read(d/'metrics.json');by[arm]={};details=[]
 assert len(rs)==27 and len({r['id'] for r in rs})==27
 for r in rs:
  f=d/'private/records'/r['id'];req=read(f/'generation_call/request.json');raw=read(f/'generation_call/response.json');parsed=json.loads(raw['choices'][0]['message']['content'])
  assert parsed==read(f/'generation_call/parsed.json') and parsed['output_text']==r['output_text']
  assert json.loads(req['messages'][1]['content'])==read(f/'generation_packet.json')
  assert req['seed']==20261103+r['repeat'] and req['temperature']==(0 if arm=='T0' else 0.7)
  detail=inspect_case(cases[r['source_id']],r);assert detail['instruction_match']==r['diagnostic']['instruction_match']
  details.append({**r,**detail});by[arm][r['id']]=req
 assert sum(r['instruction_match'] for r in details)==metrics['instruction_matches']
 assert all(sha((d/k).read_bytes())==v for k,v in read(d/'artifact_hashes.json').items())
 assert all(read(d/'postflight.json').values())
 runs[arm]={'path':p,'metrics':metrics,'records':details}
for key,a in by['T0'].items():
 b=by['T7'][key];assert {k:v for k,v in a.items() if k!='temperature'}=={k:v for k,v in b.items() if k!='temperature'}
s={'runs':runs,'validated_requests':54,'paired_difference':'temperature_only','seeds':[20261104,20261105,20261106],'adopted':False,'conclusion':'no_observed_improvement; not official full sampling recipe; no naturalness evaluation'}
save(H/'private/temperature_summary.json',s)
print({a:v['metrics']['instruction_matches'] for a,v in runs.items()})
