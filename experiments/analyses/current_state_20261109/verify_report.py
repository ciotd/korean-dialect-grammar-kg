"""Check reproducible status artifacts and local navigation, not grammar accuracy."""
from pathlib import Path
import hashlib,json,subprocess,sys,re
from urllib.parse import unquote
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(BASE/'overview.json')
subprocess.run([sys.executable,'-B','-X','utf8',str(BASE/'collect_snapshot.py')],check=True,capture_output=True)
assert sha(BASE/'overview.json')==before,'Inventory not reproducible'
before_html=sha(BASE/'report.html')
subprocess.run([sys.executable,'-B','-X','utf8',str(BASE/'build_report.py')],check=True,capture_output=True)
assert sha(BASE/'report.html')==before_html,'Report not reproducible'
links=re.findall(r'href="([^"]+)"',(BASE/'report.html').read_text(encoding='utf-8'))
missing=[x for x in links if not x.startswith(('#','https:','http:')) and not (BASE/unquote(x.split('#')[0])).is_file()]
assert not missing,missing
nav=ROOT/'experiments/management/report_navigation.json'
entries=json.loads(nav.read_text(encoding='utf-8-sig'))
assert any(x.get('local_path')=='experiments/analyses/current_state_20261109/report.html' for x in entries)
overview=json.loads((BASE/'overview.json').read_text(encoding='utf-8'))
assert overview['runtime_code_match']['changed']==[]
assert overview['graph']['matches_latest_run']
assert overview['saved_run_rule_stages']['knowledge_equals_selected']
out={'scope':'Status artifact validation only','inventory_reproducible':True,'report_reproducible':True,'local_links_checked':len([x for x in links if not x.startswith(('#','https:','http:'))]),'missing_links':missing,'runtime_12_files_unchanged':True,'graph_matches_frozen_run':True,'review_hashes':{p.name:sha(p) for p in (BASE/'private').glob('*state_review.md')},'new_qwen_calls':0}
(BASE/'private/validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
