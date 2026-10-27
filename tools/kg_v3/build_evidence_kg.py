"""Build an evidence-linked, non-executable KG from the approved design and PDFs.
No model calls, network calls, DB writes, or modifications to source documents.
Python 3.10+, pypdf. Output is a new directory; existing runs are never overwritten.
"""
import argparse, collections, csv, hashlib, json, re, sys
from pathlib import Path
from html.parser import HTMLParser
from pypdf import PdfReader

RUN = 'kg_v3_evidence_20261019'
def js(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def sha(x): return hashlib.sha256(x).hexdigest()
def dump(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def norm(x): return ''.join(x.split())
def locate(text, needle):
    chars=[(i,c) for i,c in enumerate(text) if not c.isspace()]
    joined=''.join(c for _,c in chars); target=norm(needle); at=joined.find(target)
    if at<0: raise ValueError('Exact normalized quote not found: '+needle)
    start=chars[at][0]; end=chars[at+len(target)-1][0]+1
    return start,end,text[start:end]

class Headings(HTMLParser):
    def __init__(self): super().__init__(); self.on=False; self.buf='';self.items=[]
    def handle_starttag(self,t,a):
        if t in ('h1','h2','h3'): self.on=True;self.buf=''
    def handle_data(self,d):
        if self.on:self.buf+=d
    def handle_endtag(self,t):
        if t in ('h1','h2','h3') and self.on:self.items.append(self.buf.strip());self.on=False

EXTENSIONS = {
 'has_module':(['Framework'],['Module'],'관리용 12개 모듈. 언어학적 실행 순서가 아님.'),
 'has_common_concept':(['Framework'],['AnalysisConcept','AggregateInterface','GrammarFeature','Construction'],'공통 개념 탐색용 연결'),
 'in_module':(['SourceAtom','AnalysisConcept','AggregateInterface','GrammarFeature','Construction','TechnicalResponsibility'],['Module'],'최종 설계 _module의 관리 분류'),
 'cites_source_span':(['SourceAtom','AnalysisConcept','AggregateInterface','GrammarFeature','Construction','TechnicalResponsibility'],['SourceSpan'],'기존 설계의 인용 위치. 진술 입증을 뜻하지 않음'),
 'part_of_document':(['SourceSpan'],['SourceDocument'],'PDF 1-based 위치와 해시'),
 'documents_atom':(['Claim'],['SourceAtom'],'직접 대조한 좁은 진술의 관련 기존 항목. 항목 전체 승인 아님'),
 'interpreted_as':(['Claim'],['AnalysisConcept','AggregateInterface','GrammarFeature','Construction'],'Builder의 해석적 매핑. 원문 직접 진술과 구별'),
 'review_target':(['ReviewIssue'],['SourceAtom','AnalysisConcept','AggregateInterface','GrammarFeature','Construction','TechnicalResponsibility','Claim','SourceSpan','Framework'],'불확실성·충돌 추적'),
}

def build(args):
    out=Path(args.out)
    if out.exists(): raise SystemExit('Output exists; use a new --out run directory.')
    design_dir=Path(args.design_dir) if args.design_dir else None; pdf_dir=Path(args.pdf_dir)
    design_file=Path(args.design_json) if args.design_json else design_dir/'경상방언_KG_설계데이터.json'
    design=json.loads(design_file.read_text(encoding='utf-8'))
    seeds=json.loads(Path(args.claims).read_text(encoding='utf-8'))
    pages={}; source_manifest=[]
    for src in design['sources']:
        path=pdf_dir/src['filename']; data=path.read_bytes()
        assert sha(data)==src['sha256'],f"Changed source {src['id']}"
        reader=PdfReader(path); texts=[p.extract_text() or '' for p in reader.pages]
        assert len(texts)==src['pages']
        pages[src['id']]=texts
        source_manifest.append({'id':src['id'],'filename':src['filename'],'sha256':sha(data),'pages':len(texts),
          'accessible':True,'text_extracted_pages':len(texts),'empty_pages':[i+1 for i,t in enumerate(texts) if not t.strip()],
          'nul_pages':[i+1 for i,t in enumerate(texts) if '\x00' in t],
          'current_analysis_scope':'all pages extracted and cited locations checked; semantic comparison limited to curated claim spans; prior full-reading audit is a distinct review',
          'manual_claim_pages':sorted({c['page'] for c in seeds if c['doc']==src['id']}),
          'policy':design['root']['source_policy'][src['id']]})
    atoms=design['atoms']; baseline={a['id']:a for a in atoms}; nodes={}; edges=[]; edge_ids=set(); mappings=[];issues=[]
    def node(id,typ,title,**props):
        assert id not in nodes,id
        nodes[id]={'id':id,'type':typ,'title':title,'properties':props};return id
    def edge(s,r,t,**props):
        eid='E_'+sha(js([s,r,t,props]).encode())[:24]
        assert eid not in edge_ids,(s,r,t)
        edge_ids.add(eid);edges.append({'id':eid,'source':s,'relation':r,'target':t,'properties':props})
    def issue(id,title,targets,reason,severity='확인 필요'):
        record={'id':id,'title':title,'targets':targets,'reason':reason,'severity':severity,'status':'Human Review','recommendation':'원문 또는 설계 계약을 대조하여 범위를 확인; 검증된 언어 사실로 승격하지 않음'}
        issues.append(record);node(id,'ReviewIssue',title,**{k:v for k,v in record.items() if k not in ['id','title']})
        for target in targets:edge(id,'review_target',target,origin='builder_review')
    node('COMMON_SPINE','Framework','공통 척추 · 설계 탐색 뷰',origin='implementation_navigation_extension',
      note='기존 설계에는 Spine ID가 없음. 공통 개념과 12개 모듈을 탐색하기 위한 관리 노드이며 언어학적 루트 또는 실행 순서가 아니다.',runtime_active=False)
    for m in design['root']['module_catalog']:
        mid='M'+m['number'].zfill(2);node(mid,'Module',m['name'],number=int(m['number']),original_spec=m)
        edge('COMMON_SPINE','has_module',mid,origin='root.module_catalog')
    for src in source_manifest:
        node(src['id'],'SourceDocument',src['policy']['title'],**{k:v for k,v in src.items() if k!='id'})
    for a in atoms:
        role=a['_role']; kind=a.get('kind')
        typ='SourceAtom' if role=='dialect' else 'TechnicalResponsibility' if role=='graph' else {'Feature':'GrammarFeature','Construction':'Construction','AggregateInterface':'AggregateInterface'}.get(kind,'AnalysisConcept')
        node(a['id'],typ,a['_title'],role=role,module=int(a['_module']),original_kind=kind,
          epistemic_status='inherited_design_specification',semantic_review_status='not_individually_revalidated',
          runtime_active=False,original_spec=a)
        edge(a['id'],'in_module','M'+str(a['_module']).zfill(2),origin='final_design._module',mapping_kind='inherited_administrative_assignment')
        if role=='grammar':edge('COMMON_SPINE','has_common_concept',a['id'],origin='implementation_navigation_extension')
    for i,e in enumerate(design['connections']['edges']):
        edge(e['source'],e['relation'],e['target'],origin='inherited_design',baseline_index=i,
          original_spec=e,execution_dependency=False)
    for a in atoms:
        refs=[]
        for ref in a.get('_refs',[]):
            pp=ref['page'] if isinstance(ref['page'],list) else [ref['page']]
            refs += [(ref['doc'],p,ref.get('note','')) for p in pp]
        seen=set(); reference_rows=[]
        for doc,p,note in refs:
            if (doc,p) in seen:continue
            seen.add((doc,p))
            if doc not in pages or not isinstance(p,int) or not 1<=p<=len(pages[doc]):
                issue('HR_REF_'+a['id']+'_'+str(len(seen)),'인용 위치 확인 필요',[a['id']],str((doc,p)));continue
            text=pages[doc][p-1]
            forms=a.get('output',{}).get('forms',[]) if isinstance(a.get('output'),dict) else []
            candidates=sorted([f.lstrip('-') for f in forms if isinstance(f,str) and len(f.lstrip('-'))>=2],key=len,reverse=True)
            hits=[(text.find(f),f) for f in candidates if f in text]
            anchor=hits[0][0] if hits else min(20,len(text));start=max(0,anchor-55);end=min(len(text),start+280)
            quality='damaged_extraction' if '\x00' in text[start:end] or '\ufffd' in text[start:end] else 'readable_excerpt'
            span_props=dict(doc=doc,pdf_page=p,page_system='PDF 1-based',start=start,end=end,quote=text[start:end],
                 quote_kind='automatic_context_not_semantic_evidence',extraction_quality=quality,
                 text_sha256=sha(text.encode()),document_sha256=next(s['sha256'] for s in source_manifest if s['id']==doc))
            sid='CTX_'+doc+'_'+str(p)+'_'+sha(js(span_props).encode())[:20]
            if sid not in nodes:
                node(sid,'SourceSpan',f'{doc} PDF {p} · 설계 인용 위치',**span_props)
                edge(sid,'part_of_document',doc,origin='source_locator')
            edge(a['id'],'cites_source_span',sid,origin='inherited_citation',note=note,semantic_support='not_automatically_asserted')
            reference_rows.append({'doc':doc,'pdf_page':p,'span':sid,'anchor':hits[0][1] if hits else None,
                  'anchor_status':'literal_form_found' if hits else 'page_context_only','quality':quality})
        mappings.append({'atom_id':a['id'],'role':a['_role'],'primary_module':a['_module'],'refs':reference_rows,
          'mapping_basis':'final_design._module and existing cross_reference, not new linguistic assertion','curated_claim_ids':[]})
        if a['_role']=='dialect':
            nodes[a['id']]['properties']['citation_status']='linked' if reference_rows else 'missing'
            if not reference_rows:issue('HR_NO_REF_'+a['id'],'문헌 항목의 근거 위치 없음',[a['id']],'문헌 항목이지만 유효한 PDF 위치를 연결하지 못함','우선 확인')
    # Curated claims have exact text offsets, independent from inherited broader atoms.
    for c in seeds:
        text=pages[c['doc']][c['page']-1];start,end,quote=locate(text,c['needle']);sid='SPAN_'+c['id']
        assert '\x00' not in quote and '\ufffd' not in quote,c['id']
        node(sid,'SourceSpan',f"{c['doc']} PDF {c['page']} · 직접 대조 구절",doc=c['doc'],pdf_page=c['page'],page_system='PDF 1-based',
             start=start,end=end,quote=quote,quote_kind='curated_exact_span',text_sha256=sha(text.encode()),
             document_sha256=next(s['sha256'] for s in source_manifest if s['id']==c['doc']))
        edge(sid,'part_of_document',c['doc'],origin='source_locator')
        node(c['id'],'Claim',c['summary'],claim_text=c['summary'],claim_kind=c['kind'],claim_origin='document_based',
             interpretation_origin='builder_paraphrase',source_statement=quote,scope_note=c.get('scope_note','문헌의 조사·서술 범위에 한정; 현대 경상도 전체로 자동 일반화하지 않음'),
             evidence_family=design['root']['source_policy'][c['doc']]['family'],semantic_review_status='builder_source_compared',runtime_active=False)
        edge(c['id'],'analyzed_by',sid,origin='direct_text_comparison',relation_note='문헌이 서술·분석한 위치이며 연구자가 독립 관찰한 자료라는 뜻 아님')
        for cid in c['concepts']:
            assert cid in nodes
            edge(c['id'],'interpreted_as',cid,origin='builder_mapping',mapping_kind='interpretive_not_identity',mapping_status='review_candidate')
        for aid in c['atoms']:
            assert aid in baseline
            edge(c['id'],'documents_atom',aid,origin='builder_mapping',coverage='claim_only_not_whole_atom',
                 mapping_note=c.get('mapping_notes',{}).get(aid,'이 Claim의 좁은 진술만 관련됨. 기존 항목의 모든 조건·형태·일반화를 지지하거나 승인하지 않음.'))
            nodes[aid]['properties']['semantic_review_status']='has_narrow_source_compared_claim'
            next(m for m in mappings if m['atom_id']==aid)['curated_claim_ids'].append(c['id'])
    for conflict in design['root']['known_source_conflicts']:
        issue('HR_'+conflict['id'],conflict['title'],['COMMON_SPINE'],js(conflict),'기존 문헌 충돌')
    issue('HR_YEO_OUTPUT','해여 목표와 출력 목록 불일치',['GS_ENDRULE_YO_COMPOSE','GS_ENDRULE_YEO_SCOPE'],'원문에 해여 용례 존재. 기존 목표 목록과 출력 목록의 경계를 정해야 하며 원문 부재로 처리하면 안 됨.')
    issue('HR_SOURCE_SCOPE','문헌의 위키 주장·2차 인용과 직접 조사 구분',['COMMON_SPINE'],'D03–D06은 동일 위키 근거군. 원전 재확인 없이 독립 문헌 4개로 근거 강도를 가산하지 않음.')
    issue('HR_COVERAGE','기존 721개 방언 항목의 개별 해석 검증 범위',['COMMON_SPINE'],
          '모든 기존 항목과 인용 위치는 보존·연결하였으나 이번 직접 의미 대조는 curated Claim 단위다. 그 밖의 기존 조건/형태 목록 전체가 독립 승인된 것은 아니다.')
    issue('HR_MODULE_ASSIGNMENT','기존 관리 모듈과 언어학적 적용 영역의 차이',['COMMON_SPINE'],
          '일부 동사 활용 항목도 최종 _module=2로 분류된다. 기존 관리 분류를 보존하며 원문 Claim에서 모듈1 공통 개념에도 명시적으로 연결한다. 16장 원목차와 12모듈을 혼동하지 않음.')
    schema={'version':'evidence_graph_1','baseline_entity_registry':design['roles']['graph']['entity_registry'],
      'baseline_edge_registry':design['roles']['graph']['edge_registry'],'node_types':sorted({n['type'] for n in nodes.values()}),
      'extensions':{k:{'from':v[0],'to':v[1],'meaning':v[2],'change_kind':'evidence_or_navigation_only'} for k,v in EXTENSIONS.items()},
      'additional_node_types':{'Framework':'관리·탐색용 척추','ReviewIssue':'미해결 검토 기록'},
      'property_contract':{'node':['id','type','title','properties'],'edge':['id','source','relation','target','properties'],
       'nested_properties':'canonical JSON in JSONL; Neo4j properties_json/original_spec_json strings preserve nested values without APOC',
       'claim_origins':['document_based','inference_candidate'],'inference_candidate_policy':'future candidates remain separate; no inferred knowledge asserted in this build',
       'quotes':'raw pypdf text offsets; whitespace-normalized matching only, no glyph repair. Neo4j display quote replaces NUL with U+2400; properties_json retains raw escaped NUL.',
       'source_span_context':'automatic context quote does not establish semantic support; curated_exact_span is a separate classification'},
      'runtime_policy':'Evidence/navigation graph only. No Rule instantiated, no LLM calls, no generation or mandatory demographic filtering.'}
    # Freeze source design rather than copying PDFs/full extracted text into the project.
    out.mkdir(parents=True)
    dump(out/'inputs/design.json',design);dump(out/'inputs/curated_claims.json',seeds)
    dump(out/'provenance/sources.json',source_manifest)
    htmls=[]
    if design_dir:
        for f in sorted(design_dir.rglob('*.html')):
            parser=Headings();content=f.read_text(encoding='utf-8');parser.feed(content)
            htmls.append({'path':f.relative_to(design_dir).as_posix(),'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size,
                          'headings':parser.items,'selection':'final_design' if f.parent==design_dir and '최종설계' in f.name else 'history_or_role_report'})
    elif args.html_inventory:
        htmls=json.loads(Path(args.html_inventory).read_text(encoding='utf-8'))
    dump(out/'provenance/html_inventory.json',htmls)
    dump(out/'provenance/input_manifest.json',{'run_id':RUN,'build_date_kst':'2026-10-19','design_sha256':sha(design_file.read_bytes()),
       'design_semantic_digest':design['semantic_digest'],'sources':[{'id':s['id'],'sha256':s['sha256']} for s in source_manifest],
       'html_files':len(htmls),'source_paths_are_external':True,'no_original_modifications':True})
    dump(out/'schema/schema.json',schema);dump(out/'schema/modules.json',design['root']['module_catalog']);dump(out/'schema/layers.json',design['root']['layers'])
    dump(out/'mapping/source_to_kg.json',mappings);dump(out/'reviews/human_review.json',issues)
    dump(out/'reviews/inherited_item_status.json',[{'id':n['id'],'status':n['properties']['semantic_review_status'],
       'whole_atom_semantically_approved':False} for n in nodes.values() if n['type']=='SourceAtom'])
    dump(out/'reviews/design_decisions.json',[
       {'decision':'final_design_authority','basis':'root.module_catalog + atoms._module; 16장 목차와 12개 모듈은 서로 다른 분류축','impact':'기존 모듈 지정 보존'},
       {'decision':'preserve_original_graph','basis':'911 atom IDs and all 2909 typed connections preserved','impact':'새 의미 연결은 별도 origin 필드'},
       {'decision':'minimum_schema_extension','basis':'원 계약에 출처 위치 소속과 Claim→SourceAtom 연결이 없음','impact':'8개 근거/관리 관계 및 Framework/ReviewIssue 추가; 기존40관계 변경 없음'},
       {'decision':'no_runtime_promotion','basis':'설명형 설계를 실행 규칙으로 가정하지 않음','impact':'모든 runtime_active=false; 검색과 시각화에 사용'},
       {'decision':'scope_metadata_only','basis':'사용자 연구 범위','impact':'지역·세대는 원문 속성 보존; 필수 프로필 필터 미구현'},
       {'decision':'source_vs_interpretation','basis':'원문 인용과 Builder 요약/개념매핑 구별','impact':'Claim.source_statement / claim_text / interpreted_as 분리'},
       {'decision':'deduplicate_source_spans','basis':'같은 문헌·쪽·offset·발췌·유형의 중복 위치는 동일 span','impact':'출처 발췌 공유; 항목별 검색어 anchor는 source_to_kg 매핑에 보존. 기존 원자 ID/연결 변경 없음'}])
    (out/'graph').mkdir()
    for fname,rows in [('nodes.jsonl',sorted(nodes.values(),key=lambda n:n['id'])),('edges.jsonl',sorted(edges,key=lambda e:e['id']))]:
        (out/'graph'/fname).write_text(''.join(js(r)+'\n' for r in rows),encoding='utf-8')
    dump(out/'provenance/extraction_manifest.json',{'library':'pypdf','version':__import__('pypdf').__version__,
          'page_text_hashes':{d:[sha(t.encode()) for t in ts] for d,ts in pages.items()},
          'pdfs_and_full_page_text_not_bundled':True})
    emit_neo4j(out,nodes,edges)
    # Export build configuration, not authentication or machine-specific secrets.
    dump(out/'provenance/build_scope.json',{'baseline_atoms':len(atoms),'baseline_edges':len(design['connections']['edges']),
       'curated_claims':len(seeds),'sources':len(source_manifest),'total_pdf_pages':sum(s['pages'] for s in source_manifest),
       'neo4j_live_validation':'not_performed_no_environment_provided','generation_experiment':'not_performed',
       'semantic_review_scope':'curated claims plus inherited audit findings; not independent semantic reread of all 721 atoms'})
    print(js({'out':str(out),'nodes':len(nodes),'edges':len(edges),'curated_claims':len(seeds),'html':len(htmls)}))

def csvwrite(path,rows,fields):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def emit_neo4j(out,nodes,edges):
    dest=out/'neo4j';dest.mkdir(); groups=collections.defaultdict(list); rels=collections.defaultdict(list)
    for n in nodes.values():groups[n['type']].append(n)
    for e in edges:rels[e['relation']].append(e)
    statements=['// Neo4j 5.x / Cypher 5. No APOC. Run against a database selected by the operator.',
      'CREATE CONSTRAINT kg_evidence_identity IF NOT EXISTS FOR (n:KGNode) REQUIRE (n.dataset_id, n.id) IS UNIQUE;']
    for typ,ns in sorted(groups.items()):
        assert re.fullmatch('[A-Za-z][A-Za-z0-9_]*',typ)
        fname='nodes_'+typ+'.csv'
        rows=[{'id':n['id'],'title':n['title'],'node_type':typ,'module':n['properties'].get('module',''),
           'role':n['properties'].get('role',''),'epistemic_status':n['properties'].get('epistemic_status',n['properties'].get('claim_kind','')),
           'review_status':n['properties'].get('semantic_review_status',''),'quote':n['properties'].get('quote','').replace('\x00','␀'),
           'pdf_page':n['properties'].get('pdf_page',''),'doc':n['properties'].get('doc',''),
           'properties_json':js(n['properties'])} for n in sorted(ns,key=lambda n:n['id'])]
        csvwrite(dest/fname,rows,list(rows[0]))
        statements.append(f"LOAD CSV WITH HEADERS FROM 'file:///{RUN}/{fname}' AS row\nMERGE (n:KGNode:{typ} {{dataset_id: '{RUN}', id: row.id}})\nSET n.title=row.title, n.node_type=row.node_type, n.module=toInteger(row.module), n.role=row.role, n.epistemic_status=row.epistemic_status, n.review_status=row.review_status, n.quote=row.quote, n.pdf_page=toInteger(row.pdf_page), n.doc=row.doc, n.runtime_active=false, n.properties_json=row.properties_json;")
    for rel,es in sorted(rels.items()):
        assert re.fullmatch('[A-Za-z][A-Za-z0-9_]*',rel)
        fname='edges_'+rel+'.csv'
        rows=[{'id':e['id'],'source':e['source'],'target':e['target'],'origin':e['properties'].get('origin',''),
              'properties_json':js(e['properties'])} for e in sorted(es,key=lambda e:e['id'])]
        csvwrite(dest/fname,rows,list(rows[0]))
        statements.append(f"LOAD CSV WITH HEADERS FROM 'file:///{RUN}/{fname}' AS row\nMATCH (s:KGNode {{dataset_id:'{RUN}',id:row.source}}), (t:KGNode {{dataset_id:'{RUN}',id:row.target}})\nMERGE (s)-[r:`{rel}` {{id:row.id}}]->(t)\nSET r.origin=row.origin, r.properties_json=row.properties_json;")
    (dest/'import.cypher').write_text('\n\n'.join(statements)+'\n',encoding='utf-8')
    queries=f"""// 1. Framework and all 12 modules (navigation view)
MATCH p=(s:Framework {{dataset_id:'{RUN}'}})-[:has_module]->(m:Module) RETURN p;
// 2. Source -> exact span -> claim -> common concept -> module
MATCH p=(d:SourceDocument {{dataset_id:'{RUN}'}})<-[:part_of_document]-(s:SourceSpan)<-[:analyzed_by]-(c:Claim)-[:interpreted_as]->(g)-[:in_module]->(m:Module) RETURN p LIMIT 80;
// 3. A lexical-constrained imperative and its evidence
MATCH (n:KGNode {{dataset_id:'{RUN}',id:'GS_ENDRULE_NNA_O'}}) OPTIONAL MATCH p=(n)-[r]-(neighbor) RETURN n,p LIMIT 60;
// 4. Unresolved review issues
MATCH p=(r:ReviewIssue {{dataset_id:'{RUN}'}})-[:review_target]->(n) RETURN p;
// 5. Module atomic node counts (no duplicate counting of provenance)
MATCH (n:KGNode {{dataset_id:'{RUN}'}})-[:in_module]->(m:Module) RETURN m.number,m.title,count(n) ORDER BY m.number;
// 6. Verify final database totals against validation.json
MATCH (n:KGNode {{dataset_id:'{RUN}'}}) RETURN count(n) AS node_count;
MATCH (n:KGNode {{dataset_id:'{RUN}'}})-[r]->(m:KGNode {{dataset_id:'{RUN}'}}) RETURN count(r) AS edge_count;
"""
    # Module number is also retained as a directly queryable property.
    statements.append(f"MATCH (m:Module {{dataset_id:'{RUN}'}}) SET m.number=toInteger(substring(m.id,1));")
    (dest/'import.cypher').write_text('\n\n'.join(statements)+'\n',encoding='utf-8')
    (dest/'explore.cypher').write_text(queries,encoding='utf-8')
    (dest/'README.md').write_text(f'''# Neo4j import

대상: Neo4j 5.x/Cypher 5. APOC 불필요. DB 적재는 아직 실행하지 않았습니다.

1. 이 폴더의 CSV를 **Neo4j 서버** import 디렉터리의 `{RUN}/` 하위에 복사합니다. 클라이언트 폴더가 아닙니다.
2. 서버 설정에서 로컬 CSV 읽기가 허용되어 있는지 확인합니다. Aura 등 로컬 파일 미지원 환경에는 파일 경로를 그대로 사용할 수 없습니다.
3. 대상 데이터베이스를 선택하여 `cypher-shell -d <database> -f import.cypher`를 실행합니다. 인증은 환경 설정이나 대화형 입력으로 제공합니다. 비밀번호를 스크립트에 기록하지 않습니다.
4. `explore.cypher`의 집계와 `validation/validation.json`의 통계를 대조합니다.

Import는 dataset_id+id로 MERGE합니다. 같은 산출물의 재실행은 중복을 만들지 않습니다. 다른 실행은 다른 dataset_id를 사용해야 합니다. 삭제 쿼리는 포함하지 않습니다. 병렬 import는 수행하지 마세요. 파일 적재와 Cypher 파싱의 실제 성공은 제공된 DB에서 별도 확인해야 합니다.

문헌 원자(SourceAtom)는 실행 Rule이 아닙니다. 기존 설계의 중첩 조건과 속성은 properties_json에 보존하며, 이 문자열은 실행 코드가 아닙니다. 그래프 시각화에는 title을 캡션으로 사용하세요.

공식 참고: https://neo4j.com/docs/cypher-manual/5/clauses/load-csv/ 및 https://neo4j.com/docs/cypher-manual/5/constraints/create-constraints/
''',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--design-dir');g.add_argument('--design-json');p.add_argument('--html-inventory');p.add_argument('--pdf-dir',required=True);p.add_argument('--claims',required=True);p.add_argument('--out',required=True)
    p.add_argument('--dataset-id',default=RUN);args=p.parse_args()
    if not re.fullmatch('[A-Za-z][A-Za-z0-9_]*',args.dataset_id):p.error('dataset-id must be a safe ASCII identifier')
    RUN=args.dataset_id;build(args)
