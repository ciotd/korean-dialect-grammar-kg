// 1. Framework and all 12 modules (navigation view)
MATCH p=(s:Framework {dataset_id:'kg_v3_evidence_20261019_r2'})-[:has_module]->(m:Module) RETURN p;
// 2. Source -> exact span -> claim -> common concept -> module
MATCH p=(d:SourceDocument {dataset_id:'kg_v3_evidence_20261019_r2'})<-[:part_of_document]-(s:SourceSpan)<-[:analyzed_by]-(c:Claim)-[:interpreted_as]->(g)-[:in_module]->(m:Module) RETURN p LIMIT 80;
// 3. A lexical-constrained imperative and its evidence
MATCH (n:KGNode {dataset_id:'kg_v3_evidence_20261019_r2',id:'GS_ENDRULE_NNA_O'}) OPTIONAL MATCH p=(n)-[r]-(neighbor) RETURN n,p LIMIT 60;
// 4. Unresolved review issues
MATCH p=(r:ReviewIssue {dataset_id:'kg_v3_evidence_20261019_r2'})-[:review_target]->(n) RETURN p;
// 5. Module atomic node counts (no duplicate counting of provenance)
MATCH (n:KGNode {dataset_id:'kg_v3_evidence_20261019_r2'})-[:in_module]->(m:Module) RETURN m.number,m.title,count(n) ORDER BY m.number;
// 6. Verify final database totals against validation.json
MATCH (n:KGNode {dataset_id:'kg_v3_evidence_20261019_r2'}) RETURN count(n) AS node_count;
MATCH (n:KGNode {dataset_id:'kg_v3_evidence_20261019_r2'})-[r]->(m:KGNode {dataset_id:'kg_v3_evidence_20261019_r2'}) RETURN count(r) AS edge_count;
