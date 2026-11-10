"""Call-based progress separates instantaneous skipped records from actual calls."""
import time
import runner as r
s=r.WorkStore(r.ROOT)
while True:
 latest=r.read(r.HERE/'private/latest.json');rows=[]
 for rid in latest['run_ids']:
  for f in (r.ROOT/'experiments/runs'/rid/'private/records').glob('*/result.json'):
   try:rows.append(r.read(f))
   except ValueError:pass
 done=sum(x['worker_calls'] for x in rows);terminal=latest['state']=='completed'
 s.task({'id':'selection-probe-calls-20261102','title':'Qwen 실제 호출 진행','actor':'호출 기록 집계','stage':'실제 응답 대기','status':'completed' if terminal else 'running','done':done,'total':219,'unit':'호출','unit_key':'qwen_calls','message':f'Qwen 호출 {done}/219회 완료. 전체 처리 기록 {len(rows)}/300. 서버 응답 시간에 따라 남은 시간은 변합니다.'})
 if terminal:break
 time.sleep(12)
