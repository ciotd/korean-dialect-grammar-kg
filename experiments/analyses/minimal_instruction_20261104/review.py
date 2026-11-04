from pathlib import Path
import importlib.util,sys
R=Path.cwd();H=R/'experiments/analyses/minimal_instruction_20261104';phase=sys.argv[1] if len(sys.argv)>1 else 'design'
s=importlib.util.spec_from_file_location('exchange',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
for who in ('codex','claude'):
 d=H/'private/reviewers'/who;d.mkdir(parents=True,exist_ok=True)
 role='A/B 사용자패킷동일,B/C 시스템동일 여부, 위치·목표·지표·반복·집계 확인. 첫 오류단계를 인과적으로 해석할 한계 지적.' if who=='codex' else '이는 원문보존 편집 진단이며 자연스러움 정답률 아님. 기존9위치 범위, 시제/높임 보존과 방언사실 구별, 결론의 과대해석 검토.'
 prompt=f'''승인된 다음 분리진단 {phase} 검토. {H}/PLAN.md,run.py,test_experiment.py를 읽으세요. 기존50에서 실제 아/어요계열지시9위치전체를추출(새9문장아님),각입력의한위치만수정. A짧은시스템+원문/위치/끝요→예지시, B같은사용자패킷+기존r7시스템, C같은B시스템+기존KGaction정보추가(수정지시유지). 조건별3반복81호출. 실제사용한패킷/응답/설정은 private/latest.json에연결되면읽을수있음. 정답문장은모델에미전달,평가만원문최종요교체값과비교. {role} 추가로 WORD_PLAN.md,word_probe.py,diagnostic_transport.py와 private/latest_word.json 연결 D/E 실행도 확인하세요. D는 어절만 입력, E는 D에서 response_format만 제거. 54호출이 완료되면 결과까지 확인. 이전 설계검토 때 본 051311 준비실패 폴더와 현재 latest의 051408 실제완료 폴더를 혼동하지 마세요. 현재 사용자께서 이번 코드·원문·요청·응답·집계 전달을 명시 승인했습니다. 코드/KG수정·새모델호출금지. 자기파일 {d/(phase+'_review.md')}만작성. 문제위치→실제근거→수정안,실행차단문제유무. 전체문헌재검토/이전검토반복불필요. 끝 END_MINIMAL_{phase.upper()}_{who.upper()}_20261104.'''
 (d/(phase+'_prompt.txt')).write_text(prompt,'utf8');x.dump(d/(phase+'_receipt.json'),x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,'sent',flush=True)
