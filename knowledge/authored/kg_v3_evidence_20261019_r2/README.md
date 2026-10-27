# 문헌 근거 KG — kg_v3_evidence_20261019_r2

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
python code/build_evidence_kg.py --design-json inputs/design.json --html-inventory provenance/html_inventory.json --pdf-dir "C:/Users/ciot28/Downloads/1" --claims inputs/curated_claims.json --dataset-id kg_v3_evidence_20261019_r2 --out "../kg_v3_reproduced"
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
