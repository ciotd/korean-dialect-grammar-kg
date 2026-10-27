# 실행·검색·보고서 검증

96개 자동 검사 통과. 한 차례 대시보드 새로고침 HTTP500은 단독 5회 및 전체 재실행에서 재현되지 않았으며 test_log_transient_failure.txt에 보존했다.

- test_log.txt / test_exit.json: 최종 검사 결과
- search_coverage.json: 721개 문헌 항목의 실제 Neo4j 조회
- validation.json: 18개 실행·7,023개 파일 해시 및 원본 그래프 일치
- private/browser_qa.json: 필터·문장 추적·실패 대조·평가 양식·모바일·링크 검사

재검증: python tools/validate_search_execution.py --credentials C:/Users/ciot28/Documents/Codex/neo4j-kg-local/credentials.json
브라우저 검사: node tests/qa_search_execution.cjs
