# 전체 KG 목록·구조 검사 — 2026-11-09

[사람이 읽는 검사 보고서](private/report.html)부터 읽는다. 전체 노드·관계를 검색하고56규칙의 실제 조건을 펼칠 수 있다.

이번 완료: 최신1,491노드/5,037관계 전수 목록·참조·중복·고립 검사,56규칙/57분기 조건·실현형 명세 대조,분리 audit 복원,원본1,625/6,167 보존 대조,실제 두 Orca 리뷰어 검토와 리드 반영. KG/운영 코드 수정·새 Qwen 호출·신규 자연어 예문 실행은 없다.

주요 결과: 연결 단절·중복 ID·고립 없음. 그러나 설명/조건 불일치,분석 질문의 의미값 혼합,limits/limitations 전달 불일치,혼합 메모 잔류,구버전 특징 헤더,기존12규칙의 작업묶음 대응 공백이 있다. 직접 모듈 관계 없는6규칙은 구성 경유로 연결되므로 실행 불능으로 분류하지 않았다.

## 파일

- `RESULTS.md`: 검사/미확인·실제 문제·수정안·다음 검사.
- `REVIEW_RESOLUTION.md`: 실제 검토 범위·반영/정정 판단. 원문은 private의 두 review 파일.
- `summary.json`: 자동 전수 구조 검사 집계. issue_counts는 자동 규칙 검사 종류만이며 전체 의미 문제 수가 아님.
- `private/audit.json`, `nodes.csv`, `edges.csv`, `rules.csv`, `branches.csv`, `feature_contracts.csv`: 각 항목별 상태와 실제 내용. CSV의 limitations는 읽기 편의를 위한 합친 값; 실제 전달값은 payload_limitations로 별도 표시.
- `private/interface_findings.json`: 실제 전달에서 직접 선택하지 않는 필드,헤더 차이,단위별 질문 선택지,메모·출처 연결.
- `private/example_test_plan.json`:57분기와 기존57예문 후보의 연결. 분기별 예문 타당성·Qwen 실행은 미완료.
- `audit_structure.py`, `build_report.py`, `verify_audit.py`, `browser_qa.mjs`: 재집계·화면·검증. 운영 파이프라인 코드가 아님.

다음은 이번 불일치의 보완안 확정 후 규칙별 적용/비적용/미확정 예문 검사다. 문헌 충돌을 모델 합의로 확정하지 않는다. 구조 검사를 자연스러움 평가나 KG 효과 입증으로 쓰지 않는다.

복구 기준: 직전 로컬 체크포인트9b528e9. 완료 체크포인트와 비공개 원문 백업은 private/version_receipt.json에 기록한다. GitHub 푸시는 이번 범위에 없고, 기존 원본·실행 기록은 보존한다.
