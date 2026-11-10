"""Publish measured work events and explicitly transcribed human decisions."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from research_management.work import WorkStore

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=ROOT)
    p.add_argument('operation',choices=['task','proposal','chat-decision','applied','state'])
    p.add_argument('--file',type=Path,help='UTF-8 payload file; omit to read stdin')
    args=p.parse_args();store=WorkStore(args.project)
    if args.operation=='state':result=store.state()
    else:
        data=json.loads(args.file.read_text(encoding='utf-8-sig') if args.file else sys.stdin.read())
        if args.operation=='chat-decision':result=store.decide(data,channel='chat')
        else:result=getattr(store,args.operation)(data)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
