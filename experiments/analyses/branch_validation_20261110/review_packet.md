# 두 기존 검토자 요청

사용자가 다음 단계 진행과 두 검토자 협업을 승인했다. 한국어로 읽기 쉽게 작성한다. 인증정보를 읽거나 기록하지 않는다. 운영 코드/KG를 수정하지 않는다. 본 폴더 private 안 검토 결과만 저장한다.

공통 근거: ../kg_structure_audit_20261109/RESULTS.md, private/audit.json, private/example_test_plan.json, private/interface_findings.json, PLAN.md. 실제 KG는 knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json. 원문 출처는 분리 audit에서 읽을 수 있으나 원본 PDF 전체를 복사하지 않는다.

## Claude
1. 기존57예문(experiments/analyses/semantic_reachability_20261107/private/20261107T052951500203Z/natural_probes.json)을 전체57분기와 대조한다. 조건을 그대로 복제한 가짜 정답을 만들지 않는다. 각 분기에 자연스러운 적용 후보·비적용 후보·판단 불가 상황을 제안하고, 현재 조건과 충돌하면 명시한다.
2. 결과를 private/claude_examples.json에 JSON 배열로 저장: branch_id, rule_id, positive{text,target,reason}, negative{text,target,reason}, unknown{text,target,reason}, verdict(ready/needs_revision/unresolved), issues. 예문을 확인하기 어려운 경우 빈칸 대신 사유와 unresolved. 모델의 판단이며 사람 인증이 아님을 명시.
3. 39규칙의 '조건 보완' 메모 중 실제 문법 제한과 낡은 구현 메모를 구별한다. 특히 KKE, AUX_PRESERVE_COMMON, CONN_SEQ_AGA, HORT, PROHIB_MAISO, QUOTE를 확인. 삭제해도 되는 정확한 문자열/대체안/보존할 조건을 private/claude_review.md에 기록한다. 조건 미확정을 허용으로 바꾸지 않는다.

## Codex
이번 리드는 integrated.py payload에서 limits/limitations 병합(충돌시 둘 다 보존), generation_operation/target/surface_postcondition/operation 및 실현형unit 전달, SUPPORTED_IN 경로 기록 누락을 보완할 예정이다. 생성 담당을 Kiwi로 지시하는 낡은 문구는 함부로 정규식 삭제하지 않는다.
기존990 논리 사례와57 자연어 후보를 구별한 검사 설계를 검토하고, src/kg_pipeline/integrated.py 및 새 tests/test_branch_delivery.py(준비 중)의 실제 수정을 확인한다. 문제 위치→근거→수정안, 심각도, 미확인 범위를 private/codex_review.md에 기록한다. 파일이 아직 없으면 현재 분석을 먼저 하되 마지막에 실제 수정 확인이 필요하다고 명시한다.
