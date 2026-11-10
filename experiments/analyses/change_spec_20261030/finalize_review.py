"""Build the local reading view and verify frozen evidence; no model calls."""
import hashlib
import html
import json
import re
from pathlib import Path

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[2]
PRIVATE=BASE/'private'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(data):return hashlib.sha256(data).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def inline(s):
    s=html.escape(s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
    return re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
def render(text):
    # Deliberately limited renderer for this authored document; all source text escaped.
    out=[];table=False;fence=False
    for line in text.splitlines():
        if line.startswith('```'):
            out.append('</pre>' if fence else '<pre>');fence=not fence;continue
        if fence:out.append(html.escape(line)+'\n');continue
        if line.startswith('|'):
            if re.fullmatch(r'[| :\-]+',line):continue
            if not table:out.append('<div class="scroll"><table>');table=True
            out.append('<tr>'+''.join('<td>'+inline(c.strip())+'</td>' for c in line.strip('|').split('|'))+'</tr>');continue
        if table:out.append('</table></div>');table=False
        if line.startswith('#'):
            level=min(len(line)-len(line.lstrip('#')),4);out.append(f'<h{level}>'+inline(line.lstrip('# '))+f'</h{level}>')
        elif line.strip():out.append('<p>'+inline(line)+'</p>')
    if table:out.append('</table></div>')
    return '\n'.join(out)

def main():
    packet=(PRIVATE/'review_packet.txt').read_text(encoding='utf-8-sig')
    parts=[read(PRIVATE/f'dispatch/codex/part_{i:02}.json')['text'].split('BEGIN_SEGMENT\n',1)[1].split('\nEND_SEGMENT',1)[0] for i in range(1,4)]
    checks={'codex_segments_equal_packet_text':''.join(parts)==packet,
            'packet_text_matches_original_manifest':digest(packet.encode('utf-8'))==read(PRIVATE/'packet_manifest.json')['sha256']}
    preservation={}
    for name in ['preservation_manifest','evidence_manifest']:
        manifest=read(PRIVATE/f'{name}.json')
        mismatches=[p for p,d in manifest.items() if not (PROJECT/p).exists() or digest((PROJECT/p).read_bytes())!=d]
        preservation[name]={'files_checked':len(manifest),'changed_or_missing':mismatches}
    integrity={'checks':checks,'packet_raw_file_sha256':digest((PRIVATE/'review_packet.txt').read_bytes()),
        'packet_lf_text_sha256':digest(packet.encode('utf-8')),'preservation':preservation,
        'note':'기존 패킷 manifest는 LF 텍스트 해시다. 디스크 파일은 CRLF로 저장되어 원시 바이트 해시와 다를 수 있다.'}
    save(PRIVATE/'final_integrity.json',integrity)
    assert all(checks.values()) and all(not x['changed_or_missing'] for x in preservation.values()),integrity
    tests=read(PRIVATE/'reproduction_results.json')
    reviews={name:read(PRIVATE/f'reviews/{name}.json') for name in ['codex','claude']}
    resolution=(BASE/'REVIEW_RESOLUTION.md').read_text(encoding='utf-8')
    content='<h1>적용 전 변경 명세 · 독립 검토 결과</h1><p class="notice">명세·재현 시험 완료 / 실제 KG·생성 코드 변경 전 / 새 Qwen 호출 0회</p>'
    content+=f'<div class="stats"><b>입력 50개 · 기존 결과 100개</b><b>선택 카드 46종</b><b>재현·무결성 시험 {tests["tests_run"]}개 통과</b><b>Codex 8건 · Claude 7건 검토</b></div>'
    content+='<p>시험 통과는 기존 오류를 재현하고 기록 연결을 확인했다는 뜻입니다. 방언 품질이 개선됐다는 뜻이 아닙니다.</p><nav><a href="#resolution">총괄의 검토 반영</a> · <a href="#codex">Codex 의견 원문</a> · <a href="#claude">Claude 의견 원문</a> · <a href="mapping.html">50개 입력의 실제 카드·지시·출력</a></nav>'
    content+='<section id="resolution">'+render(resolution)+'</section>'
    labels={'target':'대상','severity':'검토자 심각도','evidence':'제시한 근거','problem':'지적한 문제','recommendation':'검토자 권고','validation':'제안한 검증'}
    for name,review in reviews.items():
        meta=read(PRIVATE/f'reviews/{name}_meta.json')
        content+=f'<section id="{name}"><h2>{name.title()} 독립 검토 원문</h2><p>{inline(meta.get("model",""))} · 초안에 대한 검토. 총괄이 채택하지 않은 주장도 아래 원문에는 남아 있습니다.</p>'
        for item in review['findings']:
            content+='<details><summary>'+inline(item['id']+' — '+item['target'])+'</summary>'
            for key,label in labels.items():content+='<h4>'+label+'</h4><p>'+inline(str(item.get(key,'')))+'</p>'
            content+='</details>'
        for key,label in [('accepted_points','동의한 점'),('limitations','검토 한계')]:
            vals=review.get(key,[]);vals=vals if isinstance(vals,list) else [vals]
            content+='<h3>'+label+'</h3>'+''.join('<p>'+inline(str(v))+'</p>' for v in vals)
        content+='</section>'
    css='body{font:16px/1.75 system-ui,sans-serif;color:#17243a;background:#f4f6fa;margin:0}main{max-width:1120px;margin:auto;padding:36px}section{background:white;padding:24px;margin:24px 0;border-radius:14px}h1{font-size:29px}h2{margin-top:28px}td{padding:12px;border:1px solid #d7dfe9;vertical-align:top;min-width:140px}table{border-collapse:collapse;width:100%}tr:first-child{background:#eaf0f9;font-weight:bold}.scroll{overflow:auto}pre,code{background:#edf2f7;overflow:auto}pre{padding:18px;font-size:14px}.stats{display:flex;flex-wrap:wrap;gap:12px}.stats b,.notice{padding:14px;background:#e1edff;border-radius:8px}details{border:1px solid #d7dfe9;padding:14px;margin:14px 0}summary{cursor:pointer;font-weight:bold}nav{position:sticky;top:0;background:#fff;padding:14px;border-bottom:1px solid #cad3df}a{color:#1558b0}h4{margin-bottom:0}p{overflow-wrap:anywhere}'
    (PRIVATE/'review.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>적용 전 명세 검토</title><style>'+css+'</style><main>'+content+'</main></html>',encoding='utf-8')
    print(json.dumps({'integrity':checks,'preserved':preservation,'tests':tests,'report':str(PRIVATE/'review.html')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
