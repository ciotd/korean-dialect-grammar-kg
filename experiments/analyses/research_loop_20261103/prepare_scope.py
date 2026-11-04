"""Stage 1: explicit human-authored coverage map, never used to choose runtime rules."""
import collections
import datetime
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_pipeline.io import read,save,sha,load_jsonl
from kg_runtime.morphology import Morphology
from research_management.work import WorkStore
INPUT=ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
ATLAS=ROOT/'experiments/analyses/source_workmap_20261102/private/atlas.json'
GRAPH=ROOT/'knowledge/authored/semantic_questions_20261102_r3/private/graph.json'

# Lead's planning annotations. These are not labels supplied to Qwen or lookup rules.
NOTES={
'DEV002':('F04 F16 F18','가는 길의 관형 구성, 샀어의 과거 평서'),
'DEV003':('F04 F08 F10','비교보다, 형용사와 -네요의 발견·평가 표현'),
'DEV004':('F02 F08 F16 F18','있던 관형절, 친구예요 명사 서술'),
'DEV005':('F04 F10','비교보다/더, 형용사 좋아'),
'DEV007':('F04 F18 F19','아직 안 먹었어의 부정·과거 형태·현재 관련성'),
'DEV011':('F03 F08 F18','과거·상대 높임의 판정 질문'),
'DEV012':('F03 F09 F18','어디에 질문, 두다의 과거 활용'),
'DEV013':('F03 F07 F08 F13 F21','만나면 될까요의 조건·가능/상의 질문'),
'DEV014':('F03 F10 F18 F19','왜 질문, 아무 말도 부정극어, 안 했어'),
'DEV017':('F05 F08 F21','닫아 주다의 수혜 보조구성과 부탁'),
'DEV019':('F05 F08 F13','미끄러우니까의 이유, 걸으세요의 명령·높임'),
'DEV020':('F05 F09 F19 F21','하지 마의 금지, 한테의 상대'),
'DEV021':('F05 F07 F08 F21','두 문장: 기다려 주세요 부탁, 확인해 볼게요 시도·의지'),
'DEV022':('F06 F13','괜찮으면 조건과 같이 먹자 청유'),
'DEV026':('F07 F08 F13 F18','늦을까 봐의 우려·이유와 과거'),
'DEV028':('F02 F08 F16 F18 F19','말한 건·버리라는 인용 관형과 아니었어요'),
'DEV029':('F04 F14 F18 F21','가 봤는데 경험/시도·연결, 괜찮더라 회상'),
'DEV030':('F05 F07 F13','피곤하면 조건 명령, 내가 할게 의지'),
'LONG001':('F02 F03 F06 F07 F13 F14 F16 F18 F19 F21','위치 질문, 만나자고 인용·연결, 왜 안 와, 먹고 있을게 진행·의지'),
'LONG002':('F03 F04 F05 F14 F16 F18 F19 F21','사 온 관형, 먹어 봤어 질문, 작아도 양보, 더라 회상, 먹지 말고 금지·연결'),
'LONG003':('F03 F04 F05 F08 F13 F14 F19 F21','뭐 들어가서 질문, 못 먹는데, 괜찮네요, 더 주세요 부탁'),
'LONG004':('F03 F05 F07 F08 F13 F14 F18 F19 F21','높임 질문, 이유·금지, 모셔다드릴게요 객체/상대높임·약속'),
'NEW001':('F02 F08 F16 F21','앉아 있는 진행/상태 관형과 선생님이에요'),
'NEW004':('F03 F08 F18','과거·높임 판정 질문'),
'NEW005':('F03 F07 F08 F13 F21','어디에 놓으면 될까요 조건·상의 질문'),
'NEW006':('F05 F08 F13 F14','어두우니까 이유, 조심해서 순서/방식, 내려오세요'),
'NEW007':('F05 F07 F13 F18 F21','먹고 있을 테니까 진행·의지·이유, 와 명령'),
'NEW008':('F02 F19','잘못이 아니야의 부정 명사 서술'),
'NEW009':('F04 F16 F18','좋아하는 관형절과 넣었어 과거'),
'NEW012':('F02 F05 F08 F16 F18 F19 F21','버리라고 한 건, 옮겨 달라는 인용·부탁과 과거 부정'),
'ADVCE001A':('F03 F08 F18','지금·높임 판정 질문, 정차+하 파생동사'),
'ADVCE001B':('F03 F08 F18','어제·과거·높임 판정 질문'),
'ADVCE002A':('F04 F08 F18 F21','읽고 계세요 진행과 주체/상대 높임'),
'ADVCE002B':('F04 F08 F18 F21','읽고 계셨어요 과거 진행과 주체/상대 높임'),
'ADVCE003A':('F03 F07 F08','제가 닫을까요 행동 제안/의향 질문'),
'ADVCE003B':('F03 F07 F08 F20','문이 닫힐까요 피동·추측 질문'),
'ADVCE005A':('F02 F08','동료예요 명사 서술·상대높임'),
'ADVCE005B':('F04 F08','도와요 불규칙 활용·상대높임'),
'ADVCE006A':('F04 F08 F18','저는과 설명했어요의 겸양 지칭·과거·상대높임'),
'ADVCE006B':('F04 F08 F18','나는과 설명했어요의 지칭·과거·상대높임'),
'ADVCE008A':('F07 F08 F16 F18 F21','읽고 있는 관형 진행, 빌려드릴게요 수혜·높임·약속'),
'ADVCE008B':('F07 F08 F16 F18 F21','읽던 관형 시간, 빌려드릴게요'),
'ADVCE010A':('F03 F04 F08 F18','제출하셨죠? 과거·주체/상대높임·확인 질문'),
'ADVCE010B':('F04 F08 F18','제출하셨죠. 과거·높임·확인 평서; 구두점만으로 화행 확정 불가'),
'QUAL002':('F02 F04 F08 F14 F16 F18 F21','하고·하면서 연결, 눈을 뜨게 된 거예요 변화·명사화'),
'QUAL003':('F04 F08 F14 F16 F18 F21','어떻게 보면, 선정해가지고, 날리면서 보낸 것 같아요 추측'),
'QUAL005':('F02 F08 F16 F18','공부했던 관형, 졸업반 애들이었어요 과거 명사 서술'),
'QUAL017':('F04 F07 F08 F12 F13 F14 F15 F18 F19 F21','하려고 의도·거든요, 기간·조건, 해 보고 안 되면'),
'QUAL018':('F04 F07 F08 F13 F14 F16 F18 F21','했다고 인용, 생각해서, 합격할 줄 알았는데 기대·대조·과거'),
'QUAL020':('F04 F07 F08 F10 F13 F14 F15 F16 F18 F20 F21','조건·추측·대조, 하려는 의도 관형, 장벽이 되는 것 같다고 인용·판단'),
}

def main():
 if (HERE/'private/scope.json').exists():raise SystemExit('Scope already recorded; use a new revision')
 rows=load_jsonl(INPUT);atlas=read(ATLAS);packages={p['id']:p for p in atlas['work_packages']}
 assert set(NOTES)=={r['id'] for r in rows}
 morphology=Morphology();cases=[]
 for r in rows:
  groups,note=NOTES[r['id']];ids=sorted(set(['F00','F01']+groups.split()))
  assert all(k in packages for k in ids)
  morph=morphology.analyze(r['text'])
  final_words=[w for w in morph['words'] if any(t.split('-')[0]=='EF' for f,t in w['morphs'])]
  cases.append({**r,'required_analysis_packages':ids,'lead_reading':note,'annotation_status':'lead_planning_not_gold',
   'kiwi_final_targets':[{'id':w['uid'],'surface':w['surface'],'span':[w['start'],w['end']],'morphs':w['morphs']} for w in final_words],
   'contains_question': 'F03' in ids,'existing_question_slice':'candidate_for_runtime_check' if 'F03' in ids else 'no_question_target_in_lead_reading',
   'other_grammar_work':[k for k in ids if k not in ('F00','F01','F02','F03')],
   'runtime_use':'none; this annotation must not be loaded by analyzer/retriever'})
  save(HERE/'private/morphology50'/f'{r["id"]}.json',morph)
 frequencies=collections.Counter(k for r in cases for k in r['required_analysis_packages'])
 package_rows=[]
 for k,n in frequencies.most_common():
  p=packages[k]
  package_rows.append({'id':k,'title':p['title'],'input_count':n,'input_ids':[r['id'] for r in cases if k in r['required_analysis_packages']],
   'source_section_candidates':p['section_ids'],'legacy_ids':p['legacy_ids'],
   'source_mapping_status':'existing provisional workmap, not freshly revalidated linguistic support',
   'current_runtime_status':'partial_question_support_only' if k in ('F00','F01','F02','F03') else 'not_implemented_in_refined_question_runtime'})
 frozen={str(p):sha(p.read_bytes()) for p in (INPUT,ATLAS,GRAPH)}
 save(HERE/'private/scope.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inputs':cases,
  'packages':package_rows,'sources':atlas['sources'],'input_hashes':frozen,
  'statistics':{'inputs':50,'with_question_in_lead_reading':sum(r['contains_question'] for r in cases),'packages':len(package_rows)},
  'limitations':['Required analysis is not a mandate to dialect-convert every element.',
    'Source7 mapping reused as provisional inventory; no new whole-source reading claimed.',
    'Existing50 are regression data, not held-out accuracy evidence.','Runtime support determined by actual analysis and retrieval, not these ID annotations.']})
 save(HERE/'private/authorization.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'user_quote':'1~4단계를 한 묶음으로 지정하여 ... 일반적인 코드 오류 수정과, 합의된 검사/실험은 매번 재승인받지 않고 진행',
  'scope':['50 input requirements','analysis/retrieval repair','generation comparison','full50 diagnosis'],
  'approval_boundaries':['new dialect grammar facts','major KG meaning changes','research scope expansion'],
  'loop_policy':'freeze each comparison, review concrete failures, do not silently tune gold or auto-expand grammar scope'})
 WorkStore(ROOT).task({'id':'research_loop_20261103','title':'1~4단계 연구 보완','actor':'총괄·Orca 검토자·Qwen',
  'stage':'1단계: 50문장 요구사항 대조','status':'running','done':1,'total':4,'unit':'단계',
  'message':'50문장 전부 직접 읽고 기존 문법군 작업지도와 연결. 실행 지원 여부는 후속 실제 조회로 확인.'})
 print(json.dumps({'cases':50,'question_cases':sum(r['contains_question'] for r in cases),'grammar_groups':len(package_rows),'top':[(p['id'],p['title'],p['input_count']) for p in package_rows[:8]]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
