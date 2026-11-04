"""Check completed runs, paired inputs, query-derived cards and bounded report routes."""
import hashlib,json,sys,urllib.request,urllib.error
from pathlib import Path
from html.parser import HTMLParser
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];P=BASE/'private';sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime.edit_contract import assemble
def read(p):return json.loads(p.read_text(encoding='utf8'))
class Page(HTMLParser):
 def __init__(self):super().__init__();self.cases=[];self.ids=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if a.get('class')=='case':self.cases.append(a['id'])
def main():
    a=read(P/'active_run.json');rows=read(P/'cases.json');assert len(rows)==50
    checked=0;assemblies=0;new_calls=[]
    for arm,run in a['runs'].items():
        root=ROOT/'experiments/runs'/run
        for rel,h in read(root/'artifact_hashes.json').items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==h,rel
        post=read(root/'postflight.json');assert all(post.values())
        for row in rows:
            folder=root/'private/records'/row['id'];result=read(folder/'result.json');packet=read(folder/'reference_packet.json')
            query=read(folder/'retrieval_raw.json');selection=read(folder/'compatibility_selection.json')
            assert set(c['id'] for c in packet['cards'])<=set(query['retrieved_ids'])
            assert selection['delivered_ids']==[c['id'] for c in packet['cards']] and len(packet['cards'])<=48
            assert read(folder/'selection_audit.json')['selected_ids']==selection['delivered_ids']
            assert 'reference' not in packet and 'gold' not in packet
            if result['output_text'] is not None:
                assert assemble(result['input_text'],read(folder/'final_plan.json'))==result['output_text'];assemblies+=1
            if arm=='single':
                other=ROOT/'experiments/runs'/a['runs']['multi']/'private/records'/row['id']
                assert read(other/'reference_packet.json')==packet
            checked+=1
    for rel,h in read(P/'input_hashes.json').items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
    page=Page();page.feed((P/'report.html').read_text('utf8'))
    assert len(page.cases)==50 and set(page.cases)=={r['id'] for r in rows} and len(page.ids)==len(set(page.ids))
    out={'actual_records':checked,'assembled_outputs':assemblies,'artifact_hashes_passed':True,'same_inputs_and_packets_between_arms':True,
         'delivered_cards_from_actual_query_only':True,'max48':True,'reference_not_in_packet':True,'report_cases':50}
    if '--http' in sys.argv:
        url='http://127.0.0.1:8767/reports/register-connective-20261030/'
        for name in ('report.html','report.css','report.js'):assert urllib.request.urlopen(url+name,timeout=10).read()==(P/name).read_bytes()
        for name in ('cases.json','summary.json','../private/cases.json'):
            try:urllib.request.urlopen(url+name,timeout=10);raise AssertionError('raw file exposed')
            except urllib.error.HTTPError as e:assert e.code==404
        out.update(http_assets_match=True,raw_files_not_served=True)
    (P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
