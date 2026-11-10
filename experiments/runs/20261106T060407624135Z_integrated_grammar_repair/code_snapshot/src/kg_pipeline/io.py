import ast
import base64
import hashlib
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

def dumps(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(data): return hashlib.sha256(data).hexdigest()
def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def load_jsonl(path):return [json.loads(l) for l in Path(path).read_text(encoding='utf-8-sig').splitlines() if l.strip()]

class CallError(RuntimeError): pass
def unique_json_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise CallError('duplicate_json_key:'+key)
        result[key]=value
    return result
class Qwen:
    def __init__(self,path,model=None,timeout=180):
        vals={}
        for n in ast.parse(Path(path).read_text(encoding='utf-8-sig')).body:
            if isinstance(n,ast.Assign):
                for t in n.targets:
                    if isinstance(t,ast.Name) and t.id in ('LLM_BASE_URL','GATEWAY_TOKEN'):
                        vals[t.id]=ast.literal_eval(n.value)
        self.url=vals['LLM_BASE_URL'].rstrip('/');self.key=vals['GATEWAY_TOKEN'];self.timeout=timeout
        req=urllib.request.Request(self.url+'/models',headers={'Authorization':'Bearer '+self.key})
        with urllib.request.urlopen(req,timeout=20) as r:self.models=json.load(r)
        ids=[m['id'] for m in self.models['data']]
        if model is None and len(ids)!=1:raise ValueError('Explicit model required when multiple models are served')
        self.model=model or ids[0]
        if self.model not in ids:raise ValueError('Requested model is not served')
    def build_request(self,stage,prompt,user,schema,max_tokens,seed):
        return {'model':self.model,'messages':[{'role':'system','content':prompt},{'role':'user','content':user if isinstance(user,str) else dumps(user)}],
          'temperature':0,'top_p':1,'seed':seed,'max_tokens':max_tokens,'chat_template_kwargs':{'enable_thinking':False},
          'response_format':{'type':'json_schema','json_schema':{'name':stage,'strict':True,'schema':schema}}}
    def call(self,stage,prompt,user,schema,out,max_tokens,seed):
        request=self.build_request(stage,prompt,user,schema,max_tokens,seed)
        save(out/'request.json',request)
        t=time.perf_counter();meta={'stage':stage,'request_sha256':sha(dumps(request).encode()),'attempt':1,'retry':False}
        try:
            # Preserve schema property order: kind precedes its dependent feature schema.
            req=urllib.request.Request(self.url+'/chat/completions',data=json.dumps(request,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=self.timeout) as r:
                raw=r.read();meta['http_status']=r.status
            response=json.loads(raw);save(out/'response.json',response)
            choice=response['choices'][0];meta.update(usage=response.get('usage'),model=response.get('model'),response_id=response.get('id'),finish_reason=choice.get('finish_reason'))
            if choice.get('finish_reason')!='stop':raise CallError('non_stop_finish:'+str(choice.get('finish_reason')))
            content=choice['message'].get('content')
            if not isinstance(content,str):raise CallError('missing_content')
            value=json.loads(content,object_pairs_hook=unique_json_object);save(out/'parsed.json',value)
            meta['status']='response_received';return value
        except Exception as e:
            meta['status']='failed';meta['error_type']=type(e).__name__
            if isinstance(e,urllib.error.HTTPError):
                meta['http_status']=e.code;meta['server_error']=e.read().decode(errors='replace')[:2000].replace(self.key,'[REDACTED]')
            elif isinstance(e,(json.JSONDecodeError,CallError)):meta['error']=str(e)[:400]
            raise CallError(meta['error_type']+':'+str(meta.get('http_status',''))) from None
        finally:
            meta['seconds']=round(time.perf_counter()-t,4);save(out/'meta.json',meta)

class Neo4j:
    """Reuses the existing project's stdlib HTTP transaction interface; fixed read queries only."""
    def __init__(self,credentials):
        c=read(credentials)
        self.endpoint='http://127.0.0.1:7474/db/'+c['database']+'/tx/commit'
        self.auth=base64.b64encode((c['username']+':'+c['password']).encode()).decode()
    def query(self,statement,params=None):
        # No caller-provided model-generated query is accepted by the pipeline.
        req=urllib.request.Request(self.endpoint,data=dumps({'statements':[{'statement':statement,'parameters':params or {}}]}).encode(),headers={'Authorization':'Basic '+self.auth,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as r:data=json.load(r)
        if data.get('errors'):raise CallError('neo4j_query_error:'+dumps(data['errors']))
        r=data['results'][0]
        return [dict(zip(r['columns'],d['row'])) for d in r['data']]
