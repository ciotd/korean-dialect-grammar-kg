# 최소 지시 수행 진단

[쉬운 결과 보고서](private/report.html)에서 결과·실제 출력·다음 작업을 확인한다.

- 실제 135호출: 기존 50건의 9위치(표면형8개), 5조건×3반복. 새 평가 문장135개가 아니다.
- A짧은지시3/27, B기존시스템3/27, C기존KG추가18/27, D어절만14/27, E형식강제해제12/27.
- D/E 각2회 응답미확보. 자연스러움 점수가 아니라 지정 문자 편집 수행 검사.
- KG추가만으로 해결되지 않았고, KG가 없어도 실패했다. 실제원인미확정. r7 유지, 새 전체50 미실행.
- 정답 완성문장 미전달, Qwen raw 출력 보존. 기존원문/실험/KG 미수정.

| 파일 | 용도 |
|---|---|
| PLAN.md / WORD_PLAN.md | 실행 전 조건·분기 고정 |
| run.py / word_probe.py | 실제 비교 실행기. 재실행시 새 Run ID·모델 호출 발생 |
| diagnostic_transport.py | 기존 전송부 재사용, response_format만 선택적으로 제외하는 진단용 복사본 |
| audit.py | 모델 호출 없이 저장된 요청·응답·집계·해시 대조 |
| report.py | 실제 summary에서 보고서 재생성 |
| private/latest.json / latest_word.json | 실제 실행 위치 |
| private/summary.json / validation.json | 재계산된 결과·검증 |
| reviewer_resolution.md | 독립 검토 반영·수치 정정 |
| private/reviewers/ | 기존 Orca 두 검토자의 지시문·원문 검토 |
| private/server_check.md | 서버 담당자에게 전달 가능한 확인 요청 |

검증: 기존관리38검사+실험설계3검사 통과. 추가 진단 분류 검사는 test_audit.py 참고.
관리 오류도 수정: failure.json이 있는 중단 실행을 완료로 표시하지 않는다. 준비실패3개 원본은 보존했다.

## 서버 명령 수신 후 추가54회

서버 명령은 private/server_launch_20261104.json에 사용자 제공 정보로 기록했다. 실제 프로세스 조회와 구분한다. temperature만0/0.7로 바꾼 두조건은18/27,16/27로 개선이 없어 미채택. 실제54요청의 차이·출력·해시를 audit_temperature.py로 확인했다. 원본연결은 private/latest_temperature.json. 서버상세확인은 inspect_qwen_server.py 참고.
