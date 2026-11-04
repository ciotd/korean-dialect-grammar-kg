"""Summarize actual human ratings; never manufactures missing scores."""
import argparse
import collections
import datetime as dt
import statistics
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,sha,dumps
from research_management.evaluation import ROOT as REVIEW_ROOT,validate_ratings

def summarize(tasks,key,payload):
    valid=validate_ratings({'reviewer':payload['reviewer'],'ratings':payload['ratings']},tasks)
    groups=collections.defaultdict(list);pairs=collections.defaultdict(dict)
    for r in valid['ratings']:
        item=key[r['blind_id']];groups[item['condition']].append(r)
        if r['naturalness'] is not None:pairs[item['input_id']][item['condition']]=r['naturalness']
    summary={}
    for c in ('old_single','single','multi'):
        rows=groups[c];scores=[r['naturalness'] for r in rows if r['naturalness'] is not None]
        meaning=collections.Counter(r['meaning'] for r in rows if r['meaning']!='unrated')
        summary[c]={'rated_n':len(scores),'mean_naturalness':statistics.mean(scores) if scores else None,
                    'median_naturalness':statistics.median(scores) if scores else None,'meaning_counts':dict(meaning)}
    paired=[]
    for a,b in [('old_single','single'),('single','multi')]:
        delta=[x[b]-x[a] for x in pairs.values() if a in x and b in x]
        paired.append({'left':a,'right':b,'paired_n':len(delta),'mean_paired_difference':statistics.mean(delta) if delta else None,
            'right_higher':sum(x>0 for x in delta),'same':sum(x==0 for x in delta),'right_lower':sum(x<0 for x in delta)})
    return {'reviewer':valid['reviewer'],'summary':summary,'paired':paired,
        'interpretation':'descriptive scores of this rater on regression inputs; not general accuracy; missing ratings excluded, not zero'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--reveal',action='store_true',help='After rating, reveal condition-level summary');a=p.parse_args()
    if not a.reveal:raise SystemExit('평가를 마친 뒤 --reveal 옵션으로 방식별 결과를 확인하세요.')
    root=ROOT/REVIEW_ROOT
    if not (root/'ratings.json').exists():raise SystemExit('저장된 사람 평가가 아직 없습니다. 평가 화면에서 PC에 저장을 눌러 주세요.')
    value=summarize(read(root/'blind_review.json'),read(root/'blind_key.json'),read(root/'ratings.json'))
    value['ratings_sha256']=sha((root/'ratings.json').read_bytes());value['created_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    out=root/'human_summaries'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ.json');save(out,value)
    print(dumps(value));print(out)

if __name__=='__main__':main()
