"""Package reviews, reproduction instructions and code without source PDFs or secrets."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main(a):
    root=Path(a.root);rd=Path(a.review_dir);tools=Path(a.tool_dir)
    for name in ['schema_pre_review.json','schema_post_review.json','schema_recheck.json','linguistic_review.json','linguistic_recheck.json','linguistic_report_recheck.json','schema_span_recheck.json']:
        p=rd/name
        if p.exists():shutil.copyfile(p,root/'reviews'/name)
    prior=load(Path(a.prior_inventory));actual=load(root/'provenance/html_inventory.json')
    old={r['path'].replace('\\','/'):r for r in prior}
    matches=[]
    for r in actual:
        source=Path(a.design_dir)/r['path']
        normalized=hashlib.sha256(source.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
        matches.append({'path':r['path'],'raw_sha256':r['sha256'],'lf_normalized_sha256':normalized,'matches_prior_audit':normalized==old.get(r['path'],{}).get('sha'),'raw_matches_current_file':hashlib.sha256(source.read_bytes()).hexdigest()==r['sha256']})
    dump(root/'provenance/prior_review_reuse.json',{'method':'이전 19HTML 검토 기록은 LF 줄바꿈 정규화 텍스트 해시였음. 동일 방식으로 19개 모두 일치 확인 후 재사용; 현재 원본 바이트 해시도 별도 보존; 이번 작업에서는 최종 구조화 설계를 분석하고 모든 HTML의 구조·판본을 재확인. 19개 전체를 새로 정독했다고 주장하지 않음.',
       'comparison':matches,'all_match':all(r['matches_prior_audit'] for r in matches)})
    resolutions=[
      {'finding':'SR01–SR09','action':'기존 ID·모듈 분류·관계 보존, 종류 정규화, 근거 노드·최소 관계 확장, 중첩 원본 보존','status':'반영; 구조 Reviewer 확인'},
      {'finding':'SP01','action':'Module.number는 원래 import 마지막 문장에서 설정됨','status':'Reviewer 오탐 철회; 기록 보존'},
      {'finding':'SP02','action':'설명 두 곳을 한국어로 정리','status':'수정·재확인'},
      {'finding':'SP04','action':'CSV 표시값 NUL은 ␀로 변환; properties_json은 원문 유지','status':'수정·재확인'},
      {'finding':'LE01','action':'세 documents_atom 연결에 부분적으로 관련되는 범위를 mapping_note로 명시','status':'수정·재확인'},
      {'finding':'LE03','action':'C_D05_02를 2차 인용으로 표시하고 원전 미확인 기록','status':'수정·재확인'},
      {'finding':'LE02 / SP03','action':'29개 좁은 진술 대조와 721개 기존 항목을 구분; 직접 Claim이 없는 모듈12 표시','status':'보고 범위 유지'},
      {'finding':'Builder 출처 중복 검사','action':'동일 문헌·쪽·offset·발췌의 자동 SourceSpan 공유; 항목별 anchor는 매핑파일에 보존','status':'r2에서 수정; 구조 재검증'},
    ]
    dump(root/'reviews/review_resolutions.json',resolutions)
    dump(root/'provenance/implementation_log.json',{'date_kst':'2026-10-19','steps':[
       '연구 저장소 AGENTS/README와 파일 관리 관례 확인','최종 설계 JSON 및 원문 7종 해시 확인','Schema Reviewer 사전 검토',
       '원문 전쪽 추출 및 기존 출처 연결; 28개 좁은 진술 대조','초기 KG/CSV 생성 및 자동 검사','두 Reviewer 독립 검증',
       '부분 매핑·간접 인용 설명과 CSV 표시값 수정; 대명사 Claim 1건 추가','동일 출처 발췌 중복 발견 및 r2 공유화',
       '자동 검사·오류 주입 테스트·소스 대조·보고서 브라우저 검사','최종 데이터에서 통계/인터랙티브 HTML 생성'],
       'excluded_operations':['원본 저장소 수정','git commit/push','LLM API 호출','Neo4j 실DB 적재','방언 생성 평가'],
       'review_scope':'독립 언어 검토 29Claim/7문헌24쪽/이미지3쪽. 721개 원자의 전수 의미승인 아님.'})
    code=root/'code';code.mkdir(exist_ok=True)
    for name in ['build_evidence_kg.py','validate_evidence_kg.py','render_kg_report.py','report_template.html','test_validation.py','finalize_package.py']:
        p=tools/name
        if p.exists():shutil.copyfile(p,code/name)
    scope=load(root/'provenance/build_scope.json');manifest=load(root/'provenance/input_manifest.json');run=manifest['run_id']
    readme=f'''# 문헌 근거 KG — {run}

시작: [인터랙티브 구축 보고서](report.html)

공통 척추의 탐색 뷰와 최종12모듈에 기존911개 항목(방언721·공통136·기술54), 기존2909개 관계를 보존했습니다. 문헌 출처와 직접 대조한29개 좁은 진술을 추가했습니다. 생성 엔진이나 현대 경상도 전체 문법의 검증 결과가 아닙니다.

## 파일

- graph/nodes.jsonl, edges.jsonl: 통합 KG. 원래 조건·출처·종류는 original_spec에 보존.
- neo4j/: 유형별 CSV, import.cypher, explore.cypher, 실행 안내.
- schema/: 기존37개 엔터티·40개 관계 계약 및 최소 확장,12모듈,7계층.
- mapping/source_to_kg.json:911개 항목의 출처 위치와 직접 Claim 연결. 검색어 anchor는 이 파일에 기록.
- inputs/: 최종 설계 스냅샷과 직접 대조 Claim 명세. 원본 PDF·전체 추출문은 미포함.
- provenance/: 원문/HTML 해시, 추출 도구 및 페이지 해시, 범위·변경 이력.
- reviews/: 두 Reviewer의 독립 검토·한정 재검토, Builder 대응, Human Review. 과거 검토의 수치는 당시 판본에 해당.
- validation/: 자동 검사, 오류 주입 테스트와 브라우저 검사 결과.
- code/: 이 판본을 생성한 코드 스냅샷. pypdf 필요; 외부 모델 불필요.

## 재현

이 폴더를 현재 디렉터리로 두고 Python3.10 이상에서 실행합니다. source PDFs는 권한 있는 원본을 별도로 준비해야 합니다. 출처 파일명·해시는 provenance/sources.json에 있습니다.

```powershell
python code/build_evidence_kg.py --design-json inputs/design.json --html-inventory provenance/html_inventory.json --pdf-dir "C:/Users/ciot28/Downloads/1" --claims inputs/curated_claims.json --dataset-id {run} --out "../kg_v3_reproduced"
python code/validate_evidence_kg.py "../kg_v3_reproduced" --pdf-dir "C:/Users/ciot28/Downloads/1"
```

빌더는 기존 출력 폴더 덮어쓰기를 거부합니다. 같은 입력·dataset_id로 graph/CSV를 재현합니다. 새 지식판본에는 새로운 dataset_id를 사용합니다. 원문 HTML 없이도 저장된 최종설계와 HTML inventory로 KG를 재생성할 수 있지만 과거 HTML 자체의 재검토는 원본이 필요합니다. 검토보고서는 생성 코드가 재생산하는 사실이 아니므로 별도 감사기록으로 보존합니다.

보고서 재생성: `python code/render_kg_report.py .`

오류 주입 테스트: 환경변수 KG_TEST_ROOT를 이 폴더 절대경로로 지정한 뒤 `python code/test_validation.py -v`.

## 해석 및 검증 범위

SourceAtom721개 전체의 인용 위치를 연결했습니다. 각 원자의 모든 조건·형태 목록이 이번에 새로 의미 검증된 것은 아닙니다. 직접 대조 Claim29개와 그 해석적 개념 연결은 별도로 표시합니다. 자동 문맥 발췌는 의미를 입증하는 근거라고 자동 승인하지 않습니다. 문헌에 나온 것으로 확인한 진술도 현대 모든 지역에서 생산적으로 적용된다는 뜻은 아닙니다.

모듈별 직접 Claim 수는 validation.json 및 report.html을 참고합니다. 모듈12는 관리·변이·실행제어의 설계 항목이며 이번 직접 Claim의 공통개념 매핑은 없습니다. 기존 지역·시기 조건은 원문 명세로 보존하되 실행 필터로 적용하지 않았습니다.

Neo4j 환경이 제공되지 않아 실DB 적재/쿼리 실행은 미검증입니다. CSV roundtrip과 정적 연결 검사는 DB 성공과 구별합니다. schema에 확장 후보 상태(inference_candidate)를 정의했지만 LLM 추론 지식은 이번 확정 그래프에 넣지 않았습니다.

PDF 일부 깨진 문자는 임의 복원하지 않습니다. Neo4j CSV 표시 quote만 NUL을 가시기호 ␀로 바꾸며 properties_json에는 원래 문자와 offset을 보존합니다.

모든 원본은 읽기 전용입니다. 커밋·푸시하지 않았으며 원문 자료의 권리 조건을 변경하지 않습니다. 이전 kg_v3_evidence_20261019 폴더는 출처 중복 정규화 이전 구축 이력입니다. 현재 인용·탐색에는 이 r2 판본을 사용합니다.
'''
    (root/'README.md').write_text(readme,encoding='utf-8')
    print('Packaged reviews and reproduction documentation')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--review-dir',required=True);p.add_argument('--tool-dir',required=True);p.add_argument('--prior-inventory',required=True);p.add_argument('--design-dir',required=True);main(p.parse_args())
