from pathlib import Path
import json,collections,hashlib,sys
R=Path.cwd();H=R/'experiments/analyses/support_expansion_20261104';C=Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit')
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
old=read(R/'experiments/analyses/boundary_qwen_20261103/private/all_targets.json');results=read(R/'experiments/runs/20261103T111250623634Z_boundary_qwen_full50/private/results.json');inputs={x['id']:x['input_text'] for x in results}
cards={x['id']:x for x in read(R/'knowledge/authored/kg_cards_20261030_v3/cards.json')['cards']};nodes={x['id']:x for x in map(json.loads,(R/'knowledge/authored/kg_v3_evidence_20261019_r2/graph/nodes.jsonl').read_text('utf8').splitlines())}
families={
'copula':['명사·부정 서술',['GS_ENDRULE_RA_COP','GS_END_DECL_YE_04','GS_PROFILE_HAEYE'],{'D02':[198,202,203,205],'D04':[21,22],'D05':[26,27]},'현재/과거·긍정/부정·상대높임별 입력형과 결합형을 분리. 기존 라/래 카드만으로 공손함을 없애지 않음. 문헌의 전통형과 사용자 현대형 선호 충돌 확인'],
'polite_q':['높임 질문',['GS_PROFILE_HAEYE'],{'D02':[57,213,214,215,216],'D05':[26]},'질문 기능과 상대높임을 보존한 구성 추가. 어요·나요·ㄹ까요를 동일 어미로 취급하지 않고 요청/추측/의향을 구분'],
'request':['요청·명령·금지',['GS_ENDRULE_ISO_IMP','GS_CONJ_O_IMP','GS_HAM_NEG_MAL'],{'D02':[153,154,155],'D07':[22],'D05':[26]},'행위자·높임·보조주다/말다·어휘한정명령을 분리. 온나를 모든동사에 확장하지 않음'],
'promise':['의지·약속',['GS_ENDRULE_KKI_PROM','GS_END_DECL_YE_08'],{'D02':[201,203,204,205]},'일인칭 의지/약속과 청유·요청을 구분. 끼/께예 결합조건과 높임 보존 검토'],
'hort':['청유',['GS_ENDRULE_HORT_JA'],{'D02':[189,190]},'함께행위 조건, 상대높임, 시제조건을 정제. 자 유지도 가능하고 반드시바꿀의무없음'],
'memory':['회상 서술',['GS_ENDRULE_DI_MEMORY','GS_ENDRULE_RA_COP'],{'D02':[89,90,198]},'더의회상과라/래계사구분. 회상을단순과거로바꾸지않고높임보존'],
'confirm':['확인 표현',['GS_ENDRULE_JI_CONFIRM'],{'D02':[210,211,215,216],'D05':[28]},'죠의확인기능·평서/질문·상대높임을보존. 반말제를그대로높임에적용하지않음'],
'intent':['의도·하려고요',['GS_PROFILE_HAEYE'],{'D02':[203],'D05':[26]},'연결형어미의문장끝용법과의도분석필요. 형태목록만으로요→예전부변환금지'],
'plain':['반말 평서',['GS_ENDRULE_RA_COP'],{'D02':[191,192,198],'D05':[27,28]},'평서어미변이와화용을구분. 샀어를샀제처럼확인/알림으로임의변환하지않음. 유지가정상인경우도기록'],
'analysis':['계세요 분석 충돌',['GS_FEATURE_COP'],{'D02':[57],'D05':[26]},'Kiwi분절과Qwen주체높임/서술어를대조. 계세요를계사로판정한위치부터수정;그후요청용세요와평서계세요를구별']}
manual={('ADVCE002A','W4'):('계세요를 copula로 분석. 원문 읽고 계세요의 보조용언과 불일치','direct_analysis_mismatch'),('LONG001','W19'):('먹고 있을게는 화자의 예정·약속인데 suggestion으로 분석','analysis_mismatch'),('LONG004','W16'):('제가 모셔다드릴게요는 화자의 약속·제안이며 함께행위 청유와 구별 필요','analysis_review'),('ADVCE008A','W6'):('빌려드릴게요를 request로 분석. 화자가 빌려주는 약속/제안과 청자에게 요청은 구별 필요','analysis_review'),('DEV017','W4'):('tense·subject_honorific 미확정 진단도 중첩','analysis_unknown'),('DEV021','W3'):('보조주다 predicate_class 미확정도 중첩','analysis_unknown'),('DEV021','W6'):('보조보다 predicate_class 미확정도 중첩','analysis_unknown'),('LONG003','W19'):('tense 미확정 진단도 중첩','analysis_unknown')}
def group(x):
 t=x['text'];f=x['result']['features']
 if x['id']=='ADVCE002A':return 'analysis'
 if '게' in t and (t.endswith('게') or t.endswith('게요')):return 'promise'
 if t.endswith('려고요'):return 'intent'
 if f['predicate_class'] in ['copula','negative_copula']:return 'copula'
 if f['speech_act']=='confirmation':return 'confirm'
 if t.endswith('더라'):return 'memory'
 if t.endswith('자') and f['speech_act']=='suggestion':return 'hort'
 if t.endswith('까요') or f['speech_act']=='information_question':return 'polite_q'
 if f['speech_act']=='request':return 'request'
 return 'plain'
out=[]
for x in old:
 if x['result'].get('readiness')!='out_of_slice':continue
 tr=read(Path(x['trace_path']));key=group(x);name,cids,refs,fix=families[key];checks=[]
 for q in tr['construction_queries']:
  c=q['retrieval']['clauses'][0]
  checks.append({'construction_id':q['retrieval']['construction_id'],'state':c['state'],'scope_failures':c.get('scope_failures',[]),'scope_unknown':c.get('scope_unknown',[]),'narrowing':c.get('narrowing',[])})
 related=[]
 for cid in cids:
  assert cid in cards,cid
  n=nodes[cid];spec=n['properties'].get('original_spec',{})
  related.append({'card_id':cid,'title':cards[cid]['title'],'forms':cards[cid].get('forms',[]),'source_refs':spec.get('source_refs',[]),'legacy_status':spec.get('status'),'mapping_status':'related_family_not_validated_applicable_rule'})
 note,kind=manual.get((x['id'],x['target_id']),('',None))
 out.append({'id':x['id'],'target_id':x['target_id'],'input':inputs[x['id']],'target':x['text'],'group':key,'group_label':name,'observed_features':x['result']['features'],'runtime_failures':checks,'analysis_issue':note or None,'analysis_issue_type':kind,'causes':['semantic_refinement_and_connection_missing']+([kind] if kind else []),'legacy_related':related,'source_pages_to_check':refs,'fix':fix,'evidence_path':x['trace_path'],'status':'source_comparison_pending','next_check':'条件ごとの本文対照と独立検討' })
assert len(out)==46 and len({(x['id'],x['target_id']) for x in out})==46
for x in out:x['next_check']='条件별 본문 대조와 독립 검토'
save(H/'private/audit46.json',out);save(H/'private/families.json',families)
# Index exact queried strings across all seven documents; search hits are not semantic certification.
terms=['이라예','이에예','아이랐어예','아니어예','이었어예','였어예','해체+요/예/여','-끼','-지예','-시소','-지 말다']
hits=[]
for d in range(1,8):
 doc=f'D{d:02}';pages=read(C/f'{doc}.json')
 for p,page in enumerate(pages,1):
  for term in terms:
   for pos in [m.start() for m in __import__('re').finditer(__import__('re').escape(term),page['text'])]:hits.append({'doc':doc,'pdf_page':p,'term':term,'offset':pos,'context':page['text'][max(0,pos-80):pos+160]})
save(H/'private/source_search.json',{'method':'exact_string_index_not_full_semantic_read','documents':7,'terms':terms,'hits':hits})
sys.path.insert(0,str(R/'src'));from research_management.work import WorkStore
WorkStore(R).task({'id':'support_expansion_20261104','title':'미지원46곳 대조와 근거 있는 문법 확장','actor':'총괄 + 기존 Orca 검토자','stage':'조회·기존카드 대조 완료 / 문헌검토 진행','status':'running','done':46,'total':46,'unit':'위치','message':'46곳 조회 기록 추출 완료. 의미·문헌 검토 완료 수와 구별.'})
print(json.dumps({'rows':len(out),'groups':dict(collections.Counter(x['group_label'] for x in out))},ensure_ascii=False))
