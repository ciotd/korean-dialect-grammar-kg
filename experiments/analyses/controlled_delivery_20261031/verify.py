import hashlib,json,sys,urllib.request,urllib.error
from pathlib import Path
from html.parser import HTMLParser
B=Path(__file__).resolve().parent;R=B.parents[2];P=B/'private';sys.path[:0]=[str(R/'local/python'),str(R/'src')]
from kg_pipeline.io import read,save,dumps
from kg_runtime.edit_contract import assemble
from kg_runtime.delivery_aids import prepare
from kg_runtime.compatibility import guidance
from kg_runtime import card_pipeline as cp
def main():
 for filename in ('replay_source_hashes.json','replay_code_hashes.json'):
  for rel,h in read(P/filename).items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h,rel
 oldkg=read(R/'experiments/runs/20261030T085346443103Z_cards_single_regression/kg_hashes.json')
 for rel,h in oldkg.items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h,rel
 t=read(P/'tests.json');assert not t['failures'] and not t['errors']
 rows=read(P/'replay_cases.json');assert len(rows)==50;count=0
 for r in rows:
  for a,v in r['arms'].items():
   replay=v['replay']
   if replay['output'] is not None:assert assemble(r['input'],replay['final_plan'])==replay['output'];count+=1
 assert count==97
 plan=read(P/'prepared_plan.json');assert len(plan['rows'])==50
 for rel,h in plan['hashes'].items():assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h
 prepared_count=0
 for row in plan['rows']:
  source=R/row['source'];packet=read(source/'reference_packet.json');m=read(source/'morphology.json')
  packet['contract_context']=cp.context(m,packet['cards'],packet['grammar'],row['id']);packet['candidate_guidance']=guidance(packet['cards'],packet['grammar'],m)
  assert hashlib.sha256(json.dumps(packet,ensure_ascii=False,sort_keys=True).encode()).hexdigest()==row['base_packet_sha256']
  for variant,key in [('control',None),('explanation','condition_explanations'),('composition','composition_aids')]:
   value=prepare(packet,m,variant);assert {k:v for k,v in value.items() if k!=key}==packet;prepared_count+=1
 out={'tests':t['tests'],'saved_records':100,'reassembled_outputs':count,'KG_and_cards_unchanged':True,'old_records_unchanged':True,
      'prepared_packets':prepared_count,'condition_differences_only_extra_aids':True,'new_Qwen_generation_calls':0,'actual_run_completed':False}
 if '--http' in sys.argv:
  url='http://127.0.0.1:8767/reports/controlled-delivery-20261031/'
  for name in ('report.html','report.css','report.js'):assert urllib.request.urlopen(url+name,timeout=10).read()==(P/name).read_bytes()
  for name in ('replay_cases.json','prepared_plan.json','../private/reviewer.json'):
   try:urllib.request.urlopen(url+name,timeout=10);raise AssertionError('raw path exposed')
   except urllib.error.HTTPError as e:assert e.code==404
  out.update(http_verified=True,raw_paths_not_served=True)
 save(P/'verification.json',out);print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
