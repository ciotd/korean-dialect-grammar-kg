# 최신 50문장 독립 검토 요청

사용자 요청: 분석 오류와 생성 오류를 구분하고 무엇부터 보완할지, 새로 논의한 멀티 에이전트 구조가 도움이 될지 검토. 지금은 설계만, 구현과 새 Qwen 실험 금지.

먼저 PLAN.md, ../kiwi_focused_full50_20261109/RESULTS.md와 private/outputs.csv(50건 전체), private/analyst_notes.json을 읽으세요. 원본 기록은 experiments/runs/20261109T030211818725Z_kiwi_default_regression/private 입니다. records/<ID>_kiwi_focused에 meaning/parsed.json, bound_analysis.json, retrieval.json, selected_knowledge.json, writer/request.json, writer/parsed.json, reviewer/parsed.json, pipeline_result.json이 있습니다. shared/<ID>/scope에 범위 분석 원문이 있습니다. 이전 분업 설계는 experiments/analyses/semantic_workers_design_20261109/DESIGN.md입니다.

리드의 기존 해석을 정답으로 가정하지 마세요. 특히 DEV012(높임 formal 오분류→-노 탈락), DEV002(가는→가노, 샀어 지식은 전달됨), DEV020(마라 전달 후 미사용), DEV026(늦을까 봐 오분류 + 높임 손실), LONG001(절 부모 범위 모순), LONG004(겸양 금지를 언급하고도 위반), ADVCE005B(도와예 초안은 있으나 사용 신고 충돌), QUAL020(과거 전달 후 들었어요→들어예), NEW007(예정/의지 약화)을 실제 원문 기록으로 대조하세요. 사례 분류는 복수 원인 가능하며 인과를 확정하지 마세요.

각 의견은 반드시 1 문제 위치 2 실제 근거 파일/필드/인용 3 수정안. 근거로 확인된 사실, 가설, 미확인을 구별하세요. 한글 쉬운 요약 + 자세한 근거. 50건 전체 출력의 훑어보기 범위와 실제 심층 대조 범위를 구분해 기록하세요. 변화율은 자연스러움 정확도가 아닙니다. 사용자 참조는 회귀 대조용이고 생성 구현에 섞지 마세요. 원본 PDF/인증파일/외부 전송은 불필요합니다.

Claude: 문법·지식·표현 관점. 내용이 없었는가, 틀린 분석으로 조회가 끊겼는가, 전달됐는데 무시됐는가, 검토 모델도 틀렸는가. 불필요한 전달 정보와 분업 경계(관계 담당/서술 의미 담당; 생성 계획/문장 작성/보존 검토)의 이익과 역효과. 단어별 워커보다 문장 전체 의미를 유지할 방안. 검토서는 private/claude_review.md에만 작성.

Codex: 코드·실험 관점. 실제 실패 위치와 검증 규칙, 전체 차단의 영향, 프롬프트/조건 충돌, 새 분업과 단순 질문/전달 정리의 효과를 공정하게 구별할 최소 비교. 호출 수·비용·무한 재수정 방지·오류 집계 분모·선택 편향. 검토서는 private/codex_review.md에만 작성.

runtime/KG/다른 파일을 수정하지 마세요. 지금 가장 먼저 할 2~3개 묶음과 각 종료 기준, 기대가 틀렸을 때 대안을 제시하세요. 완료 후 END_FULL50_ERROR_DESIGN_REVIEW를 출력하세요.
