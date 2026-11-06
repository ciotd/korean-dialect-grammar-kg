"""Read-only inventory for planning; does not certify grammar or change KG."""
import collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def hashed(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/graph'
old={k:[json.loads(l) for l in (base/(k+'.jsonl')).read_text(encoding='utf-8-sig').splitlines() if l] for k in ('nodes','edges')}
candidate=ROOT/'knowledge/authored/semantic_grammar_20261106_integrated_r2/private/graph.json'
new=json.loads(candidate.read_text(encoding='utf8'))
def counts(g):
    return {'nodes':len(g['nodes']),'edges':len(g['edges']),
      'node_types':dict(collections.Counter(n['type'] for n in g['nodes'])),
      'relation_types':dict(collections.Counter(e['relation'] for e in g['edges']))}
out={'purpose':'Inventory only. No new semantic audit, Qwen calls or scenario executions.',
     'original':counts(old),'candidate':counts(new),'hashes':{
      'original_nodes':hashed(base/'nodes.jsonl'),'original_edges':hashed(base/'edges.jsonl'),
      'candidate_graph':hashed(candidate)},'new_qwen_calls':0}
(HERE/'inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:out[k] for k in ('hashes','new_qwen_calls')},ensure_ascii=False))
