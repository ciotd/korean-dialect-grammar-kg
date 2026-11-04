# 문헌 의미 정제 KG 첫 구성

의문문 구성1개·용법6개의 별도 후보 버전입니다. 전체 KG 완성이나 방언 생성 성능 검증이 아닙니다. 기존 공통 척추와12모듈 ID를 유지합니다.

- `private/foundation.json`: 원문 인용·해석·조건·실현형 명세
- `private/graph.json`: 실제 조건 관계로 컴파일한 그래프
- `source_mapping.json`: 기존5개 항목과의 부분 대응
- `schema.json`: 실제 노드·관계·분석값 명세
- `manifest.json`: 상태·범위·코드 및 데이터 해시

구현과 검증: `experiments/analyses/semantic_kg_rebuild_20261102/`. 이 버전은 기존 Neo4j·생성기를 교체하지 않습니다. 전체721개 정제 작업대장은 해당 실험 폴더에 있습니다.
