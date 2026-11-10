"""Record relevant offline tests with exact test counts and logs."""
import contextlib,datetime,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tools')]
patterns=['test_branch_delivery.py','test_*separat*.py','test_qwen_multi.py','test_kiwi_default*.py','test_*integrat*.py']
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=HERE/'private/test_runs'/stamp;out.mkdir(parents=True,exist_ok=False)
results=[]
for pattern in patterns:
    log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern)
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        result=unittest.TextTestRunner(stream=log,verbosity=1).run(suite)
    name=pattern.replace('*','all');(out/(name+'.txt')).write_text(log.getvalue(),encoding='utf8')
    results.append({'pattern':pattern,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful()})
    print(json.dumps(results[-1]),flush=True)
summary={'directory':str(out.relative_to(ROOT)),'results':results,'tests':sum(r['tests'] for r in results),'passed':all(r['passed'] for r in results),'model_calls':0}
(HERE/'test_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
assert summary['passed'],str(out)
