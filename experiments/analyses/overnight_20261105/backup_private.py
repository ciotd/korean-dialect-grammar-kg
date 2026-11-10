"""Local-only immutable backup of this bounded experiment bundle."""
from pathlib import Path
import datetime
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def main():
    roots = [HERE / 'private']
    for pointer in sorted((HERE / 'private').glob('latest_*.json')):
        data = json.loads(pointer.read_text(encoding='utf8'))
        if 'directory' in data:
            path = Path(data['directory']).resolve()
            if not path.is_relative_to(ROOT / 'experiments' / 'runs'):
                raise ValueError('Unexpected run path')
            roots.append(path)
    roots.append(ROOT / 'experiments/runs/20261104T151934664312Z_past_copula_paired_development')
    files = sorted({p for root in roots for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    if any(p.suffix.lower() in {'.pdf', '.pem', '.key'} or p.name in {'test.py', 'credentials.json', '.env'} for p in files):
        raise ValueError('Excluded source or credential file in backup roots')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'local/overnight_backups' / stamp
    out.mkdir(parents=True, exist_ok=False)
    archive = out / 'research_private.zip'
    manifest = []
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:
            raw = p.read_bytes()
            name = p.relative_to(ROOT).as_posix()
            manifest.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
            z.writestr(name, raw)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in manifest:
            assert hashlib.sha256(z.read(item['path'])).hexdigest() == item['sha256'], item['path']
    result = {'created_utc': stamp, 'archive': str(archive), 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'files': len(manifest), 'archive_bytes': archive.stat().st_size, 'readback_verified': True,
              'limitations': ['Same-PC local backup, not protection against disk failure.', 'External source PDFs, credentials and installed environment are excluded.'],
              'manifest': manifest}
    (out / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    summary = {k: v for k, v in result.items() if k != 'manifest'}
    (ROOT / 'local/overnight_backups/latest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__':
    main()
