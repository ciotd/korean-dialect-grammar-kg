"""Concise read-only console inspection of saved outputs and failed calls."""
import json,sys
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[2]
a=json.loads((B/'private/active_run.json').read_text('utf8'))
data=[json.loads(x) for x in (R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl').read_text('utf8').splitlines()]
for row in data:
 if len(sys.argv)>1 and row['id'] not in sys.argv[1:]:continue
 print(row['id'],row['text'])
 for arm,run in a['runs'].items():
  p=R/'experiments/runs'/run/'private/records'/row['id']
  if not (p/'result.json').exists():print(arm,'running');continue
  v=json.loads((p/'result.json').read_text('utf8'));print(arm,v['output_text'])
  if len(sys.argv)>1 and (p/'final_plan.json').exists():
   plan=json.loads((p/'final_plan.json').read_text('utf8'))
   for e in plan['edits']:print(' ',e['before'],'->',e['after'],e['outcome'],e['rule_ids'],[x['code'] for x in e['issues']])
  if v['output_text'] is None:
   for c in v['calls']:
    if c.get('error'):print(' failure',c['stage'],c['error'])
