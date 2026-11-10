"""Lossless separation of execution knowledge from documentary/audit material.

Only explicitly listed administrative fields are removed. Unknown fields and
mixed linguistic notes survive; this is not linguistic re-curation.
"""
import copy
import hashlib
import json

FORMAT = 'execution_graph_with_external_audit_v1'
DOCUMENTARY_TYPES = {'SourceDocument', 'SourceSpan', 'Evidence', 'ReviewIssue'}
ADMIN_FIELDS = {
    '_refs', 'source_refs', 'primary_evidence_ids', 'supporting_evidence_ids',
    'delivery_evidence_ids', 'evidence_ids', 'decision_id', 'source_status',
    'semantic_review_status', 'citation_status', 'epistemic_status',
    'realization_basis', 'test_design', 'code_reference', 'claim_origin',
    'interpretation_origin', 'evidence_family',
}
BOILERPLATE = {
    'scope_profile': '공통 분석 계약. 문헌별 방언 사실/실현형은 해당 문헌·지역·시기·화계 profile로 별도 조건화. 자료에 없는 전체 한국어 문법을 검증된 사실로 주장하지 않음.',
    'uncertainty': '이 항목은 분석·실행 계약 설계이며 실행 성능 검증은 별도이다.',
    'limitations': '문헌 실현형의 존재와 표준 입력→실현형 매핑은 구별한다. 후자는 이번 연구의 해석이며 현대 자연스러움은 별도 사람 검토 대상이다.',
}
ADMIN_BASES = {
    'source_interpretation_with_analyzer_mapping', 'source_classification_with_label_interpretation',
    'source_interpretation_and_declared_trial_scope', 'source_interpretation',
    'implementation_scope', 'implementation_trial_scope', 'r10 final-ending scope adapter',
    'source_interpretation_and_bounded_implementation', 'implementation_scope_not_linguistic_prohibition',
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def separate(graph, version):
    """Return a new graph and a separate, exactly reversible audit archive."""
    if graph.get('storage_format') == FORMAT:
        raise ValueError('Already separated; use the immutable source version')
    if len({n['id'] for n in graph['nodes']}) != len(graph['nodes']):
        raise ValueError('Duplicate node IDs')
    if len({e['id'] for e in graph['edges']}) != len(graph['edges']):
        raise ValueError('Duplicate edge IDs')
    old_nodes = {n['id']: n for n in graph['nodes']}
    if any(e['source'] not in old_nodes or e['target'] not in old_nodes for e in graph['edges']):
        raise ValueError('Dangling source edge')
    audit = {
        'version': version, 'source_version': graph.get('version'),
        'source_canonical_sha256': digest(graph),
        'original_header': {k: copy.deepcopy(v) for k, v in graph.items() if k not in ('nodes', 'edges')},
        'node_order': [n['id'] for n in graph['nodes']],
        'edge_order': [e['id'] for e in graph['edges']],
        'documentary_nodes': [], 'documentary_edges': [],
        'original_changed_nodes': {}, 'original_changed_edges': {}, 'changes': [],
    }
    def remove(obj, key, owner, path, reason):
        value = obj.pop(key)
        audit['changes'].append({'id': owner, 'path': path + '/' + key,
                                 'reason': reason, 'value_sha256': digest(value)})
    def clean(p, n, path):
        # These keys describe where a statement came from, not its conditions.
        for key in sorted(ADMIN_FIELDS & p.keys()):
            remove(p, key, n['id'], path, 'external_audit')
        for key, text in BOILERPLATE.items():
            if p.get(key) == text:
                remove(p, key, n['id'], path, 'exact_administrative_boilerplate')
        # Retain unknown notes, limits, scope and exceptions verbatim.
        for key, value in list(p.items()):
            if key in ('_title', 'title') and value == n.get('title'):
                remove(p, key, n['id'], path, 'duplicate_node_title')
            elif key == 'id' and value == n['id']:
                remove(p, key, n['id'], path, 'duplicate_node_id')
        if path.endswith('/original_spec'):
            outer = n.get('properties', {})
            for key, other in (('_module', 'module'), ('module', 'module'), ('_role', 'role')):
                if key in p and other in outer and p[key] == outer[other]:
                    remove(p, key, n['id'], path, 'duplicate_outer_property')
        if 'instruction' in p and p.get('meaning') == p['instruction']:
            remove(p, 'meaning', n['id'], path, 'duplicate_instruction')
        if n['type'] in ('Condition', 'ProcessingScope'):
            # Keep feature/allowed/operator, field_basis and all predicates.
            if isinstance(p.get('basis'), str) and p['basis'] in ADMIN_BASES:
                remove(p, 'basis', n['id'], path, 'condition_provenance')
            if 'evidence_role' in p:
                remove(p, 'evidence_role', n['id'], path, 'condition_provenance')
        if isinstance(p.get('original_spec'), dict):
            clean(p['original_spec'], n, path + '/original_spec')
        for index, form in enumerate(p.get('forms_annotated', [])):
            if isinstance(form, dict) and 'source' in form:
                remove(form, 'source', n['id'], path + '/forms_annotated/' + str(index), 'form_provenance')
    nodes = []
    for old in graph['nodes']:
        if old['type'] in DOCUMENTARY_TYPES:
            audit['documentary_nodes'].append(copy.deepcopy(old)); continue
        node = copy.deepcopy(old)
        clean(node.setdefault('properties', {}), old, '/properties')
        if node != old:
            audit['original_changed_nodes'][old['id']] = copy.deepcopy(old)
        nodes.append(node)
    ids = {n['id'] for n in nodes}
    edges = []
    for old in graph['edges']:
        if old['source'] not in ids or old['target'] not in ids:
            audit['documentary_edges'].append(copy.deepcopy(old)); continue
        edge = copy.deepcopy(old)
        if 'origin' in edge.get('properties', {}):
            remove(edge['properties'], 'origin', edge['id'], '/properties', 'edge_provenance')
        if edge != old:
            audit['original_changed_edges'][old['id']] = copy.deepcopy(old)
        edges.append(edge)
    result = {'version': version, 'storage_format': FORMAT, 'nodes': nodes, 'edges': edges,
              'feature_schema': copy.deepcopy(graph['feature_schema'])}
    audit['execution_canonical_sha256'] = digest(result)
    # Both semantic knowledge and every source/audit record must be recoverable.
    if restore(result, audit) != graph:
        raise ValueError('Separation is not lossless')
    return result, audit


def restore(graph, audit):
    if digest(graph) != audit['execution_canonical_sha256']:
        raise ValueError('Execution graph changed or wrong archive')
    nodes = {n['id']: copy.deepcopy(n) for n in graph['nodes'] + audit['documentary_nodes']}
    edges = {e['id']: copy.deepcopy(e) for e in graph['edges'] + audit['documentary_edges']}
    nodes.update(copy.deepcopy(audit['original_changed_nodes']))
    edges.update(copy.deepcopy(audit['original_changed_edges']))
    result = {**copy.deepcopy(audit['original_header']),
              'nodes': [nodes[i] for i in audit['node_order']],
              'edges': [edges[i] for i in audit['edge_order']]}
    if digest(result) != audit['source_canonical_sha256']:
        raise ValueError('Archive changed; restoration hash mismatch')
    return result


def compact_payload(payload):
    """Remove provenance and exact repetition only; never change instructions."""
    out = copy.deepcopy(payload)
    out.pop('sources', None)
    for form in out.get('forms', []):
        if form.get('composition') == out.get('instruction'):
            form.pop('composition')
    return out


def compact_reference(reference):
    return {k: v for k, v in reference.items()
            if k not in ('source_edge_ids', 'source_span_ids', 'document_refs')}


def lookup_audit(graph, audit, node_id):
    """Explicit human/reviewer lookup; never called by the generation reader."""
    original = restore(graph, audit)
    node = next((n for n in original['nodes'] if n['id'] == node_id), None)
    if node is None:
        raise KeyError(node_id)
    edges = [e for e in original['edges'] if node_id in (e['source'], e['target'])]
    linked = {e['source'] for e in edges} | {e['target'] for e in edges}
    return {'version': graph['version'], 'node': node, 'edges': edges,
            'linked_documentary_nodes': [n for n in audit['documentary_nodes'] if n['id'] in linked]}
