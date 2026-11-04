# 연구 진행·검토·결정 운영

## 무엇을 볼 수 있나

기존 연구 관리 서버의 `/work` 화면이다. 이번 실행 주소는 **http://127.0.0.1:8767/work**.
기존 8766 서버는 중단하지 않았다. 재시작할 때 프로젝트 루트에서 다음을 실행한다.

```powershell
python tools/research_manager.py serve --port 8767
```

- 브라우저는 2초마다 실제 작업 기록을 읽는다. 기록되지 않은 작업이나 모델 내부 사고를 자동으로 알아내지는 않는다.
- `tools/run_kg_cards.py`의 다음 실행부터 공통 분석·Single·Multi 처리 완료 수가 자동 기록된다. 프로세스 생존 기록은 20초 간격이다. 사전 모델 접속과 Kiwi 준비는 이 계측 범위 앞에 있다.
- 완료 수에는 실패한 입력도 포함된다. 성공률·자연스러움 점수로 사용하지 않는다.
- 사람/총괄의 설계·자료 확인 작업은 `tools/research_work.py task`로 실제 상태를 기록한다. 완료 단위가 없으면 퍼센트를 만들지 않는다.
- 남은 시간은 현재 단계·같은 실행 조건의 처리 간격이 3개 이상 쌓인 때만 최근 최대 20개 간격의 최소~최대 처리율로 계산한다. 통계적 신뢰구간이나 보장 시간이 아니다. 병렬 처리의 완료 간격이라 개별 모델 호출 지연과 다르다. 대기·중단·완료·90초 이상 갱신 지연에는 추정을 중지한다.
- 조회 창의 서버 확인 시각과 작업 자체의 마지막 기록 시각을 구별한다. 창만 갱신된다고 연구가 진행된 것은 아니다.

## 승인 약속

1. 기본 결정은 채팅. 총괄이 사용자 발언의 출처와 인용을 함께 전사한다. 추측한 승인을 등록하지 않는다.
2. 여러 항목은 대시보드에서 항목별 승인/수정 요청/보류를 선택한 뒤 함께 저장한다. 수정 요청에는 설명이 필요하다.
3. 수정안은 **문제·실제 근거·변경 전후·적용 범위·검증 방법**을 갖는다. 검토자가 아직 변경안을 직접 검토하지 않았다면 그 사실을 표시한다.
4. 새 수정안 버전은 이전 승인을 승계하지 않는다. 다른 창에서 먼저 결정된 항목은 오래된 화면에서 덮어쓰지 않는다.
5. 승인 기록과 적용 완료 기록은 다르다. 승인 버튼은 코드·KG를 수정하거나 Qwen을 호출하지 않는다. 총괄이 승인 범위를 읽고 작업하며, 적용 파일과 검증 결과를 따로 남긴다.
6. 기존 승인 범위 내 확인·테스트는 계속 수행한다. 의미가 달라지는 KG 변경, 새로운 모델 실험/학습은 해당 범위를 확인받는다.
7. 사용자 입력은 로컬 SQLite에 저장한다. 브라우저를 닫아도 보존되지만 서버가 꺼지면 화면 갱신·결정 저장은 멈춘다. 서버 부팅 자동 실행은 설치하지 않았다.

## 관리 명령과 재현 정보

`python tools/research_work.py <operation> --file <UTF-8 JSON>`.
운영자는 구조화 파일을 사용하되 사용자는 화면의 한국어 표기와 채팅으로 검토한다.

| operation | 용도 | 핵심 입력 |
|---|---|---|
| task | 실제 진행 상태 기록 | id, title, actor, stage, status, done/total(선택), unit_key(같은 반복 단위), message |
| proposal | 새 수정안 또는 다음 버전 | id, version, title, before, after, reason, scope, verification |
| chat-decision | 채팅 결정 전사 | items(id/version/revision/action/comment), reference, quote |
| applied | 승인된 버전의 적용 결과 기록 | id, version, revision, artifacts, verification |
| state | 전체 현재 기록 조회 | 입력 없음 |

영속 기록: `experiments/management/private/workflow.sqlite3`. 이 파일은 재생성 가능한 실험 색인과 달리 **사용자 결정 원본**이므로 백업해야 한다. Git 제외 경로이며 clone만으로 복원되지 않는다. 서버를 종료한 상태에서 복사하거나 SQLite backup 기능을 사용한다.

`src/research_management/work.py`: 버전·결정·진행 이벤트 저장과 추정 계산.
`src/research_management/live.py`: 기존 실험기에 연결한 완료 이벤트·생존 기록. 모델 입력·검색·생성 알고리즘은 변경하지 않는다.
`src/research_management/web/work.*`: 조회·결정 화면.
`tools/seed_work_review_20261029.py`: 이번 수정 제안과 대시보드 구현의 명시 승인을 등록. 반복 실행 시 기존 결정을 보존한다.

검증 명령:

```powershell
python -m unittest discover -s tests -p test_research_work.py -v
python -m unittest discover -s tests -p test_research_management.py -v
```

초기 50개 검토는 기존 `full_review_20261029/private/casebook.json`을 읽으며 덮어쓰지 않는다. 검토자 원문에는 다른 언어나 추론·잘못된 판단이 남아 있을 수 있다. 총괄 관찰·변경 제안과 구별해 보여준다. 초기 변경 제안에 붙인 검토자 요약은 새로운 독립 검토 결과가 아니다.
