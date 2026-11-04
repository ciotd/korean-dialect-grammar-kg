"""Import version-bound user feedback; never modifies KG or triggers models."""
import argparse,collections,datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def validate(dataset,feedback):
 content={k:v for k,v in dataset.items() if k!='review_set_hash'}
 actual=hashlib.sha256(json.dumps(content,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 if actual!=dataset['review_set_hash']:raise ValueError('review_dataset_hash_mismatch')
 if feedback.get('version')!=dataset['version'] or feedback.get('review_set_hash')!=actual:raise ValueError('wrong_review_version_or_hash')
 if feedback.get('kind')!='user_entered_native_judgments_pending_lead_import':raise ValueError('unexpected_record_kind')
 units={c['id']:(row,c) for row in dataset['rows'] for c in row['candidates']}
 answers=feedback.get('answers')
 if not isinstance(answers,dict) or not set(answers)<=set(units):raise ValueError('unknown_review_item')
 for key,a in answers.items():
  if not isinstance(a,dict):raise ValueError('invalid_answer')
  if a.get('naturalness') not in ('','natural','less_natural','unnatural','uncertain'):raise ValueError('invalid_naturalness')
  if a.get('meaning') not in ('','preserved','changed','context','uncertain'):raise ValueError('invalid_meaning')
  for field in ('alternative','comment'):
   if not isinstance(a.get(field),str) or len(a[field])>2000:raise ValueError('invalid_text_field')
 return units
def import_file(path):
 path=Path(path);dataset=read(HERE/'private/review_set.json');feedback=read(path);units=validate(dataset,feedback)
 digest=sha(path);dest=HERE/'private/feedback'/digest[:16];dest.mkdir(parents=True,exist_ok=True)
 snapshot=dest/'user_feedback.json'
 if snapshot.exists() and sha(snapshot)!=digest:raise ValueError('existing_feedback_conflict')
 if not snapshot.exists():snapshot.write_bytes(path.read_bytes())
 rows=[]
 for key,(row,c) in units.items():
  a=feedback['answers'].get(key)
  rows.append({'id':key,'original_input':row['input'],'reviewed_candidate':c['text'],'assumed_meaning':c['meaning'],
   'candidate_basis':c['basis'],'rule_id':c['rule_id'],'user_answer':a,
   'review_complete':bool(a and a['naturalness'] and a['meaning']),
   'accepted_by_this_reviewer_in_given_context':bool(a and a['naturalness']=='natural' and a['meaning']=='preserved')})
 summary={'version':dataset['version'],'review_set_hash':dataset['review_set_hash'],'source_file':str(path.resolve()),'source_sha256':digest,
  'exported_at':feedback.get('exported_at'),'received_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'units_total':len(units),'answers_received':len(feedback['answers']),'complete':sum(r['review_complete'] for r in rows),
  'naturalness_counts':dict(collections.Counter(a['naturalness'] for a in feedback['answers'].values())),
  'meaning_counts':dict(collections.Counter(a['meaning'] for a in feedback['answers'].values())),
  'alternatives_count':sum(bool(a['alternative'].strip()) for a in feedback['answers'].values()),
  'comment_count':sum(bool(a['comment'].strip()) for a in feedback['answers'].values()),
  'source_inputs_unchanged':{k:sha(Path(k))==v for k,v in dataset['source_hashes'].items()},
  'interpretation':'One user review of manually authored development candidates; not Qwen evaluation, universal dialect gold, or approval to mutate KG.',
  'qwen_calls':0,'kg_changes':0,'rows':rows}
 if not all(summary['source_inputs_unchanged'].values()):raise ValueError('reviewed_inputs_changed')
 # Receipt is immutable on repeated imports; latest points at the same snapshot.
 if not (dest/'receipt.json').exists():dump(dest/'receipt.json',summary)
 dump(HERE/'private/latest_receipt.json',{'directory':str(dest),'source_sha256':digest,'receipt':str(dest/'receipt.json')})
 return dest,read(dest/'receipt.json')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('file');args=parser.parse_args();p,s=import_file(args.file)
 print(json.dumps({'stored':str(p),'complete':s['complete'],'total':s['units_total'],'naturalness':s['naturalness_counts'],'meaning':s['meaning_counts'],'alternatives':s['alternatives_count']},ensure_ascii=False))
