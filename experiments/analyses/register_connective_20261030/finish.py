"""Close the authorized experiment task after saved-artifact and UI checks."""
import json,sys
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[2];P=B/'private'
sys.path.insert(0,str(R/'src'))
from research_management.work import WorkStore
s=json.loads((P/'summary.json').read_text('utf8'));v=json.loads((P/'verification.json').read_text('utf8'))
assert v['actual_records']==100 and v['assembled_outputs']==97 and v['http_assets_match']
ui={'report_loaded':True,'all_50_cases_visible':True,'search_NEW004_one_result':True,'case_and_edit_details_opened':True,'actual_unjoined_jamo_reason_displayed':True,'screenshot_visually_checked':True,'tab_marked_deliverable':True}
(P/'ui_verification.json').write_text(json.dumps(ui,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
w=WorkStore(R)
task={'id':'register-connective-20261030','title':'말높임·연결어미 보완 및 Qwen 50문장 실험','actor':'Codex 총괄','stage':'결과 대조·보고','status':'completed','done':5,'total':5,'unit':'단계','unit_key':'stage','message':'100건 처리·97건 출력. Single 변경30/유지20/무출력0, Multi 31/16/3. 155개 검사 및 기록·해시·웹 확인 완료. 자연스러움 미해결, 판정 불일치 등 후속안은 보고서에 구분. /reports/register-connective-20261030/report.html'}
w.task(task)
print('완료: 말높임·연결어미 보완 + 실제 Qwen 50문장 × Single/Multi')
for arm in ('single','multi'):
 c=s['counts'][arm+'_new'];print(f'{arm}: 변경 {c["changed"]}, 원문 유지 {c["unchanged"]}, 출력 없음 {c["no_output"]}')
print(f'호출 {s["resources"]["physical_api_attempts"]}회 / 토큰 {s["resources"]["physical_total_tokens"]:,} / 실행 {s["resources"]["wall_seconds"]/60:.2f}분')
print('검사 155개 통과. 변경 수는 이전과 같으며 자연스러움 향상으로 판단하지 않음.')
print('남은 문제: 후보의 화계 해석, 어미 결합, 기능 사전 불일치, Multi 응답 종료/위치 오류.')
print('보고서: http://127.0.0.1:8767/reports/register-connective-20261030/report.html')
