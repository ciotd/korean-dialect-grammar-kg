from pathlib import Path
import json,collections
from experiment import H,R,read,save
from report import summarize
d=summarize();packet={}
for cohort,x in d.items():
 rows=[]
 for row in x['cases']:
  outputs={}
  for arm,rs in row['arms'].items():
   unique={}
   for r in rs:unique.setdefault(r['output_text'],[]).append(r['repeat'])
   outputs[arm]=[{'output':text,'repeats':reps} for text,reps in unique.items()]
  rows.append({'id':row['id'],'source':row['text'],'action_count':row['action_count'],'rules':row['knowledge_rules'],'outputs':outputs})
 packet[cohort]={'rows':rows,'groups':x['groups'],'identical_request_controls':{k:v for k,v in x['identical_request_controls'].items() if k!='pairs'},'repeat_variation':x['repeat_variation'],'run_ids':{a:y['run_id'] for a,y in x['arms'].items()}}
save(H/'private/review_outputs.json',packet)
print(json.dumps({c:{'inputs':len(x['rows']),'groups':x['groups'],'controls':x['identical_request_controls'],'repeats':x['repeat_variation']} for c,x in packet.items()},ensure_ascii=False,indent=2))
