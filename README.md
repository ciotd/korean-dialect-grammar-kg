**2026-10-27 GitHub 반영:** KG·파이프라인·대시보드·18개 실행의 설정/요약/코드 기록을 포함합니다. 인증정보·비공개 입력과 문장별 원본은 제외되므로, 새 PC에서는 [GitHub 반영 범위와 복원 안내](docs/workflows/GITHUB_SYNC.md)를 먼저 확인하세요.

## 2026-10-25 · 검색과 실행을 분리한 비교 실험

[통합 보고서](http://127.0.0.1:8766/reports/search-execution/report.html) · [결과 요약](docs/research/SEARCH_EXECUTION_RESULTS_20261025.md) · [설계·실행 안내](docs/research/SEARCH_EXECUTION_20261025.md) · [사람 평가 화면](http://127.0.0.1:8766/reports/search-execution/review.html)

KG의 721개 문헌 항목 전체를 검색 가능하게 하고, 현재 실행 가능한 17개 변환 규칙과 구별했습니다. 회귀 50건과 사전 고정 12건에서 Single/Planner–Worker를 비교하며, Qwen 분석에 Kiwi 정보를 제공하는 영향은 별도 통제 실험으로 확인합니다. 이전 실행과 원본 KG는 보존합니다.

# Korean Dialect Grammar KG

**2026-10-24 실행층 재설계:** Kiwi 원문 위치 분석, 기존 KG ID 기반 17개 변환 실행기, Single / Planning+Worker와 50건 회귀 비교를 추가했다. [새 설계·재현 방법](docs/research/RUNTIME_REDESIGN_20261024.md)과 [실제 비교 보고서](http://127.0.0.1:8766/reports/runtime/report.html)를 먼저 확인한다. 아래 2026-10-23 수치는 보존된 이전 기준 기록이다.
경상도 방언 문법 지식그래프의 KG v3 연구 공간이다. 기존 연구의 근거·설계 결정·실패·개발 실험을 이관하고, 후속 연구를 재현 가능하게 기록한다.

**현재 상태(2026-10-23): 문헌 기반 KG 구축·Neo4j 적재, Qwen 분석→KG 조회·근거 선별→Qwen 생성 구현과 확정 입력 50건의 1차 실행을 완료했다.** 출력 검사 통과 35건(원문 유지 34·부사 변경 1), 분석 검사 실패 15건이다. 문법 방언화 성과·정확도·자연스러움은 입증하지 못했으며 독립 화자 평가는 아직 없다. 이름의 Korean은 한국어 방언 연구를 뜻하며 현재 근거 범위를 모든 한국어 방언으로 확대하지 않는다.

현재 구현은 [파이프라인 설명·재현 방법](docs/research/PIPELINE_IMPLEMENTATION.md), 실행 결과는 [1차 실험 요약](docs/research/PIPELINE_FIRST50_RESULTS_20261023.md)을 읽는다. 입력별 문장·원응답·근거는 실행 폴더의 Git 제외 `private/` 아래에 보존한다.

실험 이력·비교·오류·문장별 추적은 **로컬 연구 대시보드**에서 확인한다. 저장소 루트에서 `python tools/research_manager.py serve`를 실행하고 http://127.0.0.1:8766/ 을 연다. [관리 시스템 설계](docs/research/RESEARCH_MANAGEMENT.md), [작업 절차](docs/workflows/RESEARCH_MANAGEMENT.md), [자동 실행 현황](docs/research/RESEARCH_STATUS.md)을 참고한다. 기존 5회 실행을 보존해 등록했으며 관리 기능 검증을 위해 Qwen을 재호출하지 않는다. 신규 파이프라인 버전 0.1.4는 자동 등록·개발/평가 분리를 추가했으며 기존 0.1.3 첫 평가 결과를 대체하지 않는다.

먼저 [KG v3 연구 이관 문서](docs/KG_V3_RESEARCH_HANDOFF.md)를 읽는다. [설계 결정](docs/research/DECISIONS.md), [미해결 질문](docs/research/OPEN_QUESTIONS.md), [평가 계획](docs/research/EVALUATION_PLAN.md), [기록 규격](docs/research/RECORDING_CONTRACT.md)이 후속 연구의 출발점이다.

원본은 [ciotd/odor-complaint-dialect-rag](https://github.com/ciotd/odor-complaint-dialect-rag)이며 읽기 전용 참조 대상이다. 기준 커밋은 `0422b027ee92aaf461c29244987d4d8d2e094284`. [근거 목록](provenance/EVIDENCE_INDEX.md), [파일 목록](provenance/source_file_inventory.tsv), [94개 커밋 목록](provenance/commit_history.tsv), [실험 위치 목록](provenance/experiment_catalog.tsv)으로 원본을 추적한다. 기존 데이터를 새 KG 결과로 표시하지 않는다.

```text
docs/                 이관 문서와 연구 계획
provenance/           고정 원본 목록·SHA·추적 정보
schemas/              새 연구 기록용 계약 초안
knowledge/authored/   향후 직접 작성할 지식
knowledge/reviews/    근거·용법·조건 검토
experiments/templates/ 실행·평가 기록 예시
experiments/runs/     향후 불변 실행 폴더
data/                 자료 등록 정책
src/                  Qwen·KG 파이프라인 구현
tools/                이관 산출물·기록 계약 검사
```

Python 3.10 이상에서 현재 파이프라인의 단위 검사를 실행한다. 이 검사는 모델 서버를 호출하지 않는다.

```bash
python tests/test_kg_pipeline.py
```

검사는 문헌의 의미 충실성이나 방언 자연스러움을 검사하지 않는다. 초기 `tools/validate_research_records.py`와 `provenance/deliverable_manifest.json`은 이관 당시 고정 파일 집합의 검사 기록이며, 이후 확장된 전체 작업 트리에 대한 최신 검사가 아니다. 현재 실행은 실행별 코드·입력·KG·산출물 해시와 검증 기록으로 추적한다. 원문 PDF·AI-Hub 데이터·어휘 원본·인증정보는 저장소에 포함하지 않는다. 소스의 라이선스를 새 저장소의 라이선스로 대체하지 않으며, 이번에 포괄적 라이선스를 부여하지 않았다.
