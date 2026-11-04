"""Verify replay provenance and rendered content; optional bounded local HTTP checks."""
import hashlib,json,sys,urllib.request,urllib.error
from pathlib import Path
from html.parser import HTMLParser
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];P=BASE/'private'
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime.edit_contract import assemble
def read(p):return json.loads(p.read_text(encoding='utf8'))
class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.cases=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if a.get('class')=='case':self.cases.append(a['id'])
def main():
    rows=read(P/'cases.json');assert len(rows)==50
    hashes=read(P/'input_hashes.json')
    for rel,h in hashes.items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
    for rel,h in read(P/'code_hashes.json').items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
    assemblies=0;changes=[];unavailable=0
    for row in rows:
        for arm,v in row['arms'].items():
            assert v['analysis_validation']=='passed'
            for mode in ('contract_only','aligned_analysis'):
                r=v[mode];assert r['new_model_calls']==0 and r['new_KG_queries']==0
                if r['output'] is not None:
                    assert assemble(row['input'],r['final_plan'])==r['output'];assemblies+=1
                else:unavailable+=1
                if v['baseline']['error']=='stale_request':assert r['output'] is None and r['reason']=='original_stale_request_not_repaired'
                if v['baseline']['error']=='CallError:200':assert r['output'] is None
            if v['baseline']['output']!=v['aligned_analysis']['output']:changes.append([row['id'],arm])
    assert changes==[['LONG004','single'],['NEW004','single'],['QUAL017','single']]
    parser=Page();parser.feed((P/'report.html').read_text(encoding='utf8'))
    assert len(parser.ids)==len(set(parser.ids)) and set(parser.cases)=={r['id'] for r in rows}
    t=read(P/'test_results.json');assert not t['failures'] and not t['errors']
    result={'inputs':50,'records':100,'replay_conditions':2,'assemblies_verified':assemblies,'unavailable_replay_outcomes':unavailable,
            'original_files_unchanged':len(hashes),'code_matches_snapshot':True,'changed_outputs':changes,'html_cases':len(parser.cases),'tests':t['tests']}
    if '--http' in sys.argv:
        uri='http://127.0.0.1:8767/reports/contract-alignment-20261030/'
        for name in ('report.html','report.css','report.js'):assert urllib.request.urlopen(uri+name,timeout=8).read()==(P/name).read_bytes()
        for name in ('cases.json','reviewer.json','../private/cases.json'):
            try:urllib.request.urlopen(uri+name,timeout=8);raise AssertionError('raw file exposed')
            except urllib.error.HTTPError as e:assert e.code==404
        result['http_assets_exact']=True;result['raw_routes_404']=True
    (P/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
