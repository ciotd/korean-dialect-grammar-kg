from pathlib import Path
import importlib.util
R=Path.cwd();H=R/'experiments/analyses/support_expansion_20261104';s=importlib.util.spec_from_file_location('x',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
for who in ['codex','claude']:
 d=H/'private/reviewers'/who
 role='실제 request/response/packet을 대조해 전달 코드 누락·고정조건 위반·집계 오류가 있는지 확인. 특히 prefix 실험의 ADVCE006A/QUAL003에 preserved_source_prefix가 실제 요청에 있었는지, Qwen원문응답과출력이같은지.' if who=='codex' else '새 지식 5위치의 실제 출력과 남은 생성 오류를 구별. 설명했예/같예가 이번 원문 보존 계약 위반이라는 판단과 문헌상 가능한 모든 형태를 부정하는 주장을 구분. 반복 카드변경보다 다음 진단 우선순위 1개 권고.'
 prompt=f'''마지막 결과 검토입니다. 원문전체/KG재검토 반복말고 결과와전달만 확인해주세요. {H}/private/latest_full50.json(r7 50),latest_handoff.json,latest_realization.json,latest_typed.json,latest_prefix.json 각 경로의 private/results.json과必要한records. r7같은분석지원14→19;새5위치 친구라예/선생님이라예/동료라예/맛있어예/챙기셨어예. 하지만 설명해예 등남음. 17입력19위치고정4비교: 설명축약도일부실패지속; r8결합예로수정하면설명했예등악화; typed지시와 원문보존prefix추가도5/9 해당위치에운영계약불일치지속. 따라서r8/r9운영미채택,현재r7유지. 자연스러움정답률주장없음. 원문요제거+예후조건검사는형태보존진단일뿐. {role} 문제위치→실제근거→수정안, 최종수치해석의차단오류있으면명시. 새모델호출/수정금지. 자기 {d/'results_review.md'}만작성. 끝 END_RESULTS_{who.upper()}_20261104.'''
 (d/'results_prompt.txt').write_text(prompt,'utf8');x.dump(d/'results_receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,'sent',flush=True)
