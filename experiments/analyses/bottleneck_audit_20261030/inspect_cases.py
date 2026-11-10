import json,sys
from pathlib import Path
d=json.loads((Path(__file__).parent/'private/evidence.json').read_text(encoding='utf-8'))
for c in d[int(sys.argv[1]):int(sys.argv[2])]:
 print('\nCASE',c['id'],'INPUT',c['input'],'\nREF',c['reference'])
 for f in c['families']:
  print('NEED',f['key'],[(cid,c['arms']['single']['candidate_trace'][cid]['stage'],c['arms']['multi']['candidate_trace'][cid]['stage']) for cid in f['candidate_ids']])
 for a,v in c['arms'].items():
  print(a,v['output'],'ERROR',v['error'])
  ed=v.get('plan',{}).get('edits',v.get('raw_agent',{}).get('edits',[]))
  for e in ed:
   print(' EDIT',e.get('before',e.get('word_ids')), '->',e.get('after'),'/',e.get('outcome',e.get('action')),','.join(b['card_id'] for b in e.get('bindings',[])),[i['code'] for i in e.get('issues',[])])
  if not ed:print(' REASON',v.get('raw_agent',{}).get('reason'))
