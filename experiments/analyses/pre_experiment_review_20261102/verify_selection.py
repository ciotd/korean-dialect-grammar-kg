"""Read-only check: compatibility score is not the final eligibility gate."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parents[2]
read=lambda p:json.loads(p.read_text(encoding='utf8'))
checks=[('DEV021','W6','GS_END_DECL_YE_08'),('ADVCE008A','W6','GS_END_DECL_YE_08'),('ADVCE010B','W4','GS_END_DECL_YE_06'),('DEV002','W5','GS_END_DECL_HRA_09')]
rows=[]
for key,w,cid in checks:
 p=R/'experiments/batches/20261030T085346443103Z/private/shared'/key/'compatibility_selection.json'
 d=read(p);a=next(a for a in d['assessments'] if a['word_id']==w and a['card_id']==cid)
 qualifying=any(x['field'] in ('function','source_connective') and x['result']=='match' for x in a['checks'])
 rows.append(dict(id=key,word=w,card=cid,score=a['score'],status=a['status'],checks=a['checks'],passes_additional_match_gate=qualifying,delivered=cid in d['delivered_ids'],source=str(p.relative_to(R))))
(H/'private/selection_verified.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
