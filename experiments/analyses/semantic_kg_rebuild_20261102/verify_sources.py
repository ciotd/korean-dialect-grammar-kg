"""Verify original PDF identity and reopen selected semantic-review pages."""
import hashlib,json
from pathlib import Path
from pypdf import PdfReader
import pypdfium2
from inventory import BASE,HERE,CACHE,read,dump,sha
PDF=Path(r'C:\Users\ciot28\Downloads\1')
def run():
    access=read(HERE/'private/source_access.json');rendered=[]
    selected={'D02':[142,144,145,146],'D04':[8,9,10,11]}
    out=HERE/'private/pdf_views';out.mkdir(exist_ok=True)
    for s in access:
        p=PDF/s['filename'];s['pdf_path']=str(p);s['pdf_reopened']=False
        if not p.exists():continue
        s['current_pdf_sha256']=sha(p);s['pdf_hash_matches']=sha(p)==s['expected_pdf_sha256']
        if not s['pdf_hash_matches']:raise ValueError('pdf_changed:'+s['id'])
        reader=PdfReader(p);s['current_page_count']=len(reader.pages);s['pdf_reopened']=True
        checks=[]
        for num in selected.get(s['id'],[]):
            text=reader.pages[num-1].extract_text() or ''
            cache=next(x['text'] for x in read(CACHE/(s['id']+'.json')) if x['page']==num)
            checks.append({'page':num,'text_matches_cache':text==cache,'sha256':hashlib.sha256(text.encode()).hexdigest()})
        s['selected_page_text_checks']=checks
        if selected.get(s['id']):
            pdf=pypdfium2.PdfDocument(str(p))
            for num in selected[s['id']]:
                image=pdf[num-1].render(scale=1.5).to_pil();f=out/f'{s["id"]}_{num}.png';image.save(f);rendered.append(str(f))
            pdf.close()
    dump(HERE/'private/source_access.json',access)
    dump(HERE/'private/pdf_views/index.json',{'rendered':rendered,'visually_checked':[]})
    print(json.dumps({'pdfs_reopened':sum(s['pdf_reopened'] for s in access),'hashes_match':all(s.get('pdf_hash_matches') for s in access),'selected_text_checks':[{'id':s['id'],'checks':s.get('selected_page_text_checks',[])} for s in access],'rendered':len(rendered)},ensure_ascii=False))
if __name__=='__main__':run()
