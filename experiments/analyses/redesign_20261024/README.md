# 재설계 분석과 결과 탐색

실험 원본은 `experiments/runs`에 보존하며, 이 폴더는 그 기록에서 계산한 분석이다. 원본 실험을 수정하지 않는다.

- [설계·실행법](../../../docs/research/RUNTIME_REDESIGN_20261024.md)
- [수치·오류·판단](../../../docs/research/RUNTIME_RESULTS_20261024.md)
- [브라우저 보고서](http://127.0.0.1:8766/reports/runtime/report.html)
- `private/previous50_audit.json`: 과거 50건 각각의 최초 확인 문제, 실제 분석·선택·응답과 파일 경로.
- `private/coverage_audit.json`: 전체 721개 항목의 원래 조건과 구현 상태, 12개 모듈 집계.
- `private/comparison.json`: 세 새 조건과 이전 실험의 수치·입력별 출력·실제 계획·조회 경로·실행 해시.
- `private/report.html`, `report.js`, `report.css`: 위 데이터를 읽는 로컬 보고서. 파일을 직접 더블클릭하기보다 위 브라우저 주소를 사용한다.
- `private/v2_snapshot`: 원본 저장소 고정 커밋에서 읽은 v2 코드 사본. 원본 저장소에 쓰기 작업 없음.
- `private/blind_review.json`: 방법명을 A/B로 숨긴 사람 평가용 초안. `private/blind_review_key.json`은 평가자에게 주지 않을 조건 대응표. 순서 seed 20261024.

블라인드 평가 초안의 자연스러움 1~5는 ‘매우 어색함~자연스러움’을 뜻하는 준비용 척도다. 평가자 수·지역·세부 척도·합의 절차는 실제 평가 전에 정해야 한다. 의미 보존과 불필요한 변경은 별도 기록한다. 출력이 null이면 실행 실패로 기록하고 자연스러움 0점으로 바꾸지 않는다. 현재 사람 점수는 전부 비어 있다.

재집계:

```powershell
python tools/analyze_runtime_experiment.py --batch 20261023T165740096535Z
python tools/render_runtime_report.py
python tools/research_manager.py serve
```

수치에는 생성 결과를 사람이 교정한 내용이나 LLM으로 만든 평가 점수를 포함하지 않는다. `delivery_manifest.json`은 이번 구현·문서·검증 파일 목록과 해시이며, 별도 실행 폴더의 불변 manifest를 대체하지 않는다.
