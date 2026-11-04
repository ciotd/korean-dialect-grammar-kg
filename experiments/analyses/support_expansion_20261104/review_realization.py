from pathlib import Path
import importlib.util,datetime
R=Path.cwd();H=R/'experiments/analyses/support_expansion_20261104';s=importlib.util.spec_from_file_location('x',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
for who in ['codex','claude']:
 d=H/'private/reviewers'/who
 prompt=f'''추가 진단 결과에 따른 한정 검토입니다. 50건 r7 19위치전달17문장변경. 이어17입력고정(분석/규칙/위치동일) 기존전달vs원활용보존안내 비교: 뒀노/어디고 변화 외 설명해예·같어예 지속. 실제 FORM의 '-어예'만선택하도록한 정보와 해체+예 설명이 상충가능. 해결초안 {H}/build_realization_r8.py 및 knowledge/authored/semantic_grammar_20261104_r8/private/change_ledger.json 확인. 기존 r7의 조건·관계·나머지노드불변. 두 Realization(SEM_DECL_HAEYE_EO/SEM_SUP_POLITE_Q_EO 연결형)만 form=예, unit=right_edge_politeness_marker, composition=원문활용형끝요만예로변경/앞글자보존으로수정. 완성정답없음/문장별분기없음/최종Qwen. 근거 기존D02PDF203해체+예 및D05PDF26아/어예. 원래EF분석아요/어요는유지하고 수정단위를말끝공손표지로 명시. 이게새방언사실추가인지, 기존근거표현의실행단위정정인지, 조건통과범위에 문제가있는지 판단해주세요. 불확실한대안전체를새로승격하지않음. 과거부정계사제외그대로. 계획은같은17입력고정/같은시스템프롬프트에서 FORM두필드만바뀐정보로생성비교. 두검토자본문정독반복없이해당부분만. 모델호출·코드수정금지, 자기 realization_review.md만작성. 문제위치→근거→수정안, 차단문제유무, 끝 END_REALIZATION_{who.upper()}_20261104. 파일 {d/'realization_review.md'}'''
 (d/'realization_prompt.txt').write_text(prompt,'utf8');x.dump(d/'realization_receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,'sent',flush=True)
