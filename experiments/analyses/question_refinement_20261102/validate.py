"""Reproducible structural checks and developer cases, with explicit denominators."""
import collections,io,platform,unittest
from sources import HERE,ROOT,read,dump,sha
from query import Reader
from development import export
from test_query import QueryTests
def run():
 log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(QueryTests))
 (HERE/'private/tests.txt').write_text(log.getvalue(),encoding='utf8');print(log.getvalue())
 rows,old=export(Reader(read(HERE/'private/graph.json')));graph=read(HERE/'private/graph.json')
 frozen=read(HERE/'private/input_hashes.json');preserved={k:sha(ROOT/k)==v for k,v in frozen.items()}
 data={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'previous_cases':{'total':len(old),'matched':sum(x['pass'] for x in old)},
  'development_cases':len(rows),'readiness_counts':dict(collections.Counter(c['readiness'] for r in rows for c in r['packet']['clauses'])),
  'nodes':len(graph['nodes']),'edges':len(graph['edges']),'node_types':dict(collections.Counter(n['type'] for n in graph['nodes'])),
  'frozen_files_unchanged':preserved,'qwen_calls':0,'python':platform.python_version(),
  'interpretation':'Tests validate structural contracts and manually supplied analyses, not linguistic generalization or translation quality.'}
 dump(HERE/'private/validation.json',data)
 if not result.wasSuccessful() or not all(preserved.values()) or not all(x['pass'] for x in old):raise SystemExit(1)
 return data
if __name__=='__main__':run()
