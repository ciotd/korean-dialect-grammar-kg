"""Verify the local audit page, bounded static routes and preserved source inputs."""
import hashlib,json,urllib.request,urllib.error
from html.parser import HTMLParser
from pathlib import Path
BASE=Path(__file__).resolve().parent;P=BASE/'private'
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.cases=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if a.get('class')=='case':self.cases.append(a['id'])
def main():
 uri='http://127.0.0.1:8767/reports/bottleneck-audit-20261030/'
 checks={}
 for name in ('report.html','report.css','report.js'):
  checks[name]=urllib.request.urlopen(uri+name).read()==(P/name).read_bytes()
 assert all(checks.values())
 parser=Page();parser.feed((P/'report.html').read_text(encoding='utf-8'))
 assert len(parser.ids)==len(set(parser.ids))
 expected=set(json.loads((P/'notes.json').read_text(encoding='utf-8')))
 assert set(parser.cases)==expected and len(parser.cases)==50
 for name in ('evidence.json','notes.json','../private/evidence.json'):
  try:urllib.request.urlopen(uri+name);raise AssertionError('Unexpected raw route: '+name)
  except urllib.error.HTTPError as e:assert e.code==404
 checks.update(case_count=50,unique_anchors=True,raw_routes_404=True)
 (P/'view_verification.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
