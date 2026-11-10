from pathlib import Path
import importlib.util,sys,datetime,json
R=Path.cwd();H=R/'experiments/analyses/support_expansion_20261104'
s=importlib.util.spec_from_file_location('exchange',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
common=f'''사용자 승인된 다음 연구입니다. 한국어로 검토. 기존 Qwen 최종생성50 결과 중 현재지원밖46위치를 전부 원인대조하고, 근거가 충분한 첫문법군을 확장합니다. 최종생성은 Qwen; 조합기 보조. 원본/기존KG/코드/결과 수정금지. 새모델실험/하위에이전트 금지. 자신의 지정 review.md만 작성. 모든 결론은 문제위치→실제근거→수정안, 확인불가와 과도한일반화를 구별. 모델합의는 사실인증 아님. 원본저장소 읽기전용.
기준 결과 {R/'experiments/analyses/boundary_qwen_20261103/private/all_targets.json'}; 각trace_path에 실제기록. 실행KG {R/'knowledge/authored/semantic_grammar_20261103_r4/private/graph.json'}; 과거카드 {R/'knowledge/authored/kg_cards_20261030_v3/cards.json'}; 전체작업지도 experiments/analyses/source_workmap_20261102. 소스 manifest knowledge/authored/kg_v3_evidence_20261019_r2/provenance/sources.json. PDF C:/Users/ciot28/Downloads/1; 추출본문 C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit/Dxx.json. 기존9규칙=6질문+3해예평서. 46위치는 지식없음과동일하지않음. 총괄은 모든46세부표를 작성중.
'''
roles={
'claude':'''문법/지식 검토: 46위치 원문과 Qwen기능을 먼저 모두 읽고 공통군을 확인. 계사/부정계사 평서(친구예요,선생님이에요,아니었어요) 우선확장 후보를 검토하되 D02 PDF201~205와 전후, D05 관련부분, 7종중 관련구간을 직접대조. 근거충분하면 조건·결합형·보존·예외를 재사용 가능한 형태로 제안; 이예/예/아니어예/였어예의 현재/과거, 모음/자음, 주체/상대높임을 섞지말것. 원문적시형과 구성적추론 구별. 구체적인 인용과PDF쪽 필수. 기존카드에있지만 조건그래프미연결인지도확인. 그외높임질문/요청금지/약속 등은 근거있는읽기범위와기존ID를제시. 외부자료검색은 쟁점이있을때 허용하지만 기억으로새형식인증금지. 46개정답번역은 만들지않음.''',
'codex':'''구조/조회 검토: 46곳 모두 실제 construction_queries/scope_failures/narrowing/analysisfeatures 점검. 런타임 experiments/analyses/boundary_qwen_20261103와 grammar_expansion_20261103 및 condition_followup_20261103. 적용범위 제한과 키/값 매핑오류, 분석오류의 중첩을 구별. 특히 친구예요의EF예요→other, negative_copula, 과거계사, query후반코드의고정predicate 제한 등 첫확장시 필요한변경을소스근거로확인. 문법별Python전용함수가아닌기존조건관계/범용조회재사용. 통합계약의허점을찾고정상/부정/unknown개발검사 제안. 조회실패이후생성오류를전부KG문제로오판금지. 보고서에46범위검토완료여부와미확인영역을명시.'''}
for who in ('codex','claude'):
 d=H/'private/reviewers'/who
 prompt=common+roles[who]+f'\n결과 파일 {d/"review.md"}. 마지막 END_SUPPORT_REVIEW_{who.upper()}_20261104.'
 (d/'prompt.txt').write_text(prompt,'utf8')
 x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offset':x.LOGS[who].stat().st_size})
 x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']))
 print(who,'sent',flush=True)
