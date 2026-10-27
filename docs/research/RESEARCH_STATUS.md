# 연구 실행 현황

자동 생성: `python tools/research_manager.py sync`. 수치는 실행 상태이며 방언 품질 점수가 아니다.

| Run ID | 용도 | 상태 | 입력 | 출력 형식 통과 | 분석 실패 |
|---|---|---|---:|---:|---:|
| 20261025T090633416523Z_runtime_analysis_kiwi_regression | regression | completed | 50 | 0 | 11 |
| 20261025T090633179738Z_runtime_analysis_qwen_regression | regression | completed | 50 | 0 | 14 |
| 20261025T090456827614Z_runtime_multi_evaluation | evaluation | completed | 12 | 12 | 0 |
| 20261025T090456534523Z_runtime_single_evaluation | evaluation | completed | 12 | 12 | 0 |
| 20261025T085653584686Z_runtime_multi_regression | regression | completed | 50 | 47 | 0 |
| 20261025T085653301020Z_runtime_single_regression | regression | completed | 50 | 49 | 0 |
| 20261025T085610380100Z_runtime_multi_smoke | development | completed | 4 | 3 | 0 |
| 20261025T085610187632Z_runtime_single_smoke | development | completed | 4 | 4 | 0 |
| 20261023T165740502855Z_runtime_multi_regression | regression | completed | 50 | 48 | 0 |
| 20261023T165740319929Z_runtime_single_regression | regression | completed | 50 | 48 | 0 |
| 20261023T165740096535Z_runtime_analysis_kiwi_regression | regression | completed | 50 | 0 | 10 |
| 20261023T165529268792Z_runtime_multi_smoke | development | completed | 4 | 3 | 0 |
| 20261023T165529017937Z_runtime_single_smoke | development | completed | 4 | 4 | 0 |
| 20261023T090255985956Z_qwen_kg_first50 | evaluation_reference | completed | 50 | 35 | 15 |
| 20261023T085916247048Z_qwen_kg_smoke | development | completed | 5 | 5 | 0 |
| 20261023T085522286984Z_qwen_kg_smoke | development | completed | 5 | 5 | 0 |
| 20261023T085237851535Z_qwen_kg_smoke | development | completed | 5 | 0 | 5 |
| 20261023T085008864199Z_qwen_kg_smoke | development | completed | 5 | 5 | 0 |

확정 50건 원문은 보존한다. 2026-10-24 이후 실행은 사용자 요청에 따라 회귀 실험으로 사용하며 독립 최종 평가셋이 아니다.
정답 및 사람 평가 없음: 자연스러움·정확도는 미측정. KG 없는 통제 실험도 아직 없다.
대시보드: `python tools/research_manager.py serve` → http://127.0.0.1:8766/
상세 절차: [연구 관리 절차](../workflows/RESEARCH_MANAGEMENT.md).
