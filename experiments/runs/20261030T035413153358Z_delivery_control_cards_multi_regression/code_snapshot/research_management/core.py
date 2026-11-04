"""Reproducible experiment inventory, comparisons and agent review bundles.

Only derived metadata is stored in SQLite. Credentials and request headers are
never indexed. Raw traces stay in the original run directory.
"""
import collections
import contextlib
import datetime as dt
import hashlib
import json
import re
import sqlite3
import unicodedata
import uuid
from pathlib import Path

FROZEN = 'data/derived_private/standard_inputs_50_20261023_v1/inputs.jsonl'
FROZEN_SHA = '182dad5a3294534775bce4f4c7bd6b0a2fa22286cff3189f786f08eadcda5dff'
METRIC_CONTRACT = 'execution_counts_v1'
STAGES = {
    'input': 'input.json', 'analysis': 'analysis_call/parsed.json',
    'morphology': 'morphology.json', 'agent': 'agent_call/parsed.json',
    'agent_followup': 'agent_followup_call/parsed.json',
    'plan': 'transformation_plan.json', 'final_plan': 'final_plan.json',
    'additional_retrieval': 'additional_retrieval.json',
    'analysis_checks': 'analysis_checks.json', 'mapping': 'mapping.json',
    'retrieval': 'retrieval_raw.json', 'selection': 'reference_packet.json',
    'selection_audit': 'selection_audit.json', 'generation': 'generation_call/parsed.json',
    'generation_checks': 'generation_checks.json', 'result': 'result.json',
}

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else default

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)

def safe_child(root, name):
    root = root.resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root):
        raise ValueError('path_outside_allowed_root')
    return target

def error_category(row):
    if not row.get('status', '').endswith('_failed'):
        return None
    msg = row.get('error', '')
    # Validator categories are stable; actual surface/UID stays in the record.
    match = re.match(r'([A-Za-z][A-Za-z0-9_]+)(?=[: \[]|$)', msg)
    return match.group(1) if match else row.get('error_type', 'unclassified_failure')

def normalized_text(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())

def guard_dataset(project, inputs, role):
    """Reject exact/whitespace-normalized reuse for development, not a leakage oracle."""
    if role not in ('development', 'evaluation', 'regression'):
        raise ValueError('invalid_dataset_role')
    frozen = project / FROZEN
    if not frozen.is_file() or digest(frozen.read_bytes()) != FROZEN_SHA:
        raise ValueError('frozen_evaluation_reference_missing_or_changed')
    approved = {normalized_text(json.loads(line)['text']) for line in frozen.read_text(encoding='utf-8').splitlines() if line.strip()}
    rows = [json.loads(line) for line in inputs.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    overlap = [r['id'] for r in rows if normalized_text(r['text']) in approved]
    if role == 'development' and overlap:
        raise ValueError('development_overlaps_frozen_evaluation:' + ','.join(overlap))
    return {'role': role, 'input_sha256': digest(inputs.read_bytes()), 'records': len(rows),
            'frozen_overlap_ids': overlap, 'check': 'NFC_and_whitespace_normalized_exact_match',
            'limitation': 'Paraphrase/semantic overlap needs human review; prior exposure is not erased.'}


class Registry:
    def __init__(self, project):
        self.project = Path(project).resolve()
        self.root = self.project / 'experiments/management/private'
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'index.sqlite3'
        with self.connect() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                metadata TEXT NOT NULL, indexed_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records(run_id TEXT NOT NULL, input_id TEXT NOT NULL,
                position INTEGER NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(run_id,input_id), FOREIGN KEY(run_id) REFERENCES runs(run_id));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, time TEXT NOT NULL,
                run_id TEXT, event TEXT NOT NULL, detail TEXT NOT NULL);
            ''')

    @contextlib.contextmanager
    def connect(self):
        con = sqlite3.connect(self.db, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:
                yield con
        finally:
            con.close()

    def folder(self, run_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
            raise ValueError('invalid_run_id')
        return safe_child(self.project / 'experiments/runs', run_id)

    def sync(self):
        outcomes = []
        parent = self.project / 'experiments/runs'
        for folder in sorted(parent.iterdir()) if parent.exists() else []:
            if not folder.is_dir():
                continue
            try:
                outcomes.append(self.register(folder.name))
            except Exception as exc:
                # One corrupt run must not conceal other runs; do not expose file contents.
                with self.connect() as con:
                    con.execute('INSERT INTO events(time,run_id,event,detail) VALUES(?,?,?,?)',
                                (now(), folder.name, 'index_error', type(exc).__name__))
                outcomes.append({'run_id': folder.name, 'index_error': type(exc).__name__})
        present = {p.name for p in parent.iterdir() if p.is_dir()} if parent.exists() else set()
        missing = [r['run_id'] for r in self.runs() if r['run_id'] not in present]
        for run in self.runs():
            if run['state']=='completed' and run['run_id'] not in missing:
                self.write_summary(run['run_id'])
        self.status_document(missing)
        return {'indexed': outcomes, 'missing_run_directories': missing, 'total_runs': len(self.runs())}

    def register(self, run_id):
        folder = self.folder(run_id)
        if not folder.is_dir():
            raise ValueError('run_not_found')
        config = read(folder / 'config.json', {})
        metrics = read(folder / 'metrics.json', {})
        results = read(folder / 'private/results.json')
        if results is None:
            results = [read(p) for p in sorted((folder / 'private/records').glob('*/result.json'))]
        if len({r['id'] for r in results}) != len(results):
            raise ValueError('duplicate_result_ids')
        status = ('preflight_failed' if (folder / 'preflight_failure.json').exists() else
                  'completed' if metrics and (folder / 'artifact_hashes.json').exists() else 'incomplete')
        hashes = read(folder / 'code_hashes.json', {})
        artifacts = read(folder / 'artifact_hashes.json', {})
        tracked_names = ['config.json', 'metrics.json', 'private/results.json', 'code_hashes.json',
                         'kg_hashes.json', 'analysis.schema.json', 'generation.schema.json',
                         'analysis_prompt.txt', 'generation_prompt.txt', 'private/inputs.jsonl',
                         'freeze.json', 'postflight.json', 'server_models.json', 'artifact_hashes.json',
                         'preflight_failure.json', 'version_manifest.json','validation_contract.json']
        actual = {name: digest((folder / name).read_bytes()) for name in tracked_names if (folder / name).is_file()}
        fingerprint = digest(encoded({'files': actual, 'results': results}).encode())
        mismatch = [name for name, sha in actual.items() if name in artifacts and artifacts[name] != sha]
        if actual.get('private/inputs.jsonl') != config.get('input_sha256'):
            mismatch.append('config.input_sha256')
        if metrics and metrics.get('records') != len(results):
            mismatch.append('metrics.records')
        if status == 'completed' and config.get('input_count') != len(results):
            mismatch.append('config.input_count')
        postflight=read(folder/'postflight.json',{})
        if any(value is False for value in postflight.values()):
            mismatch.append('postflight')
        if metrics:
            valid=sum(r['status'] in ('unchanged','generated_requires_human_review','partial','needs_review') for r in results)
            changed=sum(r['status'] in ('generated_requires_human_review','partial') for r in results)
            if metrics.get('valid_output_records')!=valid:mismatch.append('metrics.valid_output_records')
            if metrics.get('changed_records')!=changed:mismatch.append('metrics.changed_records')
        validations = {name: hashes.get(name) for name in ('validation.py', 'contracts.py')}
        validation_contract = digest(encoded({'code': validations, 'schemas': {n: actual.get(n) for n in ('analysis.schema.json','generation.schema.json')}}).encode()) if all(validations.values()) else None
        if (folder/'validation_contract.json').is_file():
            validation_contract=actual['validation_contract.json']
        evidence = {'code': digest(encoded(hashes).encode()) if hashes else None,
                    'kg': digest(encoded(read(folder/'kg_hashes.json', {})).encode()) if (folder/'kg_hashes.json').exists() else None,
                    'prompts': {n: actual.get(n) for n in ('analysis_prompt.txt','generation_prompt.txt')},
                    'validation_contract': validation_contract,
                    'input': actual.get('private/inputs.jsonl'),
                    'manifest': actual.get('artifact_hashes.json')}
        categories = dict(collections.Counter(filter(None, map(error_category, results))))
        data = {'run_id': run_id, 'state': status, 'config': config, 'metrics': metrics,
                'versions': evidence, 'version_manifest': read(folder/'version_manifest.json', {}),
                'dataset_role': config.get('dataset_role', 'evaluation_reference' if config.get('phase')=='first50' else 'development' if config.get('phase')=='smoke' else 'unknown'),
                'metric_contract': config.get('metric_contract', METRIC_CONTRACT),
                'error_categories': categories, 'result_count': len(results),
                'integrity': {'status': 'mismatch' if mismatch else 'light_check_passed' if artifacts else 'unverified',
                              'mismatches': mismatch, 'scope': 'indexed files only; use verify for all artifacts'},
                'quality_evaluation': 'not_available', 'indexed_at': now()}
        with self.connect() as con:
            old = con.execute('SELECT fingerprint,metadata FROM runs WHERE run_id=?', (run_id,)).fetchone()
            if old and old['fingerprint'] == fingerprint:
                return {'run_id': run_id, 'action': 'unchanged'}
            if old and json.loads(old['metadata'])['state']=='completed':
                data['integrity']['original_completed_run_changed'] = True
                con.execute('INSERT INTO events(time,run_id,event,detail) VALUES(?,?,?,?)',
                            (now(),run_id,'completed_source_changed',encoded({'old':old['fingerprint'],'new':fingerprint})))
            con.execute('INSERT INTO runs VALUES(?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET fingerprint=excluded.fingerprint,metadata=excluded.metadata,indexed_at=excluded.indexed_at',
                        (run_id,fingerprint,encoded(data),now()))
            con.execute('DELETE FROM records WHERE run_id=?', (run_id,))
            con.executemany('INSERT INTO records VALUES(?,?,?,?)', [(run_id,r['id'],i,encoded({**r,'error_category':error_category(r)})) for i,r in enumerate(results)])
            con.execute('INSERT INTO events(time,run_id,event,detail) VALUES(?,?,?,?)',
                        (now(),run_id,'indexed',fingerprint))
        return {'run_id': run_id, 'action': 'updated' if old else 'added', 'state': status}

    def runs(self):
        with self.connect() as con:
            return [json.loads(r[0]) for r in con.execute('SELECT metadata FROM runs ORDER BY run_id DESC')]

    def get(self, run_id):
        self.folder(run_id)
        with self.connect() as con:
            row = con.execute('SELECT metadata FROM runs WHERE run_id=?', (run_id,)).fetchone()
        if not row:
            raise KeyError('run_not_indexed')
        return json.loads(row[0])

    def records(self, run_id):
        self.get(run_id)
        with self.connect() as con:
            return [json.loads(row[0]) for row in con.execute('SELECT payload FROM records WHERE run_id=? ORDER BY position', (run_id,))]

    def trace_path(self, run_id, input_id, stage):
        if stage not in STAGES or not re.fullmatch(r'[A-Za-z0-9_-]+', input_id):
            raise ValueError('invalid_trace_request')
        if input_id not in {r['id'] for r in self.records(run_id)}:
            raise KeyError('input_not_indexed')
        return safe_child(self.folder(run_id), 'private/records/' + input_id + '/' + STAGES[stage])

    def trace(self, run_id, input_id, stage):
        path = self.trace_path(run_id,input_id,stage)
        if not path.is_file():
            return {'available': False, 'reason': 'stage_not_reached_or_artifact_missing'}
        # Very large JSON is fetched only on an explicit click; list views stay small.
        return {'available': True, 'stage': stage, 'bytes': path.stat().st_size,
                'sha256': digest(path.read_bytes()), 'data': read(path)}

    def verify(self, run_id):
        folder = self.folder(run_id)
        expected = read(folder/'artifact_hashes.json', {})
        issues=[]
        for name, sha in expected.items():
            path=safe_child(folder,name)
            if not path.is_file() or digest(path.read_bytes()) != sha:
                issues.append(name)
        result={'run_id':run_id,'verified_at':now(),'checked_files':len(expected),'issues':issues,
                'status':'passed' if expected and not issues else 'failed' if issues else 'no_manifest',
                'limitation':'Consistency against saved manifest, not an external authenticity signature.'}
        write(self.root/'verification'/f'{run_id}.json',result)
        return result

    def compare(self, left_id, right_id):
        a,b=self.get(left_id),self.get(right_id)
        reasons=[]
        for name,item in [('left',a),('right',b)]:
            if not self.folder(item['run_id']).is_dir():reasons.append(name+':source_directory_missing')
            if item['state']!='completed': reasons.append(name+':run_not_completed')
            if item['integrity']['status']!='light_check_passed' or item['integrity'].get('original_completed_run_changed'):
                reasons.append(name+':integrity_not_established')
        if not a['versions']['input'] or a['versions']['input']!=b['versions']['input']:
            reasons.append('different_or_missing_dataset_hash')
        ar={r['id']:r for r in self.records(left_id)};br={r['id']:r for r in self.records(right_id)}
        if set(ar)!=set(br): reasons.append('different_record_ids')
        if a['dataset_role']!=b['dataset_role']:reasons.append('different_dataset_roles')
        if a['metric_contract']!=b['metric_contract']:reasons.append('different_metric_definitions')
        base=not reasons
        validation_equal=bool(a['versions']['validation_contract']) and a['versions']['validation_contract']==b['versions']['validation_contract']
        protocol_keys=('scope','region_filter','analysis_max_tokens','generation_max_tokens','automatic_retries','temperature','top_p','seed','enable_thinking')
        differences={k:{'left':a['config'].get(k),'right':b['config'].get(k)} for k in sorted(set(a['config'])|set(b['config'])) if a['config'].get(k)!=b['config'].get(k)}
        changed_versions=[k for k in ('code','kg','prompts','validation_contract') if a['versions'][k]!=b['versions'][k]]
        rows=[]
        for key in ('valid_output_records','changed_records','records_with_realization_reference','api_attempts','wall_seconds','mean_record_seconds','median_record_seconds','kg_query_count'):
            av,bv=a['metrics'].get(key),b['metrics'].get(key)
            allowed=base and (validation_equal or key in ('api_attempts','wall_seconds','mean_record_seconds','median_record_seconds','kg_query_count'))
            rows.append({'metric':key,'left':av,'right':bv,'delta':bv-av if allowed and av is not None and bv is not None else None,
                         'comparison':'descriptive_only' if allowed else 'not_comparable'})
        av=a['metrics'].get('reported_usage',{}).get('total_tokens');bv=b['metrics'].get('reported_usage',{}).get('total_tokens')
        usage_complete=all(x['metrics'].get('calls_without_usage')==0 and x['metrics'].get('calls_with_usage')==x['metrics'].get('api_attempts') for x in (a,b))
        rows.append({'metric':'total_tokens','left':av,'right':bv,'delta':bv-av if base and usage_complete and av is not None and bv is not None else None,'comparison':'descriptive_only' if base and usage_complete else 'not_comparable'})
        pairs=[{'id':key,'input':ar[key].get('input_text'),'left_status':ar[key]['status'],'right_status':br[key]['status'],
                'left_output':ar[key].get('output_text'),'right_output':br[key].get('output_text')} for key in ar.keys() & br.keys()] if base else []
        return {'left':left_id,'right':right_id,'same_evaluation_inputs':base,'blocking_reasons':reasons,
                'validation_contract_equal':validation_equal,'config_differences':differences,'changed_versions':changed_versions,
                'protocol_differences':[k for k in protocol_keys if k in differences], 'metrics':rows,'pairs':sorted(pairs,key=lambda x:x['id']),
                'quality_comparison':{'allowed':False,'reason':'No registered independent human evaluation with matching protocol.'},
                'causal_claim_allowed':False,
                'warnings':['Execution counts are not linguistic accuracy.','Validation changes prevent direct pass-rate comparison.' if not validation_equal else 'Same validator does not certify semantic correctness.',
                            'Latency is descriptive: server hardware/load/checkpoint revision are not controlled.','Multiple changes cannot isolate the KG contribution.']}

    def write_summary(self,run_id):
        run=self.get(run_id)
        previous=next((r for r in self.runs() if r['run_id']<run_id and r['state']=='completed'
                       and r['versions']['input']==run['versions']['input'] and r['dataset_role']==run['dataset_role']),None)
        report={'run_id':run_id,'source_manifest_sha256':run['versions']['manifest'],
                'metrics':run['metrics'],'error_categories':run['error_categories'],
                'comparison':self.compare(previous['run_id'],run_id) if previous else None,
                'comparison_note':'Latest earlier run with identical input hash and role; all other compatibility checks remain active.' if previous else 'No earlier run with identical inputs and role. No baseline delta calculated.',
                'interpretation_status':'Deterministic summary; AI/human interpretation is separate.',
                'next_review':['Inspect analysis failures in original stage artifacts.','Review evidence appropriateness and changed outputs with a dialect speaker.','Use separate development inputs for fixes.']}
        write(self.root/'summaries'/f'{run_id}.json',report)
        return report

    def review_bundle(self, run_id, previous=None):
        run=self.get(run_id)
        bundle={'generated_at':now(),'run':run,'source_run_path':str(self.folder(run_id)),
                'comparison':self.compare(previous,run_id) if previous else None,
                'cases':[r for r in self.records(run_id) if r['status']!='unchanged'],
                'agent_instructions':['Explain big picture, logical design, technical evidence in Korean.',
                    'Separate observed counts, hypotheses, and missing human validation.',
                    'Do not edit run artifacts or manufacture scores. Link every case to run_id/input_id/stage.',
                    'The original50 are regression inputs after the 2026-10-24 user directive. Preserve historical roles; use separate unseen data for final quality evaluation.',
                    'Do not invoke models or apply changes without an authorized experiment scope.'],
                'output_contract':{'observations':[],'hypotheses':[],'recommended_next_experiments':[],'limitations':[],'reviewer':'identify AI or human explicitly'}}
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path=self.root/'reviews'/f'{stamp}_{run_id}.json';write(path,bundle)
        return path

    def status_document(self, missing=()):
        runs=self.runs()
        doc=['# 연구 실행 현황','', '자동 생성: `python tools/research_manager.py sync`. 수치는 실행 상태이며 방언 품질 점수가 아니다.', '',
             '| Run ID | 용도 | 상태 | 입력 | 출력 형식 통과 | 분석 실패 |', '|---|---|---|---:|---:|---:|']
        for r in runs:
            m=r['metrics'];doc.append(f"| {r['run_id']} | {r['dataset_role']} | {r['state']} | {r['config'].get('input_count','미확인')} | {m.get('valid_output_records','—')} | {m.get('status_counts',{}).get('analysis_failed',0)} |")
        doc+=['','확정 50건 원문은 보존한다. 2026-10-24 이후 실행은 사용자 요청에 따라 회귀 실험으로 사용하며 독립 최종 평가셋이 아니다.',
              '정답 및 사람 평가 없음: 자연스러움·정확도는 미측정. KG 없는 통제 실험도 아직 없다.',
              '대시보드: `python tools/research_manager.py serve` → http://127.0.0.1:8766/',
              '상세 절차: [연구 관리 절차](../workflows/RESEARCH_MANAGEMENT.md).']
        if missing:doc+=['','원본 폴더 누락(색인 유지): '+', '.join(missing)]
        target=self.project/'docs/research/RESEARCH_STATUS.md';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('\n'.join(doc)+'\n',encoding='utf-8')
