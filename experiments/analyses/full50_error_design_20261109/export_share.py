"""Export only the authorized human-readable report; never export raw run data."""
from pathlib import Path
import csv, hashlib, json, re

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'experiments/analyses/kiwi_focused_full50_20261109/private'
DST = ROOT / 'local/sites/kg-full50-report-20261109/dist'
DST.mkdir(parents=True, exist_ok=True)
report = (SRC / 'report.html').read_text(encoding='utf-8')
removed = len(re.findall(r'<a href="file:[^"]+">', report))
report = re.sub(r'<a href="file:[^"]+">(.*?)</a>', r'<span title="원시 기록은 연구자 로컬에 보관">\1 (로컬 보관)</span>', report)
report = report.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="robots" content="noindex,nofollow">')
banner = '<section><strong>공유용 읽기 전용 보고서</strong><p>2026년 11월 9일 실행 결과의 사본입니다. 링크를 아는 누구나 읽을 수 있습니다. 원문·참조문·출력·단계별 설명은 유지했습니다. 인증정보와 원시 실행 파일은 게시하지 않습니다. 원시 기록 링크는 로컬 보관 표시로 바꿨습니다. 이 자료는 회귀 검사이며 독립적인 자연스러움 평가가 아닙니다.</p></section>'
report = report.replace('<main>', '<main>'+banner, 1)
assert 'file:///' not in report
assert len(re.findall(r'id="case-[^"]+"', report)) == 50
(DST / 'index.html').write_text(report, encoding='utf-8')
for name in ['pipeline.html','outputs.csv']:
    (DST/name).write_bytes((SRC/name).read_bytes())
(DST/'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
with (DST/'outputs.csv').open(encoding='utf-8-sig', newline='') as f:
    assert len(list(csv.DictReader(f))) == 50
for p in DST.iterdir():
    s=p.read_text(encoding='utf-8-sig')
    assert not re.search(r'file:///|127\.0\.0\.1|210\.91\.154\.131|[GC]:[/\\]',s), p.name
manifest={'exported_files':[{ 'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(DST.iterdir())], 'local_links_replaced':removed,'case_count':50,'audience':'anyone_with_link','source_report_unchanged':True}
(Path(__file__).parent/'private/share_export.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
