# 해라체 질문 지식 r3

별도 후보 버전. 운영 Neo4j/KG/카드를 대체하지 않았다.

- 원문 조건과 용례를 나눈 6개 용법, 9개 참고 관찰.
- 전체 12개 모듈의 식별자는 유지하지만 해당 모듈의 지식 전체를 정제했다는 뜻은 아니다.
- private/spec.json: 문헌 해석과 조건 명세. private/graph.json 및 nodes.jsonl/edges.jsonl: 실제 그래프.
- private/source_mapping.json: 기존 ID와 정제된 용법의 부분 대응. private/schema.json: 관계 의미와 분석 특징.
- 근거 원문·위치가 포함되어 private 데이터는 Git에 올리지 않는다. clone만으로 이 파일이 복원되지 않는다.
- 구현·검사·보고서: ../../../experiments/analyses/question_refinement_20261102/
- 수작업 분석으로 조회·전달만 검사. 실제 분석/Qwen 생성/현대 자연스러움 검증 미실행.
