"""Freeze the reviewed candidate as a separate authored graph, never production."""
import datetime,json,collections,subprocess,sys
from sources import HERE,ROOT,read,dump,sha,CACHE
import validate,report

RESOLUTION=[
 {'issue':'판정·설명 질문에 서로 다른 질문의 예문이 근거로 섞임','decision':'채택. 용언 판정에는 옳나·있나, 설명에는 하노·됐노를 연결. 계사+었+노에는 일반 조건 진술을 연결하고 직접 예문 미확인을 명시.','files':['build.py','test_query.py']},
 {'issue':'조회 결과 변조, 같은 위치 중복, 다른 절의 의문사 혼입','decision':'채택. 조회 재계산 대조, 원본 그래프 복사, 수정 위치와 주절 범위의 중복 검사, 질문 변수 소유 검사 추가.','files':['query.py','test_query.py']},
 {'issue':'명사·어간이 입력과 달라도 준비 완료가 됨','decision':'채택. 수작업 원문 대응 기록과 명사 표면 대조 추가. 기록과 다른 어간·명사는 분석 보완으로 반환. 이 검사는 새 형태소 분석기가 아니며 자동 분석 연결은 다음 작업.','files':['query.py','development.py','test_query.py']},
 {'issue':'근거 속성과 실제 간선이 서로 다른 정본으로 작동','decision':'채택. 조건별 근거를 spec에 명시하고 그래프 생성. 주/보조 역할을 실제 근거 간선에 기록하고 속성과 간선의 일치를 검사. 전달도 실제 간선에서 생성.','files':['build.py','query.py','test_query.py']},
 {'issue':'관찰 ID만 전달되어 무슨 문제인지 알 수 없음','decision':'채택. 짧은 뜻·상태·출처 쪽과 조합 전략을 함께 전달. 있다/없다 참고는 해당 어휘에만 전달.','files':['query.py']},
 {'issue':'계사+노·지역형·하게체·꼬·지/제·더 체계의 경계가 빠짐','decision':'부분 채택. 원문 양쪽을 참고 관찰·대조 간선으로 보존. 원문 시대와 표본이 다를 수 있어 모든 차이를 논리적 모순으로 확정하지 않음.','files':['build.py']},
 {'issue':'과거 계사의 완성 예문이 없으면 생성 준비를 막자는 의견','decision':'부분 채택. 확인 수준과 미검증 조합을 전달하되 일반 규칙의 적용 시험은 허용. 입력의 계사·선어말을 유지하며 다른 방언 선어말은 고르지 않음. ready는 전달 준비 상태이지 문헌 채록·품질 인증이 아님.','files':['query.py','README.md']},
 {'issue':'있다/없다, 지/제, 안동 세대 자료를 일괄 제한하거나 충돌로 확정','decision':'일괄 판단은 미채택. 있나 직접 용례는 유지. 지/제를 모두 확인 질문으로 단정하지 않음. 다른 시기·표본의 세대 자료를 동일 모집단의 모순으로 쓰지 않음.','files':['build.py','README.md']},
 {'issue':'최종 수정본의 검토 범위','decision':'독립2건과 교차2건을 완료. 교차 지적 반영 후 총괄이 원문·39개 검사를 재확인. 마지막 수정본 전체를 두 검토자가 다시 독립 검토한 것은 아님.','files':['private/dispatch','private/tests.txt']}
]

def main():
 v=validate.run();dump(HERE/'private/review_resolution.json',RESOLUTION)
 ledger=read(HERE/'private/source_reading.json')
 for page in (136,137,138):
  if not any(x.get('doc')=='D02' and x.get('pdf_page')==page for x in ledger['extra_reading']):
   ledger['extra_reading'].append({'doc':'D02','pdf_page':page,'scope':'full extracted page read by lead; no additional PDF screen inspection'})
 ledger['note']='25 designated pages plus D02 136–138 full extracted pages by lead; extra D04/D05 footnote excerpts. Seven PDF pages visually inspected separately. Not all seven sources fully reread.'
 dump(HERE/'private/source_reading.json',ledger)
 rounds=[]
 for phase in ('independent','cross'):
  for who in ('claude','codex'):
   d=HERE/'private/dispatch'/phase/who;start=read(d/'start.json');messages=read(d/'messages.json')
   rounds.append({'phase':phase,'reviewer':who,'complete':any(m['role']=='assistant' and start['marker'] in m['text'] for m in messages),
    'models':sorted({str(m['model']) for m in messages if m['role']=='assistant' and m.get('model')}),'prompt_sha256':sha(d/'prompt.txt'),'response_sha256':sha(d/'response.md')})
 if not all(x['complete'] for x in rounds):raise ValueError('review_not_complete')
 v['review_rounds']=rounds;v['post_cross_revision']='lead checked exact excerpts and reran tests; no second independent review of final whole version'
 dump(HERE/'private/validation.json',v)
 spec=read(HERE/'private/spec.json');graph=read(HERE/'private/graph.json');published=ROOT/'knowledge/authored'/spec['version']
 mapping=[{'usage_id':r['id'],'old_source_atoms':r['legacy_atom_ids'],'common_concepts':r['concept_ids'],
  'primary_evidence_ids':r['primary_evidence_ids'],'supporting_evidence_ids':r['supporting_evidence_ids'],
  'scope':'partial usage refinement, not completion of whole SourceAtom','status':r['realization_basis']} for r in spec['rules']]
 schema={'version':spec['version'],'node_types':v['node_types'],'relations':dict(collections.Counter(e['relation'] for e in graph['edges'])),
  'meaning':{'HAS_USAGE':'construction contains a usage','ANY_BRANCH':'any complete branch is sufficient','ALL':'all conditions in the same clause must hold',
   'ACCEPTS':'condition accepts this feature value','REALIZES':'usage has this ending realization','SUPPORTED_BY':'source support with source interpretation separate',
   'HAS_CONTEXT_NOTE':'reference, not executable candidate','CONTRASTS_WITH':'contrasting assertions, not automatically adjudicated contradiction'},
  'feature_schema':graph['feature_schema'],'generation_policy':graph['generation_policy'],'production_imported':False}
 for name,obj in [('spec.json',spec),('graph.json',graph),('source_mapping.json',mapping),('schema.json',schema)]:
  dest=published/'private'/name
  if dest.exists() and read(dest)!=obj:raise ValueError('published_version_exists_with_different_content:'+name)
  dump(dest,obj)
 for kind in ('nodes','edges'):
  path=published/'private'/f'{kind}.jsonl';data=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in graph[kind])
  if path.exists() and path.read_text('utf8')!=data:raise ValueError('published_jsonl_differs')
  path.write_text(data,encoding='utf8')
 pubreadme='''# 해라체 질문 지식 r3

별도 후보 버전. 운영 Neo4j/KG/카드를 대체하지 않았다.

- 원문 조건과 용례를 나눈 6개 용법, 9개 참고 관찰.
- 전체 12개 모듈의 식별자는 유지하지만 해당 모듈의 지식 전체를 정제했다는 뜻은 아니다.
- private/spec.json: 문헌 해석과 조건 명세. private/graph.json 및 nodes.jsonl/edges.jsonl: 실제 그래프.
- private/source_mapping.json: 기존 ID와 정제된 용법의 부분 대응. private/schema.json: 관계 의미와 분석 특징.
- 근거 원문·위치가 포함되어 private 데이터는 Git에 올리지 않는다. clone만으로 이 파일이 복원되지 않는다.
- 구현·검사·보고서: ../../../experiments/analyses/question_refinement_20261102/
- 수작업 분석으로 조회·전달만 검사. 실제 분석/Qwen 생성/현대 자연스러움 검증 미실행.
'''
 (published/'README.md').write_text(pubreadme,encoding='utf8')
 report.main()
 git=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
 manifest={'version':spec['version'],'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'code_commit':git.stdout.strip() if git.returncode==0 else None,
  'working_tree':'contains current uncommitted version; file hashes identify actual implementation',
  'implementation_hashes':{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.md','.cjs')},
  'input_hashes':read(HERE/'private/input_hashes.json'),'published_hashes':{p.name:sha(p) for p in (published/'private').iterdir() if p.is_file()},
  'test_summary':{k:v[k] for k in ('tests_run','failures','errors','previous_cases','development_cases','readiness_counts','qwen_calls')},
  'review_rounds':rounds,'production_replaced':False,'neo4j_imported':False}
 dump(published/'manifest.json',manifest);dump(HERE/'private/build_manifest.json',manifest)
 print(json.dumps({'version':spec['version'],'tests':v['tests_run'],'old_cases':v['previous_cases'],'ready':v['readiness_counts'],'graph':[v['nodes'],v['edges']],'reviews':len(rounds),'qwen_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
