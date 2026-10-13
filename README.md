# Korean Dialect Grammar KG

경상도 방언 문법 지식그래프의 KG v3 연구 공간이다. 기존 연구의 근거·설계 결정·실패·개발 실험을 이관하고, 후속 연구를 재현 가능하게 기록한다.

**현재 상태: 연구 이관 및 초기 구조 완료. KG v3 구현·새 모델 실험·독립 화자 평가는 아직 수행하지 않았다.** 이름의 Korean은 한국어 방언 연구를 뜻하며 현재 근거 범위를 모든 한국어 방언으로 확대하지 않는다.

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
src/                  향후 구현 공간
tools/                이관 산출물·기록 계약 검사
```

Python 3.10 이상에서 초기 기록 계약과 이관 산출물의 무결성을 검사한다. 외부 패키지나 모델 서버가 필요하지 않다.

```bash
python tools/validate_research_records.py
```

검사는 파일 해시, 원본 링크·집계, 예시 기록의 필수 항목을 확인한다. 문헌의 의미 충실성이나 방언 자연스러움을 검사하지 않는다. 원문 PDF·AI-Hub 데이터·어휘 원본·인증정보는 저장소에 포함하지 않는다. 소스의 라이선스를 새 저장소의 라이선스로 대체하지 않으며, 이번에 포괄적 라이선스를 부여하지 않았다.
