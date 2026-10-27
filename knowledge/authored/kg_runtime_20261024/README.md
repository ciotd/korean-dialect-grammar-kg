# 문법 KG 실행용 뷰

원본 `../kg_v3_evidence_20261019_r2`의 1,625개 노드 ID와 6,167개 관계를 그대로 보존한다. 노드 속성에서 실행에 반복 전달하지 않을 해설·메타데이터를 분리했다. 원본 노드의 사실 상태나 Neo4j 속성을 변경하지 않는다.

- `runtime.json`: 간결한 노드·관계와 17개 실행 규칙 명세. 실행기는 `src/kg_runtime/rules.py`.
- `statistics.json`: 원본/실행 뷰의 실제 수와 파일 크기·원본 해시.
- `coverage_ledger.json`: 전체 721개 문헌 항목의 구현 여부, 원래 조건·출력·연결. 보고서의 추가 설명은 분석 폴더 `coverage_audit.json`에 있다.
- `source_versions.json`: 원본 7개 PDF와 추출 텍스트의 해시. 생성 시 PDF 해시가 기존 문헌 manifest와 같은지 확인했다.
- `private/source_pages.json`: 이번 실행 규칙을 대조한 실제 페이지 본문. 커밋 제외.

17개는 일반 한국어/경상도 전체 문법을 완성한 수가 아니다. 11개 종결어미 ID, 3개 연결어미 ID, 3개 부사 ID다. 여러 문법 모듈이 탐색에 쓰여도 모든 모듈에 변환 코드가 있는 것은 아니다.

재생성 진입점은 `tools/build_kg_runtime.py --source-texts <D01.txt…D07.txt와 manifest.json 디렉터리>`다. 기존 출력이 있으면 덮어쓰지 않고 중단한다. 새 버전은 출력 경로와 실행기 버전을 함께 변경하여 별도로 생성한다. 추출 문서는 `=== PDF PAGE N ===` 구분자를 사용하며 manifest의 실제 PDF 위치가 유효해야 한다.

자세한 설계와 실행은 [실행층 문서](../../../docs/research/RUNTIME_REDESIGN_20261024.md)를 따른다.
