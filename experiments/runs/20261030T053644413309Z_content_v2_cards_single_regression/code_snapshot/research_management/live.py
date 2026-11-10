"""Measured progress adapter; records completion, never changes model inputs."""
import sys
import threading
from .work import WorkStore


class BatchProgress:
    def __init__(self, project, batch, total):
        try:self.store=WorkStore(project)
        except Exception as exc:
            self.store=None
            print('Progress initialization failed: '+type(exc).__name__,file=sys.stderr,flush=True)
        self.batch=batch;self.total=total
        self.lock=threading.RLock();self.stop=threading.Event();self.tasks={}
        for stage,label in [('analysis','공통 문장 분석·KG 조회'),('single','Single 생성'),('multi','Multi 생성'),('finalize','실험 결과·재현 정보 저장')]:
            self.tasks[stage]=dict(id=f'{batch}-{stage}',title=label,actor='Qwen 실행기',stage=stage,
                status='waiting',done=0,total=1 if stage=='finalize' else total,unit='저장 작업' if stage=='finalize' else '입력 처리 (실패 포함)',
                unit_key=f'{batch}-{stage}',message='실행 대기. 처리 건수는 방언 품질 점수가 아닙니다.')

    def publish(self, stage):
        if self.store is None:return
        try:self.store.task(self.tasks[stage])
        except Exception as exc:
            # A management outage must not discard an expensive model result.
            print('Progress recording failed: '+type(exc).__name__,file=sys.stderr,flush=True)

    def __enter__(self):
        for stage in self.tasks:self.publish(stage)
        self.thread=threading.Thread(target=self.heartbeat,daemon=True);self.thread.start()
        return self

    def heartbeat(self):
        while not self.stop.wait(20):
            with self.lock:
                for stage,t in self.tasks.items():
                    if t['status']=='running':self.publish(stage)

    def start(self, stage):
        with self.lock:
            self.tasks[stage].update(status='running',message='실행 프로세스 동작 중. 내부 토큰 생성 진행률은 측정하지 않습니다.')
            self.publish(stage)

    def completed_item(self, stage, input_id, status):
        with self.lock:
            task=self.tasks[stage];task['done']+=1
            task.update(message=f'최근 처리: {input_id} · {status}')
            if task['done']==task['total']:task['status']='completed'
            self.publish(stage)

    def __exit__(self, exc_type, exc, tb):
        self.stop.set();self.thread.join(timeout=2)
        with self.lock:
            for stage,t in self.tasks.items():
                if t['status'] not in ('completed','failed'):
                    t.update(status='failed',message='작업이 완료되기 전에 실행이 종료되었습니다. 원본 로그를 확인하세요.')
                    self.publish(stage)
