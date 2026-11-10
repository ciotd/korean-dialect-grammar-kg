# 의미·관계 분업 설계 검토 · 2026-11-09

- [최종 설계안](DESIGN.md): 쉬운 설명, 역할표, 흐름도, 입력 예, 기대효과·한계·비교와 종료기준.
- [두 검토 의견과 리드의 채택/비채택](REVIEW_RESOLUTION.md).
- [검토 전 초안](PROPOSAL.md), [추가 코드 근거](SUPPLEMENT.md).
- [Claude 독립 검토](private/claude_design_review.md), [Codex 독립 검토](private/codex_design_review.md).

설계 기록만 작성했다. 운영코드·KG·실험 데이터셋 변경과 신규 Qwen 호출은 없다. 최신 Kiwi 기본값과 기존 B2 후보 보류 상태를 유지한다. 제안은 절 범위→관계·역할→서술 의미의3개 Qwen 분석 역할이다. 질문 정리 단일군과 비교하기 전 분업을 품질 개선으로 채택하지 않는다. 내부 분석 워커와 외부 연구 검토자인 Claude/Codex를 구별한다.
