import datetime,sys,json
from pathlib import Path
from reviewers import HERE,ROOT,x
who=sys.argv[1];d=HERE/'private/reviewers'/who/'results_review';d.mkdir(parents=True,exist_ok=False)
other='codex' if who=='claude' else 'claude'
prompt=f'''[연구루프 결과 검토 20261103 — 한 번의 교차 검토]
한국어로 문제 위치→실제 근거→수정안. 코드/KG/원문 변경 금지. 검토파일은 {d}/response.md에만 작성.
앞선 본인·상대 설계검토를 확인: {HERE}/private/reviewers/{other}/response.md. 상대 의견을 자동 채택하지 말 것.
현재 코드 pipeline.py/run.py/replay.py/test_pipeline.py와 실행 동결 사본 구별.
실제 결과1: experiments/runs/20261103T072412784953Z_research_loop_dev (32분석,54생성. whole27생성/piece27모델보류)
실제 결과2: experiments/runs/20261103T072835388759Z_research_loop_composition_replay (동일분석조회 재사용27생성. 과거계사 명사누락 코드오류 포함)
실제 결과3: experiments/runs/20261103T073040472661Z_research_loop_composition_replay (명사누락 수정,27생성,자동표면경고5. 이5가 전체언어학오류수라는 뜻 아님.)
실제 결과4: experiments/runs/20261103T073106231833Z_research_loop_full50 (현재 실행 중, 완료된 result만 읽거나 metrics.json 완성 후 확인. 실행완료로 추정하지 말 것.)
수정: 생성실패 상위상태 반영, 실행범위/절미분석/투영미지원 구별, 과거계사 명사 부품 보존, 출력어휘의심·다어절확장 검사. 테스트11개통과. KG 사실 변경 없음.
Claude: 생성된 개발27후보 전체와 full50의 실제생성 결과에서 직접 확인할 수 있는 활용오류를 구체적으로 찾아줘. 현대자연스러움 추정/문헌근거/명백한형태오류 구분. 특히 보었나/춨나, 학생이, 원문유지, 과거계사, 현재계사 보존 확인. 새 PDF 재대조 없이 단정하지 말고 필요시 원문 접근해 범위 기록.
Codex: 새 집계/코드/동결의 실제문제와 사용자보고에 필요한 분모, 잘못된 성공표시 확인. 원본실행은 덮어쓰지 않고 report의 재집계로 바로잡을 수 있음. 실제 출력경고탐지와 공백변화·후보없음의분류를 확인.
결론: 아직 남은것, 다음1개 수정/실험의 근거. 추가 에이전트 생성/Qwen 호출 없음. 최종 줄 END_LOOP_RESULTS_{who.upper()}_20261103.
'''
(d/'prompt.txt').write_text(prompt,'utf8');x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who+' result review sent')
