"""Source-first work atlas. Page intersections and routing are NEVER semantic approval."""
from __future__ import annotations
import collections, csv, hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2'
CACHE=Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit')
PDF=Path('C:/Users/ciot28/Downloads/1')
DESIGN_TYPES={'SourceAtom','Construction','AnalysisConcept','GrammarFeature','AggregateInterface','TechnicalResponsibility'}
COMMON_WORK={
 'F00':'G_ANALYSIS_ALTERNATIVES G_ANALYSIS_UNSUPPORTED G_CLAUSE_COMPONENT G_CLAUSE_ELLIPSIS G_CLAUSE_HEAD G_CLAUSE_SCOPE G_END_COMPOSITE G_END_FINAL G_END_SLOT G_FEATURE_UNKNOWN G_NOUN_PROPER G_NP_HEAD G_TAG_MAPPING G_TOKEN_ALIGNMENT G_VERB_ARGFRAME G_VERB_COMPOUND G_VERB_DERIVED',
 'F01':'G_VERB_ALLOMORPH G_VERB_INFLECTION G_VERB_STEM G_REALIZATION_ALLOMORPH G_REALIZATION_ALLOWLIST G_ADJ_EXISTENCE',
 'F02':'G_BOUND_NOUN_GEOT',
 'F08':'G_REGISTER_MAP G_REGISTER_VARIATION',
 'F09':'G_CASE_ROLE G_PARTICLE_COORD G_PARTICLE_DATIVE G_PARTICLE_INSTRUMENT G_PARTICLE_OBJECT G_PARTICLE_STACK G_PARTICLE_SUBJECT G_REALIZATION_PARTICLE',
 'F10':'G_PARTICLE_COMPARE',
 'F11':'G_PRON_REFLEXIVE',
 'F12':'G_NUMERAL_COUNTER G_LEX_DATE',
 'F13':'G_END_CAUSE G_END_CONDITIONAL',
 'F14':'G_CLAUSE_COORD G_CLAUSE_LINK G_END_CONCESSION G_END_SEQUENCE G_END_SIMULTANEOUS',
 'F16':'G_ADJ_ADNOMINAL G_CLAUSE_EMBED G_CLAUSE_NOMINAL G_END_NOMINAL',
 'F17':'G_GE_DEGREE G_GE_LIMIT G_GE_PURPOSE G_GE_CAUSATIVE_HA G_GE_HA_ORDER G_GE_HA_PROMISE G_GE_HA_PROPOSAL G_MAIN_BECOME G_ADJ_ADVERB',
 'F20':'G_VOICE_FRAME',
 'F22':'G_LEX_ONOMATOPOEIA G_LEX_PROTECTED G_LEX_RETRIEVE G_LEX_SELECTION G_LEX_SENSE',
 'F23':'G_REALIZATION_CONTEXT G_REALIZATION_CONTRACTION G_REALIZATION_ORTHO G_REALIZATION_PROSODY',
 'F25':'G_INVARIANT_AUDIT'}
COMMON_ROUTE={i:[f] for f,ids in COMMON_WORK.items() for i in ids.split()}

def read(p): return json.loads(p.read_text(encoding='utf8'))
def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def jsonl(p): return [json.loads(l) for l in p.read_text(encoding='utf8').splitlines() if l.strip()]

def normalize_refs(spec):
    out=set()
    refs=spec.get('source_refs',spec.get('_refs',[]))
    for r in refs:
        doc=r.get('doc',r.get('document_id',r.get('doc_id')))
        pages=r.get('pdf_pages',r.get('pdf_page',r.get('page',[])))
        if isinstance(pages,int): pages=[pages]
        for page in pages: out.add((doc,page))
    return sorted(out)

# These assign REVIEW WORK, not grammar rules or executable acceptance conditions.
def route(n):
    i=n['id'];p=n['properties'];m=p.get('module');t=n['type']
    if t=='TechnicalResponsibility': return ['F25'],'technical_role'
    if i in COMMON_ROUTE:return COMMON_ROUTE[i],'main_title_checked_common_contract_scope'
    if i.startswith('GS_PROFILE_'):return ['F24','F08'],'id_family'
    if i.startswith('GS_FEATURE_'):return ['F00'],'shared_feature'
    if i.startswith('GS_CONJ_'):return ['F01'],'id_family'
    if i.startswith('GS_GEORO_'):return ['F17'],'id_family'
    if i.startswith('GS_PHON_'):return ['F23'],'id_family'
    if i.startswith('GS_LEX_'):return ['F22'],'id_family'
    if i.startswith(('GS_NUM_','GS_HUMAN_COUNTER','GS_TIMELEX')):return ['F12'],'id_family'
    if i.startswith('GS_END_'):
        for part,f in [('Q','F03'),('DECL','F04'),('IMP','F05'),('HORT','F06')]:
            if i.startswith('GS_END_'+part+'_'):return [f],'id_family'
    if i.startswith('GS_ENDRULE_'):
        tail=i.removeprefix('GS_ENDRULE_')
        exact={'DA_GO_REQUEST':['F05'],'HGE_SI':['F05','F08'],'ISO_IMP':['F05','F08'],
          'ISO_OPTIONAL':['F05','F08'],'JIYE_HORT_GAP':['F06','F08'],'KKUMA_PROM':['F07'],
          'NNA_O':['F05','F01'],'RAE_BO':['F05','F21'],'SE_AGENTS':['F05','F06'],
          'SIYO_HORT_GAP':['F06','F08'],'JI_ASSERT':['F04','F03']}
        if tail in exact:return exact[tail],'main_title_checked_work_assignment'
        if tail.startswith('Q_') or 'JI_CONFIRM' in tail:return ['F03'],'id_family'
        if tail.startswith('IMP_'):return ['F05'],'id_family'
        if tail.startswith('HORT_'):return ['F06'],'id_family'
        if tail.startswith(('PROMISE','INTENT','GEOT','KKI','M_SI','SI_INTENT')):return ['F07'],'id_family'
        if 'COP' in tail:return ['F02','F04'],'id_family'
        if tail.startswith(('YO_','YEO_','SIP_','NI_','I_DEO','EXIST','SI_')):return ['F08','F04'],'id_family'
        return ['F04'],'ending_rule_draft_needs_individual_check'
    if i.startswith('GS_PART_'):
        cat=i.split('_')[2]
        return (['F09'] if cat in {'NOM','ACC','GEN','DAT','COMIT','INSTR'} else ['F10']),'id_family'
    if i.startswith('GS_CONNECT_'):
        cat=i.split('_')[2]
        f={'QUOTE':'F16','CAUSE':'F13','COND':'F13','REASON':'F13','INTENT':'F15','NEG':'F19'}.get(cat,'F14')
        return [f],'id_family'
    if i.startswith('GS_HAM_'):
        x=i.removeprefix('GS_HAM_')
        if x in {'LOC','OBJ'}:return ['F11'],'main_title_checked_work_assignment'
        if x=='QUOTE':return ['F16'],'main_title_checked_work_assignment'
        if x=='Q' or x.startswith('Q_'):return ['F03'],'functional_family_across_legacy_module'
        for prefixes,f in [
          (('P1','P2','P3','REFL','WH'),'F11'),(('NOM','ACC','GEN','LOCATIVE','DAT','COMIT','INSTR','CAPACITY','VOC'),'F09'),
          (('ONLY','TOPIC','SIMIL','MEAS','MIN'),'F10'),(('DECL','EXCLAIM'),'F04'),(('IMP'),'F05'),(('HORT'),'F06'),
          (('QUOTE','ADN'),'F16'),(('PRESENT','PAST','FUTURE','TAM'),'F18'),(('NEG'),'F19'),(('CAUSE','PASS'),'F20'),(('AUX'),'F21'),(('ADV'),'F22'),
          (('CONDITION','GEOLLANG','REASON','BACKGROUND'),'F13'),(('INTENT','MOVE_PURPOSE','DESIRE'),'F15'),
          (('COORD','CONCESS','CHANGE','SCALE','AS_KNOW'),'F14')]:
            if x.startswith(prefixes):return [f],'functional_family_across_legacy_module'
        return [],'unassigned_needs_review'
    # Common concepts are proposals/contracts, not automatically attested dialect facts.
    if i.startswith(('G_QUOTE','G_CLAUSE_REL','G_END_ADN')):return ['F16','F00'],'common_contract_name'
    if i.startswith('G_COP'):return ['F02','F00'],'common_contract_name'
    if i.startswith('G_AUX'):return ['F21','F00'],'common_contract_name'
    if i.startswith('G_TAM'):return ['F18','F00'],'common_contract_name'
    if i.startswith('G_NEG'):return ['F19','F00'],'common_contract_name'
    if i.startswith(('G_CAUS','G_PASS')):return ['F20','F00'],'common_contract_name'
    if i.startswith(('G_Q_','G_WH')):return ['F03','F00'],'common_contract_name'
    if t in {'AggregateInterface','GrammarFeature'}:return ['F00'],'shared_contract'
    return [],'unassigned_needs_review'

def section_key(s):return s['doc']+':'+s['section']

def section_assignment(s,assignments):
    return assignments.get(section_key(s),{'work_packages':[],'content_role':'unassigned_needs_review','priority':'unknown','basis':'new section requires review'})

MAIN_READ={
 'D01':{'full_current':[1,2,3,4,6,7,8,9], 'previous':[]},
 'D02':{'full_current':[5,6,7,8,9,28,39,40], 'previous':[142,143,144,145,146]},
 'D03':{'full_current':[1,2,3], 'previous':[]},
 'D04':{'full_current':[1,2,3], 'previous':[8,9,10,11,12,21,22]},
 'D05':{'full_current':[1,2,3], 'previous':[]},
 'D06':{'full_current':list(range(1,9)), 'previous':[]},
 'D07':{'full_current':[1,2,3,4,12], 'previous':[]}}


ISSUES=[
 {'id':'I01','location':'기존 SourceSpan 655개','problem':'자동 발췌와 검증된 근거가 섞여 보임','evidence':'626개가 automatic_context_not_semantic_evidence; 29개만 curated_exact_span','fix':'발췌는 찾아갈 위치로만 사용. 정제 때 본문·표 머리글·주석을 읽어 주장별 의미 근거를 작성','families':['F25'],'status':'확인: 구조'},
 {'id':'I02','location':'기존 cross_reference 2,841개','problem':'참고 연결이 조건 실행 관계처럼 보임','evidence':'전부 execution_dependency=False. G_TAM_PAST의 관계 이름은 original_spec 안의 설계 선언','fix':'속성에 선언 / 실제 관계 / 실행 코드 / 시험 통과를 분리. 정제된 조건만 별도 버전으로 구현','families':['F00','F25'],'status':'확인: 구조'},
 {'id':'I03','location':'M12의 GS_HAM_NEG_AN·GS_HAM_AUX_SERVICE 등','problem':'관리 분류와 문법 기능의 조회 경로가 다름','evidence':'함양 관찰이 지역·변이 모듈에 소속; 부정·수혜 등의 기능은 original_spec에 있음','fix':'기존 모듈 보존 + 부정·보조용언 등 기능별 작업묶음에 중복 연결. 실제 조회는 후속 시험','families':['F19','F21','F24'],'status':'확인: 소속 / 영향은 후속 시험'},
 {'id':'I04','location':'D02 PDF 202–204 / GS_END_DECL_YE_08','problem':'-께예 목록만으로 약속 기능을 확정할 수 없음','evidence':'Codex가 p202의 간께예 용례와 p203 목록, p204 분포를 대조. 표의 분류와 개별 기능을 구별해야 함','fix':'앞뒤 논의와 표를 다시 읽고 동형 용법을 분리. 약속·이유 등을 근거 없이 하나로 합치지 않음','families':['F04','F07','F13'],'status':'검토 후보: 개별 의미 판정 필요'},
 {'id':'I05','location':'D07 PDF 12 주10 / GS_HAM_TOPIC_GAP','problem':'미사용 보고를 조사 삭제 지시로 바꿀 위험','evidence':'제보자의 미사용 보고와 보리는·팣은·나는 기록을 주10이 함께 제시하며 재확인을 요구','fix':'보고와 반례를 함께 연결. 은/는 삭제를 허용하는 규칙으로 승격하지 않음','families':['F10','F24'],'status':'확인: 총괄 본문 대조'},
 {'id':'I06','location':'D04 PDF 3 / D06','problem':'문헌의 형태소 보존 표기와 목표 관습 표기가 다름','evidence':'D04는 밥뭇나 대신 밥 무웄나를 적는다고 설명. 사용자 목표는 관습 표기 우선','fix':'문법 지식과 출력 표기를 분리. 다음 표기 정제 때 실제 사용자 선호를 별도 기록','families':['F01','F23'],'status':'확인: 총괄 본문 대조'},
 {'id':'I07','location':'D02 PDF 28 주7 / 기존 출처 시기 속성','problem':'기존 1978–1984 설명과 원문 1차 사업 1979–1985가 다름','evidence':'주7은 1차 사업 1979–1985와 증보본 배제를 명시. 이것이 개별 녹음일 전체를 뜻하지는 않음','fix':'출처 메타데이터 교정 후보로 기록. 사업 기간과 개별 채록 기간을 구별; 기존 파일은 보존','families':['F24'],'status':'확인: 총괄 본문 대조'},
 {'id':'I08','location':'D03–D06 및 논문 재인용','problem':'PDF 수를 독립 증거 수로 오인할 수 있음','evidence':'4개 PDF는 같은 위키 계열; D02 주162 등은 다른 연구 재인용','fix':'파일·문헌 계열·원저 관계 분리. 7개 파일의 일치를 독립 7회 검증으로 세지 않음','families':['F24'],'status':'확인: 계통 / 원저별 중복은 미확정'},
 {'id':'I09','location':'D02의 서술·명령 등 통사·의미 설명 부분','problem':'목록은 배정했지만 결합 조건 본문은 충분히 재검토하지 못함','evidence':'Claude는 다수 장절에서 목록표만 읽었다고 보고; 조건 재구축의 핵심 본문은 남음','fix':'각 묶음의 본문+표+주석 전체 읽기를 종료 조건으로 지정. 목록 분류를 정제 완료로 세지 않음','families':['F03','F04','F05','F06','F07','F08'],'status':'확인: 검토 범위 한계'}
]

def build():
    ns=jsonl(BASE/'graph/nodes.jsonl');es=jsonl(BASE/'graph/edges.jsonl')
    design=[n for n in ns if n['type'] in DESIGN_TYPES]
    sources=read(BASE/'provenance/sources.json');source_by={s['id']:s for s in sources}
    reviewer=read(HERE/'private/reviewer_work/claude/source_sections.json')
    source_assignments=read(HERE/'source_assignments.json')
    packs=read(HERE/'work_packages.json');pack_by={p['id']:p for p in packs}
    page_to_ids=collections.defaultdict(set);rows=[];invalid=[]
    for n in design:
        p=n['properties'];spec=p.get('original_spec',{})
        refs=normalize_refs(spec);families,basis=route(n)
        for d,pg in refs:
            if d not in source_by or type(pg)!=int or not 1<=pg<=source_by[d]['pages']:invalid.append([n['id'],d,pg])
            else:page_to_ids[(d,pg)].add(n['id'])
        rows.append({'legacy_id':n['id'],'title':n['title'],'type':n['type'],'role':p.get('role'),
          'legacy_module':p.get('module'),'legacy_kind':p.get('original_kind'),
          'work_packages':families,'routing_basis':basis,'routing_status':'provisional_work_assignment_not_semantic_validation',
          'context_links':(['F08'] if n['id'].startswith('GS_END_') else [])+(['F24'] if n['id'].startswith('GS_HAM_') else []),
          'references':[{'doc':d,'pdf_page':pg} for d,pg in refs],
          'reference_state':'declared_reference' if refs else 'design_contract_without_source_reference',
          'prior_semantic_status':p.get('semantic_review_status'),
          'semantic_validation_this_stage':'not_performed',
          'condition_property_present':bool(spec.get('match')),
          'condition_edge_validation':'not_certified_by_this_map',
          'runtime_validation':'not_tested_this_stage'})
    row_by={r['legacy_id']:r for r in rows}
    sections=[];links=[]
    for number,s in enumerate(reviewer['sections'],1):
        sid=section_key(s);matched=set()
        for pg in range(s['pdf_start'],s['pdf_end']+1):matched.update(page_to_ids[(s['doc'],pg)])
        reference_families=sorted({f for i in matched for f in row_by[i]['work_packages']})
        assignment=section_assignment(s,source_assignments);families=assignment['work_packages']
        atom_candidates=[i for i in matched if row_by[i]['type']=='SourceAtom']
        disposition=('candidate_links_require_semantic_reading' if atom_candidates else 'possible_gap_or_concept_only_requires_reading') if assignment['content_role'].startswith('grammar') else 'scope_or_reference_material_retained'
        sections.append({**s,'id':sid,'display_index':number,'legacy_candidates':sorted(matched),'work_packages':families,
            'content_role':assignment['content_role'],'refinement_priority':assignment['priority'],
            'source_atom_candidates':atom_candidates,
            'reference_derived_work_packages':reference_families,
            'source_assignment_basis':'main reviewed section summary/TOC; proposed work scope, not claim validation',
            'mapping_status':'page_intersection_only','scope_disposition':disposition,
            'reading_attribution':'Claude self-reported; not a whole-source semantic certification',
            'pdf_visual_checked_this_stage':False})
        for i in sorted(matched):links.append({'section_id':sid,'legacy_id':i,'relation':'page_reference_candidate','semantic_support':'unverified'})
    pages=[];source_stats=[];expected=read(BASE/'provenance/extraction_manifest.json')['page_text_hashes']
    for s in sources:
        d=s['id'];cached=read(CACHE/f'{d}.json')
        pdf=PDF/s['filename'];refs=set()
        hashes=[hashlib.sha256(p['text'].encode()).hexdigest() for p in cached]
        for pg in cached:
            p=pg['page'];sect=[q for q in sections if q['doc']==d and q['pdf_start']<=p<=q['pdf_end']]
            ids=sorted(page_to_ids[(d,p)]);refs.update(ids)
            pages.append({'doc':d,'pdf_page':p,'section_ids':[q['id'] for q in sect],'legacy_ids':ids,
              'text_sha256':hashlib.sha256(pg['text'].encode()).hexdigest(),
              'text_chars':len(pg['text']),'has_nul':'\0' in pg['text'],
              'main_full_text_read_this_stage':p in MAIN_READ[d]['full_current'],
              'main_prior_targeted_read':p in MAIN_READ[d]['previous'],
              'reviewer_section_read_scopes':[{'section_id':q['id'],'scope':q['read_scope'],'note':q['read_note']} for q in sect],
              'semantic_validation':'pending_claim_level_refinement'})
        source_stats.append({'id':d,'title':s['policy']['title'],'pages':s['pages'],
          'family':s['policy']['family'],'pdf_sha256':sha(pdf) if pdf.exists() else None,
          'pdf_matches_original':pdf.exists() and sha(pdf)==s['sha256'],
          'cache_sha256':sha(CACHE/f'{d}.json'),'cache_matches_extraction':hashes==expected[d],
          'source_sections':sum(q['doc']==d for q in sections),'referencing_legacy_items':len(refs),
          'referenced_pages':sum(bool(page_to_ids[(d,p)]) for p in range(1,s['pages']+1)),
          'main_current_read_pages':MAIN_READ[d]['full_current'],
          'coverage_claim':'page inventory and section map; not full semantic review'})
    for p in packs:
        members=[r for r in rows if p['id'] in r['work_packages']]
        p['legacy_ids']=[r['legacy_id'] for r in members]
        p['source_atom_count']=sum(r['type']=='SourceAtom' for r in members)
        p['common_contract_count']=sum(r['type'] not in ('SourceAtom','TechnicalResponsibility') for r in members)
        p['technical_count']=sum(r['type']=='TechnicalResponsibility' for r in members)
        p['section_ids']=[s['id'] for s in sections if p['id'] in s['work_packages']]
        p['status']='work_scope_draft_not_refined'
    node_ids={n['id'] for n in ns}
    gap_candidates=[]
    for s in sections:
        atom_ids=[i for i in s['legacy_candidates'] if row_by[i]['type']=='SourceAtom']
        if s['content_role'].startswith('grammar') and not atom_ids:
            gap_candidates.append({'section_id':s['id'],'doc':s['doc'],'pages':[s['pdf_start'],s['pdf_end']],
                'title':s['title'],'work_packages':s['work_packages'],
                'reason':'Relevant source section has no SourceAtom citing its page range; other concepts or equivalent claims elsewhere may exist.',
                'common_or_technical_candidates':s['legacy_candidates'],
                'status':'search_other_pages_and_read_body_before_declaring_missing'})
    # Includes every Claim, even those with no documents_atom link; these are not "missing" by definition.
    claim_rows=[]
    for n in ns:
        if n['type']!='Claim':continue
        related=[e for e in es if e['source']==n['id'] or e['target']==n['id']]
        atoms=sorted({(e['target'] if e['source']==n['id'] else e['source']) for e in related if e['relation']=='documents_atom'})
        claim_rows.append({'claim_id':n['id'],'title':n['title'],'source_atom_ids':atoms,
          'all_neighbor_ids':sorted({e['target'] if e['source']==n['id'] else e['source'] for e in related}),
          'status':'existing_claim_keep_narrow_scope' if atoms else 'review_concept_only_or_missing_atom_link'})
    tracked=[BASE/'graph/nodes.jsonl',BASE/'graph/edges.jsonl',BASE/'inputs/design.json',BASE/'inputs/curated_claims.json',BASE/'provenance/sources.json',
      ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json',ROOT/'src/kg_runtime/graph.py',ROOT/'src/kg_runtime/cards.py',
      ROOT/'knowledge/authored/semantic_foundation_20261102_r2/manifest.json']
    # Also freeze all prior foundation data, not only its manifest.
    tracked+=list((ROOT/'knowledge/authored/semantic_foundation_20261102_r2').rglob('*.json'))
    frozen={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(tracked)) if p.is_file()}
    lock=HERE/'private/input_hashes.json'
    if not lock.exists():dump(lock,frozen)
    preservation={k:sha(ROOT/k)==v for k,v in read(lock).items()}
    prior_dataset_hashes=read(ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/private/dataset_separation.json')['existing_files_sha256']
    for k,v in prior_dataset_hashes.items():preservation[k]=sha(ROOT/k)==v
    source_lock=HERE/'private/source_map_input_hashes.json'
    map_inputs={'reviewer_work/claude/source_sections.json':sha(HERE/'private/reviewer_work/claude/source_sections.json')}
    if not source_lock.exists():dump(source_lock,map_inputs)
    source_input_unchanged=all(sha(HERE/'private'/p)==h for p,h in read(source_lock).items())
    discrepancies=[]
    for s in sections:
        for f in set(s['reference_derived_work_packages'])-set(s['work_packages']):
            related=[i for i in s['legacy_candidates'] if f in row_by[i]['work_packages']]
            discrepancies.append({'section_id':s['id'],'work_package':f,'legacy_ids':related,
               'status':'pending_content_or_shared_context_check',
               'reason':'Reference-page and source-first work assignments differ. Do not union all page candidates into executable knowledge.',
               'next_action':'When refining this work package, inspect these cited sections and mark direct/supporting/unrelated/duplicate.'})
    stats={'legacy_design_items':len(rows),'source_atoms':sum(r['type']=='SourceAtom' for r in rows),
       'common_contracts':sum(r['type'] not in ('SourceAtom','TechnicalResponsibility') for r in rows),
       'technical_contracts':sum(r['type']=='TechnicalResponsibility' for r in rows),
       'pages':len(pages),'sections':len(sections),'work_packages':len(packs),'mapping_candidates':len(links),
       'semantic_items_completed_this_stage':0,'new_generation_calls':0,
       'unmapped_pages':sum(not p['section_ids'] for p in pages),'invalid_references':invalid,
       'referenced_pages':sum(bool(p['legacy_ids']) for p in pages),
       'source_atom_kind_counts':dict(collections.Counter(r['legacy_kind'] for r in rows if r['type']=='SourceAtom')),
       'routing_basis_counts':dict(collections.Counter(r['routing_basis'] for r in rows)),
       'claims_without_atom_links':sum(not c['source_atom_ids'] for c in claim_rows),
       'source_gap_candidates':len(gap_candidates),
       'assignment_discrepancies_pending':len(discrepancies),
       'unassigned_legacy_items':sum(not r['work_packages'] for r in rows),
       'unassigned_source_sections':sum(s['content_role']=='unassigned_needs_review' for s in sections),
       'source_map_input_unchanged':source_input_unchanged,
       'all_frozen_inputs_unchanged':all(preservation.values())}
    atlas={'version':'source_workmap_20261102','purpose':'review work map, not executable grammar KG',
       'stats':stats,'sources':source_stats,'pages':pages,'sections':sections,'legacy_items':rows,
       'candidate_links':links,'existing_claims':claim_rows,'work_packages':packs,'issues':ISSUES,
       'source_gap_candidates':gap_candidates,
       'assignment_discrepancies':discrepancies,
       'preservation':preservation,'review_scope_legend':reviewer['read_scope_legend'],
       'limitations':['Work assignments use ID families and module fallbacks; semantic mapping remains pending.',
          '102 section units are a coarse location map, not an exhaustive table/footnote claim inventory.',
          'No claim of complete 7-source reading, source-to-KG semantic equivalence, or current runtime correctness.',
          'Section page overlaps are intentional; counts are not additive independent evidence.',
          'Documents with no reference on a page may contain background or unrepresented grammar; not automatically a gap.']}
    dump(HERE/'private/atlas.json',atlas)
    dump(HERE/'private/structural_summary.json',stats)
    dump(HERE/'private/build_manifest.json',{'source_map_input_hashes':read(source_lock),
      'code_and_assignment_hashes':{p.name:sha(p) for p in [HERE/'build_atlas.py',HERE/'source_assignments.json',HERE/'work_packages.json',HERE/'next_work.json']},
      'dataset_hashes_from_prior_snapshot':prior_dataset_hashes,
      'atlas_sha256':sha(HERE/'private/atlas.json')})
    with (HERE/'private/legacy_worklist.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['기존ID','이름','종류','기존모듈','작업묶음후보','분류방법','의미검증상태'])
        for r in rows:w.writerow([r['legacy_id'],r['title'],r['type'],r['legacy_module'],','.join(r['work_packages']),r['routing_basis'],'이번 단계 미수행'])
    print(json.dumps(stats,ensure_ascii=False))
    return atlas

if __name__=='__main__':build()
