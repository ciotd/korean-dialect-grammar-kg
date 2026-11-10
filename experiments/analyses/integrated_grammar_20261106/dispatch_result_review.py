"""Send completed run evidence to the two existing user-designated reviewers."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/analyses/full_review_20261029'))
from review_exchange import cli,dump,HANDLES

p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--phase',choices=['regression','repair'],required=True);args=p.parse_args()
run=ROOT/'experiments/runs'/args.run
assert (run/'metrics.json').exists(),'Run must be complete before final review'
here=Path(__file__).resolve().parent
for who in ('claude','codex'):
    dest=here/'private'/who
    prompt=f'''{args.phase} 실제 실행이 종료됐습니다: experiments/runs/{args.run}.
모든 입력·원시 출력을 확인하고 문제 사례는 분석→조회→실제 전달→원시 응답에서 처음 어긋난 위치를 대조하세요. private/results.json, private/records/ID의 morphology, analysis/parsed, bound_analysis, retrieval, generation_packet, generation/request/response, meta와 frozen code가 근거입니다.
출력 불변을 자동 오류로 세거나, 문자열 변경을 방언 품질로 세지 마세요. source_ref 존재만으로 조건 적합성을 확정하지 마세요. 다른 검토자 결과는 읽지 마세요. 원본 코드/KG/기록 수정·새 모델 호출·인증정보/test.py 열람 금지.
결과는 experiments/analyses/integrated_grammar_20261106/private/{who}/{args.phase}_review.json에 작성: {{reviewed_ids:[], findings:[{{id,first_observed_stage,observation,evidence,certainty:direct|inference|needs_human,repair}}],cross_case:[],limitations:[]}}.
모든 입력을 검토했는지 IDs를 정확히 기록하고, 근거 없는 원인 추측은 가설로 구별하세요. 반복 사항은 cross_case에 묶되 대표 실제 ID를 남기세요. 목적은 문제 위치→실제 근거→다음 수정안입니다.
'''
    if who=='claude':prompt+='문법/언어 관점: 문장 기능·높임·시제·어간·의미 보존, 정제/미정제 지식 전달의 혼선과 불필요 정보 확인. 자연스러움 단정 대신 구체적으로 어떤 뜻/형태가 달라졌는지 설명하세요.\n'
    else:prompt+='구조/통제 관점: 실제 wire와 packet 일치, 조건/관계 판정, 원시 출력 보존, 코드·KG 고정, 호출·토큰·실패 분모를 확인하세요. 형식 실패와 언어 오류를 구별하세요.\n'
    if args.phase=='repair':prompt+='기준은 development 20261106T051728566435Z이며 같은18개만 대조하세요. ANALYSIS_REPAIR_PLAN.md 및 private/analysis_repair_comparison.json을 실제기록과 확인하세요. 바뀐 것은 분석지시 정의뿐입니다. 참고 전달 대안은 이실험에 적용되지 않았습니다. 기대값은 사람 독립정답이 아닌 사전개발검사입니다.\n'
    target=dest/(args.phase+'_prompt.txt')
    assert not target.exists(),'Do not duplicate an existing reviewer dispatch'
    target.write_text(prompt,encoding='utf8')
    dump(dest/(args.phase+'_receipt.json'),cli(['terminal','send','--terminal',HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']))
    print('sent',who,args.phase,flush=True)
