from pathlib import Path
import importlib.util,datetime
H=Path(__file__).resolve().parent;R=H.parents[2]
s=importlib.util.spec_from_file_location('review_exchange',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
common=f'''후속 구현을 검토해 주세요. 작업 폴더: {H}
검토의견은 문제 위치 → 실제 근거 → 수정안으로, 한국어로 쉽게 작성해 주세요.
기존 산출물·코드·KG는 읽기 전용입니다. 자기 검토 폴더의 implementation_review.md만 작성하세요. 새 모델 호출·하위 에이전트·실험 실행은 하지 마세요.
실제 코드: runtime.py, build_provenance.py, test_runtime.py. 새 그래프: knowledge/authored/semantic_grammar_20261103_r3/private/graph.json.
규칙/실행 조건/실현형은 r2와 동일하며 출처 구별만 추가했습니다. 단위검사 10건, 기존 검사 29건 통과. Qwen 구조진단12건은9생성/1분석보류/2미지원이며 자연스러움 평가는 아닙니다.
현재50건실행: experiments/runs/20261103T093451123726Z_research_loop_followup50. 미완료면 완료 결과를 추측하지 마세요.
'''
tasks={'codex':'''관측 경계를 고정 객체로 묻고 EC/ETM/ETN 후보를 다르게 주는 계약, unknown VX를 유지하는 부분 범위 평가, 지원범위와 분석문제의 분리, 기존 동작 손상을 확인하세요. word_id 키와 원본 morph 스냅샷을 사용하며 한 어절의 복수 경계는 기존 검사로 보류합니다. 경계별 morph_index 객체로 확대하는 것은 이번 수정에 포함하지 않았습니다. 실제 문제인 경우 근거를 구체적으로 남겨 주세요.''',
'claude':'''Condition 근거를 INTERPRETS_SOURCE로 연결하고 구현 결정은 DEFINED_BY_DECISION으로 분리했습니다. prefinal 목록에는 문헌 확정 연결을 달지 않았습니다. D02 PDF201 서술법 높임 설명을 원문 offset/hash 확인 후 새 Evidence로 추가하고 규칙의 PRESERVATION_SUPPORTED_BY로 연결했습니다. 기존 PDF214 근거는 보존됩니다. 해석을 원문 확정 사실로 과장한 곳이 있는지 확인해 주세요. 이번 관계명은 실행 조건이 아니라 추적 관계입니다.'''}
for who,body in tasks.items():
 d=H/'private/reviewers'/who;prompt=common+body+'\n출력: '+str(d/'implementation_review.md')
 (d/'implementation_prompt.txt').write_text(prompt,'utf8')
 x.dump(d/'implementation_start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 x.dump(d/'implementation_receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']))
 print(who+' implementation sent',flush=True)
