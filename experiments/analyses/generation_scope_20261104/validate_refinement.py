"""Validate offline refinement artifacts without model calls or KG writes."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
import json, hashlib, subprocess, tempfile, sys

H = Path(__file__).resolve().parent
R = H.parents[2]
def read(p): return json.loads(p.read_text(encoding='utf8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.scripts=[]; self.in_script=False; self.cases=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a' and 'href' in a: self.links.append(a['href'])
        if 'case' in a.get('class','').split(): self.cases+=1
        if tag=='script': self.in_script=True
    def handle_endtag(self, tag):
        if tag=='script': self.in_script=False
    def handle_data(self, data):
        if self.in_script: self.scripts.append(data)

def main():
    out=Path(read(H/'private/latest_refinement.json')['directory'])
    cases=read(out/'cases.json'); ids={c['id'] for c in cases}
    assert len(ids)==50 and sum(len(c['current_targets']) for c in cases)==62
    assert ids=={c['id'] for c in read(out/'lead_notes.json')}
    hashes=read(out/'manifest.json')['source_hashes']
    changed=[p for p,h in hashes.items() if not Path(p).exists() or sha(Path(p))!=h]
    assert not changed, changed
    for who in ('codex','claude'):
        review=(out/'reviewers'/who/'review.md').read_text(encoding='utf8')
        assert f'END_REFERENCE_REFINEMENT_{who.upper()}_20261104' in review
        assert all(i in review for i in ids)
    page=Page(); page.feed((out/'report.html').read_text(encoding='utf8'))
    assert page.cases==50
    missing=[]
    for link in page.links:
        u=urlparse(link)
        if u.scheme=='file':
            path=Path(unquote(u.path).lstrip('/'))
            if not path.exists(): missing.append(str(path))
    assert not missing, missing
    with tempfile.TemporaryDirectory() as td:
        js=Path(td)/'report.js'; js.write_text('\n'.join(page.scripts),encoding='utf8')
        subprocess.run(['node','--check',str(js)],check=True,capture_output=True,text=True)
    result={'inputs':50,'target_positions':62,'source_hashes_checked':len(hashes),
            'source_changes':0,'reviewers_completed':2,'report_rows':page.cases,
            'report_links':len(page.links),'missing_links':0,'javascript_syntax':'passed',
            'browser_visual_check':'not_performed','new_qwen_calls':0,'operational_kg_changes':0}
    (out/'final_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    paths=list(H.glob('*refinement*.py'))+[H/'repair_feedback.py',H/'test_repair_feedback.py',H/'preview_feedback.py',H/'REFINEMENT_PLAN.md']
    paths+=list(out.rglob('*.json'))+list(out.rglob('*.md'))+[out/'report.html']
    paths=[p for p in paths if p.name!='final_manifest.json']
    (out/'final_manifest.json').write_text(json.dumps({str(p):sha(p) for p in paths},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    sys.path.insert(0,str(R/'src'))
    from research_management.work import WorkStore
    WorkStore(R).task({'id':'reference_refinement_final_'+out.name,'title':'참조50 대조·두 검토·수정 후보 검증','actor':'연구 리드','stage':'완료','status':'completed','done':50,'total':50,'unit':'입력','unit_key':'reference_refinement_final','message':'50입력·62조회 위치, 두 검토 완료. 새 Qwen 실행 및 운영 KG 변경 없음.'})
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
