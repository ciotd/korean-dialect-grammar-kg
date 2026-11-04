"""Read-only readiness checks; /models only, never /chat/completions."""
import sys,json,hashlib,datetime,urllib.request,urllib.error
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parents[2]
sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import Qwen
def read(p):return json.loads(p.read_text(encoding='utf8'))
out={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'generation_calls':0}
try:
 q=Qwen(R/'test.py',timeout=20);out['qwen']={'models_endpoint_reachable':True,'model':q.model,'generation_verified':False}
except urllib.error.HTTPError as e:out['qwen']={'models_endpoint_reachable':False,'http_status':e.code,'error_type':type(e).__name__}
except Exception as e:out['qwen']={'models_endpoint_reachable':False,'error_type':type(e).__name__}
try:
 with urllib.request.urlopen('http://127.0.0.1:8767/work',timeout=5) as r:out['dashboard_http_status']=r.status
except Exception as e:out['dashboard_error_type']=type(e).__name__
src=R/read(R/'experiments/analyses/selection_probe_20261102/private/latest.json')['root']
freeze=read(src/'freeze.json');mismatches=[];snapshot_bad=[]
for name,digest in freeze.items():
 p=R/name
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:mismatches.append(name)
 p=src/'snapshot'/name
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:snapshot_bad.append(name)
out['frozen_files']=len(freeze);out['current_mismatches']=mismatches;out['snapshot_mismatches']=snapshot_bad
latest=read(R/'experiments/analyses/selection_probe_20261102/private/latest.json')
out['run_artifact_count']=0;out['run_artifact_mismatches']=[]
for rid in latest['run_ids']:
 root=R/'experiments/runs'/rid
 for name,digest in read(root/'artifact_hashes.json').items():
  p=root/name;out['run_artifact_count']+=1
  if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:out['run_artifact_mismatches'].append(f'{rid}/{name}')
(H/'private/readiness.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(out,ensure_ascii=False))
