"""Execute preserved import, verify database content, and record no credentials."""
import argparse,base64,collections,hashlib,json,time,urllib.request
from pathlib import Path

def main(a):
    root=Path(a.kg);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    c=json.loads(Path(a.credentials).read_text());auth=base64.b64encode((c['username']+':'+c['password']).encode()).decode()
    endpoint='http://localhost:7474/db/'+c['database']+'/tx/commit'
    def query(s,params=None):
        body=json.dumps({'statements':[{'statement':s,'parameters':params or {},'includeStats':True}]}).encode()
        req=urllib.request.Request(endpoint,body,{'Content-Type':'application/json','Authorization':'Basic '+auth})
        with urllib.request.urlopen(req,timeout=120) as r:result=json.load(r)
        if result['errors']:raise RuntimeError(json.dumps(result['errors']))
        return result['results'][0]
    def rows(s):return [r['row'] for r in query(s)['data']]
    run=json.loads((root/'provenance/input_manifest.json').read_text())['run_id']
    where="{dataset_id:'"+run+"'}"
    script=(root/'neo4j/import.cypher').read_text(encoding='utf-8')
    statements=[s.strip() for s in '\n'.join(l for l in script.splitlines() if not l.lstrip().startswith('//')).split(';') if s.strip()]
    log={'date_kst':'2026-10-21','dataset_id':run,'database':c['database'],'components':rows('CALL dbms.components() YIELD name,versions,edition RETURN name,versions,edition'),'import_sha256':hashlib.sha256(script.encode()).hexdigest(),'passes':[]}
    def save(): (out/'live_validation.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    log['csv_settings']=rows("SHOW SETTINGS YIELD name,value WHERE name='db.import.csv.legacy_quote_escaping' RETURN name,value")
    assert log['csv_settings']==[['db.import.csv.legacy_quote_escaping','false']], 'Set CSV quote parsing to false before import'
    for repeat in range(2):
        changes=[];t=time.monotonic()
        log['passes'].append({'pass':repeat+1,'stats':changes})
        for i,s in enumerate(statements):
            try:res=query(s)
            except Exception as e:
                log['failure']={'pass':repeat+1,'statement':i+1,'error':str(e)};save();raise
            changes.append(res['stats']);save()
            print('import',repeat+1,'statement',i+1,'of',len(statements),flush=True)
        log['passes'][-1]['seconds']=time.monotonic()-t;save()
    ns=[json.loads(l) for l in (root/'graph/nodes.jsonl').read_text(encoding='utf-8').splitlines()]
    es=[json.loads(l) for l in (root/'graph/edges.jsonl').read_text(encoding='utf-8').splitlines()]
    actualn=rows('MATCH (n:KGNode '+where+') RETURN n.id,n.node_type,n.title,n.properties_json')
    actuale=rows('MATCH (s:KGNode '+where+')-[r]->(t:KGNode '+where+') RETURN r.id,s.id,type(r),t.id,r.properties_json')
    expectedn={n['id']:[n['type'],n['title'],n['properties']] for n in ns}
    expectede={e['id']:[e['source'],e['relation'],e['target'],e['properties']] for e in es}
    checks={'node_count':len(actualn)==len(ns),'edge_count':len(actuale)==len(es),
      'all_node_properties_preserved':{r[0]:[r[1],r[2],json.loads(r[3])] for r in actualn}==expectedn,
      'all_relationship_properties_preserved':{r[0]:[r[1],r[2],r[3],json.loads(r[4])] for r in actuale}==expectede,
      'second_import_creates_no_duplicates':all(s.get('nodes_created',0)==0 and s.get('relationships_created',0)==0 for s in log['passes'][1]['stats'])}
    log['counts']={'nodes':len(actualn),'edges':len(actuale)};log['checks']=checks
    log['explore_queries']=[]
    text=(root/'neo4j/explore.cypher').read_text(encoding='utf-8')
    for s in '\n'.join(l for l in text.splitlines() if not l.lstrip().startswith('//')).split(';'):
        if s.strip():
            r=query(s);log['explore_queries'].append({'query':s.strip(),'returned_rows':len(r['data'])})
    log['module_counts']=rows('MATCH (n:KGNode '+where+')-[:in_module]->(m:Module) RETURN m.number,m.title,count(n) ORDER BY m.number')
    log['passed']=all(checks.values()) and all(r['returned_rows']>0 for r in log['explore_queries']);save()
    print(json.dumps({'passed':log['passed'],'counts':log['counts'],'checks':checks,'explore_queries':len(log['explore_queries'])}))
    if not log['passed']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kg',required=True);p.add_argument('--out',required=True);p.add_argument('--credentials',required=True);main(p.parse_args())
