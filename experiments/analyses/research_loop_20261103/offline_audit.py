"""Offline audit: actual request settings and uniformly evaluated saved candidates."""
import collections
from pipeline import *
from kg_pipeline.io import read,save,sha
from kg_runtime.morphology import Morphology
import importlib.util
spec=importlib.util.spec_from_file_location("loop_report",HERE/"report.py");report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report);RUNS=report.RUNS

def main():
 m=Morphology();audit={'version':'offline_audit_v1','checker_sha256':sha((HERE/'pipeline.py').read_bytes()),'runs':[]}
 for label,rid in RUNS:
  d=ROOT/'experiments/runs'/rid;calls=[]
  for path in (d/'private/records').rglob('request.json'):
   meta=read(path.parent/'meta.json');request=read(path)
   calls.append({'path':str(path.relative_to(d)),'stage':meta['stage'],'max_tokens':request['max_tokens'],'model':request['model'],
    'http_status':meta.get('http_status'),'finish_reason':meta.get('finish_reason'),'call_status':meta.get('status'),
    'parsed_exists':(path.parent/'parsed.json').exists(),'error':meta.get('error')})
  candidates=[];records=read(d/'private/results.json')
  if 'replay' in rid:
   for r in records:
    if r['status']!='generated':continue
    tid=r['targets'][0]['target_id'];payload=read(d/'private/records'/r['id']/'targets'/tid/'enhanced.json')
    candidates.append({'id':r['id'],'arm':'components','output':r['output_text'],'checks':preservation_check(m,r['output_text'],payload)})
  else:
   for r in records:
    for t in r['targets']:
     for arm,g in t['generation'].items():
      if not g.get('output_text'):continue
      payload=read(d/'private/records'/r['id']/'targets'/t['target_id']/'enhanced.json')
      candidates.append({'id':r['id'],'target':t['target_id'],'arm':arm,'output':g['output_text'],'checks':preservation_check(m,g['output_text'],payload)})
  config=read(d/'config.json');generation_caps=sorted({c['max_tokens'] for c in calls if c['stage'].startswith('generation')})
  audit['runs'].append({'run_id':rid,'calls':calls,'candidates':candidates,'candidate_count':len(candidates),
   'unchanged_candidates':sum(c['checks'].get('unchanged',False) for c in candidates),
   'warning_candidates':sum(bool(c['checks']['warnings']) for c in candidates),
   'generation_caps_actual':generation_caps,'generation_cap_config':config.get('generation_max_tokens'),
   'generation_cap_config_matches':generation_caps==[config.get('generation_max_tokens')],
   'non_stop_calls':sum(c['finish_reason'] not in (None,'stop') for c in calls)})
 assert audit['runs'][0]['non_stop_calls']==2
 assert audit['runs'][2]['candidate_count']==27 and audit['runs'][2]['unchanged_candidates']==2 and audit['runs'][2]['warning_candidates']==5
 assert sum(r['candidate_count'] for r in audit['runs'])==84
 manifest=read(ROOT/'data/derived_private/standard_inputs_50_20261029_v2/manifest.json')
 feedback=ROOT/manifest['source_feedback']
 audit['input_version']={'version':manifest['dataset_id'],'parent':manifest['parent_dataset_id'],'changed_id':'ADVCE008A','change':manifest['input_change'],
  'feedback_path':str(feedback),'feedback_hash_matches':sha(feedback.read_bytes())==manifest['source_feedback_sha256']}
 save(HERE/'private/offline_validation.json',audit)
 print({'saved_candidates_checked':84,'length_failures':2,'last_replay_candidates':27,'unchanged':2,'warning_candidates':5,'input_approval_hash':audit['input_version']['feedback_hash_matches']})
if __name__=='__main__':main()
