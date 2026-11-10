"""Read-only comparison of actual Claude translations and frozen Qwen traces."""
import json,hashlib,re,collections,html,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];P=BASE/'private'
CACHE=Path(r'C:\Users\ciot28\Documents\Codex\2026-10-13\ciotd-odor-complaint-dialect-rag-kg\work\source_audit')
BATCH='20261030T020345468863Z'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Analyst mapping: related forms are candidates, never applicability certificates.
# label, card IDs, documentary location and literal anchor, interpretation limit
F={
 'da':('평서 -다',['GS_END_DECL_HRA_09'],[('D04',27,'-다/대이')],'표준어와도 공유하는 형태. 변화 자체가 방언 고유성은 아님.'),
 'neye':('감탄·평서 -네예',['GS_END_DECL_YE_02'],[('D02',203,'-네예')],'형태 목록 확인. 각 어간과 현대 화자 적합성까지 검증한 것은 아님.'),
 'raye':('계사 -라예/-이라예',['GS_END_DECL_YE_04','GS_ENDRULE_RA_COP','GS_ENDRULE_YO_COMPOSE'],[('D05',26,'-이라예'),('D02',203,'-라예')],'문헌에 직접 대응 설명 있음. 대상 화자·세대별 선호는 별도.'),
 'aeye':('해요체 → 해예체, 과거·부정·높임 유지',['GS_ENDRULE_YO_COMPOSE','GS_END_DECL_YE_01','GS_PROFILE_HAEYE'],[('D05',26,'-어/아예'),('D02',203,'해체+요/예/여')],'예 하나를 종결어미 전체와 교체할 수 없음. 원래 활용을 유지하며 결합해야 함.'),
 'kkaye':('의문 -까예',['GS_END_Q_HAE_09','GS_ENDRULE_YO_COMPOSE'],[('D05',9,'드리까예'),('D02',258,'-까예/꼬예')],'구성 성분 카드만 확인. -까예 완성형의 직접 실행 카드와 같은 뜻이 아님.'),
 'promise_ye':('약속 -께예',['GS_END_DECL_YE_08','GS_ENDRULE_YO_COMPOSE'],[('D04',21,'가보께예'),('D04',28,'내 하께'),('D02',203,'-께예')],'D02 목록의 유일 용례 간께예를 약속으로 단정하지 않음. 약속 용법은 별도 D04 용례와 대조. 카드에 의지 기능·결합 절차가 충분한지는 별도 문제.'),
 'promise_bare':('약속 -께/하께',[],[('D04',28,'-(으)(ㄹ)께')],'해당 표준어→방언 대응이 문헌에는 있으나 721개 카드의 제목·forms·조건에서 직접 대응을 찾지 못함. -끼/-꾸마는 다른 대안이며 동일 형태로 세지 않음.'),
 'formal_q':('높임 의문 -ㅂ니꺼/-습니꺼',['GS_END_Q_HI_04','GS_END_Q_HI_03'],[('D02',228,'-ㅂ니꺼')],'부분 형태 목록. -습니꺼 전체·받침 결합은 추가 조합이 필요하며 해요체와 격식 차이 확인 필요.'),
 'formal_decl':('높임 평서 -ㅂ니더/-습니더',['GS_ENDRULE_NI_B_OPTION','GS_ENDRULE_SIP_NO_SUBJ','GS_END_DECL_HI_02'],[('D04',28,'맞습니더')],'형태와 조합 관련 카드 있음. 원문의 격식·주체 높임 보존은 별도 확인.'),
 'iso':('요청·명령 -(으)이소',['GS_ENDRULE_ISO_IMP','GS_END_IMP_HI_01'],[('D02',154,'-이소')],'명령형 목록과 혼용 설명 확인. 각 어간의 결합·요청 강도까지 자동 보장하지 않음.'),
 'no':('의문사 질문 -노',['GS_ENDRULE_Q_WH_V','GS_END_Q_HRA_04'],[('D02',145,'-나/노')],'의문사와 같은 절에 있는지·높임·시제 조합을 확인해야 함.'),
 'go':('계사 의문사 질문 -고',['GS_ENDRULE_Q_WH_C','GS_END_Q_HRA_02'],[('D02',144,'-가/고')],'어디고 등 계사 구성과 용언 질문을 구분해야 함.'),
 'na':('예/아니오 질문 -나',['GS_ENDRULE_Q_POLAR_V','GS_END_Q_HRA_03'],[('D02',145,'-나/노')],'질문 유형·높임·시제 조건이 함께 필요.'),
 'compare':('비교 조사 -보담',['GS_PART_COMPARE_04'],[('D04',27,'보담')],'비교 뜻으로 사용되는 조사임을 확인. 비교 의미 외 일반 교체 아님.'),
 'cause':('원인 연결 -아/어가',['GS_CONNECT_CAUSE_01'],[('D04',27,'-아가')],'문헌 표기 -아가를 모든 어간에 그대로 붙일 수 없음. 어가·해가 등 활용은 별도 조합.'),
 'intent':('의도 -(으)ㄹ라꼬',['GS_CONNECT_INTENT_02','GS_CONNECT_INTENT_01'],[('D04',28,'ㄹ라꼬')],'할라 카는 관형 구성이나 -예 결합 전체와 동일한 단일 카드가 아님.'),
 'quote':('인용 -다꼬 / -라 카다',['GS_CONNECT_QUOTE_02','GS_PHON_CONTRACT'],[('D04',28,'(인용)꼬'),('D04',21,'오라칸')],'인용 내용의 평서/명령/청유와 뒤의 서술어·관형형을 함께 보존해야 함.'),
 'onna':('오다 명령 온나',['GS_CONJ_O_IMP','GS_ENDRULE_NNA_O'],[('D04',7,'온나')],'어휘 한정 용례. 모든 동사에 확장 불가.'),
 'muk':('먹다→묵다와 활용',['GS_CONJ_MUK_UU'],[('D04',6,'묵다')],'카드는 무우형 패러다임 중심. 먹다→묵다의 일반 어휘 대응까지 완비됐다는 뜻은 아님.'),
 'put':('넣다→옇다',['GS_LEX_061'],[('D04',37,'옇다')],'직접 어휘 대응은 존재. 옇었다 활용 생성은 별도.'),
 'small':('조금→쪼매',['GS_LEX_063'],[('D04',38,'쪼매')],'어휘 선택으로 얻는 방언 느낌과 문법 효과를 구분.'),
 'retro':('회상·배경 봤드만',['GS_CONNECT_RETRO_03','GS_CONNECT_RETRO_04'],[('D04',28,'-더니만')],'가까운 계열만 확인. -봤는데→봤드만의 모든 의미 등가를 입증하지 않음.'),
 'rai':('금지·당부 마레이',['GS_END_IMP_HRA_10','GS_END_DECL_HAE_04'],[('D04',28,'-라/래이')],'근접 표기·다른 용법 카드. 마레이 전체나 추가 당부 뉘앙스의 등가는 미확인.'),
 'negcop':('아니야→아이다',['GS_PHON_N_NASAL'],[('D04',21,'아이다')],'음운 관찰 카드가 있을 뿐 부정 계사의 변환 절차까지 담은 직접 카드라고 볼 수 없음.'),
 'ji_q':('확인 질문 -지예',['GS_END_Q_YE_05','GS_ENDRULE_JI_CONFIRM','GS_ENDRULE_YO_COMPOSE'],[('D04',28,'맞지예')],'질문/평서·시제·높임을 같이 보존해야 함.'),
 'ji_d':('확인 진술 -지예',['GS_END_DECL_YE_06','GS_ENDRULE_JI_ASSERT','GS_ENDRULE_YO_COMPOSE'],[('D02',203,'-지예')],'마침표만으로 실제 담화 기능을 확정하지 않음. 이 입력은 원래 -죠 형태.'),
 'geodeunye':('설명 종결 -거든예',['GS_END_DECL_YE_07'],[('D02',203,'-거든예')],'설명 기능의 문장 적용은 추가 대조 필요.'),
 'ra':('명령 -라',['GS_END_IMP_HRA_10'],[('D04',28,'-라/래이')],'원문의 요청 강도가 달라질 가능성 확인 필요.'),
 'progress':('진행 구성 유지',['GS_HAM_AUX_PROGRESS'],[('D07',24,'진행을 나타내는 보조동사')],'방언 변경 없이 보존하는 지식도 필요. 관찰 카드가 곧 편집 명령은 아님.'),
}
M={
'DEV002':['da'],'DEV003':['compare','neye'],'DEV004':['raye'],'DEV005':['compare','da'],'DEV007':['muk','da'],'DEV011':['formal_q'],'DEV012':['no'],'DEV013':['kkaye'],'DEV014':['no'],'DEV017':['iso'],'DEV019':['cause','iso'],'DEV020':['rai'],'DEV021':['iso','promise_ye'],'DEV022':['muk'],'DEV026':['aeye','small'],'DEV028':['aeye','quote'],'DEV029':['retro'],'DEV030':['ra','promise_bare'],
'LONG001':['go','quote','no','cause','muk','promise_bare'],'LONG002':['muk','na','ra','small'],'LONG003':['cause','formal_q','neye','iso'],'LONG004':['aeye','cause','iso','promise_ye'],'NEW001':['raye'],'NEW004':['formal_q'],'NEW005':['kkaye'],'NEW006':['cause','iso'],'NEW007':['muk','onna'],'NEW008':['negcop'],'NEW009':['put','da'],'NEW012':['quote','aeye'],
'ADVCE001A':['formal_q'],'ADVCE001B':['formal_q'],'ADVCE002A':['progress','formal_decl'],'ADVCE002B':['progress','aeye'],'ADVCE003A':['kkaye'],'ADVCE003B':['kkaye'],'ADVCE005A':['raye'],'ADVCE005B':['formal_decl'],'ADVCE006A':['aeye'],'ADVCE006B':['aeye'],'ADVCE008A':['promise_ye','progress'],'ADVCE008B':['promise_ye'],'ADVCE010A':['ji_q'],'ADVCE010B':['ji_d'],
'QUAL002':['raye'],'QUAL003':['aeye'],'QUAL005':['aeye'],'QUAL017':['intent','geodeunye','aeye'],'QUAL018':['quote','cause','aeye'],'QUAL020':['cause','intent','quote','aeye']}
NOTES={
'DEV002':'Claude는 -데이를 억지로 붙이지 않고 샀다를 선택. 원문 유지와 이 대안의 품질 차이는 사람 확인 사항.',
'DEV019':'미끄러버가의 완성형은 7종 텍스트의 문자 검색으로 확인되지 않음. ㅂ 활용 변이와 자연스러움은 사람·문헌 추가 검토 대상.',
'DEV020':'Claude도 -레이가 당부 느낌을 추가한다고 명시. 원문에 없는 뉘앙스가 생기는지 확인 필요.',
'DEV028':'Claude는 인용 관형 관계를 유지. Single은 버리라는→버리고로 바꿔 뒤의 뜻과 연결을 잃음. 내삐리다 자체의 의미 범위는 추가 확인.',
'DEV029':'Claude는 괜찮더라를 유지하고 앞 연결어미만 바꿈. 시스템은 더라를 래로 바꿔 회상 보존 검사가 빠짐.',
'LONG003':'Qwen은 들어가아가와 맛있나 등을 출력. Claude가 고른 높임말이 유일한 정답은 아니지만, 질문 유형·높임 보존 검사의 공백은 로그에서 확인됨.',
'LONG004':'할매 호칭과 가족 대화 느낌은 원문의 상황과 맞는지 사용자 확인 필요.',
'NEW006':'어두버가의 완성형은 검색으로 확인되지 않음. 어두워가 등과의 자연스러움 비교를 사람에게 남김.',
'NEW007':'있을 끼니까 전체를 직접 구현한 카드가 확인된 것은 아님. 온나는 별도 어휘 한정 카드.',
'NEW012':'Claude의 딴 데로는 원문의 다른 곳에와 조사도 달라짐. 의미 보존을 자동 확정하지 않음.',
'ADVCE008A':'빌리드리께예의 어휘·표기는 지역 화자 확인 필요. 사용자가 선호한 빌려드릴게예와도 다름.',
'ADVCE010B':'Claude 스스로 억양 의존성을 명시. 마침표만으로 확인 진술의 적합성을 확정하지 않음.',
'QUAL002':'공통 분석이 허용 목록 밖 기능명 때문에 실패하여 실제 KG 조회 이전에 종료됨. 가상 조회 결과로 메우지 않음.',
'QUAL017':'Single은 이번에/저번에를 수단 조사로 바꿈. Claude는 이 부분을 유지. 전체 원인은 KG 부족 하나로 설명되지 않음.',
'QUAL018':'Single 생각아가, Claude 생각해가. 실제 카드 -아가는 이미 전달·선택됐지만 하(XSV) 보존 검사 누락.',
'QUAL020':'두 Qwen 방식 모두 재밌아가, Claude 재밌어가. 같은 원인 연결 카드가 이미 전달되어 조합·검사 문제를 확인 가능.'}
def norm(s):return re.sub(r'\s+','',s)
def main():
 cards=read(ROOT/'knowledge/authored/kg_cards_20261028_v2/cards.json')['cards'];by={c['id']:c for c in cards};prov=read(ROOT/'knowledge/authored/kg_cards_20261028_v2/provenance.json')
 pages={f'D{k:02}':{p['page']:p['text'] for p in read(CACHE/f'D{k:02}.json')} for k in range(1,8)}
 evidence={}
 for key,(label,ids,refs,note) in F.items():
  assert set(ids)<=set(by),key
  ev=[]
  for doc,page,anchor in refs:
   text=norm(pages[doc][page]);i=text.find(norm(anchor));assert i>=0,(key,doc,page,anchor)
   ev.append({'doc':doc,'pdf_page':page,'anchor':anchor,'excerpt':text[max(0,i-65):i+150],'proof':'wording_exists_not_full_sentence_validation'})
  evidence[key]={'label':label,'cards':[by[i] for i in ids],'source_excerpts':ev,'card_source_refs':{i:prov[i]['source_refs'] for i in ids},'limit':note}
 translations=read(P/'translations.json');inputs=[json.loads(l) for l in (ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl').read_text(encoding='utf-8').splitlines()]
 assert [r['id'] for r in translations['rows']]==[r['id'] for r in inputs];assert set(M)=={r['id'] for r in inputs}
 cases=[];bottlenecks=collections.Counter();delivered_families=[]
 for inp,tr in zip(inputs,translations['rows']):
  id=inp['id'];arms={};raw=None;packet=None
  for arm in ['single','multi']:
   folder=ROOT/'experiments/runs'/f'{BATCH}_cards_{arm}_regression/private/records'/id
   r=read(folder/'result.json');plan=read(folder/'final_plan.json') if (folder/'final_plan.json').exists() else None
   arms[arm]={'output':r.get('output_text'),'status':r['status'],'error':r.get('error'),'selected_rules':r['selected_rules'],'applied_rules':r.get('applied_rules',[]),'edits':plan['edits'] if plan else [],'record':str(folder.relative_to(ROOT))}
   if arm=='single':
    raw=read(folder/'retrieval_raw.json') if (folder/'retrieval_raw.json').exists() else None
    packet=read(folder/'reference_packet.json') if (folder/'reference_packet.json').exists() else None
  families=[]
  for key in M[id]:
   e=evidence[key];traces=[]
   for card in e['cards']:
    cid=card['id'];rank=next((x for x in raw['ranking'] if x['id']==cid),None) if raw else None
    found=cid in raw['retrieved_ids'] if raw else None;delivered=any(c['id']==cid for c in packet['cards']) if packet else None
    stage='analysis_failed' if not raw else 'not_retrieved' if not found else 'filtered_out' if not delivered else 'delivered'
    paths=[p for p in raw['paths'] if p['rule_id']==cid] if raw else []
    traces.append({'card_id':cid,'card_kind':card.get('kind'),'stage':stage,'retrieved':found,'delivered':delivered,'ranking':rank,'paths':paths,'single_selected':cid in arms['single']['selected_rules'],'multi_selected':cid in arms['multi']['selected_rules'],'single_applied':cid in arms['single']['applied_rules'],'multi_applied':cid in arms['multi']['applied_rules']})
   families.append({'key':key,'label':e['label'],'traces':traces,'source_excerpts':e['source_excerpts'],'card_source_refs':e['card_source_refs'],'limit':e['limit']})
  stages={t['stage'] for f in families for t in f['traces']}
  for s in stages:bottlenecks[s]+=1
  if any(not f['traces'] for f in families):bottlenecks['no_direct_card']+=1
  cases.append({'id':id,'input':inp['text'],'claude':tr,'arms':arms,'families':families,'lead_note':NOTES.get(id,'기록된 핵심 문법 대안의 경로를 확인했다. 대명사·어휘·생략 등 나머지 변화의 정확성과 현대 자연스러움은 확정하지 않았다.'),'scope':'core_grammar_families_not_every_lexical_change','raw_retrieved':len(raw['retrieved_ids']) if raw else None,'delivered_count':len(packet['cards']) if packet else None})
 save(P/'family_evidence.json',evidence);save(P/'cases.json',cases)
 summary={'case_count':len(cases),'family_count':len(evidence),'trace_count':sum(len(f['traces']) for c in cases for f in c['families']),'case_stage_counts_nonexclusive':dict(bottlenecks),'analysis_failed_ids':[c['id'] for c in cases if not c['families'][0]['traces'] and c['raw_retrieved'] is None or c['raw_retrieved'] is None],'scope':'All50 translations and core-family trace audit. Not full semantic validation of all changes. No quality scores or causal intervention.', 'no_kg_or_pipeline_change':True,'new_qwen_calls':0}
 save(P/'summary.json',summary)
 esc=lambda x:html.escape(str(x if x is not None else '없음'))
 h='<h1>Claude 50문장과 우리 시스템 비교</h1><p class="lead">표현이 없었나, 있었는데 못 썼나?<br><strong>이번에는 더 나은 표현 후보에서 출발해 문헌 → KG → 조회 → 48개 선별 → 적용을 거꾸로 확인했습니다.</strong></p>'
 h+='<p>Claude 번역 50개를 모두 받았습니다. 아래 비교는 정답 채점이 아닙니다. 기존 세션은 이전 결과를 본 적이 있어 맹검이 아니며, Claude도 경남·부산 쪽 말투에 치우쳤다고 밝혔습니다.</p>'
 h+='<h2>확인된 세 갈래 문제</h2><table><tr><th>실제 사례</th><th>어디까지 있었나</th><th>확인한 문제</th></tr><tr><td>맵네예 / 친구라예</td><td>문헌과 카드에 존재 → 그래프 조회됨 → 최종 전달에서 누락</td><td>지식 자체의 부재보다 48개 선별 단계의 누락</td></tr><tr><td>하께 / -께예 약속</td><td>문헌에 직접 대응·용례 존재. -께예 목록 카드는 있지만 -ㄹ게→-께 직접 대응 카드는 검색에서 확인되지 않음</td><td>원문 수록과 실행 가능한 지식 정리는 다름</td></tr><tr><td>생각해가 / 재밌어가</td><td>-아가 카드가 Qwen에 전달되고 선택됨</td><td>생각아가 / 재밌아가로 잘못 조합·통과</td></tr></table>'
 h+='<p class="warn">문헌에 형태가 나온다는 사실만으로 그 문장에 적용 가능하다고 확정하지 않습니다. 특히 -까예, -께예처럼 여러 성분이 결합하는 표현은 재료 카드와 완성된 변환 규칙을 구분합니다.</p>'
 h+='<details><summary>이번 확인 범위와 다음 판단</summary><ul><li>50개 모두 Claude·Single·Multi 출력과 핵심 문법 대안의 카드 경로를 연결했습니다.</li><li>7종 PDF의 원본 해시를 확인하고 474쪽 추출본을 검색했습니다. 핵심 표 3쪽은 PDF 이미지로 대조했습니다. 474쪽 전체를 이번에 재정독했다는 뜻은 아닙니다.</li><li>문헌·카드의 문자 검색 실패는 부재 확정이 아닙니다. 모든 어휘 교체와 미끄러버가 같은 완성형의 지역 적합성은 미확정으로 남겼습니다.</li><li>이번에는 KG·Qwen 파이프라인을 고치거나 새 Qwen 실험을 하지 않았습니다. 먼저 해당 대안을 실제로 전달했을 때 달라지는지 확인해야 인과 효과를 말할 수 있습니다.</li></ul></details>'
 h+='<h2>50개 실제 출력</h2><p>문장을 펼치면 세 결과와 지식 전달 경로가 나옵니다. 카드의 “전달됨”은 적용이 옳았다는 뜻이 아닙니다.</p>'
 labels={'analysis_failed':'분석 실패·조회 전 종료','not_retrieved':'KG 카드 있음·조회 안 됨','filtered_out':'조회됐지만 48개 선별에서 탈락','delivered':'Qwen에 전달됨'}
 for c in cases:
  h+='<details class="case"><summary>'+esc(c['id']+' · '+c['input'])+'</summary><table><tr><th>Claude 대안</th><td>'+esc(c['claude']['translation'])+'</td></tr>'
  for arm in ['single','multi']:h+='<tr><th>'+arm.title()+'</th><td>'+esc(c['arms'][arm]['output'])+'</td></tr>'
  h+='</table><p><strong>리드 확인:</strong> '+esc(c['lead_note'])+'</p>'
  if c['claude']['uncertainty']:h+='<p><strong>Claude 자체 유보:</strong> '+esc(c['claude']['uncertainty'])+'</p>'
  h+='<table><tr><th>대안과 관련된 지식 후보</th><th>카드와 실제 경로</th><th>문헌·확인 한계</th></tr>'
  for f in c['families']:
   ts=[]
   for t in f['traces']:
    picks=', '.join(a.title()+(' 적용' if t[a+'_applied'] else ' 선택') for a in ['single','multi'] if t[a+'_selected']) or '두 방식 모두 미선택'
    ts.append('<code>'+esc(t['card_id'])+'</code><br>'+esc({'design_rule':'설계 규칙','observation':'관찰 기록','classification':'분류 정보'}.get(t['card_kind'],t['card_kind']))+' · '+esc(labels[t['stage']])+' / '+esc(picks))
   src='; '.join(e['doc']+' PDF '+str(e['pdf_page'])+'쪽' for e in f['source_excerpts']) or '아래 카드 출처 위치 참조'
   h+='<tr><td>'+esc(f['label'])+'</td><td>'+('<hr>'.join(ts) or '직접 대응 카드 미확인')+'</td><td>'+esc(src)+'<br>'+esc(f['limit'])+'</td></tr>'
  h+='</table><details><summary>문헌 근거와 Claude가 설명한 변화</summary>'
  for f in c['families']:
   h+='<p><strong>'+esc(f['label'])+'</strong></p>'
   for e in f['source_excerpts']:h+='<blockquote>'+esc(e['doc']+' PDF '+str(e['pdf_page'])+'쪽 · '+e['excerpt'])+'</blockquote>'
   for cid,refs in f['card_source_refs'].items():h+='<p class="small">'+esc(cid)+' · '+esc('; '.join(str(r.get('doc'))+' PDF '+str(r.get('pdf_page',r.get('page'))) for r in refs))+'</p>'
  h+='<ul>'+''.join('<li>'+esc(x['source']+' → '+x['target']+' · '+x['function'])+'</li>' for x in c['claude']['changes'])+'</ul></details></details>'
 h+='<details><summary>Claude가 밝힌 한계와 원본 기록</summary><ul>'+''.join('<li>'+esc(x)+'</li>' for x in translations['limitations'])+'</ul><p>원본 답변·전송 지시·입력 해시·50개 경로·문헌 발췌는 같은 private 폴더에 보존했습니다. 모델: claude-fable-5(세션 기록). Qwen 비교 Run: '+BATCH+'.</p></details>'
 css='body{margin:0;background:#f5f7fb;color:#172d42;font:17px/1.8 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:28px}h1{font-size:30px}h2{margin-top:28px}.lead{background:#e9f0fc;padding:20px;border-radius:12px}table{width:100%;border-collapse:collapse;margin:15px 0;background:white}td,th{text-align:left;vertical-align:top;padding:12px;border:1px solid #dce3ed;overflow-wrap:anywhere}th{background:#edf2f8}details{background:white;padding:16px;border:1px solid #dce3ed;border-radius:10px;margin:12px 0}summary{font-weight:650;cursor:pointer}blockquote{border-left:3px solid #99abc0;padding:8px 14px;background:#f7f9fc;margin:12px 0}.warn{background:#fff4db;padding:14px}.small,code{font-size:13px}code{overflow-wrap:anywhere}hr{border:0;border-top:1px solid #e0e5ed}@media(max-width:650px){main{padding:12px}td,th{padding:6px;font-size:14px}}'
 (P/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Claude 50문장 비교</title><link rel="stylesheet" href="report.css"><main>'+h+'</main></html>',encoding='utf-8');(P/'report.css').write_text(css,encoding='utf-8')
 save(P/'hashes.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'translations.json',P/'cases.json',P/'family_evidence.json',P/'summary.json',P/'report.html',BASE/'compare.py']})
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
