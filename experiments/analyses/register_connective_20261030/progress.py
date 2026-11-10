"""Reflect completed saved records, not estimated successful translations."""
import json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from research_management.work import WorkStore
a=json.loads((BASE/'private/active_run.json').read_text('utf8'))
counts={arm:len(list((ROOT/'experiments/runs'/run/'private/records').glob('*/result.json'))) for arm,run in a['runs'].items()}
done=sum(counts.values())
WorkStore(ROOT).task({'id':'register-connective-20261030','title':'말높임·연결어미 보완 및 Qwen 50문장 실험','actor':'Codex 총괄','stage':'Qwen 본 실험','status':'running','done':3,'total':5,'unit':'단계','unit_key':'stage','message':f'공통 분석 50/50 완료. 생성 처리 {done}/100 (실패 포함). Single {counts["single"]}/50, Multi {counts["multi"]}/50. 자연스러움은 별도 검토.'})
print(json.dumps(counts))
