# ① 정보가 끊긴 위치 확인

기존 50문장의 실제 분석·조회·생성 기록을 대조했다. 새 Qwen 실험이나 KG·운영 코드 수정은 하지 않았다.

- 읽기: [쉬운 보고서](private/report.html)
- 실행 범위: [PLAN.md](PLAN.md)
- 현재 연구 약속: [CURRENT_RESEARCH_PLAN.md](../../../docs/research/CURRENT_RESEARCH_PLAN.md)
- 코드: `audit.py`가 저장 기록을 검증·집계하고 `report.py`가 같은 자료로 화면을 만든다.
- `private/cases.json`: 50문장별 원문·출력·단계별 근거
- `private/targets.json`: 62위치별 네 구성 조회·조건·전달 결과
- `private/restriction_ledger.json`: 제한 위치, 관찰된 영향, 수정 후보
- `private/restriction_reasons.json`: 조건별 제외 근거
- `private/validation.json`: 원본 1,023파일 해시와 요청·응답 검증
- `private/reviewers/`: 기존 Orca 두 검토자의 지시·전송 확인·의견 원본

## 결과

62위치 중 19곳을 전달했다. 미전달 43곳은 실행 경로상 범위 밖 29, 후보 없음 12, 분석 미확정 2다. 이 경로 수를 지식 공백의 크기로 해석하면 안 된다. 분석 오류도 포함되어 있다.

수정 지시가 없었던 33문장은 모두 원문 유지였다. 지시 있는 17문장은 일부 변경됐지만, 한 위치(LONG001 W12)는 그대로였다. 과거 표지를 잃는 생성 오류도 확인했다. 최종 저장 출력 50건은 모두 Qwen 원시 응답과 같다. 검사 코드가 원문으로 되돌린 것이 아니다.

## 재현

저장소 루트에서 다음을 실행한다. 외부 모델 연결이 필요 없다.

```powershell
python experiments/analyses/restriction_audit_20261104/audit.py
python experiments/analyses/restriction_audit_20261104/report.py
python experiments/analyses/restriction_audit_20261104/test_audit.py
```

원본 실행: `20261104T013633051461Z_support_expansion_full50`. 파일의 `private/` 부분은 비공개 연구 자료이며 기존 정책대로 커밋하지 않는다.

다음은 ② 비교 조건 확정이다. 이번에 발견한 제한을 일괄 해제하지 않는다. 이전에 실패한 비교를 반복하지 않도록 가설·바꾸는 요소·고정 요소·종료 기준을 먼저 정한다. 논문 효과 평가는 독립 입력·공정한 기준선·사람 평가가 별도로 필요하다.
