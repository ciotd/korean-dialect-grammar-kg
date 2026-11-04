"""Verify the completed run and derived report without model calls."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def main():
    run = Path(read(HERE/'private/latest_run.json')['directory'])
    audit = read(HERE/'private/audit.json')
    results = read(run/'private/results.json')
    manifest = read(run/'artifact_hashes.json')
    changed = [name for name, digest in manifest.items()
               if hashlib.sha256((run/name).read_bytes()).hexdigest() != digest]
    assert not changed, changed
    original = read(run/'kg_hashes.json')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in original.items())
    assert len(results) == 32 and len({r['source_case'] for r in results}) == 16
    assert sum(bool(r['output_text']) for r in results) == 13
    assert not any(r['output_text'] for r in results if r['condition'] == 'model')
    assert len(list((run/'private').rglob('request.json'))) == audit['summary']['all_api_attempts'] == 30
    report = (HERE/'private/report.html').read_text(encoding='utf-8')
    assert all(f'<b>Q{i:02d}</b>' in report for i in range(1,17))
    assert '실시간 Neo4j 조회는 아닙니다' in report
    assert audit['summary']['manual_exact_reference_agreement'] == 10
    # This checks the actual saved generation request, not only adapter output.
    requests = list((run/'private').glob('records/*/generation_call/request.json'))
    assert len(requests) == 13
    for path in requests:
        request = read(path)
        user = next(m['content'] for m in request['messages'] if m['role'] == 'user')
        payload = json.loads(user)
        assert 'actions' in payload
        assert not ({'reference', 'references', 'gold', 'expected', 'candidates', 'alternatives'} & payload.keys())
    result = {'status':'passed', 'frozen_artifacts_checked':len(manifest),
              'source_hashes_preserved':True, 'records':32, 'source_cases':16,
              'generation_requests':13, 'all_requests':30,
              'report_rows':16, 'actual_output_count':13,
              'scope':'artifact integrity, accounting and saved request contract; not linguistic accuracy',
              'browser_render_checked':False}
    (HERE/'private/artifact_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
