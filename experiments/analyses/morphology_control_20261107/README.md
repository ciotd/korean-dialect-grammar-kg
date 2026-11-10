# 형태 분석 공급자 통제 비교 — 2026-11-07

Qwen과 Kiwi가 나눈 형태소를 같은 코드로 문법 단위에 연결하고, 이후 의미 분석·KG 조회·문장 생성·검토를 동일하게 수행한다. 기존 전체 경로 비교에서 섞였던 생성 지시·검토 구성 차이를 제거하기 위한 개발 진단이다.

- [사람이 읽는 결과 비교](private/report.html)
- [실행 전 계획과 종료 기준](PLAN.md)
- [검토 의견 반영·수정 결정](DECISIONS.md)
- [실제 프롬프트](prompts.md)
- [통제 조건을 실제 요청에서 확인한 기록](private/control_audit.json)
- [최종 자동검사](private/tests_final.json)
- [실행 위치](latest.json)

핵심 구현은 `src/kg_pipeline/morphology_control.py`(공통 형태 연결), `tools/run_morphology_control.py`(6쌍 실행·기록), `multi_agent.py`의 prepared_structure 연결이다. 기존 실행 경로를 기본적으로 교체하지 않는다. Qwen 형태 분석 결과나 Kiwi 분석값이 정답이라는 가정은 하지 않는다.

실행은 `tools/run_morphology_control.py --execute --source experiments/runs/20261107T070359552481Z_qwen_multi_development --deadline <시간대가 있는 미래 ISO 시각>`으로 가능하다. 실제 호출·비용이 발생하므로 재실행은 별도 연구 실행으로 기록한다. 기존 결과를 덮어쓰지 않는다. 보고서 재생성은 `python experiments/analyses/morphology_control_20261107/build_report.py`이며 모델 호출이 없다.

평가 범위는 노출된 개발6문장/12경로다. 기존50건 및 독립 최종 평가를 대체하지 않는다. 원문과 정답을 암기시키는 작업은 하지 않았으며 최종 문장은 Qwen이 작성한다. 원본 문헌·출처·문법 조건을 이 비교에 맞추어 변경하지 않았다.
