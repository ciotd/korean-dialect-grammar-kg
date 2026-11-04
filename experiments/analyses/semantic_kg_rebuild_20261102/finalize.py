"""Run checks, preserve review decisions, publish a separate candidate KG version."""
import collections,datetime,hashlib,json,shutil,sys,unittest
from pathlib import Path
from inventory import HERE,ROOT,BASE,read,dump,sha
from build_foundation import build,VERSION
def run():
    build()
    suite=unittest.defaultTestLoader.discover(str(HERE),pattern='test_*.py')
    with (HERE/'private/tests.txt').open('w',encoding='utf8') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    validation={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'development_queries':24,'translation_experiments':0,'independent_linguistic_accuracy':None}
    dump(HERE/'private/validation.json',validation)
    if not result.wasSuccessful():raise RuntimeError('tests_failed')
    resolutions=[
      {'problem':'절·서술어 연결을 입력 형식에만 맡김','action':'절·서술어·종결 슬롯·질문 변수·특징의 소속을 확인. 잘못된 범위 연결은 오류로 반환.','remaining':'실제 문법 분석의 정답 여부, 형태소 경계는 아직 검증하지 않음.'},
      {'problem':'다른 분석/그래프의 조회 결과를 전달할 수 있음','action':'분석 전체와 그래프 내용의 해시를 조회 결과에 결속. 다르면 전달 거부.','remaining':'Qwen 분석기 연결 후 실제 요청 기록 확인 필요.'},
      {'problem':'범위 밖 표현을 불가능한 문법처럼 제외','action':'초기 지원 범위 노드와 out_of_slice 결과를 추가. 조건 미일치·분석 부족·입력 오류와 구분.','remaining':'아니다·시·겠·더 등의 지식 정제 및 지원 범위 확대.'},
      {'problem':'계사 이형태와 조건별 근거가 빠짐','action':'이가/가·이고/고와 직접 발췌를 추가. 용언/계사 조합 설명을 분리. 조건의 문헌/연구정책/지원범위 출처 표시.','remaining':'이랐나를 원문에 직접 나온 형태로 승인하지 않음. 과거 계사 변이의 완성형은 후속 검토.'},
      {'problem':'판정 의문을 설명 의문 개념에 연결','action':'G_Q_POLAR/G_Q_WH 구별. 특징값을 G_PRED_KIND·G_TAM_SLOTS·G_HON_SUBJECT 등 기존 개념에 연결.','remaining':'다른 문법 모듈 전체의 특징 계약과 연결 확대.'},
      {'problem':'개발 예문 확인만으로 충분한 검증처럼 보일 수 있음','action':'별도 테스트에서 OR·다절·범위 오류·오타·unknown·오래된 결과·관계 삭제를 검사. 동일 지식 평면 조회와 후보 일치 확인.','remaining':'사람이 확인한 분석·미노출 번역 평가·자연스러움은 미실시.'},
      {'problem':'검토자의 문헌 모순 주장과 효과 해석이 과도함','action':'D02 p146은 다/도 전체 설명과 다만의 각주가 반드시 모순되지 않음. PDF 확인 후 확정 모순 등록하지 않음. KG가 평문보다 낫지 않다고 곧 정보량 원인이라고 단정하지 않음.','remaining':'현대 실제 사용, 운율·담화의 영향은 별도 연구.'}
    ]
    dump(HERE/'private/review_resolution.json',resolutions)
    spec=read(HERE/'private/foundation.json');graph=read(HERE/'private/graph.json');ledger=read(HERE/'private/refinement_ledger.json')
    mapping=collections.defaultdict(list)
    for r in spec['rules']:
        for old in r['legacy_atom_ids']:mapping[old].append(r['id'])
    for r in ledger:
        if r['id'] in mapping:r.update(new_rule_ids=mapping[r['id']],new_semantic_review_status='partially_refined_in_question_slice',remaining='원래 항목 전체 범위의 정제·활용·현대 자연스러움 검증은 미완료')
    dump(HERE/'private/refinement_ledger.json',ledger)
    views=read(HERE/'private/pdf_views/index.json');views['visually_checked']=['D02:142','D02:144','D02:145','D02:146','D04:8','D04:9','D04:10','D04:11'];dump(HERE/'private/pdf_views/index.json',views)
    # New version only. Original source IDs and observations are not overwritten.
    pub=ROOT/'knowledge/authored'/VERSION
    for name in ('foundation.json','graph.json'):
        dest=pub/'private'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and sha(dest)!=sha(HERE/'private'/name):raise ValueError('published_version_changed_create_new_version')
        if not dest.exists():shutil.copy2(HERE/'private'/name,dest)
    manifest={'version':VERSION,'status':'bounded_source_refinement_candidate','construction_count':1,'usage_count':6,'node_count':len(graph['nodes']),'edge_count':len(graph['edges']),'source_atom_partial_mapping_count':len(mapping),'whole_source_atoms_semantically_completed':0,'legacy_source_atoms_total':len(ledger),'analysis':'manual_development_annotation','qwen_calls':0,'neo4j_loaded':False,'graph_sha256':sha(pub/'private/graph.json'),'spec_sha256':sha(pub/'private/foundation.json'),'report':str(HERE/'private/report.html'),'code_files':{str(f.relative_to(ROOT)):sha(f) for f in HERE.glob('*.py')}}
    dump(pub/'manifest.json',manifest);dump(HERE/'private/manifest.json',manifest)
    dump(pub/'source_mapping.json',dict(mapping))
    schema={'node_types':dict(collections.Counter(n['type'] for n in graph['nodes'])),'relations':dict(collections.Counter(e['relation'] for e in graph['edges'])),'feature_schema':spec['feature_schema'],'support_scope':spec['support_scope'],'new_relations_are_new_implementation_not_inherited_facts':True}
    dump(pub/'schema.json',schema)
    (pub/'README.md').write_text('# 문헌 의미 정제 KG 첫 구성\n\n의문문 구성1개·용법6개의 별도 후보 버전입니다. 전체 KG 완성이나 방언 생성 성능 검증이 아닙니다. 기존 공통 척추와12모듈 ID를 유지합니다.\n\n- `private/foundation.json`: 원문 인용·해석·조건·실현형 명세\n- `private/graph.json`: 실제 조건 관계로 컴파일한 그래프\n- `source_mapping.json`: 기존5개 항목과의 부분 대응\n- `schema.json`: 실제 노드·관계·분석값 명세\n- `manifest.json`: 상태·범위·코드 및 데이터 해시\n\n구현과 검증: `experiments/analyses/semantic_kg_rebuild_20261102/`. 이 버전은 기존 Neo4j·생성기를 교체하지 않습니다. 전체721개 정제 작업대장은 해당 실험 폴더에 있습니다.\n',encoding='utf8')
    regression={str(f.relative_to(ROOT)):sha(f) for d in ['standard_inputs_50_20261023_v1','standard_inputs_50_20261029_v2','gyeongsang_reference50_20261030_v1'] for f in (ROOT/'data/derived_private'/d).glob('*.jsonl')}
    dev=read(HERE/'private/easy_development.json');standard=ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
    original_rows=[json.loads(x) for x in standard.read_text(encoding='utf8').splitlines()]
    old_strings={v for row in original_rows for v in row.values() if isinstance(v,str)}
    overlap=[c['id'] for c in dev if c['analysis']['text'] in old_strings]
    dump(HERE/'private/dataset_separation.json',{'existing_files_sha256':regression,'new_development_sentences':len(dev),'exact_sentence_overlap_with_existing50':overlap,'role':'development_not_unseen_test','structural_template_overlap_not_excluded':True})
    if overlap:raise ValueError('duplicate_development_sentence')
    sys.path.insert(0,str(ROOT/'src'))
    from research_management.work import WorkStore
    try:
        WorkStore(ROOT).task({'id':'semantic-kg-foundation-20261102','title':'문헌 의미 정제와 조건 기반 KG 검증','actor':'총괄 + Orca 두 검토자','stage':'첫 구성 검증 완료 · 전체 지식 정제는 남음','status':'completed','message':f'PDF7종 확인, 독립2+교차2 검토 완료. 의문문 구성1개/용법6개, 개발 조회24개·자동검사{result.testsRun}개 통과. Qwen0호출. 전체721개 의미 정제 완료 아님.'})
    except ValueError as exc:
        if str(exc)!='terminal_task_use_new_id':raise
    from report import run as report
    report()
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
