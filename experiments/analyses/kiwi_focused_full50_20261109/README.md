# 전체 50문장 재실험 — 2026-11-09

최근 구현된 Kiwi 형태 분석과 Qwen의 명시적인 본·보조용언 연결 질문(`kiwi_focused`)을 전체 50문장에 적용한 회귀 실행이다. 새 분석 워커 분업 설계는 포함하지 않는다. 연구 코드·KG·프롬프트는 이번 실행 중 수정하지 않는다.

- 실행: `experiments/runs/20261109T030211818725Z_kiwi_default_regression`
- 사람이 읽는 결과: `private/report.html`
- 전체 문장 비교: `private/outputs.csv` (사용자 승인 참조는 모델에게 보내지 않음)
- 사례 해석: `private/analyst_notes.json`
- 수치·입력별 기록: `private/summary.json`, `private/cases.json`
- 실제 구현 흐름: `private/pipeline.html` — Archify 검증본
- 계획과 종료 기준: [PLAN.md](PLAN.md)

보고서의 완료·변경·지식 전달 건수는 처리 기록이다. 자연스러움 정확도, 사람 평가 결과 또는 KG 효과의 증명으로 쓰지 않는다. 출력 원문은 그대로 보존하고, 검사 모델의 의견도 사실 확인 전 의견으로 구분한다.

## 재생성

실험을 다시 호출하지 않고 저장 기록만 읽어 보고서를 만든다.

```powershell
python experiments/analyses/kiwi_focused_full50_20261109/build_report.py experiments/runs/20261109T030211818725Z_kiwi_default_regression
python experiments/analyses/kiwi_focused_full50_20261109/verify_run.py experiments/runs/20261109T030211818725Z_kiwi_default_regression
```

`verify_run.py`는 실행이 끝나고 파일 해시 목록이 생긴 뒤 실행한다. 실패 문장의 절 범위 검사는 저장된 응답으로만 재생하며 새 모델 호출을 하지 않는다. 실험 원본과 인증정보를 변경하지 않는다.

기존 관리 화면은 로컬 `http://127.0.0.1:8767/work`에서 진행률을 표시한다. 보고서의 문장별 화면은 원문·참조·출력과 실제 분석·전달·선택 이유를 연결한다. 이 폴더의 `private`와 원시 실행 기록은 GitHub에 공개하지 않는다.
