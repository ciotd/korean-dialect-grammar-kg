"""Local work events and version-bound human decisions; never executes research."""
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


def encoded(value):
    return json.dumps(value, ensure_ascii=False)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', value):
        raise ValueError('invalid_id')
    return value


class WorkStore:
    def __init__(self, project):
        self.project = Path(project)
        self.path = self.project / 'experiments/management/private/workflow.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY, at REAL NOT NULL, kind TEXT NOT NULL,
              item TEXT NOT NULL, version INTEGER, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS proposals (
              id TEXT PRIMARY KEY, version INTEGER NOT NULL, revision INTEGER NOT NULL,
              state TEXT NOT NULL, body TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def event(self, db, kind, item, body, version=None, at=None):
        db.execute('INSERT INTO events(at,kind,item,version,body) VALUES(?,?,?,?,?)',
                   (time.time() if at is None else at, kind, item, version, encoded(body)))

    def task(self, data):
        key = identifier(data['id'])
        if data.get('status') not in ('running', 'waiting', 'completed', 'failed'):
            raise ValueError('invalid_task_status')
        for k in ('title', 'actor', 'stage'):
            if not isinstance(data.get(k), str) or not data[k].strip():
                raise ValueError('missing_' + k)
        done, total = data.get('done'), data.get('total')
        if done is not None and (type(done) is not int or done < 0):
            raise ValueError('invalid_done')
        if total is not None and (type(total) is not int or total < 1 or done is None or done > total):
            raise ValueError('invalid_total')
        if data['status'] == 'completed' and total is not None and done != total:
            raise ValueError('incomplete_count')
        now = time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM tasks WHERE id=?', (key,)).fetchone()
            old = json.loads(row['body']) if row else {}
            if old.get('status') in ('completed', 'failed'):
                raise ValueError('terminal_task_use_new_id')
            if old.get('stage') == data['stage'] and old.get('done') is not None and done is not None and done < old['done']:
                raise ValueError('count_cannot_decrease_in_same_stage')
            value = {k: data[k] for k in ('id','title','actor','stage','status','done','total','unit','message','unit_key') if k in data}
            value.update(started_at=old.get('started_at', now), updated_at=now)
            if value['status'] in ('completed','failed'):
                value['finished_at'] = now
            db.execute('INSERT OR REPLACE INTO tasks VALUES(?,?)', (key, encoded(value)))
            self.event(db, 'task', key, value, at=now)
        return value

    def proposal(self, data):
        key = identifier(data['id'])
        version = data.get('version')
        if type(version) is not int or version < 1:
            raise ValueError('invalid_version')
        for k in ('title', 'before', 'after', 'reason', 'scope', 'verification'):
            if not isinstance(data.get(k), str) or not data[k].strip():
                raise ValueError('missing_' + k)
        value = {k: data[k] for k in ('id','version','title','before','after','reason','scope','verification','evidence','reviewers','lead','human_question') if k in data}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT version FROM proposals WHERE id=?', (key,)).fetchone()
            if version != (old['version'] + 1 if old else 1):
                raise ValueError('proposal_version_must_increment')
            db.execute('INSERT OR REPLACE INTO proposals VALUES(?,?,0,?,?)', (key,version,'pending',encoded(value)))
            self.event(db, 'proposal', key, value, version)
        return value

    def decide(self, payload, channel='dashboard'):
        items = payload.get('items')
        if not isinstance(items,list) or not 1 <= len(items) <= 100:
            raise ValueError('invalid_items')
        if channel not in ('dashboard','chat'):
            raise ValueError('invalid_channel')
        if channel == 'chat' and (not payload.get('reference') or not payload.get('quote')):
            raise ValueError('chat_reference_and_quote_required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            seen = set()
            for item in items:
                if not isinstance(item,dict): raise ValueError('decision_object_required')
                key = identifier(item['id'])
                if key in seen: raise ValueError('duplicate_item')
                seen.add(key)
                if item.get('action') not in ('approved','changes_requested','deferred'):
                    raise ValueError('invalid_action')
                if not isinstance(item.get('comment',''),str) or len(item.get('comment','')) > 10000:
                    raise ValueError('invalid_comment')
                if item['action']=='changes_requested' and not item.get('comment','').strip():
                    raise ValueError('change_request_needs_comment')
                row = db.execute('SELECT * FROM proposals WHERE id=?',(key,)).fetchone()
                if not row or (row['version'],row['revision']) != (item.get('version'),item.get('revision')):
                    raise ValueError('stale_proposal_reload')
                if row['state']=='applied': raise ValueError('already_applied_create_new_version')
            for item in items:
                db.execute('UPDATE proposals SET state=?,revision=revision+1 WHERE id=?', (item['action'],item['id']))
                self.event(db,'decision',item['id'],{**item,'channel':channel,'actor':'user' if channel=='dashboard' else 'lead_transcription_of_user','reference':payload.get('reference'), 'quote':payload.get('quote')},item['version'])
        return {'saved':len(items),'applies_changes':False}

    def applied(self, data):
        key = identifier(data['id'])
        if not isinstance(data.get('artifacts'),list) or not data['artifacts'] or not data.get('verification'):
            raise ValueError('application_requires_artifacts_and_validation')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM proposals WHERE id=?',(key,)).fetchone()
            if not row or row['state'] != 'approved' or row['version'] != data.get('version') or row['revision'] != data.get('revision'):
                raise ValueError('current_version_approval_required')
            db.execute("UPDATE proposals SET state='applied',revision=revision+1 WHERE id=?",(key,))
            self.event(db,'applied',key,data,row['version'])
        return {'recorded':True,'executed':False}

    def state(self):
        now = time.time()
        with self.connect() as db:
            tasks = [json.loads(r['body']) for r in db.execute('SELECT body FROM tasks')]
            proposals = [{**json.loads(r['body']),'state':r['state'],'revision':r['revision']} for r in db.execute('SELECT * FROM proposals ORDER BY id')]
            for task in tasks:
                task['elapsed_seconds'] = max(0,task.get('finished_at',now)-task['started_at'])
                task['stale'] = task['status']=='running' and now-task['updated_at']>90
                task['eta'] = None
                task['eta_note'] = '이 작업의 반복 단위 측정이 3개 이상 쌓이면 추정합니다.'
                if task['status'] != 'running' or task['stale']:
                    task['eta_note'] = '완료·대기·실패 또는 갱신 지연 상태에서는 남은 시간을 추정하지 않습니다.'
                    continue
                events = [json.loads(r['body']) for r in db.execute("SELECT body FROM events WHERE kind='task' AND item=? ORDER BY seq",(task['id'],))]
                rates=[]; previous=None
                for event in events:
                    comparable = event.get('stage')==task['stage'] and event.get('unit_key')==task.get('unit_key') and event.get('unit_key') and event['status']=='running'
                    if not comparable: previous=None;rates=[];continue
                    if previous and event.get('done') is not None and previous.get('done') is not None and event['done']>previous['done']:
                        rates.append((event['updated_at']-previous['updated_at'])/(event['done']-previous['done']))
                        previous=event
                    elif previous is None: previous=event
                if len(rates)>=3 and task.get('total') is not None:
                    samples=rates[-20:];remaining=task['total']-task['done']
                    # Empirical range, not a statistical confidence interval.
                    task['eta']={'low_seconds':round(min(samples)*remaining),'high_seconds':round(max(samples)*remaining),'sample_intervals':len(samples)}
                    task['eta_note']='현재 단계의 동일 작업 단위에서 측정한 처리 간격 범위. 모델 내부 진행률이나 보장 시간이 아닙니다.'
            events=[{**dict(r),'body':json.loads(r['body'])} for r in db.execute("SELECT * FROM events WHERE kind!='task' ORDER BY seq DESC LIMIT 300")]
        return {'server_time':now,'tasks':tasks,'proposals':proposals,'events':events,'poll_seconds':2}

    def review(self):
        root=self.project/'experiments/analyses/full_review_20261029/private'
        def read(name,default):
            path=root/name
            return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default
        cases=read('casebook.json',{}).get('cases',[])
        compact=[]
        for case in cases:
            compact.append({k:case.get(k) for k in ('id','input','lead_observations','reviewers','user_preference')})
        return {'coverage':read('progress.json',{}),'cases':compact,'source':'experiments/analyses/full_review_20261029/private/casebook.json'}
