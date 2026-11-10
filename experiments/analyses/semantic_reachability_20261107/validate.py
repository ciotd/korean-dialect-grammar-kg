"""Verify recorded audit accounting without invoking a model or changing KG."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def main():
    out = ROOT / read(HERE / 'latest.json')['directory']
    summary = read(out / 'reviewed_summary.json')
    rows = read(out / 'reviewed_regression50.json')
    probes = read(out / 'natural_probes.json')
    pointer = read(ROOT / 'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
    graph_path = ROOT / pointer['graph']
    graph = read(graph_path)
    rules = {n['id'] for n in graph['nodes'] if n['type'] == 'SemanticRule'}
    goals = [g for row in rows for g in row['goals']]
    neo = read(HERE / 'neo4j_latest.json')
    assert len(rows) == len({r['id'] for r in rows}) == 50
    assert len(goals) == 90
    assert dict(collections.Counter(g['status'] for g in goals)) == summary['reviewed_goal_states']
    assert all(g['rule_id'] is None or g['rule_id'] in rules for g in goals)
    assert len(probes) == 57 and {p['rule_id'] for p in probes} == rules and len(rules) == 56
    assert all(p['status'] == 'observation_ready_meaning_unchecked' for p in probes)
    assert summary['fresh_qwen_calls'] == 0 and not summary['kg_modified']
    assert hashlib.sha256(graph_path.read_bytes()).hexdigest() == neo['graph_sha256']
    assert all(neo[k] for k in ['passed','node_properties_match','edge_properties_match','old_database_unchanged','sample_branch_matches_file_reader'])
    assert len(graph['nodes']) == neo['nodes'] and len(graph['edges']) == neo['edges']
    html = (out / 'report.html').read_text(encoding='utf-8')
    assert html.count('class="sentence"') == 50
    result = {'passed': True, 'inputs': 50, 'goals': 90, 'rules': 56, 'probes': 57,
              'graph_unchanged_since_import': True, 'independent_quality_evaluation': False}
    (out / 'artifact_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__ == '__main__':
    main()
