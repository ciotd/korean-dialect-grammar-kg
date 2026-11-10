# 카드 내용 보완 · 2026-10-30

[쉬운 변경 보고서](http://127.0.0.1:8767/reports/card-revision-20261030/report.html)

카드 새 버전은 `knowledge/authored/kg_cards_20261030_v3`에 있다. 전체 721개 중 573개 정리, 그중 10개에 방향성 안내를 추가했다. 기존 카드·그래프·ID·형태 목록과 검색 순위는 보존했다.

- `private/packet_validation.json`: 이전 49개 + 카드 전달 실험 26개 목록의 투영 검사. 모델 실행이 아님.
- `private/compatibility_cases.json`: Codex가 사전에 작성한 시험계획 6개를 기존 검사로 확인한 결과. Qwen 결과가 아님.
- `private/original_integrity.json`: 원본 KG와 v2의 이전 실험 해시 일치.
- `private/reviewers.json`: 두 검토자의 지적·반영 요약.
- `report.py`: 위 실제 자료에서 보고서 재생성.

Qwen 신규 호출은 0회다. 다음 비교에서는 같은 입력·분석·선택 ID를 고정하고 카드 내용만 v2/v3로 바꿔야 한다. 카드 방향 안내는 새 조건 판정 엔진이 아니며, 품질 향상은 아직 측정하지 않았다.
