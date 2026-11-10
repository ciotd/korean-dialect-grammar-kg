"""Preserve pre-change code and declare the controlled experiment before running it."""
import json,sys,shutil,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[2];P=B/'private';P.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'src'))
from research_management.work import WorkStore
files=['compatibility.py','edit_contract.py','card_pipeline.py','card_experiment.py','suffix_composition.py']
hashes={}
for name in files:
 src=R/'src/kg_runtime'/name;dst=P/'before'/name;dst.parent.mkdir(exist_ok=True)
 if not dst.exists():shutil.copy2(src,dst)
 hashes[name]=hashlib.sha256(dst.read_bytes()).hexdigest()
(P/'before_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf8')
protocol={'approval':'진행해 — 판단 기준 수정 후 카드 설명과 어미 결합 도움을 분리해 같은 입력으로 비교',
 'source_batch':'20261030T085346443103Z','inputs':50,'architectures':['single','multi'],
 'conditions':{'control':'common function-contract fix only','explanation':'control + explicit per-card condition explanations','composition':'control + source-morph composition aids'},
 'fixed':['input text','saved Kiwi and Qwen analysis','retrieval results','selected card IDs/order/content','model settings','post-generation checks'],
 'reference_policy':'No approved reference sentences in model requests; regression, not unseen evaluation',
 'phase1':'offline replay of all 100 saved decisions before any new generation',
 'phase2':'50 x 3 conditions x 2 architectures; new generation only, no new analysis/retrieval',
 'retries':0,'workers':2,'KG_changed':False,'limitations':'one run per condition; full sentence naturalness requires human assessment'}
dest=P/'protocol.json'
if not dest.exists():dest.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
WorkStore(R).task({'id':'controlled-delivery-20261031','title':'판단 기준 통일·설명/조합 도움 분리 검증','actor':'Codex 총괄','stage':'판정 코드 수정 및 저장 기록 검증','status':'running','done':0,'total':4,'unit':'단계','unit_key':'phase','message':'기존 50문장 분석·조회·카드를 고정. Qwen 서버는 모델 목록 요청에 503 응답, 코드·오프라인 검증 진행 중.'})
print('Protocol and pre-change snapshots preserved; no generation calls.')
