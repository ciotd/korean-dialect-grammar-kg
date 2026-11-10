"""Versioned, non-destructive Neo4j import of the separated execution graph."""
import argparse
import base64
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,dumps,sha


def identifier(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',value):raise ValueError('Invalid schema identifier')
    return '`'+value+'`'


def properties(values):
    result={}
    for key,value in values.items():
        if value is None:continue
        native=isinstance(value,(str,int,float,bool)) or (isinstance(value,list) and all(isinstance(v,(str,int,float,bool)) for v in value) and len({type(v) for v in value})<=1)
        result[key]=value if native else dumps(value)
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--credentials',type=Path,default=Path('C:/Users/ciot28/Documents/Codex/neo4j-kg-local/credentials.json'));args=ap.parse_args()
    pointer=read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
    source=ROOT/pointer['graph'];graph=read(source);version=graph['version']
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'experiments/analyses/semantic_reachability_20261107/private'/stamp
    out.mkdir(parents=True,exist_ok=False)
    c=read(args.credentials);auth=base64.b64encode((c['username']+':'+c['password']).encode()).decode()
    endpoint='http://127.0.0.1:7474/db/'+c['database']+'/tx/commit'
    def query(statement,params=None):
        body={'statements':[{'statement':statement,'parameters':params or {}}]}
        request=urllib.request.Request(endpoint,dumps(body).encode(),{'Authorization':'Basic '+auth,'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=120) as response:data=json.load(response)
        if data.get('errors'):raise RuntimeError(dumps(data['errors']))
        r=data['results'][0];return [dict(zip(r['columns'],row['row'])) for row in r['data']]
    def snapshot(exclude=None):
        params={'version':exclude}
        ns=query('MATCH (n) WHERE $version IS NULL OR n.dataset_id IS NULL OR n.dataset_id <> $version RETURN elementId(n) AS dbid, labels(n) AS labels, properties(n) AS properties ORDER BY dbid',params)
        es=query('MATCH (a)-[r]->(b) WHERE $version IS NULL OR r.dataset_id IS NULL OR r.dataset_id <> $version RETURN elementId(r) AS dbid,elementId(a) AS source,elementId(b) AS target,type(r) AS type,properties(r) AS properties ORDER BY dbid',params)
        return {'nodes':ns,'edges':es}
    before=snapshot();save(out/'database_before.json',before)
    check_old=snapshot(version)
    existing=query('MATCH (n:KGNode {dataset_id:$version}) RETURN count(n) AS count',{'version':version})[0]['count']
    if existing:raise RuntimeError('Version already exists; refusing to overwrite: '+version)
    expected_nodes={};expected_edges={}
    try:
        groups=collections.defaultdict(list)
        for n in graph['nodes']:
            props={**properties(n.get('properties',{})),'id':n['id'],'dataset_id':version,'node_type':n['type']}
            title=n.get('title',n.get('properties',{}).get('title'))
            if title is not None:props['title']=title
            expected_nodes[n['id']]={'labels':sorted(['KGNode','ExecutionKG',n['type']]),'properties':props}
            groups[n['type']].append({'id':n['id'],'properties':props})
        for kind,items in groups.items():
            for i in range(0,len(items),200):
                query('UNWIND $rows AS row CREATE (n:KGNode:ExecutionKG:'+identifier(kind)+') SET n = row.properties',{'rows':items[i:i+200]})
        groups=collections.defaultdict(list)
        for e in graph['edges']:
            extra={k:v for k,v in e.items() if k not in ('id','source','target','relation','properties')}
            attrs={**e.get('properties',{}),**extra,'id':e['id'],'dataset_id':version}
            props=properties(attrs);expected_edges[e['id']]={'source':e['source'],'target':e['target'],'type':e['relation'],'properties':props}
            groups[e['relation']].append({'source':e['source'],'target':e['target'],'properties':props})
        for kind,items in groups.items():
            for i in range(0,len(items),200):
                query('UNWIND $rows AS row MATCH (a:KGNode {dataset_id:$version,id:row.source}), (b:KGNode {dataset_id:$version,id:row.target}) CREATE (a)-[r:'+identifier(kind)+']->(b) SET r = row.properties',{'version':version,'rows':items[i:i+200]})
        ns=query('MATCH (n:KGNode {dataset_id:$version}) RETURN n.id AS id,labels(n) AS labels,properties(n) AS properties',{'version':version})
        es=query('MATCH (a:KGNode {dataset_id:$version})-[r]->(b:KGNode {dataset_id:$version}) RETURN r.id AS id,a.id AS source,b.id AS target,type(r) AS type,properties(r) AS properties',{'version':version})
        node_ok={n['id']:{'labels':sorted(n['labels']),'properties':n['properties']} for n in ns}==expected_nodes
        edge_ok={e['id']:{k:e[k] for k in ('source','target','type','properties')} for e in es}==expected_edges
        old_ok=snapshot(version)==check_old
        sample=query('MATCH (r:SemanticRule {dataset_id:$version,id:$id})-[:ANY_BRANCH]->(b)-[:ALL]->(c:Condition)-[:ACCEPTS]->(v:FeatureValue) RETURN r.id AS rule,b.id AS branch,c.feature AS feature,v.value AS value ORDER BY branch,feature,value',{'version':version,'id':'SEM_Q_V_WH'})
        local=__import__('kg_pipeline.integrated',fromlist=['IntegratedReader']).IntegratedReader(graph)
        branch=local.rules['SEM_Q_V_WH']['branches'][0]
        observed=collections.defaultdict(list)
        for x in sample:observed[x['feature']].append(x['value'])
        # Local reader additionally inherits family scopes; show that distinction.
        inherited=query('MATCH (f)-[:HAS_USAGE]->(r:SemanticRule {dataset_id:$version,id:$id}) MATCH (f)-[:SUPPORTED_IN]->(s) RETURN s.allowed AS allowed',{'version':version,'id':'SEM_Q_V_WH'})
        for x in inherited:
            for key,values in json.loads(x['allowed']).items():
                observed[key]=[v for v in observed[key] if v in values] if key in observed else values
        if 'unit_kind' not in observed:observed['unit_kind']=['predicate']
        path_ok={k:sorted(set(v)) for k,v in observed.items()}=={k:sorted(set(v)) for k,v in branch['conditions'].items()}
        result={'dataset_id':version,'graph_sha256':sha(source.read_bytes()),'nodes':len(ns),'edges':len(es),
                'node_properties_match':node_ok,'edge_properties_match':edge_ok,'old_database_unchanged':old_ok,
                'sample_branch_matches_file_reader':path_ok,'qwen_pipeline_backend':'file_based_IntegratedReader; Neo4j visualization mirror',
                'browser':'http://localhost:7474/browser/','backup':str((out/'database_before.json').relative_to(ROOT)),
                'passed':node_ok and edge_ok and old_ok and path_ok}
        save(out/'neo4j_result.json',result);save(out/'sample_branch.json',{'conditions':sample,'inherited_scope':inherited})
        if not result['passed']:raise RuntimeError('Import verification failed')
        queries=f"""// 새 KG만 표시: 이전 버전은 유지됩니다.
MATCH p=(m:Module {{dataset_id:'{version}'}})<-[:IN_MODULE]-(r:SemanticRule)
RETURN p LIMIT 100;

// 한 규칙의 분기·조건·허용값·표현 보기
MATCH p=(r:SemanticRule {{dataset_id:'{version}',id:'SEM_Q_V_WH'}})-[:ANY_BRANCH|ALL|ACCEPTS|REALIZES*1..3]->(n)
RETURN p;

// 긍정/부정의 두 조건 묶음을 가진 실제 규칙
MATCH p=(r:SemanticRule {{dataset_id:'{version}',id:'SEM_EXT_COP_PAST_HAEYE'}})-[:ANY_BRANCH|ALL|ACCEPTS|REALIZES*1..3]->(n)
RETURN p;
"""
        (out/'explore.cypher').write_text(queries,encoding='utf8')
        save(out.parent.parent/'neo4j_latest.json',{'directory':str(out.relative_to(ROOT)),**result})
        print(dumps(result),flush=True)
    except Exception as exc:
        save(out/'failure.json',{'type':type(exc).__name__,'message':str(exc),'dataset_id':version,'old_versions_deleted':False})
        raise


if __name__=='__main__':main()
