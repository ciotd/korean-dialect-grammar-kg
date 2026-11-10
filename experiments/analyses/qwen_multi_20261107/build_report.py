"""Build one human-readable report from real worker prompts and optional run logs.

No model calls, KG mutations, or quality scores. Inputs/outputs stay in private/.
Run this after freezing the implementation; repeated invocations update the same
report while the underlying run directories remain immutable.
"""
import argparse
import datetime as dt
import html
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from kg_pipeline.multi_agent import PROMPTS
from kg_pipeline.io import sha

ROLES = {
    'structure': ('① 구조 분석', '어디에 어떤 말이 있는지 찾습니다.',
                  '어간·어미·절·본용언과 보조용언을 먼저 나눕니다. 이 결과는 모델의 추정이며, 원문 위치가 맞다는 코드 검사만으로 문법 정답이 되지는 않습니다.'),
    'meaning': ('② 의미·관계 분석', '그 말의 뜻과 서로의 관계를 판단합니다.',
                '질문인지 약속인지, 과거인지, 누구를 높이는지 구분합니다. ‘어디’가 장소이면서 의문 표현일 수 있도록 서로 다른 질문을 나누었습니다.'),
    'writer': ('③ 선택·문장 작성', '쓸 지식을 고른 뒤 문장 전체를 씁니다.',
               '별도 계획과 작성에 같은 정보를 반복 전달하는 비용을 줄입니다. 대신 어떤 후보를 썼고 안 썼는지 먼저 기록하여 선택 과정을 확인할 수 있게 했습니다.'),
    'reviewer': ('④ 별도 검토', '초안에서 사라지거나 바뀐 내용을 찾습니다.',
                 '원문·지식·초안을 대조하여 과거·높임·부정·참여자·절 누락을 확인합니다. 같은 Qwen의 다른 호출이므로 독립적인 사람 평가와 같지 않습니다.'),
    'planner': ('비교용: 별도 계획', '선택 계획만 먼저 작성합니다.',
                '기본 경로에서는 사용하지 않습니다. --separate-plan을 켜면 선택과 작성을 분리하여 추가 호출의 이득과 비용을 비교할 수 있습니다.'),
}
STAGES = {
    'structure_model_call': '구조 분석 응답 받기', 'structure_validation': '구조·위치 기록 검사',
    'meaning_model_call': '의미·관계 분석 응답 받기', 'meaning_validation': '의미·관계 기록 검사',
    'retrieval': 'KG 조건 조회', 'writer_model_call': '문장 초안 받기',
    'writer_validation': '초안의 후보 번호·누락 기록 검사',
    'reviewer_model_call': '초안 검토 응답 받기', 'review_validation': '검토 근거 확인',
    'revision_model_call': '수정 문장 받기', 'revision_validation': '수정 문장 기록 검사',
    'completed': '전체 처리 종료',
}


def stage_label(stage):
    return STAGES.get(stage, stage or '기록 없음')


def esc(value):
    return html.escape(str(value), quote=True)


def read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default


def table(headers, rows):
    return '<div class="tablewrap"><table><thead><tr>' + ''.join('<th>' + esc(h) + '</th>' for h in headers) + \
        '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + str(c) + '</td>' for c in row) + '</tr>' for row in rows) + \
        '</tbody></table></div>'


def plain(value):
    if value is None:
        return '기록 없음'
    if isinstance(value, list):
        return ', '.join(str(x) for x in value) if value else '없음'
    return str(value)


def prompt_blocks(prompts, prefix=''):
    blocks = []
    for key in ['structure', 'meaning', 'writer', 'reviewer', 'planner']:
        if key not in prompts:
            continue
        label, task, reason = ROLES[key]
        blocks.append('<details><summary>' + esc(prefix + label) + ' — 실제 지시문 전체</summary><p>' +
                      esc(reason) + '</p><div class="prompt">' + esc(prompts[key]) + '</div></details>')
    return ''.join(blocks)


def decision_markdown():
    """Render the short local decision note without embedding Markdown as JSON/code."""
    path = HERE / 'DECISIONS.md'
    if not path.exists():
        return '<p>검토 반영 문서가 아직 없습니다. 검토 완료로 표시하지 않습니다.</p>'
    text = path.read_text(encoding='utf-8')
    sections = []
    for block in re.split(r'\n\s*\n', text.strip()):
        if block.startswith('|'):
            lines = block.splitlines()
            cells = [[esc(c.strip()) for c in line.strip().strip('|').split('|')] for line in lines]
            if len(cells) > 2:
                sections.append(table([html.unescape(x) for x in cells[0]], cells[2:]))
        elif block.startswith('#'):
            sections.append('<h3>' + esc(block.lstrip('#').strip()) + '</h3>')
        else:
            escaped = esc(block)
            escaped = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', escaped)
            sections.append('<p>' + escaped.replace('\n', '<br>') + '</p>')
    return ''.join(sections)


def knowledge_rows(record_dir):
    selected = read(record_dir / 'selected_knowledge.json', [])
    output = []
    for item in selected:
        form_strings = []
        for form in item.get('forms', []):
            if isinstance(form, dict):
                form_strings.append(str(form.get('form', '')))
            else:
                form_strings.append(str(form))
        output.append([esc(item.get('source_text', item.get('unit_id', ''))),
                       esc(item.get('action_id', '')) + '<br><small>' + esc(item.get('rule_id', '')) + '</small>',
                       esc(item.get('instruction', '')), esc(', '.join(x for x in form_strings if x) or '별도 형태 기록 없음'),
                       esc(plain(item.get('preserve', [])))])
    return output


def case_html(row, result, run, index):
    rid = row['id']
    rd = run / 'private/records' / rid
    draft = read(rd / 'writer/parsed.json', {})
    revision = read(rd / 'revision/parsed.json', {})
    review = read(rd / 'reviewer/parsed.json', {})
    packet = read(rd / 'retrieval_packet.json', {})
    draft_text = result.get('draft_text') or draft.get('output_text')
    final_text = result.get('output_text') if result.get('pipeline_completed') else None
    selected = read(rd / 'selected_knowledge.json', None)
    delivered = len(selected) if isinstance(selected, list) else None
    final_state = result.get('output_state', '기록 없음')
    states = {'revision_written_not_rechecked': '수정본 작성 완료 · 수정 후 의미 재검토 없음',
              'draft_reviewed': '초안 작성과 검토 완료 · 사람 평가 전',
              'draft_review_unreliable': '출력은 있으나 검토 근거에 오류가 있음',
              'draft_review_unverified': '출력은 있으나 검토 완료를 확인하지 못함',
              'draft_review_unreliable': '초안은 있음 · 검토 근거 일부 또는 전체가 유효하지 않음',
              'pipeline_failed_draft_preserved': '중간 실패 · 초안만 보존',
              'no_draft_available': '초안 없음'}
    state = '미시도' if not result else states.get(final_state, result.get('status', '기록 없음'))
    parts = ['<details class="case"><summary>' + esc(rid) + ' · ' + esc(state) + '</summary>',
             '<div class="sentences"><div><b>표준어 원문</b><p>' + esc(row.get('text', '')) + '</p></div>',
             '<div><b>Qwen 초안</b><p>' + esc(draft_text or '작성 결과 없음') + '</p></div>',
             '<div><b>최종 출력</b><p>' + esc(final_text or '최종 출력 없음 — 초안을 대신 채우지 않았습니다.') + '</p></div></div>']
    if revision.get('output_text') and not final_text:
        parts.append('<p class="warn"><b>완료 처리되지 않은 수정 응답:</b> ' + esc(revision['output_text']) + '</p>')
    parts.append('<p><b>작성자에게 전달된 KG 후보:</b> ' +
                 ('기록 없음' if delivered is None else str(delivered) + '개') +
                 ('. 0개인 경우에도 모델 자체 지식으로 작성할 수 있으며, 원문 유지를 코드가 강제하지 않습니다.' if delivered == 0 else '') + '</p>')
    decisions = draft.get('decisions', [])
    if decisions:
        decision_rows = []
        for d in decisions:
            decision_rows.append([esc(d.get('action_id', '')), esc(plain(d.get('decision', d.get('status', '기록 없음')))),
                                  esc(plain(d.get('reason', ''))), esc(plain(d.get('keep', d.get('preserve', ''))))])
        parts.append('<details><summary>초안에서 후보를 고른 이유</summary>' +
                     table(['후보 번호', '적용 판단', '이유', '보존할 내용'], decision_rows) + '</details>')
    if delivered:
        parts.append('<details><summary>실제 전달한 지식 읽기</summary>' +
                     table(['원문 위치', '후보와 규칙 ID', '변환 안내', '표현 후보', '보존 정보'], knowledge_rows(rd)) + '</details>')
    omissions = packet.get('delivery_omissions', [])
    if omissions:
        reasons = {'analysis_disagreement': '분석 담당자 사이에 구조 해석이 달랐음',
                   'delivery_character_budget': '전달 길이 상한',
                   'unrefined_reference_top3_policy': '미정제 참고 검색의 표시 제한'}
        parts.append('<details><summary>전달하지 않은 항목과 이유 (' + str(len(omissions)) + '개)</summary>' +
                     table(['대상', '이유'], [[esc(o.get('rule_id', o.get('source_id', o.get('unit_id', '')))),
                           esc(reasons.get(o.get('reason'), o.get('reason', '기록 없음')))] for o in omissions]) + '</details>')
    issues = review.get('issues', [])
    if issues:
        parts.append('<details open><summary>Qwen 검토자가 지적한 내용 — 사람의 확정 판정 아님</summary>' +
                     table(['원문 근거', '출력 근거', '문제', '수정 방향'],
                           [[esc(i.get('source_quote', '')), esc(i.get('output_quote') or '해당 구절 누락'),
                             esc(i.get('problem', i.get('issue', i.get('description', '')))),
                             esc(i.get('suggestion', i.get('fix', i.get('recommendation', i.get('correction', '')))))] for i in issues]) + '</details>')
    elif review:
        parts.append('<p>검토 응답에 구체적 지적이 없습니다. 이것만으로 자연스러움이나 정확성을 보장하지 않습니다.</p>')
    if result.get('error_type'):
        parts.append('<p class="warn">중단 위치: ' + esc(stage_label(result.get('current_pipeline_stage'))) +
                     ' · 오류 종류: ' + esc(result['error_type']) + '</p>')
        call_slot = result.get('last_call_slot')
        meta = read(rd / str(call_slot) / 'meta.json', {}) if call_slot else {}
        if meta.get('finish_reason') == 'length':
            parts.append('<p>서버는 응답했지만, 해당 응답이 허용된 출력 길이에 도달해 끝나지 못했습니다. '
                         '이 기록의 출력 토큰은 ' + esc(meta.get('usage', {}).get('completion_tokens', '기록 없음')) +
                         '개입니다. 완성되지 않은 응답을 정상 검토 결과로 사용하지 않았습니다. 연결 실패나 전체 입력 길이 초과와는 구분해야 합니다.</p>')
    if result:
        parts.append('<p class="muted">호출 시도 ' + esc(result.get('api_attempts', '기록 없음')) + '회 · 입력 처리시간 ' +
                     esc(result.get('total_seconds', '기록 없음')) + '초. 내용의 품질 점수가 아닙니다.</p>')
    parts.append('</details>')
    return ''.join(parts)


def first_run_observations(run):
    if run.name == '20261107T063055332251Z_qwen_multi_development':
        return '<div class="warn"><b>재확인의 결론:</b> 최종 처리4/6건이며 방언 품질 통과4건이 아닙니다. 네 출력의 전달 KG 후보는 모두0개였습니다. 빈 후보 번호 오류는 이번에 발생하지 않았지만, 요청 문장은 의미 워커의 허용값 오류로 더 앞 단계에서 중단됐고, 마지막 문장은 검토 응답이 반복되며 출력 한도에 도달했습니다. 높임 손실도 남았습니다. 따라서50건으로 확대하지 않습니다.</div><p>고친 것은 빈 후보 목록의 응답 형식과 검토 작업 목적 두 가지입니다. 문법 분석 지시·KG·모델 설정은 고정했습니다. 한 번의 재실행과 두 요소 변경이므로 숫자 차이를 각 수정의 인과 효과나 품질 개선으로 단정하지 않습니다.</p><p>다음 보완은 형태 분석과 KG 조건의 표기 연결, 그리고 검토자의 필드 해석·오류 단계 구분입니다. 예를 들어 past_form=present는 현재시제가 아니라 과거 형태가 <b>존재함</b>을 뜻하는데, 검토자가 이를 잘못 읽었습니다. 지금은 워커를 더 늘릴 단계가 아닙니다.</p>'
    if run.name != '20261107T061957241164Z_qwen_multi_development':
        return ''
    return '''<div class="warn"><b>첫 실행의 핵심:</b> 6개 모두 초안은 생겼지만, 끝까지 기록된 최종 출력은 3개입니다. 그 3개가 좋은 방언이라는 뜻은 아닙니다. 예를 들어 ‘보냈어요’를 ‘보냈어’로 바꾸어 상대 높임을 잃은 출력도 포함됩니다.</div>
<h3>지식이 있었는데 전달되지 않은 사례: MULTI_DEV02</h3>
<p>원문은 ‘나는 어제 동생한테 편지를 보냈어요.’입니다. 구조 워커는 ‘보냈어요’를 나누면서 과거 형태 ‘었’에 형용사를 만드는 접미사라는 품사표(XSA)를 붙였습니다. 동시에 다른 칸에는 과거 선어말 어미가 있다고 기록했습니다. 한 분석 안에서 두 설명이 서로 맞지 않았습니다.</p>
<div class="flow"><span class="box">구조 기록이 서로 불일치</span><span class="arrow">→</span><span class="box">해당 평서 규칙은 조회됨</span><span class="arrow">→</span><span class="box">분석 충돌로 적용 보류</span><span class="arrow">→</span><span class="box">작성자에게 KG 후보 0개</span></div>
<p>실제 조회 기록에는 평서 규칙 <small>SEM_DECL_HAEYE_EO</small>가 조건을 만족했다고 나옵니다. 그러나 후속 검사에서 구조 기록의 불일치 때문에 전달이 보류됐습니다. 따라서 이 사례는 ‘KG에 그 규칙이 없다’와 다릅니다. 후보가 없어진 뒤 작성자는 자체 지식으로 ‘보냈어’라는 초안을 썼습니다. 높임 손실까지 분석 오류 하나가 전부 유발했다고 확정할 수는 없지만, <b>지식 전달이 끊긴 위치</b>는 확인할 수 있습니다.</p>
<h3>서로 다른 세 종류의 문제를 구분했습니다</h3>''' + table(['사례', '실제 기록', '무엇을 고쳐야 하나'], [
        ['MULTI_DEV01·03', '전달 후보가 0개인데 작성자가 없는 후보 번호 “none”을 적음. 초안 기록 검사에서 중단.', '후보가 0개일 때는 판단 목록과 사용 번호를 반드시 빈 목록으로 반환하도록 응답 형식을 맞춤. 방언 문장 자체가 나쁘다는 이유로 차단한 것이 아님.'],
        ['MULTI_DEV04·05', '검토자가 원문에 있는 “그”를 추가된 말이라고 지적하거나, 방언으로 바꾸는 작업 자체를 잘못으로 지적함.', '검토자도 틀릴 수 있음. 인용 구절 존재 검사는 지적의 뜻이 맞는지까지 보장하지 않으므로 작업 목적과 지적 근거를 별도로 확인.'],
        ['MULTI_DEV06', '검토 응답은 HTTP 200으로 왔지만 4,096 출력 토큰에서 종료됨. 같은 구문을 반복한 채 JSON이 끝나지 않음.', '서버 접속 실패가 아님. 반복 생성과 출력 한도에 걸린 검토 실패. 초안은 남기되 최종 결과로 대신 채우지 않음.']]) + '''
<p>첫 실행의 ‘최종 출력 3개’는 프로그램의 마지막 단계까지 도착한 수입니다. ‘검토 유효’도 인용 구절 등의 형식 검사를 통과했다는 뜻이며, 검토 의견이 언어적으로 옳다는 인증이 아닙니다. 이 구별 때문에 숫자만 보고 성공률을 높게 해석하면 안 됩니다.</p>'''


def run_section(run, index):
    config = read(run / 'config.json', {})
    metrics = read(run / 'metrics.json', {})
    results = read(run / 'private/results.json', [])
    input_path = run / 'private/inputs.jsonl'
    inputs = [json.loads(line) for line in input_path.read_text(encoding='utf-8-sig').splitlines() if line.strip()] if input_path.exists() else []
    byid = {r['id']: r for r in results}
    frozen_prompts = {p.stem: p.read_text(encoding='utf-8') for p in (run / 'prompts').glob('*.txt')}
    prompt_equal = bool(frozen_prompts) and all(PROMPTS.get(k) == v for k, v in frozen_prompts.items())
    stop = metrics.get('stop_reason')
    rows = [
        ['방식', esc('계획을 분리한 비교 경로: 5역할, 최대6호출' if config.get('separate_plan') else '기본 경로: 4역할, 최대5호출')],
        ['계획한 입력 / 시도한 입력', esc(str(config.get('input_count', len(inputs))) + ' / ' + str(metrics.get('records', len(results))))],
        ['끝까지 처리되어 최종 파일에 기록된 입력 — 품질 통과 수 아님', esc(metrics.get('final_available_records', metrics.get('valid_output_records', '집계 없음')))],
        ['초안만 남은 입력', esc(metrics.get('draft_only_records', '집계 없음'))],
        ['호출 시도 / 실패 응답', esc(str(metrics.get('api_attempts', '집계 없음')) + ' / ' + str(metrics.get('api_failures', '집계 없음')))],
        ['입력 / 출력 토큰', esc(str(metrics.get('reported_usage', {}).get('prompt_tokens', '집계 없음')) + ' / ' + str(metrics.get('reported_usage', {}).get('completion_tokens', '집계 없음')))],
        ['토큰 집계 범위', esc('전체 호출의 보고값 확보' if metrics.get('usage_completeness') == 'complete' else '일부 또는 전부 미확보 — 보고된 값만 합산')],
        ['전체 경과시간', esc(str(metrics.get('wall_seconds', '집계 없음')) + '초')],
        ['종료 사유', esc(stop or ('입력 처리 완료' if metrics else '실행 기록 미완료'))],
        ['현재 지시문과 실행 당시 지시문', esc('일치' if prompt_equal else '다르거나 확인되지 않음 — 아래 실행 당시 지시문을 기준으로 해석')],
    ]
    failure = read(run / 'failure.json', {})
    setup = '<p class="warn">실행 준비 단계에서 멈췄습니다. 오류 종류: ' + esc(failure.get('error_type', '기록 없음')) + '. 생성 성공이나 서버 자체 결함으로 해석하지 않습니다.</p>' if stop == 'setup_failure' else ''
    overview = []
    for row in inputs:
        r = byid.get(row['id'], {})
        rd = run / 'private/records' / row['id']
        selected = read(rd / 'selected_knowledge.json', None)
        draft = read(rd / 'writer/parsed.json', {})
        overview.append([esc(row['id']), esc(row.get('text', '')),
                         esc(draft.get('output_text') or '초안 없음'),
                         esc(r.get('output_text') if r.get('pipeline_completed') else '최종 출력 없음'),
                         esc(len(selected) if isinstance(selected, list) else '조회/전달 기록 없음'),
                         esc('전체 처리 종료 · 품질 평가 전' if r.get('pipeline_completed') else
                             stage_label(r.get('current_pipeline_stage')) if r else '미시도')])
    return '<section><h2>실제 실행 ' + str(index + 1) + '</h2><p class="muted">' + esc(run.name) + '</p>' + \
        table(['확인 항목', '기록된 결과'], rows) + setup + \
        '<p>아래 숫자는 작동과 비용의 기록입니다. 방언 정확도·자연스러움 평가 결과가 아닙니다.</p>' + \
        first_run_observations(run) + \
        '<h3>입력별로 한눈에 비교</h3>' + table(['ID', '원문', 'Qwen 초안', '최종 기록', '전달 KG 후보 수', '도착/중단 위치'], overview) + \
        ''.join(case_html(row, byid.get(row['id'], {}), run, index) for row in inputs) + \
        ('<details><summary>이 실행에 실제 사용한 지시문</summary>' + prompt_blocks(frozen_prompts) + '</details>' if frozen_prompts else '') + '</section>'


def build(runs):
    private = HERE / 'private'
    private.mkdir(exist_ok=True)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds')
    role_rows = [[esc(ROLES[k][0]), esc(ROLES[k][1]), esc(ROLES[k][2])] for k in ['structure', 'meaning', 'writer', 'reviewer']]
    prompts_md = '# Qwen 워커별 실제 지시문과 설계 이유\n\n2026-11-07. 기본4역할·필요시 작성자 수정1회. Kiwi를 사용하지 않는 새 실행 경로.\n\n'
    for key in ['structure', 'meaning', 'writer', 'reviewer', 'planner']:
        prompts_md += '## ' + ROLES[key][0] + '\n\n' + ROLES[key][2] + '\n\n```text\n' + PROMPTS[key] + '\n```\n\n'
    (HERE / 'prompts.md').write_text(prompts_md, encoding='utf-8')
    neo = read(ROOT / 'experiments/analyses/semantic_reachability_20261107/neo4j_latest.json', {})
    neo_detail = '새 버전 ' + str(neo.get('nodes', '미확인')) + '개 노드·' + str(neo.get('edges', '미확인')) + '개 관계'
    runs_html = ''.join(run_section(run, i) for i, run in enumerate(runs)) if runs else \
        '<section><h2>실제 생성 결과</h2><p class="warn">이 보고서에 연결한 실행 기록이 아직 없습니다. 설계를 구현했다는 사실과 실제 모델 생성 성공을 구분해야 합니다. 생성 성공률이나 품질 점수는 표시하지 않습니다.</p></section>'
    screenshot = '<details><summary>Neo4j 연결 성공 화면</summary><img src="neo4j_connected.png" alt="Neo4j 연결됨 상태를 확인한 화면"></details>' if (private / 'neo4j_connected.png').exists() else ''
    page = '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Qwen 분업 파이프라인 — 무엇을 나누었고 어떻게 확인하나</title>
<style>body{font-family:"Malgun Gothic",Arial,sans-serif;color:#20354a;background:#f4f7fa;line-height:1.8;max-width:1080px;margin:32px auto;padding:0 22px}h1{font-size:30px;line-height:1.4}h2{font-size:23px}h3{font-size:18px}section{background:white;border:1px solid #dce5ee;border-radius:12px;padding:24px;margin:20px 0}.lead{font-size:19px}.muted,small{font-size:13px;color:#637285}.warn{padding:12px;background:#fff3da;border-left:4px solid #d49a2b}.good{padding:12px;background:#eaf6f1}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #dce5ee;padding:10px;text-align:left;vertical-align:top}th{background:#edf3fa}details{border:1px solid #dce5ee;border-radius:8px;padding:12px;margin:12px 0}summary{font-weight:700;cursor:pointer}.prompt{white-space:pre-wrap;background:#f8fafc;padding:16px;line-height:1.9;font-size:15px;overflow-wrap:anywhere}.flow{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:22px 0}.box{background:#eaf1fb;border:1px solid #c8d9ee;border-radius:8px;padding:12px;text-align:center;min-width:110px}.box.code{background:#ecf5ee}.arrow{color:#71849a}.sentences>div{border-left:4px solid #6f92b8;padding:8px 16px;margin:10px 0;background:#f8fafc}.sentences p{margin:4px 0}a{color:#175ba2}img{max-width:100%;height:auto}button{font:inherit;padding:6px 12px;cursor:pointer}@media print{body{background:white;margin:0}section{border:0;padding:12px 0}details{break-inside:avoid}button{display:none}.flow{font-size:12px}}</style></head><body>
<h1>한 모델에게 한꺼번에 맡기던 일을 나누었습니다</h1><p class="lead">Qwen이 구조를 찾고, 뜻을 판단하고, KG 지식을 골라 문장을 쓰고, 다른 호출에서 초안을 검토합니다. 최종 문장은 계속 Qwen이 작성합니다.</p>
<p class="muted">작성 시각: ''' + esc(now) + ''' · 연구 구현과 실행 기록 안내 · 자연스러움의 독립 평가 보고서가 아닙니다.</p>
<section><h2>1. 이번에 바꾼 것과 그대로 둔 것</h2><p>새 실행 경로에서는 Kiwi를 부르지 않습니다. 구조 분석 워커가 어간·어미·절을 분석합니다. 코드는 원문 속 위치와 식별자가 실제로 존재하는지 확인하지만, 문법의 뜻을 대신 판단하거나 방언 문장을 몰래 고치지 않습니다.</p>
<p>출처·검토 기록은 이미 실행 그래프 밖으로 분리했습니다. 불필요한 중복 설명은 제거했고, 실제 적용 조건·보존해야 할 뜻이 담긴 설명은 남겨 두었습니다. 이번 파이프라인 변경이 KG의 모든 문법 내용을 정제 완료했다는 뜻은 아닙니다.</p>
<p class="good">Neo4j 로그인 인증 문제를 저장된 로컬 계정으로 복구했습니다. 암호 변경이나 인증 해제는 하지 않았습니다. ''' + esc(neo_detail) + '''를 이전 버전과 구분해 볼 수 있습니다. <a href="http://localhost:7474/browser/">Neo4j 열기</a></p>''' + screenshot + '''
<p>현재 실행기는 파일에 저장된 실제 KG 조건·관계를 읽습니다. Neo4j는 같은 데이터를 시각적으로 탐색하는 사본입니다. 화면에 연결되었다는 사실과 조회 엔진을 Neo4j로 바꾸었다는 것은 다릅니다.</p></section>
<section><h2>2. 전체 흐름과 역할</h2><div class="flow"><span class="box">표준어 원문</span><span class="arrow">→</span><span class="box">① 구조 분석</span><span class="arrow">→</span><span class="box">② 의미·관계</span><span class="arrow">→</span><span class="box code">코드: KG 조건 조회</span><span class="arrow">→</span><span class="box">③ 선택·문장 작성</span><span class="arrow">→</span><span class="box">④ 별도 검토</span></div><p><b>기본은 4역할·4호출입니다.</b> 검토자가 구체적인 생성 오류를 찾으면 작성자가 최대 한 번 수정하여 총5호출입니다. 수정본을 다시 의미 검토하지 않았다는 사실을 결과에 표시합니다. 단어 수만큼 워커를 늘리지 않습니다.</p>''' + table(['담당', '하는 일', '이렇게 나눈 이유'], role_rows) + '''
<p>비교 옵션은 ② 다음에 ‘별도 계획’을 넣어 5역할·기본5호출, 수정 시 최대6호출로 실행합니다. 역할 수가 많을수록 더 좋다는 결론은 내리지 않았습니다. 같은 입력·KG·모델로 비용과 품질을 비교할 다음 후보입니다.</p>
<p><b>워커</b>는 같은 Qwen 모델을 서로 다른 지시문으로 호출하는 역할입니다. 독립적으로 학습한 모델 여러 개가 투표하는 구조는 아닙니다. 같은 오해를 공유할 가능성이 남아 있습니다.</p></section>
<section><h2>3. 어떤 정보가 다음 담당자에게 가나?</h2>''' + table(['전달 구간', '전달하는 내용', '확인하거나 제한하는 내용'], [
    ['구조 → 의미', '원문, 원문에서의 위치, 어간·어미 묶음, 절과 단위 ID', '구조를 정답으로 고정하지 않음. 다음 워커의 수정 제안은 별도로 보존'],
    ['의미 → KG', '실제 단위별 질문/평서, 시제·높임·부정, 조사·절·보조용언 관계', '조건이 맞는지 코드가 대조. 미확정·관계 불일치도 기록'],
    ['KG → 작성', '이번 위치에 맞는 표현·결합 안내·지킬 내용과 후보 번호', '출처·검토 이력은 제외. 미정제 참고 검색은 기록에 남기지만 작성 지시로 전달하지 않음'],
    ['작성 → 검토', '원문 전체, 분석, 전달 지식, 실제 작성 초안', '정답 번역을 넣지 않음. 지적마다 원문/출력의 실제 구절을 요구'],
    ['검토 → 수정', '구체적인 오류 근거와 복구할 내용', '수정은 최대1회. 초안·수정 실패를 보존하며 코드가 원문으로 대신 채우지 않음']]) + '''
<p>KG 후보가 0개여도 원문 전체를 유지하도록 강제하지 않습니다. Qwen이 자체 지식으로 바꾸면 그 사실을 별도로 기록합니다. 따라서 출력이 좋아져도 곧바로 KG 덕분이라고 단정할 수 없습니다.</p></section>
<section><h2>4. 워커에게 준 실제 지시문</h2><p>아래를 열면 설명용 요약이 아닌 현재 코드의 지시문 전체를 볼 수 있습니다. 실행 당시 내용이 달라졌다면 각 실행 결과 아래에 보존된 지시문을 따로 표시합니다.</p>''' + prompt_blocks(PROMPTS) + '''</section>
<section><h2>5. 검토자와 논의하여 정한 내용</h2><p>역할 분담은 최적이라고 가정한 답이 아니라 검토를 거쳐 선택한 첫 구현입니다. 아래는 채택·미채택 이유를 남긴 실제 결정 기록입니다.</p><details><summary>검토 반영 결정 전체 읽기</summary>''' + decision_markdown() + '''</details></section>
''' + runs_html + '''
<section><h2>6. 아직 확인하지 못한 것과 다음 작업</h2><p>구조화된 응답을 받았다고 분석이 정확한 것은 아닙니다. 다른 호출이 검토했다고 방언이 자연스러운 것도 아닙니다. 지금 확인할 것은 원문에서 필요한 정보가 어디서 처음 빠지거나 달라졌는지입니다.</p>''' + table(['다음 순서', '끝나는 기준', '예상과 다를 때'], [
    ['새 개발 문장에서 구조·의미·지식 전달·출력을 함께 대조', '잘못된 위치/관계/시제/높임이 처음 생긴 단계를 실제 기록으로 특정', '반복 결함이 있으면 50건으로 확대하지 않고 해당 연결부터 보완'],
    ['같은 입력·KG·모델에서 기본 분업과 별도 계획 방식 비교', '호출 수·토큰·시간과 사람의 품질 판정을 함께 확보', '추가 역할의 효과가 없으면 단순한 구조 유지'],
    ['기존50 회귀와 새로운 독립 평가 문장 분리', '기존 문제가 재발하는지와 새로운 문장에서도 작동하는지 구별', '노출된50을 독립 최종 성능으로 주장하지 않음'],
    ['같은 지식의 문서 검색·조건표·그래프 비교', '지식량과 생성 조건을 맞춰 KG의 실제 기여와 비용을 평가', '그래프가 우월하지 않거나 동등해도 그대로 보고']]) + '''
<p>언어 해석이 충돌하거나 연구 목표를 바꾸는 결정은 사용자에게 요청합니다. 일반 코드 오류와 합의된 검사는 반복 승인 없이 진행할 수 있습니다. 사람 평가는 작동 오류를 먼저 줄인 뒤 자연스러움과 의미·높임 보존을 확인하는 데 사용합니다.</p></section>
<p class="muted">원시 실행은 각 고유 Run ID 폴더에 보존됩니다. 이 보고서를 다시 만들어도 과거 입력·요청·응답은 덮어쓰지 않습니다.</p></body></html>'''
    report = private / 'report.html'
    report.write_text(page, encoding='utf-8')
    (HERE / 'report_latest.json').write_text(json.dumps({'report': str(report.relative_to(ROOT)),
        'runs': [str(run.relative_to(ROOT)) if run.is_relative_to(ROOT) else str(run) for run in runs],
        'prompt_sha256': {k: sha(v.encode()) for k, v in PROMPTS.items()},
        'independent_quality_evaluation': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(report), 'prompts': str(HERE / 'prompts.md'), 'linked_runs': len(runs)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='append', default=[], type=Path, help='Saved run directory; repeat for multiple runs')
    args = parser.parse_args()
    runs = [p.resolve() for p in args.run]
    if any(not p.is_dir() for p in runs):
        parser.error('Every --run must be an existing directory')
    build(runs)
