# 생성 범위 비교 — 2026-11-04

수정 지시가 없을 때도 Qwen이 방언으로 바꾸도록 허용하면 결과가 좋아지는지 비교했다.

- A: 지정된 위치만 수정. 지시가 없으면 원문 유지.
- B: 지시가 없는 문장에서는 모델의 자유 생성 허용.
- C: 지정된 위치 밖에도 자유 생성 허용.

최종 비교는 기존50과 새개발12 각각 조건별 두 반복이다. 분석·KG·입력·모델 설정은 공유했다. 이전 v1 300회도 보존했다. 총 686 chat 호출·582,961 토큰이며 변경 수는 품질 점수가 아니다.

| 묶음 | A 변경 | B 변경 | C 변경 |
|---|---:|---:|---:|
| 기존50, 각 반복 | 17/50 | 44/50 | 44/50 |
| 새개발12, 각 반복 | 5/12 | 9/12 | 9/12 |

뜻·높임·시제 오류가 남아 운영 기본값은 유지했다. 카드/KG 수정 없음. 두 Orca 검토자의 설계·결과 검토 완료. ④ 전체 분석 재실행과 ⑤ 규칙 확장은 수행하지 않았다.

- [읽기 쉬운 비교 보고서](private/report.html): 62입력 원문/세 조건/반복별 출력, 검색·필터·메모 내보내기.
- [계획](PLAN.md), [결론·다음 단계](findings.md), [검토 반영](reviewer_resolution.md), [반말 평서 근거](plain_statement_notes.md).
- `private/latest_regression.json`, `latest_development.json`, `latest_dev_analysis.json`: 실행 위치.
- `private/v1_latest_regression.json`: 보존된 초안 실행 위치.
- `private/comparison.json`, `validation.json`, `run_integrity.json`, `report_manifest.json`: 집계·요청 통제·원본 무결성·보고서 재현 정보.

보고서만 다시 만들기(모델 호출 없음):

```powershell
python -X utf8 experiments/analyses/generation_scope_20261104/report.py
python -X utf8 -m unittest discover -s experiments/analyses/generation_scope_20261104 -p test_experiment.py
```

`experiment.py regression`과 `experiment.py development`는 실제 새 모델 호출을 수행한다. 이미 완료한 비교를 다시 실행하려면 새 연구 범위를 먼저 정한다. 원본 결과는 덮어쓰지 않는다. 비공개 실행 자료는 Git clone만으로 복원되지 않는다.

## 승인 참조 기반 후속 점검

[참조50 대응과 과거형 전달 점검](reference_followup.md): 실제300요청·출력 연결, 과거보존9위치 추출, 이전 접두부 실험 대조. 새로운 모델 호출과 KG 변경은 없음. `reference_followup.py`는 읽기 전용 원본 대조 도구다.

## 참조50 전체 진단 및 수정 후보

- [50문장별 문제·수정안 보고서](private/refinement/20261104T083517Z/report.html): 62조회 위치, 실제 요청·출력, 기존 두 Orca 검토자의 의견과 리드 판단.
- [다음 비교 계획](REFINEMENT_PLAN.md): 오류 위치 피드백, 전역 차단의 의존 조건, 과거/부정 계사부터 지식 연결. 운영 변경 전 후보다.
- `repair_feedback.py`: 기존 그래프의 한정된 표면 보존 조건에 대해 실패 위치를 반환한다. Qwen 호출·정답 참조 읽기·문장 자동 대체 없음. 입력/KG/첫 출력 결속과 변조 방지를 검사한다.
- 기존8개와 신규13개 코드 검사, 총21개 통과. 199개 원본 해시 동일, 보고서50행·166개 링크 검사 통과. 브라우저 시각 검사는 미실시.
- 기존 A100출력 중16개만 검사 범위에 해당하며6개 위반을 찾았다. 84개는 검사 밖이다. 자연스러움 점수가 아니다. 새 Qwen 호출0, 운영 KG 변경0.
- `validate_refinement.py`로 원본 무결성·두 검토 완료·HTML 링크/스크립트를 재검사할 수 있다. `private/.../final_manifest.json`에 산출물 해시를 보존했다.
