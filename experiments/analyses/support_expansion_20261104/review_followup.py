"""Bounded follow-up to the existing two Orca reviewers, no new sessions."""
from pathlib import Path
import importlib.util,datetime
R=Path.cwd();H=R/'experiments/analyses/support_expansion_20261104'
s=importlib.util.spec_from_file_location('x',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
for who in ['codex','claude']:
 d=H/'private/reviewers'/who
 prompt=f'''r6 검토의 지적을 반영한 r7에 한정한 후속 확인입니다. {H}/runtime.py, run.py, build_graph.py, test_runtime.py, question_refinement_20261102/query.py, boundary_qwen_20261103/run.py 변경만 확인. 기존 원문·전체KG 재검토 불필요. r6/실험 원본 보존, r7 195노드472관계11규칙(기존9불변). nominal_kind unknown→None, Condition INTERPRETS_SOURCE/DEFINED_BY_DECISION을 직접증거와 분리 반환·전달. primary D02직접용례, supporting/전달3근거명시, 해체카드RELATED_COMPONENT, 지역관찰노트연결, 과거후보대안기록. 계사 생성action만 -시-미관찰을 not_marked_on_predicate로 전달(원Qwen판단보존), 결합설명명시, 표면후보검사만기록(정답/직접용례아님). 공통packet옛계사지시수정. IMPORTANT: 과거packet의 옛지시는 실제 generation_packet의 instruction이 아니었음. 최종요청에는 미전달되어 실패원인단정불가. 기존생성시스템프롬프트불변. 계세요를문자열로하드코딩교정하지않고오적용금지회귀검사추가. 17+39+17코드검사통과. source상모음별필수축약확정아님. 현재개발실험후50진행. 새실험실행금지/자기review파일만기록. 검토의견 문제위치→근거→수정안, 차단문제유무를 짧게. 출력 {d/'followup_review.md'}, 끝 END_SUPPORT_FOLLOWUP_{who.upper()}_20261104.'''
 (d/'followup_prompt.txt').write_text(prompt,'utf8');x.dump(d/'followup_start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat()});x.dump(d/'followup_receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,'sent',flush=True)
