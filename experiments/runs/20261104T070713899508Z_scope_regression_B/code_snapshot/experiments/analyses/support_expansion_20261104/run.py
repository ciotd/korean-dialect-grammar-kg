"""Reuse the existing run workflow with a new KG and versioned development inputs."""
from pathlib import Path
import importlib.util,sys
import runtime as rt
H=Path(__file__).resolve().parent;R=H.parents[2]
s=importlib.util.spec_from_file_location('boundary_runner_parent',R/'experiments/analyses/boundary_qwen_20261103/run.py');parent=importlib.util.module_from_spec(s);s.loader.exec_module(parent)
parent.rt=rt;parent.H=H;parent.RUN_FAMILY='support_expansion';parent.EXTRA_CODE_PATHS=[R/'experiments/analyses/boundary_qwen_20261103/run.py',R/'experiments/analyses/boundary_qwen_20261103/runtime.py',H/'build_graph.py']
parent.DEV=[('S01','저 사람은 연구원이에요.'),('S02','저 사람은 가수예요.'),('S03','이 상자는 선물이에요.'),('S04','저분은 제 교수님이에요.'),('S05','밖에 비가 와요?'),('S06','요즘 무엇을 배워요?'),('S07','선생님은 벌써 도착하셨어요?'),('S08','어제 일은 끝났어요?'),('S09','그때 저는 학생이었어요.'),('S10','그 말은 사실이 아니었어요.'),('S11','제가 찾던 거예요.'),('S12','창문을 열어 주세요.'),('S13','어제 내용을 기록했어요.'),('S14','날씨가 생각보다 추워요.')]
def select_evidence(graph,action):
 nodes={n['id']:n for n in graph['nodes']};rid=action['rule_id']
 # Preserve existing evidence delivery for old rules to isolate expansion.
 if not rid.startswith('SEM_SUP_'):
  ids=['EV_DECL_STRUCTURE'] if any(e['source']==rid and e['relation']=='SUPPORTED_BY' and e['target']=='EV_DECL_STRUCTURE' for e in graph['edges']) else []
 else:
  ids=nodes[rid]['properties']['delivery_evidence_ids']
 return [{'evidence_id':eid,'quote':nodes[eid]['properties']['quote'],'document_id':nodes[eid]['properties'].get('document_id'),'pdf_page':nodes[eid]['properties'].get('pdf_page'),'role':'primary' if eid in nodes[rid]['properties'].get('primary_evidence_ids',[]) else 'supporting','source_family':nodes[eid]['properties'].get('source_family')} for eid in ids]
parent.EVIDENCE_SELECTOR=select_evidence
if __name__=='__main__':parent.main(sys.argv[1])
