"""Static artifact checks; this does not claim a browser rendering test."""
import hashlib,json,sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
sys.stdout.reconfigure(encoding='utf8')
BASE=Path(__file__).resolve().parent/'private'
class Report(HTMLParser):
    def __init__(self):super().__init__();self.cases=[];self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='article' and a.get('class')=='case':self.cases.append(a['data-id'])
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
text=(BASE/'review.html').read_text(encoding='utf8');p=Report();p.feed(text)
want=[c['id'] for c in json.loads((BASE/'casebook.json').read_text(encoding='utf8'))['cases']]
assert p.cases==want and len(set(p.cases))==50
assert len(p.ids)==len(set(p.ids))
assert not any(x.startswith(('http:','https:','javascript:')) for x in p.links)
missing=[x for x in p.links if not x.startswith('#') and not (BASE/unquote(x)).resolve().is_file()]
assert not missing,missing
assert '@@' not in text
result={'case_panels':50,'unique_control_ids':len(p.ids),'local_links_checked':len(p.links),'missing_links':[],
        'external_links':0,'unfilled_placeholders':0,'browser_rendering_test':'not_performed_file_protocol_blocked',
        'scope':'HTML content and file links only; no claim that interactive UI was browser-tested'}
if '--complete' in sys.argv:
    summary=json.loads((BASE/'summary.json').read_text(encoding='utf8'))
    assert summary['independent_review_coverage']=={'codex':50,'claude':50}
    assert summary['lead_crosschecked_inputs']==50
    reviewed={}
    for who in ['codex','claude']:
        all_ids=[]
        for i in range(1,6):
            bid=f'B{i:02}'
            packet=BASE/'packets'/f'{bid}.json'
            expected=json.loads(packet.read_text(encoding='utf8'))
            review=json.loads((BASE/'reviews'/who/f'{bid}.json').read_text(encoding='utf8'))
            meta=json.loads((BASE/'reviews'/who/f'{bid}.meta.json').read_text(encoding='utf8'))
            ids=[c['id'] for c in review['cases']]
            assert set(ids)=={c['id'] for c in expected['cases']} and len(ids)==10
            assert all('single' in c and 'multi' in c for c in review['cases'])
            assert meta['packet_sha256']==hashlib.sha256(packet.read_bytes()).hexdigest()
            if who=='codex':
                dispatch=BASE/'dispatch'/who/bid
                chunks=[json.loads(f.read_text(encoding='utf8')) for f in sorted(dispatch.glob('segment_[0-9][0-9].json'))]
                bodies=[c['prompt'].split('\nBEGIN_SEGMENT\n',1)[1].rsplit('\nEND_SEGMENT\n',1)[0] for c in chunks]
                assert ''.join(bodies)==(dispatch/'prompt.txt').read_text(encoding='utf8')
                assert all(hashlib.sha256(v.encode()).hexdigest()==c['part_content_sha256'] for v,c in zip(bodies,chunks))
                assert meta['delivery_check']['exact_segments_verified']
            else:assert meta['delivery_check']['exact_prompt_in_transcript']
            all_ids.extend(ids)
        assert len(all_ids)==len(set(all_ids))==50 and set(all_ids)==set(want)
        reviewed[who]=50
    result['complete_review_integrity']={'reviewed_inputs':reviewed,'lead_crosschecked':50,
        'all_packet_hashes_matched':True,'segmented_evidence_losslessly_reassembled':True}
(BASE/'report_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
