"""Freeze the derived report separately from immutable experimental runs."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlparse
import json,hashlib,datetime,shutil,subprocess
H=Path(__file__).resolve().parent;P=H/'private'
def read(p):return json.loads(p.read_text('utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.cases=0;self.script=False;self.js=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a' and a.get('href','').startswith('file:'):self.links.append(a['href'])
  if tag=='details' and a.get('class')=='case':self.cases+=1
  if tag=='script':self.script=True
 def handle_endtag(self,tag):
  if tag=='script':self.script=False
 def handle_data(self,data):
  if self.script:self.js.append(data)
p=Parser();p.feed((P/'report.html').read_text('utf8'))
missing=[x for x in p.links if not Path(unquote(urlparse(x).path).lstrip('/')).is_file()]
assert p.cases==62 and not missing,(p.cases,missing)
for who in ('codex','claude'):
 for stage in ('plan','results'):
  assert f'END_SCOPE_{stage.upper()}_{who.upper()}_20261104' in (P/'reviewers'/stage/who/'review.md').read_text('utf8')
js=P/'report_script.js';js.write_text(''.join(p.js),'utf8')
node=shutil.which('node');js_status='not_available'
if node:
 result=subprocess.run([node,'--check',str(js)],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 js_status='passed'
paths=[]
for name in ('v1_latest_regression','latest_regression','latest_development'):paths.extend(Path(x) for x in read(P/(name+'.json')).values())
paths.append(Path(read(P/'latest_dev_analysis.json')['directory']))
snapshot=P/'report_snapshot';snapshot.mkdir(exist_ok=True)
for name in ('report.py','experiment.py','verify_report.py','findings.md','reviewer_resolution.md','plain_statement_notes.md'):
 shutil.copy2(H/name,snapshot/name)
files=[H/x for x in ('report.py','experiment.py','verify_report.py','findings.md','reviewer_resolution.md','plain_statement_notes.md')]
files += [P/x for x in ('report.html','comparison.json','validation.json','review_outputs.json','executive.json','run_integrity.json','all_run_totals.json','v1_comparison.json')]
files += list((P/'reviewers').rglob('review.md'))+list(snapshot.iterdir())
manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'purpose':'Derived reporting snapshot; raw experiment artifacts remain unchanged','runs':[{'run_id':d.name,'directory':str(d),'manifest_sha256':sha(d/'artifact_hashes.json'),'metrics_sha256':sha(d/'metrics.json')} for d in paths],'files':{str(x.relative_to(H)):sha(x) for x in files},'validation':{'cases':p.cases,'local_links_checked':len(p.links),'missing_links':missing,'javascript_syntax':js_status,'reviewer_markers':4},'units':'50 regression and 12 development inputs, each generated twice per arm. Repeats are not independent inputs. v1/v2 are separate.'}
(P/'report_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
print(json.dumps(manifest['validation'],ensure_ascii=False))
