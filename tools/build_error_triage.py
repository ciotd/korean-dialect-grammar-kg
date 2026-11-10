"""Read frozen runs and existing human ratings; create a reproducible diagnosis ledger.

No model calls, KG mutation, quality-score inference, or writes to source runs.
Manual screening notes are separate from measured facts and human judgments.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

BATCH = '20261028T011829489985Z'
ARMS = ('single', 'multi')
STATUS_KO = {'no_output': '출력 없음', 'unchanged': '원문 동일', 'changed': '변경 출력'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    out = args.output or root / 'experiments/analyses/error_triage_20261029/private'
    if out.exists() and any(out.iterdir()):
        raise SystemExit('Output exists. Use a new --output directory; do not overwrite diagnosis history.')
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def rel(path):
        return path.relative_to(root).as_posix()

    def load(path):
        hashes[rel(path)] = digest(path)
        return json.loads(path.read_text(encoding='utf-8'))

    def optional(path, default):
        return load(path) if path.is_file() else default

    def save(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    historical = root / 'experiments/analyses/grammar_cards_20261028/private'
    ratings = load(historical / 'ratings.json')
    key = load(historical / 'blind_key.json')
    tasks = {x['id']: x for x in load(historical / 'blind_review.json')}
    human = {}
    legacy_human = []
    for rating in ratings['ratings']:
        assignment = key[rating['blind_id']]
        value = {k: v for k, v in rating.items() if k != 'blind_id'}
        value.update(reviewer=ratings['reviewer'], saved_utc=ratings['saved_utc'],
                     source='existing_human_rating', run_id=assignment['run_id'],
                     input_id=assignment['input_id'], arm=assignment['condition'])
        if assignment['condition'] in ARMS:
            pair = (assignment['input_id'], assignment['condition'])
            assert pair not in human, 'Duplicate human rating for an output'
            task = tasks[assignment['input_id']]
            value['rated_output'] = next(a['output'] for a in task['answers'] if a['blind_id'] == rating['blind_id'])
            human[pair] = value
        else:
            legacy_human.append(value)
    annotations = load(root / 'experiments/analyses/error_triage_20261029/screening_notes.json')
    card_file = root / 'knowledge/authored/kg_cards_20261028_v2/cards.json'
    cards = {c['id']: c for c in load(card_file)['cards']}
    rows = []
    inputs = {}
    metric_sources = {}
    for arm in ARMS:
        run = root / f'experiments/runs/{BATCH}_cards_{arm}_regression'
        results = load(run / 'private/results.json')
        metric_sources[arm] = load(run / 'metrics.json')
        assert len(results) == 50 and len({r['id'] for r in results}) == 50
        inputs[arm] = {r['id']: r['input_text'] for r in results}
        frozen_code = run / 'code_snapshot/kg_runtime/card_pipeline.py'
        code = frozen_code.read_text(encoding='utf-8')
        hashes[rel(frozen_code)] = digest(frozen_code)
        assert "if not e['rule_ids'] or not set(e['rule_ids'])<=ids" in code
        for raw in results:
            ident = raw['id']
            folder = run / 'private/records' / ident
            original = load(folder / 'result.json')
            assert original['input_text'] == raw['input_text']
            assert original['output_text'] == raw['output_text']
            packet = load(folder / 'reference_packet.json')
            analysis = load(folder / 'analysis_call/parsed.json')
            final = optional(folder / 'final_plan.json', {'edits': []})
            draft = optional(folder / 'agent_call/parsed.json', {'edits': []})
            retrieval = load(folder / 'retrieval_raw.json')
            text = raw['output_text']
            outcome = 'no_output' if text is None else 'unchanged' if text == raw['input_text'] else 'changed'
            failure = None
            if outcome == 'no_output':
                length_calls = []
                for meta_path in sorted(folder.glob('*_call/meta.json')):
                    meta = load(meta_path)
                    if meta.get('finish_reason') == 'length':
                        response = load(meta_path.with_name('response.json'))
                        content = response['choices'][0]['message'].get('content') or ''
                        length_calls.append({'stage': meta_path.parent.name,
                                             'trailing_whitespace': len(content) - len(content.rstrip()),
                                             'meta_path': rel(meta_path)})
                if length_calls:
                    failure = {'type': 'length_limit', 'label': '응답 길이 한도 도달', 'calls': length_calls}
                elif raw.get('error') == 'after_not_single_word':
                    value = optional(folder / 'generation_call/parsed.json', draft)
                    bad = [e for e in value.get('edits', [])
                           if not e.get('after', '').strip() or re.search(r'[\s.,!?…]', e['after'])]
                    assert bad
                    failure = {'type': 'single_word_contract', 'label': '한 어절 제한 위반', 'rejected_edits': bad,
                               'note': '실행 형식 위반이다. 해당 표현이 언어적으로 틀렸는지는 별도 판단한다.'}
                elif raw.get('error') == 'unretrieved_rule_reference':
                    allowed = {c['id'] for c in packet['cards']}
                    empty = [e['word_id'] for e in draft['edits'] if not e['rule_ids']]
                    missing = sorted({k for e in draft['edits'] for k in e['rule_ids'] if k not in allowed})
                    assert empty or missing
                    failure = {'type': 'empty_rule_ids' if empty and not missing else 'unknown_rule_ids',
                               'label': '수정 항목의 근거 카드 목록이 비어 있음' if empty and not missing else '전달 목록 밖 카드 사용',
                               'empty_word_ids': empty, 'missing_card_ids': missing,
                               'original_error': raw['error'], 'validator': rel(frozen_code)}
                else:
                    failure = {'type': 'unclassified_execution_error', 'label': raw.get('error', raw['status'])}
            known_human = human.get((ident, arm))
            if known_human:
                assert known_human['rated_output'] == text
            edits = final['edits']
            jamo = sorted(set(re.findall(r'[ㄱ-ㅎㅏ-ㅣ]', text or '')))
            used_ids = sorted({k for e in edits for k in e['rule_ids']})
            used_paths = [x for x in retrieval['paths'] if x['rule_id'] in used_ids]
            row = {'key': f'{ident}:{arm}', 'id': ident, 'arm': arm, 'run_id': run.name,
                   'input': raw['input_text'], 'output': text, 'outcome': outcome,
                   'original_status': raw['status'], 'failure': failure, 'human_rating': known_human,
                   'standalone_jamo': jamo, 'analysis': analysis, 'edits': edits,
                   'selected_cards': [cards[k] for k in used_ids], 'selected_graph_paths': used_paths,
                   'packet_card_count': len(packet['cards']), 'screening_notes': [],
                   'evidence': {'result': rel(folder / 'result.json'), 'analysis': rel(folder / 'analysis_call/parsed.json'),
                                'packet': rel(folder / 'reference_packet.json'),
                                'draft': rel(folder / 'agent_call/parsed.json'),
                                'final_plan': rel(folder / 'final_plan.json') if (folder / 'final_plan.json').is_file() else None}}
            for note in annotations['notes']:
                if row['key'] in note['cases']:
                    anchor = note.get('anchors', {}).get(row['key'])
                    if anchor:
                        actual = json.dumps({'input': row['input'], 'output': text, 'analysis': analysis,
                                             'edits': edits, 'draft': draft}, ensure_ascii=False)
                        assert anchor in actual, (row['key'], note['id'], 'missing evidence anchor')
                    row['screening_notes'].append({k: v for k, v in note.items() if k not in ('cases', 'anchors')})
            rows.append(row)
    assert inputs['single'] == inputs['multi']
    assert set(human) <= {(r['id'], r['arm']) for r in rows}
    all_keys = {r['key'] for r in rows}
    assert all(set(n['cases']) <= all_keys for n in annotations['notes'])
    for arm in ARMS:
        subset = [r for r in rows if r['arm'] == arm]
        assert sum(r['output'] is not None for r in subset) == metric_sources[arm]['valid_output_records']
        assert sum(r['outcome'] == 'changed' for r in subset) == metric_sources[arm]['changed_records']
    summary = {
        'batch': BATCH, 'input_count': 50, 'output_attempts': len(rows),
        'counts': {arm: dict(Counter(r['outcome'] for r in rows if r['arm'] == arm)) for arm in ARMS},
        'failure_counts': {arm: dict(Counter(r['failure']['type'] for r in rows if r['arm'] == arm and r['failure'])) for arm in ARMS},
        'unique_inputs_with_no_output': len({r['id'] for r in rows if r['outcome'] == 'no_output'}),
        'long_whitespace_failures': sum(any(x['trailing_whitespace'] >= 1000 for x in r['failure'].get('calls', [])) for r in rows if r['failure']),
        'human_ratings_existing_total': len(ratings['ratings']), 'human_ratings_current': len(human),
        'human_ratings_older': len(legacy_human), 'human_current_by_arm': dict(Counter(x['arm'] for x in human.values())),
        'human_current_low_scores_1_or_2': sum(x['naturalness'] in (1, 2) for x in human.values()),
        'outputs_without_human_rating': sum(r['output'] is not None and not r['human_rating'] for r in rows),
        'standalone_jamo_outputs': [r['key'] for r in rows if r['standalone_jamo']],
        'note': '실행 통계와 부분 사람 평가다. 무작위 표본이 아니며 전체 방언 정확도·방식별 우열을 계산하지 않는다.'}
    save('summary.json', summary)
    save('cases.json', {'batch': BATCH, 'review_mode': 'diagnosis_not_blind_evaluation', 'records': rows,
                        'legacy_human_context': legacy_human})
    # Neutral first-round review packets omit the lead's hypotheses and human ratings.
    packet_dir = out / 'review_packets'; packet_dir.mkdir()
    for ident in annotations['first_review_inputs']:
        neutral = []
        for arm in ARMS:
            r = next(x for x in rows if x['id'] == ident and x['arm'] == arm)
            folder = root / Path(r['evidence']['result']).parent
            packet = load(folder / 'reference_packet.json')
            neutral.append({'arm': arm, 'run_id': r['run_id'], 'input': r['input'], 'output': r['output'],
                            'original_status': r['original_status'], 'words': packet['words'], 'analysis': r['analysis'],
                            'supplied_cards': packet['cards'],
                            'draft': optional(folder / 'agent_call/parsed.json', None),
                            'worker_response': optional(folder / 'generation_call/parsed.json', None),
                            'final_edits': r['edits'], 'paths_for_selected_cards': r['selected_graph_paths'],
                            'evidence': r['evidence']})
        (packet_dir / f'{ident}.json').write_text(json.dumps({'id': ident, 'records': neutral}, ensure_ascii=False, indent=2), encoding='utf-8')
    def md(value):
        return str(value if value is not None else '출력 없음').replace('|', '\\|').replace('\n', '<br>')
    lines = ['# 최신 Single/Multi 오류 진단 대장', '', f'대상 배치: `{BATCH}` · 50개 입력 / 100개 시도',
             '', '이 대장은 실행 원본과 기존 사람 평가를 연결한 초기 진단이다. AI의 의심을 사람 정답으로 취급하지 않는다.',
             '재실험·KG 수정·추가 모델 호출은 수행하지 않았다. 두 독립 검토자의 실제 검토는 아직 시작하지 않았다.', '',
             '| 구분 | Single | Multi |', '|---|---:|---:|']
    for outcome in ('no_output', 'unchanged', 'changed'):
        lines.append(f'| {STATUS_KO[outcome]} | {summary["counts"]["single"].get(outcome,0)} | {summary["counts"]["multi"].get(outcome,0)} |')
    lines += ['', f'기존 사람 평가 {len(ratings["ratings"])}건 중 현재 두 방식 {len(human)}건, 이전 Single {len(legacy_human)}건. 현재 출력 중 미평가 {summary["outputs_without_human_rating"]}건.',
              '낮은 점수나 높은 점수를 전체 품질로 확대하지 않는다. 높은 점수에도 특정 어절 수정 의견이 함께 있을 수 있다.', '',
              '## 원인 설명 정정', '',
              '- Multi DEV026의 원래 오류 코드 `unretrieved_rule_reference`는 빈 카드 목록도 같은 코드로 처리한다. 실제 W2의 목록은 비어 있고 나머지 카드 ID는 모두 전달 목록에 있다. “전달하지 않은 카드 ID 사용”이라는 이전 보고서 해석을 정정한다.',
              '- 한 어절 제한 위반 4건은 언어적 오답 4건이라는 뜻이 아니다. 제한을 풀기만 하면 되는지도 별도 검증해야 한다. 실패한 초안 안에 다른 잘못된 지시가 함께 보인다.',
              '- DEV020 원문 유지에 대해 기존 평가자는 억양에 의해 방언성이 드러날 수 있다고 기록했다. 출력 유지와 무관하게 근거 카드 연결이 적절했는지는 별도로 검토한다.',
              '- 과거 현황 문서의 “사람 평가 없음”은 현재 저장 파일과 다르다. 현재 판단은 원본 ratings.json의 저장 시각과 이 대장의 해시를 기준으로 한다.', '',
              '## 초기 검토 메모', '', '| 항목 | 관찰/의심 | 판단 상태 | 우선 확인 단계 |', '|---|---|---|---|']
    for n in annotations['notes']:
        lines.append(f'| {md(n["title"])} | {md(n["observation"])} | {md(n["status"])} | {md(n["stage"])} |')
    lines += ['', '## 입력별 전체 결과', '', '기존 사람 점수는 원문 그대로 보존했다. 구체적인 수정 제안은 유일한 정답을 뜻하지 않는다.']
    for ident in inputs['single']:
        lines += ['', f'### {ident}', '', f'**입력:** {inputs["single"][ident]}', '', '| 방식 | 상태 | 실제 출력 |', '|---|---|---|']
        pair = [next(r for r in rows if r['id'] == ident and r['arm'] == arm) for arm in ARMS]
        for r in pair:
            lines.append(f'| {r["arm"]} | {STATUS_KO[r["outcome"]]} | {md(r["output"])} |')
        for r in pair:
            lines += ['', f'**{r["arm"]} 확인 사항**', '']
            if r['failure']: lines.append('- 실행 실패: ' + r['failure']['label'])
            if r['standalone_jamo']: lines.append('- 완성 문장에 단독 자모가 남음: ' + ', '.join(r['standalone_jamo']))
            if r['human_rating']:
                h=r['human_rating'];lines.append(f'- 기존 사람 판단: 자연스러움 {h["naturalness"]}/5 · 의미 {h["meaning"]} · 의견: {md(h.get("comment") or "별도 의견 없음")}')
            else: lines.append('- 기존 사람 판단 없음. 정상 출력으로 확정하지 않음.')
            for n in r['screening_notes']: lines.append(f'- {n["title"]} [{n["status"]}]: {n["observation"]}')
            for e in r['edits']: lines.append(f'- 수정: `{e["before"]}` → `{e["after"]}` · 카드: ' + ', '.join(e['rule_ids']))
            lines.append('- 원본: `' + r['evidence']['result'] + '`')
    (out / 'casebook.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    hashes[rel(Path(__file__).resolve())] = digest(Path(__file__).resolve())
    assert all(digest(root / name) == sha for name, sha in hashes.items()), 'Source changed during diagnosis'
    validation = {'source_files_unchanged': True, 'source_files_checked': len(hashes), 'unique_output_keys': len(all_keys),
                  'input_sets_identical': True, 'result_files_match_aggregate': True, 'metrics_match_outcomes': True,
                  'human_rating_outputs_match': len(human), 'annotation_anchors_checked': True,
                  'model_calls': 0, 'reviewers_dispatched': False}
    save('validation.json', validation)
    save('manifest.json', {'created_utc': datetime.now(timezone.utc).isoformat(), 'batch': BATCH,
                           'source_sha256': hashes, 'outputs_sha256': {f.relative_to(out).as_posix(): digest(f) for f in out.rglob('*') if f.is_file()},
                           'reviewer': 'lead_codex_initial_screening', 'linguistic_ground_truth': False})
    print(json.dumps({'output': str(out), 'summary': summary, 'validation': validation}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
