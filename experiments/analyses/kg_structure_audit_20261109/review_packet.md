# 전체 KG 목록·구조 독립 검토

이번 사용자 승인: ② 전체 KG 목록·구조 검사, 두 리뷰어 의견과 실제 근거·수정안 보고. KG/운영 코드 수정·새 모델 호출 없음. 원본 PDF 전수 재독 아님. 지정 검토서 외 파일 수정 금지. 인증정보 읽기 금지.

공통: PLAN.md, ../current_state_20261109/SNAPSHOT.md, 현재 knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json이 가리키는 graph/audit/manifest. src/kg_pipeline/integrated.py, separated_graph.py, kiwi_default.py, multi_agent.py 및 기존 대응 특징 정의. 26묶음은 integrated_grammar_20261106/coverage_r2.json. 최근50은 experiments/runs/20261109T030211818725Z_kiwi_default_regression/private/records. 리드가 audit_structure.py와 private/audit.json,summary.json을 만들면 후반에 함께 대조하되 기다리지 말고 독립 검토.

Codex: 전체 노드/관계의 참조·유형·고립·중복,56규칙/57분기의 조건 명세·실제 reader 적용, 읽히지 않는 관계/명세 불일치,6모듈 직접 미연결과 전체12+44/26묶음 대응, 출처 복원 가능성을 확인. 리드 집계도 검토. 실행 영향과 분류/추적성 문제를 구분. 지정 출력 private/codex_structure_review.md.

Claude: 56규칙의 조건/표현/보존/제약 설명을 전부 훑고, 텍스트 조건과 실제 그래프 조건의 차이·모순 후보·메모 잔류를 항목별로 정리. 별도 audit에 근거 연결이 있는지 확인하되 PDF 미열람을 명시. 최근50에서 조건 통과 미관찰30규칙을 입력기회 없음/분석·관계·조건 문제/미확인으로 근거 있게 구분하고 무리한 확정 금지. 모든 규칙의 문헌 의미 인증을 주장하지 말 것. 다음 규칙/분기별 적용·비적용·미확정 예문 검사 대상 제안. 지정 출력 private/claude_structure_review.md.

형식: 문제 위치(ID/속성/파일) → 실제 근거 → 영향 → 수정안 → 수정 후 검사. 심각도는 ‘실행 판단 영향 / 전달 혼동 / 목록·추적 문제 / 미확인’으로 쉬운 한국어. 실제 검사 범위/미확인 구분. 자동 필터에 걸렸다는 이유로 오류 확정 금지. 조회0과 조건통과0 구분. 과거 원문헌/사람 판단을 모델 합의로 대체하지 말 것. 끝에 END_STRUCTURE_REVIEW.
