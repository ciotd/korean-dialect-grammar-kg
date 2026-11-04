"""Local blind ratings. Identity key is never served by the HTTP allowlist."""
import datetime as dt
import threading
from .core import read,write

ROOT='experiments/analyses/grammar_cards_20261028/private'
LOCK=threading.Lock()

def validate_ratings(payload,tasks):
    if not isinstance(payload,dict) or set(payload)!={'reviewer','ratings'}:raise ValueError('invalid_payload')
    reviewer=payload['reviewer']
    if not isinstance(reviewer,str) or not 1<=len(reviewer.strip())<=80:raise ValueError('reviewer_required')
    allowed={a['blind_id'] for t in tasks for a in t['answers']}
    if not isinstance(payload['ratings'],list) or len(payload['ratings'])>len(allowed):raise ValueError('invalid_ratings')
    seen=set()
    for r in payload['ratings']:
        if not isinstance(r,dict) or set(r)!={'blind_id','naturalness','meaning','comment'}:raise ValueError('invalid_rating_fields')
        if r['blind_id'] not in allowed or r['blind_id'] in seen:raise ValueError('invalid_blind_id')
        seen.add(r['blind_id'])
        n=r['naturalness']
        if n is not None and (type(n)!=int or n not in range(1,6)):raise ValueError('invalid_naturalness')
        if r['meaning'] not in ('unrated','preserved','changed','unclear'):raise ValueError('invalid_meaning')
        if not isinstance(r['comment'],str) or len(r['comment'])>3000:raise ValueError('invalid_comment')
    return {'reviewer':reviewer.strip(),'ratings':payload['ratings'],'saved_utc':dt.datetime.now(dt.timezone.utc).isoformat()}

def load_ratings(project):return read(project/ROOT/'ratings.json',{'reviewer':'','ratings':[]})

def save_ratings(project,payload):
    tasks=read(project/ROOT/'blind_review.json',[])
    value=validate_ratings(payload,tasks)
    with LOCK:
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        write(project/ROOT/'rating_history'/f'{stamp}.json',value)
        write(project/ROOT/'ratings.json',value)
    return {'saved':len(value['ratings']),'saved_utc':value['saved_utc']}
