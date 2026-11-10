"""Rebuild atlas, run bounded structural tests, save machine results, render report."""
import datetime,io,json,sys,unittest
from pathlib import Path
import build_atlas as b
import report

def main():
 a=b.build()
 suite=unittest.defaultTestLoader.discover(str(b.HERE),pattern='test_*.py')
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 (b.HERE/'private/test_output.txt').write_text(stream.getvalue(),encoding='utf8')
 validation={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,
   'status':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
   'failures':len(result.failures),'errors':len(result.errors),
   'scope':'structure, provenance, work routing regression, no generation or linguistic accuracy test',
   'stats':a['stats'],'inputs_preserved':all(a['preservation'].values()),'review_rounds':[]}
 for phase in ('independent','cross'):
  for who in ('codex','claude'):
   p=b.HERE/'private/dispatch'/phase/who
   start=b.read(p/'start.json');messages=b.read(p/'messages.json')
   relevant=[m for m in messages if m['role']=='assistant']
   validation['review_rounds'].append({'phase':phase,'who':who,
    'completed':any(start['marker'] in m['text'] for m in relevant),
    'models':sorted({str(m['model']) for m in relevant if m.get('model')}),
    'prompt_sha256':b.sha(p/'prompt.txt'),'response_sha256':b.sha(p/'response.md')})
 b.dump(b.HERE/'private/validation.json',validation)
 if not result.wasSuccessful():print(stream.getvalue());raise SystemExit(1)
 report.main()
 manifest=b.read(b.HERE/'private/build_manifest.json')
 manifest['implementation_hashes']={p.name:b.sha(p) for p in b.HERE.glob('*') if p.suffix in ('.py','.json','.cjs','.md')}
 manifest['outputs']={p.name:b.sha(p) for p in (b.HERE/'private').glob('*') if p.is_file() and p.name!='build_manifest.json'}
 b.dump(b.HERE/'private/build_manifest.json',manifest)
 print(json.dumps({'tests':result.testsRun,'passed':result.wasSuccessful(),'review_rounds_completed':sum(r['completed'] for r in validation['review_rounds']),'stats':a['stats']},ensure_ascii=False))

if __name__=='__main__':main()
