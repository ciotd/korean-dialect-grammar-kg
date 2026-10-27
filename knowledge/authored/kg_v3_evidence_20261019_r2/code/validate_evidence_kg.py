"""Independent structural, source-span and CSV roundtrip validation. No DB writes."""
import argparse, collections, csv, hashlib, json, sys
from pathlib import Path

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]
def digest(x):return hashlib.sha256(x).hexdigest()
def validate(root,pdf_dir=None):
    root=Path(root); ns=rows(root/'graph/nodes.jsonl');es=rows(root/'graph/edges.jsonl');nodes={n['id']:n for n in ns}
    design=read(root/'inputs/design.json');schema=read(root/'schema/schema.json');sources=read(root/'provenance/sources.json')
    errors=[];warnings=[];checks=[]
    def check(name,ok,details=None):
        checks.append({'name':name,'passed':bool(ok),'details':details})
        if not ok:errors.append(name)
    check('unique_node_ids',len(nodes)==len(ns));check('unique_edge_ids',len({e['id'] for e in es})==len(es))
    dangling=[e['id'] for e in es if e['source'] not in nodes or e['target'] not in nodes]
    check('reference_integrity',not dangling,dangling)
    triples=collections.Counter((e['source'],e['relation'],e['target']) for e in es)
    check('no_duplicate_relationship_triples',all(c==1 for c in triples.values()))
    original={a['id']:a for a in design['atoms']}
    check('all_original_atoms_losslessly_preserved',all(aid in nodes and nodes[aid]['properties'].get('original_spec')==a for aid,a in original.items()))
    inherited=sorted([e for e in es if e['properties'].get('origin')=='inherited_design'],key=lambda e:e['properties']['baseline_index'])
    check('all_original_edges_losslessly_preserved',[e['properties']['original_spec'] for e in inherited]==design['connections']['edges'])
    check('twelve_modules',sorted(n['id'] for n in ns if n['type']=='Module')==['M'+str(i).zfill(2) for i in range(1,13)])
    memberships=collections.defaultdict(list)
    for e in es:
        if e['relation']=='in_module':memberships[e['source']].append(e['target'])
    check('one_original_module_assignment_per_atom',all(memberships[a['id']]==['M'+str(a['_module']).zfill(2)] for a in original.values()))
    check('no_runtime_rules_or_inferred_facts',not any(n['type']=='Rule' or n['properties'].get('runtime_active') is True or n['properties'].get('claim_origin')=='inference_candidate' for n in ns))
    contracts={r['name']:(r['from'].split('|'),r['to'].split('|')) for r in schema['baseline_edge_registry']}
    contracts.update({r:(c['from'],c['to']) for r,c in schema['extensions'].items()})
    invalid=[]
    for e in es:
        if e['relation'] not in contracts:invalid.append({'id':e['id'],'reason':'unregistered relation'});continue
        if e['source'] not in nodes or e['target'] not in nodes:continue
        frm,to=contracts[e['relation']]
        if nodes[e['source']]['type'] not in frm or nodes[e['target']]['type'] not in to:
            invalid.append({'id':e['id'],'source':e['source'],'relation':e['relation'],'target':e['target'],'reason':'domain/range mismatch'})
    check('relationship_domain_range',not invalid,invalid)
    counts={s['id']:s['pages'] for s in sources}
    spans=[n for n in ns if n['type']=='SourceSpan'];claims=[n for n in ns if n['type']=='Claim']
    span_keys=[(n['properties']['doc'],n['properties']['pdf_page'],n['properties']['start'],n['properties']['end'],n['properties']['quote_kind']) for n in spans]
    check('no_duplicate_source_spans',len(span_keys)==len(set(span_keys)))
    check('valid_pdf_page_ranges',all(n['properties']['doc'] in counts and 1<=n['properties']['pdf_page']<=counts[n['properties']['doc']] for n in spans))
    check('curated_claims_have_exact_spans',all(any(e['source']==c['id'] and e['relation']=='analyzed_by' and nodes[e['target']]['properties'].get('quote_kind')=='curated_exact_span' for e in es) for c in claims))
    check('claim_quote_equals_linked_span',all(c['properties']['source_statement']==nodes[e['target']]['properties']['quote'] for c in claims for e in es if e['source']==c['id'] and e['relation']=='analyzed_by'))
    check('excerpt_lengths_and_source_digests',all(p['end']-p['start']==len(p['quote']) and p['document_sha256']==next(s['sha256'] for s in sources if s['id']==p['doc']) for p in (s['properties'] for s in spans)))
    check('interpretation_not_source_identity',all(e['properties'].get('mapping_kind')=='interpretive_not_identity' for e in es if e['relation']=='interpreted_as'))
    cited={e['source'] for e in es if e['relation']=='cites_source_span'}
    check('every_source_atom_has_citation',all(a['id'] in cited for a in ns if a['type']=='SourceAtom'))
    quote_errors=[]
    if pdf_dir:
        from pypdf import PdfReader
        texts={}
        for s in sources:
            p=Path(pdf_dir)/s['filename'];check('source_hash_'+s['id'],digest(p.read_bytes())==s['sha256'])
            texts[s['id']]=[p.extract_text() or '' for p in PdfReader(p).pages]
        for n in spans:
            p=n['properties'];text=texts[p['doc']][p['pdf_page']-1]
            if p['start']<0 or p['end']<p['start'] or p['end']>len(text) or text[p['start']:p['end']]!=p['quote'] or digest(text.encode())!=p['text_sha256']:
                quote_errors.append(n['id'])
        check('all_source_excerpt_offsets_and_hashes',not quote_errors,quote_errors)
    else:warnings.append('이 실행에서는 PDF 재추출 대조를 하지 않음. --pdf-dir로 검증 가능.')
    csvnodes={};csvedges={}
    for p in (root/'neo4j').glob('nodes_*.csv'):
        for r in csv.DictReader(p.read_text(encoding='utf-8').splitlines(keepends=True)):
            csvnodes[r['id']]={'id':r['id'],'title':r['title'],'type':r['node_type'],'properties':json.loads(r['properties_json'])}
    for p in (root/'neo4j').glob('edges_*.csv'):
        relation=p.stem[len('edges_'):]
        for r in csv.DictReader(p.read_text(encoding='utf-8').splitlines(keepends=True)):
            csvedges[r['id']]={'id':r['id'],'source':r['source'],'target':r['target'],'relation':relation,'properties':json.loads(r['properties_json'])}
    check('csv_nodes_lossless_roundtrip',csvnodes==nodes)
    check('csv_edges_lossless_roundtrip',csvedges=={e['id']:e for e in es})
    check('csv_files_contain_no_nul_bytes',all(b'\x00' not in p.read_bytes() for p in (root/'neo4j').glob('*.csv')))
    degree=collections.Counter();adj=collections.defaultdict(set)
    for e in es:degree[e['source']]+=1;degree[e['target']]+=1;adj[e['source']].add(e['target']);adj[e['target']].add(e['source'])
    isolated=sorted(n for n in nodes if degree[n]==0);check('no_isolated_nodes',not isolated,isolated)
    remaining=set(nodes);sizes=[]
    while remaining:
        stack=[remaining.pop()];size=0
        while stack:
            v=stack.pop();size+=1
            for t in adj[v]&remaining:remaining.remove(t);stack.append(t)
        sizes.append(size)
    # Statistics distinguish semantic/design edges from added provenance/navigation edges.
    module_stats=[]
    for i in range(1,13):
        ids={a['id'] for a in design['atoms'] if a['_module']==i}
        direct_claims={e['source'] for e in es if e['relation']=='interpreted_as' and e['target'] in ids}
        module_stats.append({'module':i,'title':design['root']['module_catalog'][i-1]['name'],'atoms':len(ids),'curated_claims':len(direct_claims),
         'by_role':dict(collections.Counter(original[id]['_role'] for id in ids)),
         'baseline_internal_edges':sum(e['source'] in ids and e['target'] in ids for e in design['connections']['edges']),
         'baseline_cross_module_incident_edges':sum((e['source'] in ids)!=(e['target'] in ids) for e in design['connections']['edges'])})
    matrix=[]
    mapping=read(root/'mapping/source_to_kg.json')
    for source in sources:
        did=source['id'];aa=[m for m in mapping if m['role']=='dialect' and any(r['doc']==did for r in m['refs'])]
        matrix.append({'doc':did,'source_atoms':len(aa),'by_primary_module':dict(collections.Counter(m['primary_module'] for m in aa)),
         'curated_claims':sum(c['id'].startswith('C_'+did+'_') for c in claims),
         'linked_pages':len({r['pdf_page'] for m in mapping for r in m['refs'] if r['doc']==did})})
    stats={'nodes':len(ns),'edges':len(es),'baseline_atoms':len(original),'baseline_edges':len(inherited),
      'node_types':dict(collections.Counter(n['type'] for n in ns)),'relations':dict(collections.Counter(e['relation'] for e in es)),
      'modules':module_stats,'sources':matrix,'components':sorted(sizes,reverse=True),'isolated':isolated,
      'source_families':len({s['policy']['family'] for s in sources}),
      'cross_module_counting_note':'incident counts count an edge once for each endpoint module; do not sum as global edge count',
      'citation_counting_note':'same atom can cite several sources; source columns are not mutually exclusive',
      'curated_claims':len(claims),'review_issues':sum(n['type']=='ReviewIssue' for n in ns),
      'inherited_semantic_review':dict(collections.Counter(n['properties'].get('semantic_review_status') for n in ns if n['type']=='SourceAtom'))}
    return {'passed':not errors,'errors':errors,'warnings':warnings,'checks':checks,'stats':stats,
       'neo4j_execution':'NOT_RUN: no DB connection supplied','semantic_correctness':'not established by automatic checks',
       'pdf_checks_performed':bool(pdf_dir)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--pdf-dir');a=p.parse_args()
    result=validate(a.root,a.pdf_dir);dest=Path(a.root)/'validation';dest.mkdir(exist_ok=True)
    (dest/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'errors':result['errors'],'nodes':result['stats']['nodes'],'edges':result['stats']['edges']},ensure_ascii=False))
    sys.exit(0 if result['passed'] else 1)
