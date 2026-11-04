"""Create a local recovery commit without altering HEAD, index or work files.

prepare scans Git-eligible files; commit uses only that frozen manifest.
Private KG graphs and derived datasets are copied locally, never staged.
No network operations, model calls, checkout, deletion or automatic promotion.
"""
from pathlib import Path
import argparse, collections, datetime, hashlib, json, os, re, shutil, subprocess

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / 'local/version_history'
DENIED = {'.claude', '.codex', '.agents', '.aws', 'local', 'private', '__pycache__', 'node_modules', '.venv', 'work'}

def git(*args, env=None, binary=False):
    HOME.mkdir(parents=True,exist_ok=True)
    empty=HOME/'empty_global_ignore'; empty.touch(exist_ok=True)
    p=subprocess.run(['git', '-c', 'core.excludesFile='+str(empty), *args], cwd=ROOT, env=env, capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode('utf8',errors='replace'))
    return p.stdout if binary else p.stdout.decode('utf8').strip()

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value): p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def load(p): return json.loads(p.read_text(encoding='utf8'))

def denied(path):
    p=Path(path)
    return bool(set(p.parts)&DENIED) or path.startswith(('data/raw/', 'data/derived_private/')) or p.name=='test.py' or p.name.startswith('.env') or p.suffix.lower() in {'.pdf','.zip','.pem','.key'} or bool(re.search(r'credentials|settings\.local',p.name,re.I))

def scan(path):
    # Report only location and detector, never matched secret content.
    s=path.read_text(encoding='utf8',errors='replace'); findings=[]
    patterns={
        'private_key':r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
        'provider_key':r'\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{24,})',
        'literal_credential':r'''(?im)^\s*["']?(?:GATEWAY_TOKEN|API_KEY|api_key|password|NEO4J_PASSWORD|access_token)["']?\s*[:=]\s*["']([^"'\r\n]{8,})["']'''
    }
    for name,pattern in patterns.items():
        for m in re.finditer(pattern,s):
            value=m.group(1) if m.lastindex else m.group(0)
            if name=='literal_credential' and any(x in value.lower() for x in ('example','placeholder','redacted','your_','changeme','not-needed','dummy','test','unused','api_key')): continue
            findings.append({'file':path.relative_to(ROOT).as_posix(),'line':s.count('\n',0,m.start())+1,'detector':name})
    return findings

def prepare():
    if 'ciotd/korean-dialect-grammar-kg' not in git('remote','get-url','origin'): raise RuntimeError('Unexpected repository')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=HOME/stamp; out.mkdir(parents=True)
    prior=HOME/'latest.json'
    parent=load(prior)['commit'] if prior.exists() else git('rev-parse','origin/main')
    names=sorted(set(git('ls-files','--cached','--others','--exclude-standard','-z',binary=True).decode('utf8').strip('\0').split('\0')))
    paths=[p for p in names if p and not denied(p) and (ROOT/p).is_file()]
    findings=[f for p in paths for f in scan(ROOT/p)]
    # Baseline-only files remain inherited, avoiding accidental removal from the older worktree.
    prior_paths=git('ls-tree','-r','--name-only',parent).splitlines()
    forbidden_parent=[p for p in prior_paths if denied(p)]
    if forbidden_parent: raise RuntimeError('Parent contains excluded paths; review before checkpoint')
    retained=[p for p in prior_paths if p not in paths]
    private=[]
    private_paths=list((ROOT/'knowledge/authored').glob('*/private/graph.json'))
    private_paths+=list((ROOT/'data/derived_private').rglob('*'))
    for p in private_paths:
        if not p.is_file() or p.suffix.lower() not in {'.json','.jsonl','.md'}: continue
        rel=p.relative_to(ROOT); dest=out/'private_state'/rel; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest); assert digest(p)==digest(dest)
        private.append({'path':rel.as_posix(),'sha256':digest(p)})
    manifest={'id':stamp,'status':'prepared','parent':parent,'working_head':git('rev-parse','HEAD'),
              'purpose':'recovery_checkpoint_not_quality_release','files':{p:digest(ROOT/p) for p in paths},
              'retained_parent_only':retained,'private_local_copies':private,'secret_findings':findings,
              'limits':['Private run records remain in their original folders; not duplicated here.','External sources, credentials, installed dependencies and live DB are not backed up.','Automatic secret scan is not a guarantee that all sensitive content is detected.']}
    save(out/'manifest.json',manifest)
    print(json.dumps({'directory':str(out),'files':len(paths),'private_local_copies':len(private),'retained_parent_only':retained,'secret_findings':findings},ensure_ascii=False))

def commit(directory):
    out=Path(directory).resolve()
    if not out.is_relative_to(HOME.resolve()): raise ValueError('Checkpoint must be inside local/version_history')
    m=load(out/'manifest.json')
    if m['status']!='prepared' or m['secret_findings']: raise RuntimeError('Not ready; scan findings or already committed')
    changed=[p for p,h in m['files'].items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    if changed: raise RuntimeError('Files changed after preparation: '+str(changed))
    env=dict(os.environ,GIT_INDEX_FILE=str(out/'index'))
    git('read-tree',m['parent'],env=env)
    listing=out/'paths.bin'; listing.write_bytes(b''.join(p.encode('utf8')+b'\0' for p in m['files']))
    git('-c','core.autocrlf=false','add','--pathspec-from-file='+str(listing),'--pathspec-file-nul',env=env)
    # Confirm staged bytes equal manifest bytes, independent of filters/EOL settings.
    staged={}
    for line in git('ls-files','--stage','-z',env=env,binary=True).decode('utf8').strip('\0').split('\0'):
        left,path=line.split('\t',1); staged[path]=left.split()[1]
    for p,h in m['files'].items():
        blob=(ROOT/p).read_bytes()
        object_id=hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
        if hashlib.sha256(blob).hexdigest()!=h or staged.get(p)!=object_id: raise RuntimeError('Staged bytes changed: '+p)
    tree=git('write-tree',env=env)
    sha=git('commit-tree',tree,'-p',m['parent'],'-m','chore: checkpoint research state '+m['id'][:8],'-m','Recovery checkpoint only; not a validated quality release.\nPrivate source data and credentials remain excluded.')
    ref='refs/heads/checkpoints/'+m['id']
    git('update-ref',ref,sha,'0'*40)
    m.update(status='committed',commit=sha,ref=ref,tree=tree)
    save(out/'manifest.json',m); save(HOME/'latest.json',{'directory':str(out),'commit':sha,'ref':ref})
    print(json.dumps({'commit':sha,'ref':ref,'files':len(m['files']),'private_local_copies':len(m['private_local_copies']),'pushed':False,'working_branch_changed':False},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['prepare','commit']);parser.add_argument('--directory');args=parser.parse_args()
    prepare() if args.action=='prepare' else commit(args.directory)
