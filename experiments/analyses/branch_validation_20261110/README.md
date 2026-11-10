# 조건별 검사·전달 보완 (2026-11-10)

먼저 [쉬운 보고서](private/report.html)를 읽는다. [결과와 다음 작업](RESULTS.md), [두 검토자 의견 반영](REVIEW_RESOLUTION.md), [범위](PLAN.md)를 연결했다.

완료한 것은 오프라인 조건 재생·전달 코드 보완·171문장의 실제 Kiwi 관찰 및 두 Orca 검토자 대조다. **171문장 전체 Qwen 분석/조회/생성 실험은 아직 아니다.** 전체 문헌의 언어학적 재검증이나 KG 정제 완료도 아니다.

재현: validate_branches.py → check_natural_examples.py → replay_delivery.py → run_checks.py → build_report.py. 모든 스크립트는 이 폴더에서 기존 KG·과거 실행을 읽고 결과를 기록하며 모델 API를 호출하지 않는다. 중간판은 private/pre_final_records.zip과 최초 실패 기록으로 보존했다. 재실행 전 기존 결과를 버전별로 보존한다.

- summary.json: 990 논리 사례·443 전달 검사항목·코드 해시.
- natural_summary.json: 57분기171제안 예문의 형태 관찰. 모델 검토 의견은 사람 정답이 아님.
- delivery_replay_summary.json: 기존50 중49분석 고정 재생과 최종 작성 payload 직렬화 확인.
- test_summary.json: 관련 자동 검사와 로그.
- private/*review.md, *followup.md: 실제 두 검토자의 원문.
- private/claude_examples.json: 최초171후보, 수정·학습 정답으로 주입하지 않음.
- private/natural_observations.json: 표시 대상과 실제 분석 단위·형태 불일치.
- private/replayed_writer_payloads: 전후 작성 입력. 서버 전송하지 않은 오프라인 재생 결과.
- private/version_receipt.json: 완료 백업·체크포인트 기록(생성 후).

출처·검토 정보는 실행 그래프 밖으로 분리한 이전 버전을 유지한다. 전달 단계에서는 실제 조건과 제한을 보존하며 이번에 확인된 낡은 문장만 정리했다. 설명과 조건이 어긋나는 미해결 항목은 숨기지 않았다.
