from pathlib import Path
import importlib.util,json,sys
R=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('exchange',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
for who in sys.argv[1:] or ('codex','claude'):
 d=H/'private/reviewers'/who;d.mkdir(parents=True,exist_ok=True)
 role=('검토1: generation_scope_20261104/repair_feedback.py와REFINEMENT_PLAN.md의 중립/구체후속12호출비교 타당성, 논문에서 주장가능한범위. 검토2: condition_bridge_20261103/bridge.py와boundary_qwen_20261103/runtime.py의 전역 boundary_unknown 차단, DEV026나왔어요와계세요분석불일치. 기존 r7을유지하면서 최소 국소수정이논리적으로가능한지 구체코드위치/조건/반례제시. 검토3: easy-dataset의선정/개발평가분리/무KG·동일지식텍스트·조건KG대조설계. 각항목실제코드/기록참조. 직접수정하지말것.' if who=='codex' else '검토1: 과거/부정계사 아니었어요·뜻이었어요·애들이었어요의해체+예조건을 기존r7에일반적으로연결할수있는지. source_recheck.json이참조한기존본문/근거와현재graph실제조건을확인하고필요근거·해석·반례·정확한추가노드/관계권고. 단순요→예전면치환이나사용자정답암기금지. 검토2: 쉬운데이터기준과지원/미지원대조군, 자연스러움평가역할. 30개후보를만들수있으나회귀50/기존DEV와중복하지않고주요절1개,각한문법대립. 후보문장은정답/검증된용례라고주장하지말것. 새외부검색은필요하면기존허용도구로수행하고출처기록. 운영KG/코드직접수정금지.')
 prompt=f'''사용자가 11월5일08시KST까지1~6단계를가능한범위에서계속진행하고검토자들과easy-dataset을검토하도록승인했습니다. 연구목적은KG정보를받은Qwen의문장전체생성, 최종문장코드대체금지. 이번검토권한은이작업관련코드·문헌발췌·원문입력·요청·응답·실험결과읽기이며인증정보/test.py/.env/원본전체PDF전송은제외합니다.
기준계획 {H/'PLAN.md'}. 현황 {R/'docs/research/CURRENT_RESEARCH_PLAN.md'}. 직전50대조 {R/'experiments/analyses/generation_scope_20261104/private/refinement/20261104T083517Z'}. 실제KG {R/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json'}. 상대검토자결과는읽지마세요. 이전reviewer_resolution은대상제외.
역할: {role}
결과는 한국어로 문제위치→실제근거→수정안, 확정/가설/미확인구별. 실행효과/자연스러움은측정전단정금지. 계획범위를넓힐필요있으면이유와중단권고. 새Qwen호출·새에이전트생성금지. 오직 {d/'review.md'} 에작성. 끝표식 END_OVERNIGHT_{who.upper()}_20261105. 검토를지금시작해주시고완료하면파일저장. 후속실험자료는추가전달예정.'''
 (d/'prompt.txt').write_text(prompt,encoding='utf8')
 try:
  receipt=x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']);x.dump(d/'receipt.json',receipt);print(who,'sent',flush=True)
 except Exception as e:x.dump(d/'failure.json',{'type':type(e).__name__,'message':str(e)[:1500]});print(who,'failed',type(e).__name__,flush=True)
