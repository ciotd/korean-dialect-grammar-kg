"""Read-only recheck of the graph counts/hashes reported in inventory.json."""
import collections
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
inventory=json.loads((HERE/'inventory.json').read_text(encoding='utf-8'))
for rel,expected in inventory['hashes'].items():
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==expected, rel
for name,expected in inventory['graphs'].items():
    folder=ROOT/expected['source']
    if (folder/'nodes.jsonl').exists():
        nodes=[json.loads(l) for l in (folder/'nodes.jsonl').read_text(encoding='utf-8-sig').splitlines() if l.strip()]
        edges=[json.loads(l) for l in (folder/'edges.jsonl').read_text(encoding='utf-8-sig').splitlines() if l.strip()]
    else:
        graph=json.loads((folder/'graph.json').read_text(encoding='utf-8-sig'))
        nodes,edges=graph['nodes'],graph['edges']
    ids={n['id'] for n in nodes}
    assert len(nodes)==expected['nodes']==len(ids), name
    assert len(edges)==expected['edges'], name
    assert dict(collections.Counter(n['type'] for n in nodes))==expected['node_types'], name
    assert all(e['source'] in ids and e['target'] in ids for e in edges), name
    print(name, len(nodes),len(edges),'count/hash/reference checks passed')
coverage=json.loads((HERE/'coverage.json').read_text(encoding='utf-8'))
assert len(coverage['modules'])==12
assert len(coverage['packages'])==26
assert [x['id'] for x in coverage['packages']]==[x['id'] for x in inventory['work_packages']]
print('12 module rows and all 26 work packages present; semantic status remains an authored assessment.')
