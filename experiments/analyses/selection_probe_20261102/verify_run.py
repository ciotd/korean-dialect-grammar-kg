"""Post-run independent integrity checks; no generation or mutation of run artifacts."""
import runner as r
from research_management.core import Registry

def main():
 latest=r.read(r.HERE/'private/latest.json');root=r.ROOT/latest['root']
 assert latest['state']=='completed'
 cases=r.read(root/'prepared.json');by={c['id']:c for c in cases};rows=r.read(root/'results.json');checks={}
 assert len(rows)==300 and len({(x['id'],x['arm'],x['repeat']) for x in rows})==300
 checks['all_50_by_two_arms_by_three_repetitions']=True
 assert r.source_files()==r.read(root/'freeze.json');checks['frozen_sources_unchanged']=True
 req_count=0;request_common={};snapshot_n=0
 for name,digest in r.read(root/'freeze.json').items():
  assert r.sha((root/'snapshot'/name).read_bytes())==digest,name;snapshot_n+=1
 for rid in latest['run_ids']:
  folder=r.ROOT/'experiments/runs'/rid;cfg=r.read(folder/'config.json');data=r.read(folder/'private/results.json')
  assert {x['id'] for x in data}==set(by)
  for name,digest in r.read(folder/'artifact_hashes.json').items():assert r.sha((folder/name).read_bytes())==digest,(rid,name)
  for x in data:
   record=folder/'private/records'/x['id'];request=record/'generation_call/request.json'
   assert request.exists()==bool(x['worker_calls'])
   if not request.exists():
    assert x['output_text'] is None;continue
   req_count+=1;q=r.read(request);import json
   payload=json.loads(q['messages'][1]['content']);assert payload==by[x['id']]['arms'][x['arm']]['payload']
   assert q['messages'][0]['content']==r.PROMPT
   assert q['seed']==20261102+x['repeat']-1
   for e in payload['plan']['edits']:assert e['after']=='' and e['instruction']==r.NOTE and 'suffix_projection' not in e
   assert {k:v for k,v in payload.items() if k!='plan'}==by[x['id']]['common']
   if x['status']=='generation_failed':assert x['output_text'] is None
   elif (record/'final_plan.json').exists():assert r.cp.assemble(x['input_text'],r.read(record/'final_plan.json'))==x['output_text']
  registered=Registry(r.ROOT).get(rid);assert registered['state']=='completed';assert registered['integrity']['status']=='light_check_passed',registered['integrity']
 assert req_count==219
 checks.update(actual_calls_219=True,all_requests_match_frozen_payload=True,no_generated_answer_in_visible_plan=True,all_artifact_hashes_valid=True,registered_six_runs=True,failed_and_skipped_outputs_null=True,final_assembly_replays=True,snapshot_files=snapshot_n)
 r.save(r.HERE/'private/verification.json',checks);print(r.dumps(checks))
if __name__=='__main__':main()
