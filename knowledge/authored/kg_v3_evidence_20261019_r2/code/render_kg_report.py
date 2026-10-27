"""Generate a self-contained technical report from the actual frozen graph."""
import argparse,collections,hashlib,html,json
from pathlib import Path
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l]
def main(root):
    root=Path(root);ns=rows(root/'graph/nodes.jsonl');es=rows(root/'graph/edges.jsonl')
    validation=read(root/'validation/validation.json');stats=validation['stats'];schema=read(root/'schema/schema.json')
    sources=read(root/'provenance/sources.json');inventory=read(root/'provenance/html_inventory.json')
    reviews=[]
    for f in sorted((root/'reviews').glob('*.json')):
        if not f.name.startswith(('schema_', 'linguistic_')): continue
        reviews.append({'file':f.name,'content':read(f)})
    payload={'nodes':ns,'edges':es,'stats':stats,'schema':schema,'validation':validation,'sources':sources,
      'inventory':inventory,'reviews':reviews,'decisions':read(root/'reviews/design_decisions.json'),
      'modules':read(root/'schema/modules.json'),'layers':read(root/'schema/layers.json'),
      'resolutions':read(root/'reviews/review_resolutions.json') if (root/'reviews/review_resolutions.json').exists() else [],
      'reuse':read(root/'provenance/prior_review_reuse.json') if (root/'provenance/prior_review_reuse.json').exists() else {}}
    data=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    template=Path(__file__).with_name('report_template.html').read_text(encoding='utf-8')
    result=template.replace('/*__KG_DATA__*/',data)
    (root/'report.html').write_text(result,encoding='utf-8')
    print(json.dumps({'html_bytes':len(result.encode()),'nodes':len(ns),'edges':len(es)}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();main(a.root)
