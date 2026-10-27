# 연구 관리 workflow

**2026-10-24 현행 정책:** 사용자 요청에 따라 기존 50건은 회귀 테스트셋으로 사용하며 오류 분석과 개선을 허용한다. 원문과 과거 실행은 보존하고, 독립 최종 평가셋으로 주장하지 않는다. 아래 2026-10-23의 개발/평가 분리 문구는 당시 정책이다. 새 실행기와 비교 설계는 [실행층 재설계](../research/RUNTIME_REDESIGN_20261024.md)를 따른다.
## 실행 명령

저장소 루트의 VS Code 터미널에서 Python 3.10 이상으로 실행한다. 추가 패키지는 없다.

```powershell
python tools/research_manager.py sync
python tools/research_manager.py serve
```

브라우저: **http://127.0.0.1:8766/**. 터미널을 유지하고 종료할 때 Ctrl+C를 누른다. 부팅 시 자동 시작하도록 설치하지 않았다.

```powershell
# 확정 평가 문장과 새 개발 입력의 중복 검사
python tools/research_manager.py check-data data/dev_inputs.jsonl --role development
# 실제 Run ID로 대체
python tools/research_manager.py compare PREVIOUS_RUN_ID NEW_RUN_ID
python tools/research_manager.py verify RUN_ID
python tools/research_manager.py brief RUN_ID --previous PREVIOUS_RUN_ID
```

기존 `tools/run_kg_pipeline.py`에 자동 관리 단계가 연결되어 있다. `--phase smoke`와 `--phase development`는 개발용이며 확정 50건과 동일 문장·공백 변형을 차단한다. `--phase first50`은 기존 50건 해시를 확인한다. `--phase evaluation`은 추가 평가 데이터에도 쓴다. 평가 옵션을 개발 입력 검사 회피용으로 쓰지 않는다.

모델 실행은 [기존 재현 명령](../research/PIPELINE_IMPLEMENTATION.md)의 Neo4j·Qwen 설정을 따른다. 인증정보는 로컬 파일에만 둔다. 이번 관리 시스템 검증에는 기존 5개 실행과 합성 테스트를 사용했고 새 모델 호출은 하지 않는다.

## 연구 관리 Agent의 작업 절차

현재 Codex 연구 Agent를 위한 절차다. 상시 AI가 자동 실행되는 것은 아니다.

1. `AGENTS.md`와 `RESEARCH_STATUS.md`를 읽고 관리·해석·새 실험 중 승인된 작업 범위를 구별한다.
2. `sync`로 기록을 모으고 누락·미완료·오류를 숨기지 않는다.
3. `brief`로 검토 자료를 만든다. 같은 입력의 이전 실행을 우선하되 비교 판정의 제한을 그대로 설명한다.
4. 실패 유형의 대표 사례와 변경 출력을 실제 단계별 원본과 대조한다.
5. **전체 그림 → 선택 이유 → 기술 근거**로 설명한다. 관찰, 해석, 검증할 가설, 권고를 구별한다.
6. 수치 오류는 원본을 덮어쓰지 않고 계산 코드와 정정 기록으로 고친다. 이미 발표한 결론의 변경 이유를 남긴다.
7. AI 검토는 `experiments/analyses/<Run ID>_<검토이름>/`에 저장한다. 실제 문장·원문이 있으면 `private/`에 둔다. 검토자(AI/사람), 시각, 원본 Run ID·해시·단계를 명시한다.
8. 일반 설계는 기존 문서를 갱신한다. 새 HTML이 유용할 때 추가하고 `report_navigation.json`에 연결한다.
9. 설계 변경은 `DECISIONS.md`에 문제·근거·대안·이유·파일·검증·한계를 남긴다.
10. 개선은 별도 개발 입력에서 검사한다. 평가 50건의 원문·과거 결과를 고치지 않고 새 평가는 새 Run ID로 실행한다.

## 완료 확인과 복구

- 원본·설정·버전·실패 기록, 검증 범위(메타데이터/전체 파일)가 확인되는가?
- 비교 불가 항목을 0이나 개선율로 표시하지 않았는가?
- 구현 테스트와 사람 품질 평가를 구별했는가?
- 대시보드의 입력별 단계·관련 문서가 열리는가?

색인은 원본이 아니다. 손상되면 서버 종료 후 `experiments/management/private/index.sqlite3`를 다른 이름으로 보관하고 `sync`로 다시 만든다. 실행 원본·비공개 원자료·평가 입력을 별도로 백업한다. Git에서 제외된 `private/`는 clone만으로 복원되지 않는다.
