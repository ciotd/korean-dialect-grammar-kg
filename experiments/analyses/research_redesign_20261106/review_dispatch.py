"""User-requested planning discussion with the two existing Orca reviewers."""
from pathlib import Path
import argparse, sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/analyses/full_review_20261029'))
from review_exchange import cli,dump,HANDLES
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('round',choices=['independent','cross']);args=p.parse_args()
common='''이번은 연구 재설계 논의만입니다. 새 Qwen 실험·원본 KG/코드 수정 금지. 인증파일/test.py/PDF원문 열람·외부 전송 금지. 지정한 자기 검토 문서만 작성하세요. 사용자가 기존 Claude와 GPT 검토자의 논의·비판을 명시 요청했습니다.
사용자 제안: (1) 12문법 모듈 및 원본1625노드6167관계 전체를 한번씩 통과하는 표준어 시나리오를 추론+brute force로 만들고 전체 파이프라인 시험. 조건분기/불필요정보/7문헌정제를 검증. 문헌부족·충돌은 사람 판단(문헌과 달라도 사람 우선). (2) Qwen 분석·생성을 각각 여러 에이전트로 분업. 분석은 큰 오류가 없었다고 추정, 생성오류는 입력정보가 많아 망각했다고 추정. (3) Kiwi 대신 LLM 분석 검토. (4) 단어/위치별 워커+통합자 또는 문법별 워커, 동적 배치 검토. (5) zero-shot/예문/문서검색/조건표/그래프를 품질과 토큰/시간으로 비교. BLEU 포함 검토. 목적은 KG가 실제 도움이 되는지 공정하게 평가, 우월성 전제 금지.
최근 실제근거를 읽으세요: experiments/analyses/integrated_grammar_20261106/{README.md,SCHEMA.md,DECISIONS.md,summary.json,coverage_r2.json}; private/analysis_repair_comparison.json; 필요시 본인의 이전 development/regression/repair_review.json과 src/kg_pipeline/integrated.py. 원본은1625/6167, 후보2320/7476, 조건용법56(기존12+44), 원본721참고검색은 문자열. 기존50은 회귀노출, 새30개발,18재사용. 26묶음완료아님. 분석9확인1→9이나3다른판단퇴행, 관계오류51→13. 과거정보전달후생성손실도실재. 출처노드와 실행용법은다름.
보고서는 쉬운 한국어로 문제 위치→실제 근거→권고. 확인사실/가설/제안 구별. 구체적인 실험단위·역할·입출력·충돌처리·종료기준·실패시행동·호출수/비용통제를 포함. 지식부재와추출오류/모델오류/조회오류 구별. 그래프 vs 조건표는 같은지식일때 동등할 수 있음. 독립정답/테스트누출/상관오류/공정계산예산/인간 override의출처표시 논의. 단순찬성금지. 전체그래프문장커버리지의타당성과 다른검사제안 검토.
'''
for who in ('claude','codex'):
    d=HERE/'private'/who;d.mkdir(parents=True,exist_ok=True)
    if args.round=='independent':
        role=('문법·지식 및 end-to-end정보전달 전문가로서, 단어별분할이 잃는 의존관계, 올바른검사예문/음성·출처노드 처리, 현대방언 사용자결정층, 의미/높임/시제 평가를 중점 검토.' if who=='claude' else '시스템·실험설계 전문가로서, 전체노드/관계분모와조건분기커버리지, multi-call대조군, 변경변수분리, Kiwi유무공정비교, 비용·토큰·실패집계 및 원인구분실험을 중점 검토.')
        prompt=common+'\n'+role+'\n다른 검토자 의견은 아직 읽지 말고 독립 초안을 '+str(d/'independent.md')+' 에 작성. 1)반박/동의와근거 2)추천Qwen역할과최소대조군 3)KG검사방식 4)실험순서·종료기준 5)사용자결정사항. 가능하면 1500~2500한국어단어 이내. 끝나면 파일 경로를 알려주세요.'
    else:
        other='codex' if who=='claude' else 'claude'
        prompt=common+'\n독립의견 이후 상호검토 단계입니다. '+str(HERE/'PLAN.md')+' 와 '+str(HERE/'private'/other/'independent.md')+' 를 읽고 상대 및 리드의 제안에서 동의/반대/누락을 지적하세요. 기존의견을 무조건맞추지마세요. 모델합의는증거가아닙니다. 결과는 '+str(d/'cross_review.md')+' 에 작성. 최종채택가능한항목과사람판단이필요한항목·결정안·잔여리스크를 구체적으로. 추가실험/코드수정금지.'
    target=d/(args.round+'_prompt.txt')
    assert not target.exists(),'Existing dispatch must be inspected, not resent.'
    target.write_text(prompt,encoding='utf8')
    dump(d/(args.round+'_receipt.json'),cli(['terminal','send','--terminal',HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']))
    print('sent',who,args.round,flush=True)
