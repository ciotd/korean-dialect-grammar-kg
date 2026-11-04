import datetime,sys
from reviewers import HERE,ROOT,x
who=sys.argv[1];d=HERE/'private/reviewers'/who/'composition_review';d.mkdir(parents=True,exist_ok=False)
prompt=f'''[사용자 추가승인: 활용 조합기 비교 결과 — 20261103]
사용자가 방금 Qwen 대신 일반활용조합기를 동일한 분석/KG조건에서 비교하도록 명시 승인. 실제 완료. Qwen 호출0, KG수정0.
고정실행 experiments/runs/20261103T075139157865Z_kiwi_composition_fixed30 를 읽고 제한된 결과 검토만 해줘.
27개발+3회귀 위치, source_link.json으로 기존analysis/trace/enhanced 원본과 바이트동일. composer.py는 source_morphs의 단일EF만 선택어미로 교체하고 Kiwi.join(lm_search=False), -I/-R 유지. 현재계사는 KG가선택한통합형을 명사에그대로붙임. 문장ID/정답문장 분기없음. 테스트8통과. 실제30후보·표면경고0. 이걸 자연스러움100%로 해석금지.
읽을코드 {HERE}/composer.py, compose_run.py, test_composer.py 및 위run 동결사본.
기존Qwen부품 대비 바뀐것: 학생이→학생이가(Q05/Q16중복), 기다려→기다리나/기다리노, 보었나→봤나, 춨나→추웠나, 두었노→뒀노. 나머지는 동일. 원문먹었노→뭇노 새규칙없음.
Claude: 실제30후보와 위7변경을 읽고 형태개선/표기변이/아직미확인방언자연스러움을 구별. 일반활용조합을 전체문법KG완성으로 오해할 표현 지적. 새의견3개이내.
Codex: 실제30원본동일성, ID암기분기부재, 부품/계사결합,30위치분모,0모델호출·시간범위·해시집계 검증. 새로운공통분석이나50전수재실행으로표시하면안됨. 새의견3개이내.
새모델호출/다른파일수정/추가에이전트 생성금지. 검토만 {d}/response.md에저장. 한국어 문제위치→근거→수정안. 끝줄 END_COMPOSER_{who.upper()}_20261103.
'''
(d/'prompt.txt').write_text(prompt,'utf8');x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who+' composition review sent')
