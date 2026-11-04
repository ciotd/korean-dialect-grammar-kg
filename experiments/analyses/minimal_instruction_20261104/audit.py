"""Read-only audit of saved calls. Derived findings never rewrite run artifacts."""
from pathlib import Path
import sys,json,collections,html
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import read,save,sha
from research_management.core import Registry

def inspect_case(c,r):
 text=c['text'];out=r.get('output_text');i,j=c['action']['span'];target=c['action']['target']
 expected=text[:j-1]+'예'+text[j:]
 d={'instruction_match':out==expected,'model_status':r.get('model_status'),'expected_target':target[:-1]+'예'}
 if not isinstance(out,str):return {**d,'category':'call_or_output_failure','surface':None}
 if out==text:return {**d,'category':'unchanged','surface':target}
 suffix=text[j:];outside=out.startswith(text[:i]) and (not suffix or out.endswith(suffix)) and len(out)>=i+len(suffix)
 if not outside:return {**d,'category':'outside_target_or_alignment_uncertain','surface':None}
 surface=out[i:len(out)-len(suffix) if suffix else len(out)]
 kind='exact_instruction_followed' if out==expected else 'target_internal_violation'
 if surface==target[:-2]+'예요' and target[-2] in ('아','어'):kind='pre_yo_syllable_replaced_yo_kept'
 if surface==target[:-2]+'예' and target[-2] in ('아','어'):kind='pre_yo_syllable_deleted'
 return {**d,'category':kind,'surface':surface}

def main():
 paths={**read(H/'private/latest.json'),**read(H/'private/latest_word.json')};runs={};allchecks=[]
 for arm,p in paths.items():
  d=Path(p);rs=read(d/'private/results.json');cs={c['id']:c for c in read(d/'private/cases.json')};metrics=read(d/'metrics.json');by={};records=[]
  assert len(rs)==27 and len({x['id'] for x in rs})==27
  assert collections.Counter(x['repeat'] for x in rs)=={1:9,2:9,3:9}
  for r in rs:
   folder=d/'private/records'/r['id'];req=read(folder/'generation_call/request.json');packet=read(folder/'generation_packet.json');meta=read(folder/'generation_call/meta.json')
   assert json.loads(req['messages'][1]['content'])==packet
   assert req['messages'][0]['content']==(d/'generation_prompt.txt').read_text('utf8')
   if (folder/'generation_call/response.json').exists():
    response=read(folder/'generation_call/response.json');raw=json.loads(response['choices'][0]['message']['content'])
    assert raw==read(folder/'generation_call/parsed.json')
    assert raw['output_text']==r['output_text']
   detail=inspect_case(cs[r['source_id']],r);assert detail['instruction_match']==r['diagnostic']['instruction_match']
   records.append({**r,**detail,'error_type':meta.get('error_type'),'request_path':str(folder/'generation_call/request.json')})
   by[r['id']]={'request':req,'record':r}
  assert sum(x['instruction_match'] for x in records)==metrics['instruction_matches']
  assert sum(isinstance(x.get('output_text'),str) for x in records)==metrics['valid_output_records']
  artifact=read(d/'artifact_hashes.json');assert all(sha((d/k).read_bytes())==v for k,v in artifact.items())
  assert all(read(d/'postflight.json').values())
  for sid in cs:assert sorted(x['repeat'] for x in rs if x['source_id']==sid)==[1,2,3]
  usage={k:sum((read(f).get('usage') or {}).get(k,0) or 0 for f in (d/'private/records').rglob('meta.json')) for k in ('prompt_tokens','completion_tokens','total_tokens')};assert usage==metrics['reported_usage']
  runs[arm]={'path':p,'metrics':metrics,'records':records,'by':by,'categories':dict(collections.Counter(x['category'] for x in records)),'model_statuses':dict(collections.Counter(str(x['model_status']) for x in records)),'cases':cs}
  allchecks.append({'arm':arm,'request_result_metrics_hashes':'passed','records':27,'artifact_files':len(artifact)})
 for id in runs['A']['by']:
  a,b,c,d,e=[runs[k]['by'][id]['request'] for k in 'ABCDE']
  assert a['messages'][1]==b['messages'][1];assert b['messages'][0]==c['messages'][0]
  assert {k:v for k,v in a.items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'}=={k:v for k,v in c.items() if k!='messages'}
  assert {k:v for k,v in d.items() if k!='response_format'}==e
 rows=[]
 for sid,case in runs['A']['cases'].items():
  row={'id':sid,'target':case['action']['target'],'expected':case['action']['target'][:-1]+'예','arms':{}}
  for arm in runs:
   rs=[r for r in runs[arm]['records'] if r['source_id']==sid];row['arms'][arm]={'matches':sum(r['instruction_match'] for r in rs),'surfaces':[r['surface'] for r in rs],'unique_outputs':len({r['output_text'] for r in rs if r['output_text'] is not None}),'errors':[r['error_type'] for r in rs if r['error_type']]}
  rows.append(row)
 prepared=[]
 for p in sorted((R/'experiments/runs').glob('20261104T051311693771Z_minimal_instruction_*')):
  assert not list(p.rglob('request.json'));prepared.append({'run_id':p.name,'chat_calls':0,'failure':read(p/'failure.json')});Registry(R).register(p.name)
 Registry(R).status_document()
 summary={'call_attempts':sum(r['metrics']['api_attempts'] for r in runs.values()),'valid_outputs':sum(r['metrics']['valid_output_records'] for r in runs.values()),'positions':9,'distinct_forms':8,'rows':rows,'runs':{k:{a:b for a,b in v.items() if a not in ('by','cases')} for k,v in runs.items()},'prepared_failures':prepared,'naturalness':'not_evaluated','reference_answers_in_requests':False}
 save(H/'private/summary.json',summary);save(H/'private/validation.json',{'checks':allchecks,'paired_requests':'passed','no_postprocessing':'passed','prepared_failures_confirmed_zero_chat':True})
 print(json.dumps({'attempts':summary['call_attempts'],'valid':summary['valid_outputs'],'arms':{a:{'match':r['metrics']['instruction_matches'],'categories':r['categories']} for a,r in runs.items()}},ensure_ascii=False))
if __name__=='__main__':main()
