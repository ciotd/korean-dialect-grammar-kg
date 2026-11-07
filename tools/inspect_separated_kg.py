"""Explicit source lookup or restoration; never part of a generation request."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.separated_graph import lookup_audit, restore


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',type=Path,help='Directory containing graph.json and audit.json; default latest separated version')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--node',help='Existing stable knowledge/rule ID')
    group.add_argument('--restore',action='store_true',help='Reconstruct the old JSON, without changing any live files')
    parser.add_argument('--output',type=Path,required=True,help='New private JSON path; existing files are refused')
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists; choose a new path')
    if 'private' not in args.output.resolve().parts:parser.error('Source lookup/restoration must be saved in a private directory')
    def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
    bundle=args.bundle or (ROOT/read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')['graph']).parent
    graph,audit=read(bundle/'graph.json'),read(bundle/'audit.json')
    result=restore(graph,audit) if args.restore else lookup_audit(graph,audit,args.node)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
    print(json.dumps({'saved':str(args.output.resolve()),'mode':'restoration' if args.restore else 'explicit_audit_lookup'},ensure_ascii=False))


if __name__=='__main__':main()
