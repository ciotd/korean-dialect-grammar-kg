import datetime,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('exchange',ROOT/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
def send(who):
 d=HERE/'private/reviewers'/who;d.mkdir(parents=True,exist_ok=False)
 prompt=(HERE/'private/review_packet.txt').read_text('utf8')+'\n지금은 설계와 pipeline.py를 먼저 검토. 다른 검토자의 결론을 보지 말 것. 실행 결과는 후속으로 보냄.\n'
 if who=='codex':prompt+='코드 직접 열람이 불가하면 아래 내용을 검토하고 그 한계를 명시.\n'+(HERE/'pipeline.py').read_text('utf8')
 prompt+='\n자기 검토만 '+str(d/'response.md')+' 에 저장 가능. 마지막 줄 END_RESEARCH_LOOP_20261103'
 (d/'prompt.txt').write_text(prompt,'utf8');x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offset':x.LOGS[who].stat().st_size})
 receipt=x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']);x.dump(d/'receipt.json',receipt)
 print(json.dumps({'who':who,'receipt':receipt},ensure_ascii=False))
def collect():
 for who in ('codex','claude'):
  d=HERE/'private/reviewers'/who
  if not (d/'start.json').exists():continue
  start=json.loads((d/'start.json').read_text('utf8'));es=[e for e in x.entries(who) if e.get('timestamp','')>=start['at']]
  x.dump(d/'messages.json',es);a=[e for e in es if e['role']=='assistant']
  (d/'transcript.md').write_text('\n\n'.join(e['text'] for e in a),'utf8')
  print(json.dumps({'who':who,'complete':any('END_RESEARCH_LOOP_20261103' in e['text'] for e in a),'models':list({e.get('model') for e in a}),'last':a[-1]['text'][-700:] if a else None},ensure_ascii=False))
if __name__=='__main__':
 if sys.argv[1]=='send':send(sys.argv[2])
 else:collect()
