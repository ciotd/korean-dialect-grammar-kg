"""Dispatch user-authorized follow-up to the two existing Orca reviewers."""
from pathlib import Path
import json,importlib.util,sys
R=Path.cwd();H=R/'experiments/analyses/generation_scope_20261104'
spec=importlib.util.spec_from_file_location('exchange',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
out=Path(json.loads((H/'private/latest_refinement.json').read_text('utf8'))['directory'])
for who in sys.argv[1:] or ('codex','claude'):
 dest=out/'reviewers'/who;dest.mkdir(parents=True,exist_ok=True)
 role=('실제 전달·조건 차단·오류 검사·기존 진단 중복 검토. boundary_qwen/runtime.py의 전체 boundary unknown이 국소 예 결합까지 차단하는지, 실제 DEV026 기록과 대조. 후보 수정은 의존 조건별 차단과 생성 후 구체 오류 피드백이며 아직 실행 안 함. 단순 prompt/prefix 재실험과 차이·한계 검토.' if who=='codex' else '승인 참조를 일반화 가능한 문법/어휘 보완으로 연결할 때 조건·높임·화행을 검토. historical_family_evidence의 표현 존재를 입력 대응 증명으로 과장하지 말 것. 참조의 모든 생략/어휘 치환을 필수로 요구하지 말 것. 50개 모두 실제 참조·출력·현재 지식과 대조하고 짧은 문제위치→근거→수정안 표를 작성.')
 prompt=f'''사용자 후속 승인: 승인 참조 기반 보완과 A의 과거형 손실을 확인하자는 요청 뒤 ‘진행해’. 이전에 이번2·3단계 자료를 기존 두 검토자에게 전달하도록 승인됨. 이번은 같은 자료의 후속 수정안 검토이며 새 실험 아님.
읽을 묶음: {out}. cases.json은50개 전체 현재 입력/승인참조/A·B·C 두반복/실제전달actions/62위치analysis/query경로/역사적관련카드. graph.json은 현재r7 실제그래프. historical_family_evidence.json은 옛카드·짧은원문발췌이며 현재실행근거와구별. prior_experiments.json은중복진단방지.
역할: {role}
추가 읽기 허용: {H}/reference_followup.md, 해당 폴더 실제 요청·응답 경로, support_expansion_20261104/runtime.py와run.py, boundary_qwen_20261103/runtime.py와run.py, support_expansion의typed_delivery.py/prefix_probe.py/prompt_contract_probe.py, minimal_instruction_20261104/README.md. 인증정보/test.py/환경변수/PDF원본 읽기 금지. 상대 검토자의 의견 읽기 금지.
반드시 문제 위치→실제 근거→구체 수정안. 관찰/가설/제안 구별. 과거형정보는 실제전달됨. 모델출력편집실패를 전송누락으로 단정 금지. 현재11규칙을 연구영구범위로 정하지말고 역사적자료와실행구성 연결의공백을 구별.
새 Qwen 호출·KG/운영코드수정·서브에이전트생성 금지. 출력은 {dest/'review.md'} 하나만 작성. 모든50 ID를 짧게라도 포함. 미확인근거는미확인. 새실험이 필요하면 이전실험과차이·바꿀것·고정할것·종료기준 제시. END_REFERENCE_REFINEMENT_{who.upper()}_20261104 로끝내세요.'''
 (dest/'prompt.txt').write_text(prompt,'utf8')
 receipt=x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5'])
 x.dump(dest/'receipt.json',receipt);print(who,'dispatched',flush=True)
