# 구현 공간

`kg_pipeline/`에 Qwen 분석·Concept 연결·Neo4j 조회·근거 선별·Qwen 생성·검증·실행 기록 모듈을 구현했다. 전체 사용법과 제한은 [구현 기록](../docs/research/PIPELINE_IMPLEMENTATION.md)을 참고한다.

실행 진입점은 `tools/run_kg_pipeline.py`, 테스트는 `tests/test_kg_pipeline.py`이다. 원래 KG의 실행 승인 상태를 바꾸지 않고 문헌 참고 실험을 수행한다. 실제 생성 결과의 언어학적 정확성은 별도 평가가 필요하다.


`kg_runtime/`: Kiwi 원문 구간 분석, 기존 SourceAtom에 결합한 실행기, 실제 Neo4j 조회, Single/Planning+Worker 실행과 변환 계획 검증. [설계](../docs/research/RUNTIME_REDESIGN_20261024.md).
