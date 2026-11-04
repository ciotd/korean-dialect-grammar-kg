"""Independently recount reviewer observations without modifying experiments."""
import json,hashlib
from pathlib import Path
from collections import Counter
H=Path(__file__).resolve().parent;R=H.parents[2];P=H/'private'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
latest=read(R/'experiments/analyses/selection_probe_20261102/private/latest.json');S=R/latest['root']
cases=read(S/'prepared.json');results=read(S/'results.json')
states=[];repairs=[];blocked=[]
for rid in latest['run_ids']:
 for row in read(R/'experiments/runs'/rid/'private/results.json'):
  f=R/'experiments/runs'/rid/'private/records'/row['id']/'final_plan.json'
  if f.exists():
   p=read(f)
   if p['status']!=row['status']:states.append({'id':row['id'],'run_id':rid,'summary_status':row['status'],'plan_status':p['status']})
  for e in row.get('edit_trace',[]):
   for z in e.get('repairs',[]):repairs.append({'id':row['id'],'run_id':rid,'edit_id':e['edit_id'],'kind':z['kind'],'raw':e['raw'],'after':e['after']})
for c in cases:
 for arm,a in c['arms'].items():
  if a.get('status')!='ready':continue
  visible={e['edit_id']:e for e in a['payload']['plan']['edits']}
  for e in a['plan']['edits']:
   if e['outcome']=='needs_review' and visible[e['edit_id']]['action']=='apply':blocked.append({'id':c['id'],'arm':arm,'edit_id':e['edit_id'],'issues':e['issues']})
counts={'status_mismatches':len(states),'status_transitions':dict(Counter(z['plan_status']+' -> '+z['summary_status'] for z in states)),
        'repair_events':len(repairs),'records_with_repairs':len({(x['run_id'],x['id']) for x in repairs}),
        'repair_kinds':dict(Counter(x['kind'] for x in repairs)),
        'preblocked_edits_sent_as_apply':len(blocked), 'preblocked_case_arm_count':len({(x['id'],x['arm']) for x in blocked})}
out={'counts':counts,'state_disagreements':states,'repairs':repairs,'preblocked_apply':blocked}
(P/'verified_findings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(counts,ensure_ascii=False))
