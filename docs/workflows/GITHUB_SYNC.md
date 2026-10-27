# GitHub 반영 범위와 다른 PC에서의 복원

2026-10-27 기준. 연구 저장소는 `ciotd/korean-dialect-grammar-kg`이다. 기존 `ciotd/odor-complaint-dialect-rag`는 읽기 전용 참조 대상으로 유지한다.

## GitHub에 보관하는 내용

| 범위 | 위치 | 복원 가능 내용 |
|---|---|---|
| KG와 실행용 구성 | `knowledge/authored/` | 구축 당시 버전, 원본 노드·관계, Schema, 출처 위치·인용 발췌, 17개 실행 규칙과 721개 검색 항목 |
| Neo4j 적재 | KG 하위 `neo4j/`, `experiments/neo4j_live_20261021_r2/` | CSV·Cypher, 실제 적재 검사 기록. 실행 중 DB 자체는 포함하지 않음 |
| 실행 코드 | `src/`, `tools/`, `requirements-runtime.txt`, `tests/` | 분석·검색·생성, 연구 관리 대시보드, 테스트와 의존성 목록 |
| 18개 실행 기록 | `experiments/runs/` | 설정·프롬프트·요약 지표·코드 스냅샷·파일 해시. 문장별 원본은 제외 |
| 연구 문서 | `docs/`, `experiments/analyses/`, `experiments/validation/` | 설계·결과·검증 요약 및 일부 자체 포함 HTML |

과거 실행 폴더의 해시와 결과는 당시 파일에 대한 기록이다. GitHub에는 비공개 원본을 제외한 일부 파일만 있으므로, clone 직후 모든 실행 해시 검증이 통과하거나 문장별 대시보드가 완전히 열리는 것은 아니다. 누락된 원본을 결과 오류나 성능 0으로 해석하지 않는다.

`.gitattributes`는 자동 줄바꿈 변환을 끈다. 실행 산출물의 바이트와 해시를 Windows/Linux checkout에서 보존하기 위한 설정이다. 기존 커밋 파일 중 내용 변화 없이 줄바꿈만 달랐던 파일은 기존 커밋의 바이트를 유지한다.

## 별도로 옮겨야 하는 자료

기존 `AGENTS.md` 및 `.gitignore` 정책을 유지한다. 다음 자료는 이 커밋에 포함하지 않는다.

- 원본 PDF·전체 추출 본문, AI-Hub 파생 데이터 및 어휘 원본.
- `data/derived_private/`: 확정 50건, 추가 12건 등 실제 평가 입력.
- 각 `private/` 폴더: 문장별 입력·응답·조회 원본·평가 자료와 상세 HTML/데이터, 대시보드 색인.
- `test.py`, `.env`, 비밀번호·API 키, 로컬 Neo4j 인증 파일.
- `local/`: 로컬 설치 의존성·환경 자료. 실행 중 Neo4j DB와 외부 폴더의 과거 HTML 보고서도 Git 저장소에 자동 포함되지 않는다.

이 자료는 원본 위치에서 삭제하지 않는다. 다른 PC로 전체 작업 환경을 옮기려면 사용 권한이 있는 자료를 별도 보안 경로로 복사해야 한다. GitHub가 전체 연구 환경의 단독 백업은 아니다.

## 새 환경에서 시작하기

1. 저장소를 clone하고 해당 폴더를 VS Code 작업 공간으로 연다.
2. 별도 Python 환경을 만든 뒤 `python -m pip install -r requirements-runtime.txt`로 의존성을 설치한다. 실제 실행 버전은 각 실행의 설정·기록을 참고한다.
3. Neo4j를 설치하고 [적재 안내](../../knowledge/authored/kg_v3_evidence_20261019_r2/neo4j/README.md)의 CSV·Cypher를 적용한다. 해당 안내의 “미실행”은 구축 당시 상태이며, 이후 실제 적재 결과는 [적재 기록](../../experiments/neo4j_live_20261021_r2/README.md)에 있다.
4. Qwen 서버와 Neo4j의 인증정보를 새 환경에 별도로 설정한다. 문서에 기록된 이전 PC의 절대 경로를 현재 경로로 바꾼다.
5. 권한 있는 입력·`private/` 자료를 같은 상대 경로에 복원한 뒤 `python tools/research_manager.py sync`와 `python tools/research_manager.py serve`를 실행한다.
6. http://127.0.0.1:8766/ 을 연다. 이 주소는 현재 PC에서 실행한 서버이며 GitHub 게시 주소가 아니다. 이전 보고서의 8765 링크는 별도 보고서 서버와 원본 파일도 필요하다.

새 모델 실행은 [현재 실행 설계](../research/SEARCH_EXECUTION_20261025.md), 실제 결과는 [비교 결과](../research/SEARCH_EXECUTION_RESULTS_20261025.md)를 따른다. 이번 GitHub 반영을 위해 Qwen을 다시 호출하거나 기존 실험 결과를 바꾸지 않는다.

## 이번 반영 방법

G: 작업 폴더의 `.git` 쓰기가 환경 권한으로 차단되어, C:의 별도 checkout에 Git 제외 파일을 뺀 작업 파일을 바이트 그대로 복사했다. 업로드 전 로컬 검증을 거치고 연결된 GitHub 커넥터로 반영한다. G:의 소스 파일과 원본 실험 자료는 유지한다.

G:의 Git 내부 기록은 이번 원격 반영과 별도로 동기화가 필요할 수 있다. 기존 변경 파일을 보존한 상태에서 GitHub 최신 커밋과 파일 내용을 먼저 대조해야 한다. `reset --hard`, 강제 푸시, 일괄 삭제를 사용하지 않는다.
