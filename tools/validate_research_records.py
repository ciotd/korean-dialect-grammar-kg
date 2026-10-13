"""Read-only checks for this research scaffold; no model calls or artifact writes.

The small schema checker supports only keywords used by these two draft schemas.
It is not a complete JSON Schema implementation or a linguistic validator.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def matches_type(value, expected):
    if expected == 'null':
        return value is None
    if expected == 'boolean':
        return isinstance(value, bool)
    if expected == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, {'object':dict, 'array':list, 'string':str}[expected])

def check_schema(value, schema, path='$'):
    expected = schema.get('type')
    if expected:
        types = expected if isinstance(expected, list) else [expected]
        require(any(matches_type(value,t) for t in types), f'{path}: type')
    if 'enum' in schema:
        require(value in schema['enum'], f'{path}: enum')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            require(key in value, f'{path}: missing {key}')
        properties = schema.get('properties', {})
        for key,item in value.items():
            rule = properties.get(key, schema.get('additionalProperties'))
            if isinstance(rule, dict):
                check_schema(item,rule,f'{path}.{key}')
    if isinstance(value, list):
        require(len(value) >= schema.get('minItems',0), f'{path}: minItems')
        for i,item in enumerate(value):
            check_schema(item,schema.get('items',{}),f'{path}[{i}]')
    if isinstance(value, str):
        require(len(value) >= schema.get('minLength',0), f'{path}: minLength')
    if isinstance(value, int) and not isinstance(value, bool) and 'minimum' in schema:
        require(value >= schema['minimum'], f'{path}: minimum')

def rows(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))

def main():
    scope = read_json(ROOT/'provenance/source_scope.json')
    files = rows(ROOT/'provenance/source_file_inventory.tsv')
    commits = rows(ROOT/'provenance/commit_history.tsv')
    require(len(files)==scope['source_files'], 'source file count')
    require(len(commits)==scope['commits'], 'commit count')
    require(not scope['tree_truncated'] and scope['history_reaches_root'], 'source coverage')
    require(scope['source_write_operations']==0, 'source write policy')
    require(commits[0]['sha']==scope['source_commit'], 'source head')
    source_paths={r['path'] for r in files}
    for row in files:
        require(re.fullmatch(r'[0-9a-f]{40}',row['blob_sha']), 'source blob identifier')
        require(scope['source_commit'] in row['url'], 'unpinned source link')
    summary=read_json(ROOT/'provenance/source_build_summary.json')
    require(sum(summary['fact_types'].values())==summary['facts'], 'fact type totals')
    require(sum(summary['claim_statuses'].values())==summary['facts'], 'claim status totals')
    require(sum(s['facts'] for s in summary['sources'])==summary['facts'], 'source fact totals')
    require(sum(s['pages'] for s in summary['sources'])==summary['source_pages'], 'page totals')

    run=read_json(ROOT/'experiments/templates/run_record.json')
    check_schema(run,read_json(ROOT/'schemas/run_record.schema.json'))
    require(run['status']=='planned' and run['evaluation']['quality_scores'] is None, 'template not executed')
    knowledge_count=0
    for path in (ROOT/'knowledge/authored').glob('*.json'):
        check_schema(read_json(path),read_json(ROOT/'schemas/knowledge_record.schema.json'))
        knowledge_count+=1

    link_count=0
    for path in ROOT.rglob('*.md'):
        content=path.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)',content):
            if target.startswith('https://github.com/'+scope['source_repository']+'/blob/'):
                from urllib.parse import unquote
                prefix='https://github.com/'+scope['source_repository']+'/blob/'+scope['source_commit']+'/'
                require(target.startswith(prefix), f'unpinned link: {path}')
                require(unquote(target[len(prefix):]).split('#')[0] in source_paths, f'missing source path: {target}')
            elif not target.startswith(('https://','http://','#')):
                require((path.parent/target.split('#')[0]).resolve().exists(), f'broken local link: {path}: {target}')
            link_count+=1

    manifest_path=ROOT/'provenance/deliverable_manifest.json'
    manifest=read_json(manifest_path)
    expected={entry['path'] for entry in manifest['files']}
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p!=manifest_path and '__pycache__' not in p.parts}
    require(actual==expected, 'deliverable manifest file set')
    for entry in manifest['files']:
        data=(ROOT/entry['path']).read_bytes()
        require(hashlib.sha256(data).hexdigest()==entry['sha256'], f'hash mismatch: {entry["path"]}')
    print(json.dumps({'status':'passed','source_files':len(files),'source_commits':len(commits),'links_checked':link_count,'deliverable_files':len(manifest['files'])+1,'v3_knowledge_records':knowledge_count,'v3_model_calls':0,'limitations':'Structural and integrity checks only; no linguistic or quality validation.'},ensure_ascii=False))

if __name__=='__main__':
    main()
