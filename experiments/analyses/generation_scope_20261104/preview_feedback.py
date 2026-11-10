"""Rebuild versioned offline feedback after reviewer fixes; never call a model."""
from pathlib import Path
import json,collections,hashlib
from repair_feedback import build_feedback,retry_payload
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text('utf8'))
def main():
 out=Path(read(H/'private/latest_refinement.json')['directory']);g=read(out/'graph.json');cs=read(out/'cases.json');rows=[]
 for c in cs:
  for r in c['outputs']['A']:
   req=read(Path(r['request']));packet=json.loads(req['messages'][1]['content']);f=build_feedback(g,packet,r['text']);v={'id':c['id'],'repeat':r['repeat'],'feedback':f,'request':r['request']}
   if f['status']=='feedback_available':
    v['proposed_requests']={a:retry_payload(g,packet,r['text'],f,a) for a in ('neutral','specific')}
    treatment=dict(v['proposed_requests']['specific']);treatment.pop('failed_checks');assert treatment==v['proposed_requests']['neutral']
   rows.append(v)
 assert len(rows)==100
 (out/'feedback_preview_v2.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
 stats={'responses':len(rows),'status_counts':dict(collections.Counter(x['feedback']['status'] for x in rows)),'flagged_input_ids':sorted({x['id'] for x in rows if x['feedback']['status']=='feedback_available'}),'new_model_calls':0,'request_difference':'failed_checks only; not equal token count','code_sha256':hashlib.sha256((H/'repair_feedback.py').read_bytes()).hexdigest()}
 (out/'feedback_validation_v2.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n','utf8');print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':main()
