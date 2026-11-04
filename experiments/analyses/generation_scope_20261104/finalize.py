"""Verify saved runs and update navigation. Does not call Qwen."""
from pathlib import Path
import json,sys,datetime
R=Path(__file__).resolve().parents[3]; H=Path(__file__).resolve().parent; P=H/'private'
sys.path.insert(0,str(R/'src'))
from research_management.core import Registry
from research_management.work import WorkStore
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
reg=Registry(R); paths=[]
for name in ('v1_latest_regression','latest_regression','latest_development'):
 paths.extend(Path(x) for x in read(P/(name+'.json')).values())
paths.append(Path(read(P/'latest_dev_analysis.json')['directory']))
results=[reg.verify(p.name) for p in paths]
save(P/'run_integrity.json',results)
assert all(x['status']=='passed' for x in results),results
totals={'runs':len(paths),'chat_calls':sum(read(p/'metrics.json')['api_attempts'] for p in paths),'tokens':sum(read(p/'metrics.json')['reported_usage']['total_tokens'] for p in paths)}
save(P/'all_run_totals.json',totals)
nav=R/'experiments/management/report_navigation.json'; entries=read(nav); url=(P/'report.html').as_uri()
item={'title':'39 · 생성 범위 완화 비교 — 기존50·새12','url':url,'summary':'2·3단계 생성 비교. 최종 조건별 변경17→44/50, 새개발5→9/12. 의미·시제·높임 오류 남아 기본값 미채택. KG 변경 없음. 두 Orca 결과 검토 완료.'}
entries=[x for x in entries if x['url']!=url]+[item]; save(nav,entries)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
WorkStore(R).task({'id':'scope_reporting_'+stamp,'title':'생성 범위 비교 집계·원본 검증','actor':'연구 리드','stage':'보고서 정리','status':'completed','done':10,'total':10,'unit':'실행','unit_key':'scope_integrity','message':'10개 실행 무결성 확인. 두 Orca 결과 검토 완료.'})
print(json.dumps({'totals':totals,'verified_runs':len(results)},ensure_ascii=False))
