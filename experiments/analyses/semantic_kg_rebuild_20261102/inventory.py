"""Reproducible structural inventory; never labels extraction as semantic review."""
import collections, hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2'
CACHE=Path(r'C:\Users\ciot28\Documents\Codex\2026-10-13\ciotd-odor-complaint-dialect-rag-kg\work\source_audit')
def read(p):return json.loads(p.read_text(encoding='utf8'))
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 nodes=[json.loads(x) for x in (BASE/'graph/nodes.jsonl').read_text(encoding='utf8').splitlines()]
 edges=[json.loads(x) for x in (BASE/'graph/edges.jsonl').read_text(encoding='utf8').splitlines()]
 expected=read(BASE/'provenance/extraction_manifest.json')['page_text_hashes'];sources=[]
 for s in read(BASE/'provenance/sources.json'):
  path=CACHE/(s['id']+'.json');pages=read(path) if path.exists() else []
  hashes=[hashlib.sha256(p['text'].encode()).hexdigest() for p in pages]
  matches=sum(a==b for a,b in zip(hashes,expected[s['id']]))
  sources.append({'id':s['id'],'filename':s['filename'],'expected_pdf_sha256':s['sha256'],'pdf_reopened':False,'cached_path':str(path),'cache_sha256':sha(path) if path.exists() else None,'cached_pages':len(pages),'expected_pages':len(expected[s['id']]),'exact_page_hash_matches':matches,'cache_fully_matches_recorded_extraction':hashes==expected[s['id']],'policy':s['policy'],'current_semantic_review':'not_whole_document_reviewed'})
 rows=[]
 for n in nodes:
  if n['type']!='SourceAtom':continue
  p=n['properties'];o=p.get('original_spec',{})
  rows.append({'id':n['id'],'title':n.get('title'),'module':p.get('module'),'kind':p.get('original_kind',o.get('kind')),'prior_semantic_review_status':p.get('semantic_review_status'),'new_semantic_review_status':'pending','original_match':o.get('match'),'original_action':o.get('action'),'original_output':o.get('output'),'source_refs':o.get('source_refs',o.get('_refs',[])),'new_rule_ids':[]})
 stats={'node_types':dict(collections.Counter(n['type'] for n in nodes)),'edge_types':dict(collections.Counter(e.get('type',e.get('relation')) for e in edges)),'source_atom_kinds':dict(collections.Counter(r['kind'] for r in rows)),'prior_review_states':dict(collections.Counter(str(r['prior_semantic_review_status']) for r in rows)),'source_span_kinds':dict(collections.Counter(n['properties'].get('quote_kind') for n in nodes if n['type']=='SourceSpan')),'semantic_review_completed_this_inventory':0}
 frozen={str(p.relative_to(ROOT)):sha(p) for p in [BASE/'graph/nodes.jsonl',BASE/'graph/edges.jsonl',ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json',ROOT/'src/kg_runtime/graph.py',ROOT/'src/kg_runtime/cards.py']}
 dump(HERE/'private/inventory.json',stats)
 # Re-running an inventory must not erase subsequent verification or reviews.
 for name,data in [('source_access.json',sources),('refinement_ledger.json',rows),('original_hashes.json',frozen)]:
  if not (HERE/'private'/name).exists():dump(HERE/'private'/name,data)
 sys.path.insert(0,str(ROOT/'src'))
 from research_management.work import WorkStore
 try:
  WorkStore(ROOT).task({'id':'semantic-kg-foundation-20261102','title':'문헌 의미 정제와 조건 기반 KG 검증','actor':'총괄 + Orca 두 검토자','stage':'전체 구조 집계 완료 · 독립 검토 진행','status':'running','message':'721개 지식 항목의 구조를 집계. 정제 완료 수와 별개이며 접근 확인 결과는 source_access.json에 기록.'})
 except ValueError as exc:
  if str(exc)!='terminal_task_use_new_id':raise
 print(json.dumps(stats,ensure_ascii=False));print(json.dumps([{k:s[k] for k in ['id','cached_pages','expected_pages','exact_page_hash_matches']} for s in sources],ensure_ascii=False))
if __name__=='__main__':run()
