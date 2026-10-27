"""Build the versioned execution projection from the original graph and source texts."""
import argparse,json,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from kg_runtime.graph import build
from kg_runtime.catalog import build_search_projection
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=PROJECT);p.add_argument('--source-texts',type=Path)
    p.add_argument('--search-projection',action='store_true')
    a=p.parse_args()
    if not a.search_projection and not a.source_texts:p.error('--source-texts required for original projection')
    print(json.dumps(build_search_projection(a.project) if a.search_projection else build(a.project,a.source_texts),ensure_ascii=False,indent=2))
