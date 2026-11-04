"""Read-only PDF verification and explicit source-reading ledger."""
import hashlib,json
from pathlib import Path
import pypdfium2 as pdfium
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2'
CACHE=Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit')
PDF=Path('C:/Users/ciot28/Downloads/1')
SCOPE={'D02':list(range(139,148)),'D04':list(range(8,16)),'D03':[3,27,28],'D05':list(range(21,26))}
VIEWS={'D02':[145,146],'D04':[8,10,11],'D05':[24],'D03':[3]}
def read(p):return json.loads(p.read_text(encoding='utf8'))
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def evidence(doc,page,quote,meaning,kind='source_statement'):
 t=read(CACHE/f'{doc}.json')[page-1]['text'];start=t.find(quote)
 if start<0:raise ValueError(f'quote_not_found:{doc}:{page}:{quote[:20]}')
 s=next(x for x in read(BASE/'provenance/sources.json') if x['id']==doc)
 return {'document_id':doc,'pdf_page':page,'page_system':'PDF 1-based','quote':quote,'start':start,'end':start+len(quote),
  'builder_paraphrase':meaning,'evidence_kind':kind,'source_pdf_sha256':s['sha256'],'page_text_sha256':hashlib.sha256(t.encode()).hexdigest(),
  'source_family':s['policy']['family'],'source_scope':('1980년대 경북 대계 자료; 주7의 1차사업 기간1979–1985. 개별 채록일과 구별.' if doc=='D02' else s['policy']['time_scope'])}
def prepare():
 ss=read(BASE/'provenance/sources.json');ledger=[]
 for s in ss:
  path=PDF/s['filename']
  if sha(path)!=s['sha256']:raise ValueError('changed_pdf:'+s['id'])
  if s['id'] not in SCOPE:continue
  d=s['id'];cache=read(CACHE/f'{d}.json');pdf=pdfium.PdfDocument(str(path))
  for p in SCOPE[d]:
   row={'doc':d,'pdf_page':p,'main_text_read':'full_page_extracted_text','pdf_sha256':s['sha256'],
    'text_sha256':hashlib.sha256(cache[p-1]['text'].encode()).hexdigest(),'has_nul':'\0' in cache[p-1]['text'],
    'visual_review':'not_performed'}
   if p in VIEWS.get(d,[]):
    out=HERE/'private/pdf_views'/f'{d}_{p}.png';out.parent.mkdir(parents=True,exist_ok=True)
    pdf[p-1].render(scale=1.5).to_pil().save(out)
    row['render_file']=str(out.relative_to(HERE));row['visual_review']='rendered_pending_inspection'
   ledger.append(row)
  pdf.close()
 dump(HERE/'private/source_reading.json',{'primary_pages':ledger,'extra_reading':[{'doc':'D04','pdf_page':46,'scope':'footnotes28–30 and neighboring lines, not full page'},{'doc':'D05','pdf_page':34,'scope':'footnotes83–84 and neighboring lines, not full page'}],
  'note':'25 primary pages read as extracted text by lead. PDF visual review is separately recorded. Not whole7source reading.'})
 print('read ledger',len(ledger),'rendered',sum('render_file' in r for r in ledger))
if __name__=='__main__':prepare()
