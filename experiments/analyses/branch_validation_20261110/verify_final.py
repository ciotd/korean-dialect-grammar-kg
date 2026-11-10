"""Final saved-artifact consistency; not a linguistic quality certificate."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'src')]
from validate_branches import check_delivery
from kg_pipeline.integrated import IntegratedReader
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=read(HERE/'summary.json');p=read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
reader=IntegratedReader(read(ROOT/p['graph']))
assert sha(ROOT/p['graph'])==s['graph_sha256']
assert all(sha(ROOT/name)==value for name,value in s['code_hashes'].items())
stored=read(HERE/'private/delivery_comparison.json')
checks=[check_delivery(reader,rid,pair['after']) for rid,pair in stored.items()]
assert len(checks)==56 and all(all(c.values()) for c in checks)
assert sum(len(c) for c in checks)==s['delivery_fields_checked']==443
assert len(read(HERE/'private/branch_payloads.json'))==s['branch_payloads']==57
assert s['logic_passed']==990 and s['decisions_unchanged']
natural=read(HERE/'private/natural_observations.json');assert len(natural)==171
assert len({(r['branch_id'],r['category']) for r in natural})==171
for row in natural:
    for a in row['anchors']:
        assert row['text'][slice(*a['construction_span'])]==a['construction_text']
        assert all(row['text'][slice(*span)]==row['target'] for span in a['reviewer_target_spans'])
assert read(HERE/'test_summary.json')['passed']
assert read(HERE/'private/browser_qa.json')['passed']
replay=read(HERE/'delivery_replay_summary.json')
assert replay['before_matches_saved']==replay['replayed']==replay['unchanged_selection']==49
assert replay['after_actions']==replay['before_actions']==58
reviews=['claude_review.md','codex_review.md','claude_followup.md','codex_followup.md']
assert all((HERE/'private'/name).stat().st_size>1000 for name in reviews)
result={'passed':True,'graph_unchanged':True,'saved_payload_checks':443,'natural_candidates':171,
        'automated_tests':read(HERE/'test_summary.json')['tests'],'qwen_calls':0,
        'review_hashes':{name:sha(HERE/'private'/name) for name in reviews},
        'report_sha256':sha(HERE/'private/report.html')}
(HERE/'private/artifact_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
