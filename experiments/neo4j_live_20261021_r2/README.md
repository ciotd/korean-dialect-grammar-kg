# Neo4j 실제 적재 — 2026-10-21

브라우저: http://localhost:7474/browser/  
Bolt: bolt://localhost:7687  
DB / 사용자: neo4j

비밀번호는 저장소 밖 `C:/Users/ciot28/Documents/Codex/neo4j-kg-local/credentials.json`에서 확인합니다. 인증정보는 이 실행 기록에 복제하지 않았습니다.

## 파일

- report.html: 실제 DB 적재 결과 요약
- live_validation.json: 적재 2회 및 전체 저장 속성·탐색 쿼리 검증
- bolt_check.json: cypher-shell의 실제 Bolt 인증 접속 확인
- server_settings_verified.json: 실행 중인 서버 설정 확인
- downloads.json: 설치 파일 URL과 SHA-256
- ../neo4j_live_20261021/failed_attempt.json: 최초 실패와 조치 기록
- ../../tools/kg_v3/verify_neo4j_live.py: 재현용 적재·검증 코드

## 재시작

Neo4j Community 5.26.32와 Microsoft OpenJDK21을 사용자 폴더에 배치했습니다. Windows 서비스나 자동 시작으로 등록하지 않았습니다. 재부팅 후 다음 명령을 실행하고 창을 유지합니다. 이미 실행 중인 경우 중복 실행하지 않습니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/Users/ciot28/Documents/Codex/neo4j-kg-local/start.ps1"
```

해당 창의 Ctrl+C로 종료할 수 있습니다. DB는 `C:/Users/ciot28/Documents/Codex/neo4j-kg-local/neo4j-community-5.26.32/data`에 보존됩니다. 실행 정책과 JAVA_HOME은 해당 프로세스에만 적용하며 시스템 설정은 변경하지 않았습니다.

## 실제 적재에서 발견한 수정 사항

최초 적재는 nodes_ReviewIssue.csv의 중첩 JSON 따옴표 처리에서 실패했습니다. `neo4j.conf`에 아래를 적용하고 재시작했습니다.

```properties
db.import.csv.legacy_quote_escaping=false
```

기존 JSONL·CSV·Cypher는 변경하지 않았습니다. 첫 실패에서 커밋된 노드는 재실행의 MERGE로 갱신했습니다. 최종 두 번째 전체 적재에서 노드·관계가 추가 생성되지 않는지 확인합니다. 2026-10-19 보고서의 ‘DB 미검증’은 당시 상태이며, 실제 적재에 관한 최신 근거는 이번 실행 결과입니다.

## 바로 탐색하기

Neo4j Browser에 로그인한 후 실행합니다.

```cypher
MATCH p=(s:Framework {dataset_id:'kg_v3_evidence_20261019_r2'})-[:has_module]->(m:Module) RETURN p;
```

```cypher
MATCH p=(d:SourceDocument {dataset_id:'kg_v3_evidence_20261019_r2'})<-[:part_of_document]-(s:SourceSpan)<-[:analyzed_by]-(c:Claim)-[:interpreted_as]->(g)-[:in_module]->(m:Module) RETURN p LIMIT 30;
```

본 검증은 DB 적재·쿼리·정보 보존에 대한 검증입니다. 기존 721개 방언 항목의 전수 언어학 검증이나 방언 생성 실험을 뜻하지 않습니다.

공식 설치: https://neo4j.com/docs/operations-manual/current/installation/windows/  
CSV 설정 이름: https://neo4j.com/docs/upgrade-migration-guide/current/version-5/changelogs/configuration-settings/
