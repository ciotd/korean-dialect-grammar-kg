"""Bounded actual graph retrieval. Cross references indicate relevance, not application permission."""
from .io import load_jsonl,dumps,sha
from pathlib import Path
CATALOG_QUERY='MATCH (n:KGNode {dataset_id:$dataset}) RETURN n.id AS id,n.node_type AS type,n.title AS title,n.properties_json AS properties_json ORDER BY n.id'
CLAIM_QUERY='''MATCH (g:KGNode {dataset_id:$dataset}) WHERE g.id IN $concept_ids
MATCH (c:Claim {dataset_id:$dataset})-[i:interpreted_as]->(g)
MATCH (c)-[v:analyzed_by]->(s:SourceSpan {dataset_id:$dataset})-[b:part_of_document]->(d:SourceDocument {dataset_id:$dataset})
OPTIONAL MATCH (c)-[a:documents_atom]->(atom:SourceAtom {dataset_id:$dataset})
RETURN g.id AS concept_id, properties(c) AS claim, properties(s) AS span,d.id AS document_id,
 properties(atom) AS atom,i.id AS concept_edge,v.id AS span_edge,b.id AS document_edge,a.id AS atom_edge
ORDER BY c.id,atom.id,g.id'''
NEIGHBOR_QUERY='''MATCH (g:KGNode {dataset_id:$dataset}) WHERE g.id IN $concept_ids
MATCH p=(g)-[:cross_reference|maps_to*1..2]-(a:SourceAtom {dataset_id:$dataset})
WHERE all(n IN nodes(p) WHERE n.dataset_id=$dataset)
RETURN DISTINCT g.id AS concept_id,a.id AS atom_id,properties(a) AS atom,
 [r IN relationships(p) | {id:r.id,type:type(r)}] AS path
ORDER BY concept_id,atom_id LIMIT $limit'''
def load_catalog(neo,kg,dataset):
    expected={n['id']:n for n in load_jsonl(Path(kg)/'graph/nodes.jsonl')}
    import json
    rows=neo.query(CATALOG_QUERY,{'dataset':dataset})
    actual={r['id']:{'id':r['id'],'type':r['type'],'title':r['title'],'properties':json.loads(r['properties_json'])} for r in rows}
    if actual!=expected:raise ValueError('live_KG_differs_from_frozen_JSONL')
    edges=load_jsonl(Path(kg)/'graph/edges.jsonl')
    erows=neo.query('MATCH (s:KGNode {dataset_id:$dataset})-[r]->(t:KGNode {dataset_id:$dataset}) RETURN r.id AS id,s.id AS source,type(r) AS relation,t.id AS target,r.properties_json AS properties_json',{'dataset':dataset})
    actual_edges={r['id']:{'id':r['id'],'source':r['source'],'relation':r['relation'],'target':r['target'],'properties':json.loads(r['properties_json'])} for r in erows}
    if actual_edges!={e['id']:e for e in edges} or len(erows)!=len(edges):raise ValueError('live_relationships_differ_from_frozen_JSONL')
    return actual
def retrieve(neo,mapping,dataset,neighbor_limit=1501):
    params={'dataset':dataset,'concept_ids':mapping['selected_concept_ids']}
    # Reviewed claims are never truncated. Broader exploratory neighborhoods are bounded and labeled.
    claims=neo.query(CLAIM_QUERY,params) if params['concept_ids'] else []
    nb=neo.query(NEIGHBOR_QUERY,{**params,'limit':neighbor_limit}) if params['concept_ids'] else []
    truncated=len(nb)==neighbor_limit
    return {'dataset_id':dataset,'queries':[{'cypher':CLAIM_QUERY,'parameters':params},{'cypher':NEIGHBOR_QUERY,'parameters':{**params,'limit':neighbor_limit}}],
       'claim_paths':claims,'unreviewed_neighborhood':nb,'neighborhood_limit_reached':truncated,
       'policy':'No conversion authority from cross_reference/maps_to alone; reviewed claim paths complete.'}
