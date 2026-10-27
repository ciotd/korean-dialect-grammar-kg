# 검색·실행 분리 비교 산출물

[통합 보고서](http://127.0.0.1:8766/reports/search-execution/report.html) · [결과 설명](../../../docs/research/SEARCH_EXECUTION_RESULTS_20261025.md)

private/에 인터랙티브 보고서와 실제 집계 data.json, 사람이 입력할 blind_review.json, 연구자용 대응표 blind_review_key.json이 있다. 대응표는 웹으로 제공하지 않는다. 원본 실험은 experiments/runs에 불변 파일로 보존한다. delivery_manifest.json은 보고서 파일 해시다.

재생성: python tools/report_search_execution.py --regression 20261025T085653301020Z --evaluation 20261025T090456534523Z --diagnostic 20261025T090633179738Z
