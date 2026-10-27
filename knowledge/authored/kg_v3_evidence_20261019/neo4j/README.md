# Neo4j import

대상: Neo4j 5.x/Cypher 5. APOC 불필요. DB 적재는 아직 실행하지 않았습니다.

1. 이 폴더의 CSV를 **Neo4j 서버** import 디렉터리의 `kg_v3_evidence_20261019/` 하위에 복사합니다. 클라이언트 폴더가 아닙니다.
2. 서버 설정에서 로컬 CSV 읽기가 허용되어 있는지 확인합니다. Aura 등 로컬 파일 미지원 환경에는 파일 경로를 그대로 사용할 수 없습니다.
3. 대상 데이터베이스를 선택하여 `cypher-shell -d <database> -f import.cypher`를 실행합니다. 인증은 환경 설정이나 대화형 입력으로 제공합니다. 비밀번호를 스크립트에 기록하지 않습니다.
4. `explore.cypher`의 집계와 `validation/validation.json`의 통계를 대조합니다.

Import는 dataset_id+id로 MERGE합니다. 같은 산출물의 재실행은 중복을 만들지 않습니다. 다른 실행은 다른 dataset_id를 사용해야 합니다. 삭제 쿼리는 포함하지 않습니다. 병렬 import는 수행하지 마세요. 파일 적재와 Cypher 파싱의 실제 성공은 제공된 DB에서 별도 확인해야 합니다.

문헌 원자(SourceAtom)는 실행 Rule이 아닙니다. 기존 설계의 중첩 조건과 속성은 properties_json에 보존하며, 이 문자열은 실행 코드가 아닙니다. 그래프 시각화에는 title을 캡션으로 사용하세요.

공식 참고: https://neo4j.com/docs/cypher-manual/5/clauses/load-csv/ 및 https://neo4j.com/docs/cypher-manual/5/constraints/create-constraints/
