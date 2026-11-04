"""Read all historical records; create traceable, non-evaluative change evidence."""
import hashlib
import html
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
sys.path.insert(0,str(PROJECT/'src'))
from research_management.work import WorkStore

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    source=PROJECT/'experiments/analyses/full_review_20261029/private/casebook.json'
    data=load(source);cardsfile=PROJECT/'knowledge/authored/kg_cards_20261028_v2/cards.json'
    cards={c['id']:c for c in load(cardsfile)['cards']}
    store=WorkStore(PROJECT);rows=[];used=set();hashes={str(source.relative_to(PROJECT)):digest(source),str(cardsfile.relative_to(PROJECT)):digest(cardsfile)}
    task=dict(id='evidence50-20261030',title='50개 전체 변경 대상 연결',actor='총괄 분석 스크립트',stage='기존 기록 대조',status='running',done=0,total=50,unit='입력',unit_key='frozen-casebook-scan')
    store.task(task)
    for i,c in enumerate(data['cases'],1):
        row={'id':c['id'],'input':c['input'],'lead_observations':c['lead_observations'],'arms':{}}
        for arm in ('single','multi'):
            a=c['arms'][arm];path=PROJECT/a['source_record_dir']
            payload=load(path/'reference_packet.json') if (path/'reference_packet.json').exists() else {}
            supplied={x['id']:x for x in payload.get('cards',[])}
            edits=(a.get('final_plan') or a.get('draft') or {}).get('edits',[])
            flags=[]
            if not a['output']:flags.append('최종 출력 없음: 원인 분리 필요')
            if a.get('standalone_jamo'):flags.append('출력의 분리 자모: 활용 구간 확인')
            if a.get('error')=='after_not_single_word':flags.append('한 어절 제약으로 거부')
            if any(e.get('before') is not None and e.get('before')==e.get('after') for e in edits):flags.append('수정 전후 동일 항목 존재')
            ids=sorted({x for e in edits for x in e['rule_ids']});used.update(ids)
            if any(x in ids for x in ('GS_ENDRULE_JI_ASSERT','GS_ENDRULE_JI_CONFIRM')):flags.append('-지/-제 선택 근거 확인')
            if 'GS_PART_ACC_03' in ids:flags.append('-를 목표형과 계획 대조')
            for name in ('morphology.json','reference_packet.json','final_plan.json','agent_call/parsed.json','generation_call/parsed.json'):
                p=path/name
                if p.exists():hashes[str(p.relative_to(PROJECT))]=digest(p)
            row['arms'][arm]={'output':a['output'],'status':a['status'],'error':a['error'],
                'flags':flags,'card_ids':ids,'actual_edits':edits,'record_dir':a['source_record_dir'],
                'supplied_card_definitions':{key:supplied[key] for key in ids if key in supplied},
                'selected_id_missing_from_packet':[key for key in ids if key not in supplied]}
        rows.append(row);store.task({**task,'done':i,'status':'completed' if i==50 else 'running','message':c['id']+' / 양쪽 기록 확인. 문법 정확도 평가 아님.'})
    catalog=[{'card':cards[key],'used_by':[r['id']+':'+arm for r in rows for arm,a in r['arms'].items() if key in a['card_ids']],
             'mapping_state':'existing_definition_preserved_proposed_field_split_not_applied'} for key in sorted(used)]
    private=ROOT/'private'
    save(private/'all50_mapping.json',{'input_count':len(rows),'record_count':sum(len(r['arms']) for r in rows),'scope':'location/index, not linguistic adjudication','rows':rows})
    save(private/'used_card_catalog.json',catalog)
    save(private/'evidence_manifest.json',hashes)
    e=html.escape
    panels=[]
    for r in rows:
        body=''.join('<p>'+e(x)+'</p>' for x in r['lead_observations'])
        for arm,a in r['arms'].items():
            body+=f'<h3>{arm}</h3><p>{e(a["output"] or "출력 없음")}</p><p>{e(" / ".join(a["flags"]) or "자동 표시 없음 — 정답 판정 아님")}</p><p>선택 카드: {e(", ".join(a["card_ids"]))}</p>'
            body+='<table><tr><th>원문 → 결과</th><th>선택 근거</th><th>실제 지시</th></tr>'
            for ed in a['actual_edits']:
                body+=f'<tr><td>{e(ed.get("before",ed["word_id"]))} → {e(ed.get("after", ""))}</td><td>{e(", ".join(ed["rule_ids"]))}</td><td>{e(ed.get("instruction",""))}</td></tr>'
            body+='</table>'
        panels.append(f'<details><summary>{e(r["id"])} · {e(r["input"])}</summary>{body}</details>')
    (private/'mapping.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>50개 변경 대상 대조</title><style>body{font:16px/1.7 sans-serif;max-width:1200px;margin:40px auto;color:#193344}details{border:1px solid #ddd;padding:16px;margin:12px 0}summary{cursor:pointer;font-weight:bold}table{border-collapse:collapse;width:100%;table-layout:fixed}td,th{border:1px solid #ddd;padding:10px;overflow-wrap:anywhere}</style><h1>50개 전체 · 승인된 변경 대상 대조</h1><p>기존 100개 실행의 기록입니다. 새로운 번역 실험이나 정답 판정이 아닙니다. 출력 없음도 숨기지 않았습니다. 자동 표시는 위치를 찾는 도구이며 문법 오류 전체를 포괄하지 않습니다.</p>'+''.join(panels)+'</html>',encoding='utf-8')
    print(json.dumps({'inputs':len(rows),'records':100,'used_card_ids':len(used),'source_files_hashed':len(hashes)},ensure_ascii=False))

if __name__=='__main__':main()
