"""Read-only diagnostics of the frozen run. No model calls or KG mutations."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'experiments/runs/20261109T030211818725Z_kiwi_default_regression'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
changes=[]; all_before=0; all_after=0; stale=0; exact=[]; reviews={}
for d in sorted((RUN/'private/records').iterdir()):
    if not (d/'retrieval_packet.json').exists(): continue
    before=read(d/'pre_objection_retrieval_packet.json')['verified_scope_knowledge']
    after=read(d/'retrieval_packet.json')['verified_scope_knowledge']
    all_before+=len(before); all_after+=len(after)
    key=lambda x:(x.get('unit_id'),x.get('rule_id'))
    kept={key(x) for x in after}
    missing=[x for x in before if key(x) not in kept]
    if missing: changes.append({'id':d.name.removesuffix('_kiwi_focused'),'removed':[{'unit_id':x.get('unit_id'),'rule_id':x.get('rule_id')} for x in missing]})
    selected=read(d/'selected_knowledge.json')
    stale+=sum('Kiwi로 결합' in json.dumps(x,ensure_ascii=False) for x in selected)
    request=read(d/'writer/request.json')
    exact.append(json.loads(request['messages'][1]['content'])['knowledge']==selected)
out={'run_id':RUN.name,'pre_diagnostic_candidates':all_before,'delivered_candidates':all_after,'diagnostic_filter_changes':changes,'actions_with_stale_kiwi_instruction':stale,'writer_knowledge_equal_selected':{'count':len(exact),'all_equal':all(exact)}}
(Path(__file__).parent/'private/saved_record_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
