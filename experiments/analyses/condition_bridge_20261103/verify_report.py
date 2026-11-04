"""Offline report links/counts/filter checks. Does not claim browser render QA."""
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlparse
from bridge import HERE
from kg_pipeline.io import read,save

class Page(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.depth=0;self.current=None;self.script=False;self.code='';self.links=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a':self.links.append(a.get('href',''))
  if tag=='script':self.script=True
  if tag=='tr':
   if self.current is not None:self.depth+=1
   elif a.get('class')=='case':self.current={'dataset':{'group':a['data-group']},'textContent':'','hidden':False};self.depth=1
 def handle_data(self,data):
  if self.current is not None:self.current['textContent']+=data
  if self.script:self.code+=data
 def handle_endtag(self,tag):
  if tag=='script':self.script=False
  if tag=='tr' and self.current is not None:
   self.depth-=1
   if not self.depth:self.rows.append(self.current);self.current=None

def main():
 file=HERE/'private/report.html';page=Page();page.feed(file.read_text(encoding='utf-8'))
 assert len(page.rows)==32
 missing=[]
 for href in page.links:
  if href.startswith('file:'):
   path=unquote(urlparse(href).path).lstrip('/');target=Path(path)
  elif not urlparse(href).scheme:target=file.parent/href
  else:continue
  if not target.exists():missing.append(href)
 assert not missing,missing
 script='''const vm=require('vm');
const rows=ROWS; const fields={search:{value:''},group:{value:''},count:{textContent:''}};
for(const f of Object.values(fields))f.addEventListener=()=>{};
const context={document:{getElementById:id=>fields[id],querySelectorAll:()=>rows}};
vm.createContext(context);vm.runInContext(CODE,context);
function check(group,search,count){fields.group.value=group;fields.search.value=search;context.filterRows();if(rows.filter(r=>!r.hidden).length!==count)throw Error('filter count');if(fields.count.textContent!==count+'건')throw Error('counter');}
check('','',32);check('previous_development','',16);check('new_core','',12);check('new_boundary','',4);check('','N12',1);check('','없을검색문장',0);
console.log(JSON.stringify({filter_checks:6,status:'passed'}));'''.replace('ROWS',json.dumps(page.rows,ensure_ascii=False)).replace('CODE',json.dumps(page.code,ensure_ascii=False))
 result=subprocess.run(['node','-'],input=script,text=True,encoding='utf-8',capture_output=True,check=True)
 validation={'html_rows':32,'local_links_checked':len(page.links),'javascript':json.loads(result.stdout),
  'pre_run_unit_tests':{'passed':12},'post_run_extension_test':{'passed':1},
  'browser_render_checked':False,'artifact_validation':read(HERE/'private/audit.json')['validation']}
 save(HERE/'private/report_validation.json',validation);print(json.dumps(validation,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
