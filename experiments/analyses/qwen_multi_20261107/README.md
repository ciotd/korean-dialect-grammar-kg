# Kiwi 없이 Qwen이 분석하고 작성하는 분업 경로

2026-11-07 사용자의 요청에 따라 추가한 구현이다. 이전 경로·KG·실험은 보존했다. 아직 품질 개선이 검증된 운영 기준은 아니다.

## 실행 흐름

원문 → Qwen 구조 분석 → Qwen 의미·관계 분석 → 기존 KG 조건 조회 → Qwen 후보 선택·전체 문장 작성 → Qwen 별도 검토 → 필요한 경우 작성자 한 번 수정.

네 역할은 같은 모델을 별도 문맥으로 호출한다. 앞 결과가 뒤 입력이므로 기본은 순차 처리이며 동시에 네 모델을 가동한다는 뜻이 아니다. Kiwi는 새 경로에서 사용하지 않는다. 원문 위치·ID·허용값 검사와 KG 조회는 코드가 맡고, 문법 판단과 최종 문장 작성은 Qwen이 맡는다.

## 읽을 자료

- `private/report.html`: 일반 독자를 위한 흐름·실제 지시문·입력별 결과
- `prompts.md`: 코드에서 가져온 실제 지시문과 역할을 나눈 이유
- `DECISIONS.md`: 기존 Orca Claude·Codex 검토와 채택/보류 이유
- `OBSERVATIONS.md`: 첫 실행에서 실제로 정보가 끊긴 위치
- `private/tests_final.json`: 모의/자동 구조 검사 결과. 언어 품질 점수 아님

실행 코드는 `src/kg_pipeline/multi_agent.py`, 실행·기록 도구는 `tools/run_qwen_multi.py`, 자동 검사는 `tests/test_qwen_multi.py`다. Qwen 최종 출력을 코드 조합 결과로 바꾸지 않는다. 실패한 초안을 최종 출력으로 채우지 않는다.

## 재실행

명시적 모델 호출용 명령:

```powershell
python tools/run_qwen_multi.py --execute --inputs experiments/analyses/qwen_multi_20261107/development6.jsonl --phase development --max-calls 30 --deadline "<시간대가 포함된 미래 ISO시각>"
```

`--separate-plan`은 선택 계획을 추가 호출로 분리하는 비교 옵션이다. 이 옵션의 품질·비용 이득은 아직 시험하지 않았다. 실제 호출에는 로컬 서버 인증 설정이 필요하지만 키를 보고서나 Git에 넣지 않는다.

새 Run ID에 입력·KG·프롬프트·코드 해시·요청·응답·집계가 보존되고 연구 관리 시스템에 등록된다. 6문장은 개발 진단용이며 독립 평가셋이 아니다. 빈 후보가 생겨도 원문 유지를 강제하지 않으므로 모델 자체 지식과 KG 근거의 기여를 구분해야 한다.
