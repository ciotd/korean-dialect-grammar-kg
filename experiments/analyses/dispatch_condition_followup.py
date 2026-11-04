from pathlib import Path
import json,importlib.util,datetime,sys
R=Path('.').resolve();H=R/'experiments/analyses/condition_followup_20261103';H.mkdir(parents=True,exist_ok=True)
B=R/'experiments/runs/20261103T085736340654Z_research_loop_expanded50/private/records';cases=[]
for p in sorted(B.glob('*/result.json')):
 row=json.loads(p.read_text('utf8'))
 for t in row['targets']:
  if t.get('readiness')=='needs_analysis' or t['status']=='analysis_unresolved':
   d=p.parent/'targets'/t['target_id'];cases.append({'id':row['id'],'target_id':t['target_id'],'input':row['input_text'],'target':json.loads((d/'target.json').read_text('utf8')),'raw':json.loads((d/'analysis_call/parsed.json').read_text('utf8')),'result':t,'source_directory':str(d)})
(H/'private').mkdir(exist_ok=True);(H/'private/six_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),'utf8')
s=importlib.util.spec_from_file_location('ex',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
common=f'''사용자 승인 후 후속작업: 분석보완6위치 진단+새Condition별 직접근거 연결. 폴더 {H}. private/six_cases.json에실제6개원본응답/형태/결과. 모든과거결과읽기전용. 새문법범위추가금지,추가에이전트/모델호출금지. 자기검토폴더에만보고서저장. 문제위치→실제근거→수정안. 한국어핵심요약. '''
messages={'codex':'''검토:6개중LONG002 W7만현KG조건eligible. 다른5개는분석문제와out_of_scope중첩. 계획1) per-boundary고정ID객체+EC/ETM/ETN별허용relation enum을Qwen에질문,unknown유지,원래의큰절종류를각경계에복사하는오류방지. 2) unknownVX분류는verb로확정하지않고관측형태는보존,참조가능한원KG scope를동시에평가. 3) out_of_slice를needs_analysis로덮던표시수정,문제정보는별도보존. 이방법의위험/한계와검증제안. 기존scope_runtime/expanded_runtime/build_graph 읽기. 추가프로덕션수정은리드담당. review.md에저장.''','claude':'''검토:graph semantic_grammar_20261103_r2의COND_DECL_6개각각에문헌근거/해석/실험상제한을분리하려함. prefinal_sequence목록은문헌상전체허용목록이라고주장하지않고ImplementationDecision 연결,source_final3개는해체+요/예구조와각용례/표47근거 +Kiwi정규화는구현결정으로분리,statement/exclamation범주는문헌서술법과모델레이블간해석으로분리. 원본D02PDF203/202/205/57/214, D05PDF27과기존출처원문검토재사용. 부당한SUPPORTED_BY관계가생기지않도록 조건별근거를구체적으로검토. 또6위치가전부지식부족은아닌지확인. 검토범위명시. review.md에저장.'''}
for who,body in messages.items():
 d=H/'private/reviewers'/who;d.mkdir(parents=True,exist_ok=True);prompt=common+body+'\n출력 '+str(d/'review.md')+'\nEND_CONDITION_FOLLOWUP_'+who.upper()
 (d/'prompt.txt').write_text(prompt,'utf8');x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat()});x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who+' sent',flush=True)
sys.path.insert(0,str(R/'src'));from research_management.work import WorkStore
WorkStore(R).task({'id':'condition_followup_20261103','title':'분석6위치 진단·조건 근거 연결','actor':'리드 + Orca 두 검토자','stage':'실제기록 진단 완료·보완 구현','status':'running','done':6,'total':6,'unit':'진단 위치','message':'6개 중1개만 기존지식으로추가생성후보. 나머지는범위밖문제와중첩. 현재단계는진단수이며전체완료율아님.'})
