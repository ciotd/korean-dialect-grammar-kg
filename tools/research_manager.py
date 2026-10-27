"""Local research workflow; no external dependencies or model calls."""
import argparse
import json
import sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from research_management.core import Registry,guard_dataset

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=PROJECT)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('sync',help='Index existing runs and update research status')
    sub.add_parser('list')
    compare=sub.add_parser('compare');compare.add_argument('left');compare.add_argument('right')
    verify=sub.add_parser('verify');verify.add_argument('run')
    brief=sub.add_parser('brief');brief.add_argument('run');brief.add_argument('--previous')
    check=sub.add_parser('check-data');check.add_argument('inputs',type=Path);check.add_argument('--role',choices=['development','evaluation','regression'],required=True)
    server=sub.add_parser('serve');server.add_argument('--port',type=int,default=8766)
    a=p.parse_args();registry=Registry(a.project)
    if a.command=='serve':
        from research_management.server import serve
        serve(a.project,a.port);return
    if a.command=='sync':result=registry.sync()
    elif a.command=='list':result=registry.runs()
    elif a.command=='compare':result=registry.compare(a.left,a.right)
    elif a.command=='verify':result=registry.verify(a.run)
    elif a.command=='brief':result={'review_bundle':str(registry.review_bundle(a.run,a.previous))}
    elif a.command=='check-data':result=guard_dataset(a.project,a.inputs,a.role)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if a.command=='verify' and result['status']!='passed':sys.exit(1)

if __name__=='__main__':main()
