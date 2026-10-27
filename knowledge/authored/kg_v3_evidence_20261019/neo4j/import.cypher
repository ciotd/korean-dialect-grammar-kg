// Neo4j 5.x / Cypher 5. No APOC. Run against a database selected by the operator.

CREATE CONSTRAINT kg_evidence_identity IF NOT EXISTS FOR (n:KGNode) REQUIRE (n.dataset_id, n.id) IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_AggregateInterface.csv' AS row
MERGE (n:KGNode:AggregateInterface {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_AnalysisConcept.csv' AS row
MERGE (n:KGNode:AnalysisConcept {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_Claim.csv' AS row
MERGE (n:KGNode:Claim {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_Construction.csv' AS row
MERGE (n:KGNode:Construction {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_Framework.csv' AS row
MERGE (n:KGNode:Framework {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_GrammarFeature.csv' AS row
MERGE (n:KGNode:GrammarFeature {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_Module.csv' AS row
MERGE (n:KGNode:Module {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_ReviewIssue.csv' AS row
MERGE (n:KGNode:ReviewIssue {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_SourceAtom.csv' AS row
MERGE (n:KGNode:SourceAtom {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_SourceDocument.csv' AS row
MERGE (n:KGNode:SourceDocument {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_SourceSpan.csv' AS row
MERGE (n:KGNode:SourceSpan {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/nodes_TechnicalResponsibility.csv' AS row
MERGE (n:KGNode:TechnicalResponsibility {dataset_id: 'kg_v3_evidence_20261019', id: row.id})
SET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_analyzed_by.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`analyzed_by` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_cites_source_span.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`cites_source_span` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_cross_reference.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`cross_reference` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_documents_atom.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`documents_atom` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_has_common_concept.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`has_common_concept` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_has_component.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`has_component` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_has_module.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`has_module` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_in_module.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`in_module` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_interpreted_as.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`interpreted_as` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_maps_to.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`maps_to` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_part_of_document.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`part_of_document` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

LOAD CSV WITH HEADERS FROM 'file:///kg_v3_evidence_20261019/edges_review_target.csv' AS row
MATCH (s:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.source}), (t:KGNode {dataset_id:'kg_v3_evidence_20261019',id:row.target})
MERGE (s)-[r:`review_target` {id:row.id}]->(t)
SET r.origin=row.origin, r.properties_json=row.properties_json;

MATCH (m:Module {dataset_id:'kg_v3_evidence_20261019'}) SET m.number=toInteger(substring(m.id,1));
