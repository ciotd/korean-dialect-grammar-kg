"""Run on the Qwen Linux server. Read-only metadata; no network/model loading."""
from pathlib import Path
import json,hashlib,importlib.metadata,sys
root=Path('/root/project/server/server_piai/model/Qwen3.8-27B')
def digest(data):return hashlib.sha256(data).hexdigest()
def load(name):
 p=root/name
 return json.loads(p.read_text('utf8')) if p.exists() else {}
versions={}
for name in ('vllm','transformers','torch','tokenizers'):
 try:versions[name]=importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:versions[name]='not_installed'
cfg=load('config.json');tok=load('tokenizer_config.json');gen=load('generation_config.json');tc=cfg.get('text_config',cfg)
report={'python':sys.version.split()[0],'model_path':str(root),'versions':versions,
'config':{k:cfg.get(k) for k in ('model_type','architectures','transformers_version','quantization_config')},
'text_config':{k:tc.get(k) for k in ('model_type','vocab_size','num_hidden_layers','hidden_size','dtype','torch_dtype')},
'generation_config':{k:gen.get(k) for k in ('temperature','top_p','top_k','min_p','presence_penalty','repetition_penalty','eos_token_id')},
'file_hashes':{},'templates':{}}
for name in ('config.json','tokenizer_config.json','generation_config.json','chat_template.jinja'):
 p=root/name
 if p.exists():report['file_hashes'][name]=digest(p.read_bytes())
template=tok.get('chat_template')
if template is not None:
 encoded=json.dumps(template,ensure_ascii=False,sort_keys=True)
 report['templates']['tokenizer_config']={'characters':len(encoded),'sha256':digest(encoded.encode()),'mentions_enable_thinking':'enable_thinking' in encoded}
p=root/'chat_template.jinja'
if p.exists():report['templates']['chat_template.jinja']={'characters':len(p.read_text('utf8')),'mentions_enable_thinking':'enable_thinking' in p.read_text('utf8')}
print(json.dumps(report,ensure_ascii=False,indent=2))
