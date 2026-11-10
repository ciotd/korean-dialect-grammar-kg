from pathlib import Path
import sys,importlib.util
R=Path.cwd();H=R/'experiments/analyses/restriction_audit_20261104'
s=importlib.util.spec_from_file_location('exchange',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
for who in ('codex','claude'):
 d=H/'private/reviewers'/who;d.mkdir(parents=True,exist_ok=True)
 role=('검토역할: 실제제한의코드위치/후처리반환/폼선별실제누락/50입력62위치집계/동결코드와현행차이. 어떤것이실행제약이고어떤것이경고뿐인지 구분.' if who=='codex' else '검토역할: 전달된문법설명/보존정보의내부충돌, 실제표면형과Kiwi정규형혼동, 자연스러움과문자편집계약구분. 문헌전체 재검토는하지않고 근거없는새방언규칙을확정하지않음.')
 prompt=f"""사용자가 현행①~⑥순서와두검토자역할을주석으로확정하고지금①제한위치확인을수행하라고지시했습니다. 이번자료/목적지: 기존OrcaKG Reviewer {who}. 읽기대상 {H}/PLAN.md,audit.py,private/cases.json,targets.json,summary.json,validation.json 및 이 파일들이 연결하는 원본 experiments/runs/20261104T013633051461Z_support_expansion_full50의 동결코드/분석/조회/생성패킷/원시응답. 총50입력62위치입니다. 사용자원문은내부비공개연구자료이고 인증정보는대상에없습니다. test.py/credentials/환경변수읽기금지. {role} 문제위치→실제근거→수정안,확정관찰과가설구분. 단계②의실험변수후보는제시가능하나이번은새Qwen호출0·KG/운영코드수정0. 다른검토자결론읽기금지. 본인 {d/'review.md'}만작성. 이전원인진단을그대로반복하거나이실험을최종논문성능평가로주장하지않음. 검토범위·미확인·실행차단문제 명시. 완료끝 END_RESTRICTION_{who.upper()}_20261104."""
 (d/'prompt.txt').write_text(prompt,'utf8');x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,'sent',flush=True)
