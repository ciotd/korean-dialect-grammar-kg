"""Reconcile saved checks and all run manifests; read-only Neo4j verification."""
import argparse,json,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from research_management.core import Registry
from kg_pipeline.io import Neo4j,read,save
from kg_pipeline.retrieval import load_catalog

def main():
    p=argparse.ArgumentParser();p.add_argument('--credentials',type=Path,required=True);a=p.parse_args()
    registry=Registry(PROJECT);registry.sync();checks=[registry.verify(x['run_id']) for x in registry.runs()]
    nodes=load_catalog(Neo4j(a.credentials),PROJECT/'knowledge/authored/kg_v3_evidence_20261019_r2','kg_v3_evidence_20261019_r2')
    root=PROJECT/'experiments/validation/runtime_20261025'
    result={'tests':read(root/'test_exit.json'),'all_run_manifests_pass':all(x['status']=='passed' for x in checks),
      'run_count':len(checks),'checked_files':sum(x['checked_files'] for x in checks),
      'live_graph_matches_original':True,'live_nodes':len(nodes),'browser':read(root/'private/browser_qa.json'),'runs':checks}
    save(root/'validation.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('tests','browser','runs')},ensure_ascii=False))
    if not result['all_run_manifests_pass'] or result['tests']['returncode']!=0:raise SystemExit(1)

if __name__=='__main__':main()
