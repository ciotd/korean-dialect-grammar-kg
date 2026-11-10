"""Verify completeness/reproducibility of the inventory, not linguistic accuracy."""
from pathlib import Path
import json,hashlib,subprocess,sys,re
from urllib.parse import unquote
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={p:sha(BASE/p) for p in ['summary.json','private/audit.json','private/interface_findings.json','private/example_test_plan.json']}
subprocess.run([sys.executable,'-B','-X','utf8',str(BASE/'audit_structure.py')],check=True,capture_output=True)
assert all(sha(BASE/p)==v for p,v in before.items())
d=read(BASE/'private/audit.json');s=d['summary'];gpath=next(p for p in s['frozen_hashes'] if p.endswith('graph.json'));g=read(ROOT/gpath)
assert {r['id'] for r in d['nodes']}=={n['id'] for n in g['nodes']}
assert {r['id'] for r in d['edges']}=={e['id'] for e in g['edges']}
assert {r['rule_id'] for r in d['rules']}=={n['id'] for n in g['nodes'] if n['type']=='SemanticRule'}
assert {r['branch_id'] for r in d['branches']}=={n['id'] for n in g['nodes'] if n['type']=='ApplicabilityBranch'}
assert len(d['work_packages'])==26 and len(d['earlier_rules_without_package_mapping'])==12
assert len(read(BASE/'private/example_test_plan.json'))==57
for b in d['branches']:
 assert b['nonempty'] and all(c['value_edges_match'] and c['feature_names_match'] for c in b['direct_conditions'])
assert all(sha(ROOT/p)==h for p,h in s['frozen_hashes'].items())
report=BASE/'private/report.html';h=sha(report)
subprocess.run([sys.executable,'-B','-X','utf8',str(BASE/'build_report.py')],check=True,capture_output=True)
assert sha(report)==h
links=re.findall(r'href="([^"]+)"',report.read_text(encoding='utf8'))
missing=[x for x in links if not x.startswith(('#','http:','https:')) and not (report.parent/unquote(x.split('#')[0])).is_file()]
assert not missing,missing
assert report.read_text(encoding='utf8').count('data-rule=')==56
reviews=list((BASE/'private').glob('*structure_review.md'))
assert len(reviews)==2 and all('END_STRUCTURE_REVIEW' in p.read_text(encoding='utf8') for p in reviews)
result={'inventory_reproducible':True,'report_reproducible':True,'all_current_node_edge_ids_present':True,'rules':56,'branches':57,'packages':26,'example_plan_rows':57,'frozen_inputs_unchanged':True,'missing_local_links':missing,'review_hashes':{p.name:sha(p) for p in reviews},'new_qwen_calls':0,'natural_language_or_pdf_validation':False}
(BASE/'private/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False))
