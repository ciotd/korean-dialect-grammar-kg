"""Recompute run-level observations without inventing translation accuracy."""
import collections
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from kg_pipeline.io import read, save, dumps, sha

HERE = Path(__file__).resolve().parent

def audit(run):
    results = read(run/'private/results.json')
    cfg = read(run/'config.json')
    counts = collections.Counter()
    rules = collections.Counter()
    missing = collections.Counter()
    cases = []
    for row in results:
        rd = run/'private/records'/row['id']
        packet = read(rd/'generation_packet.json') if (rd/'generation_packet.json').exists() else {}
        traces = read(rd/'retrieval.json') if (rd/'retrieval.json').exists() else []
        actions = packet.get('verified_scope_knowledge', [])
        refs = packet.get('related_unprocessed_sources', [])
        counts['delivered_rule_instances'] += len(actions)
        counts['delivered_reference_instances'] += len(refs)
        counts['rule_payload_characters'] += len(dumps(actions))
        counts['reference_payload_characters'] += len(dumps(refs))
        counts['inputs_with_delivered_rules'] += bool(actions)
        counts['inputs_with_no_delivered_rules'] += bool(packet) and not actions
        counts['inputs_with_past_count_warning'] += 'past_marker_count_decreased' in row.get('observational_warnings', [])
        counts['inputs_with_undeclared_rule_id'] += bool(row.get('undeclared_rule_ids'))
        for a in actions:
            rules[a['rule_id']] += 1
        for tr in traces:
            for h in tr.get('unresolved', []):
                for branch in h['branches']:
                    if branch['state'] == 'unknown':
                        for check in branch['checks']:
                            if check['state'] == 'unknown': missing[check['feature']] += 1
                for rel in h['missing_relations']: missing['relation:'+rel] += 1
        raw_path = rd/'generation/response.json'
        equal = None
        if raw_path.exists():
            response = read(raw_path)
            # Transport saves the complete OpenAI response; parse the same content,
            # never normalize its output_text value.
            if 'choices' in response:
                content = response['choices'][0]['message']['content']
                try: decoded = json.loads(content)
                except (TypeError, json.JSONDecodeError): decoded = {}
            else: decoded = response
            if isinstance(decoded, dict) and 'output_text' in decoded:
                equal = row.get('output_text') == decoded['output_text']
                counts['raw_output_equal'] += equal
                counts['raw_output_unequal'] += not equal
        cases.append({'id':row['id'], 'status':row['status'],
                      'changed':bool(row.get('output_text')) and not row.get('unchanged', False),
                      'rule_ids':row.get('rule_ids', []), 'raw_output_equal':equal,
                      'warning_types':row.get('observational_warnings', []),
                      'delivered_rules':len(actions), 'delivered_references':len(refs)})
    metrics = read(run/'metrics.json') if (run/'metrics.json').exists() else {}
    hashes = read(run/'code_hashes.json')
    snapshot_ok = {p:sha((run/'code_snapshot'/p).read_bytes()) == h for p,h in hashes.items()}
    graph_ok = sha((run/'private/graph.json').read_bytes()) == cfg['graph_sha256']
    metas = [read(p) for p in (run/'private/records').rglob('meta.json')]
    return {'run_id':run.name, 'phase':cfg['phase'], 'complete':bool(metrics),
            'metrics':metrics, 'observations':dict(counts), 'delivered_rules':dict(rules),
            'unresolved_feature_or_relation_occurrences':dict(missing), 'cases':cases,
            'integrity':{'code_snapshot_hashes':snapshot_ok,'graph_snapshot_hash':graph_ok,
                         'actual_call_records':len(metas),
                         'recorded_calls_match':len(metas)==metrics.get('api_attempts') if metrics else None},
            'limits':['Counts are observations, not correctness or naturalness scores.',
                      'Rule IDs reported by the model do not prove actual application.',
                      'One unknown condition can be counted in multiple rule candidates.',
                      'Character counts are not model token counts.']}

def main():
    runs=[audit(p) for p in sorted((ROOT/'experiments/runs').glob('*_integrated_grammar_*'))
          if (p/'private/results.json').exists()]
    save(HERE/'private/results_audit.json', {'runs':runs})
    print(dumps([{'run':r['run_id'],'records':len(r['cases']),'observations':r['observations'],
                  'integrity':r['integrity']} for r in runs]))

if __name__=='__main__': main()
