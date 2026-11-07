"""Run the versioned Qwen-only analysis/generation pipeline; no Kiwi dependency.

Every HTTP attempt passes a shared deadline/call-budget guard. This runner does
not alter KG or substitute a Python-composed sentence for the model's output.
"""
import argparse
import collections
import datetime as dt
import platform
from pathlib import Path
import re
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'local/python')]
from kg_pipeline.integrated import IntegratedReader, require
from kg_pipeline.io import Qwen, read, save, sha, dumps, load_jsonl
from kg_pipeline.separated_graph import FORMAT as SEPARATED_FORMAT, restore
from kg_pipeline.runner import register_run
from research_management.work import WorkStore

PROGRAM_ID = 'qwen_multi_20261107'
DEFAULT_MAX_CALLS_PER_INPUT = 5


class RunLimitReached(RuntimeError):
    """A local limit stopped a call before it was sent to the server."""


class GuardedClient:
    def __init__(self, client, deadline, max_calls, max_calls_per_input=DEFAULT_MAX_CALLS_PER_INPUT):
        self.client = client
        self.deadline = deadline
        self.max_calls = max_calls
        self.max_calls_per_input = max_calls_per_input
        self.calls_started = 0
        self.input_calls = 0
        self.last_stage = 'not_started'
        self.last_slot = None

    def begin_input(self):
        self.input_calls = 0
        self.last_stage = 'structure'
        self.last_slot = None

    def call(self, stage, prompt, user, schema, out, max_tokens, seed):
        remaining = (self.deadline - dt.datetime.now(dt.timezone.utc)).total_seconds()
        reason = ('deadline' if remaining <= 0 else
                  'run_call_budget' if self.calls_started >= self.max_calls else
                  'input_call_budget' if self.input_calls >= self.max_calls_per_input else None)
        if reason:
            save(Path(out) / 'blocked_before_call.json', {'reason': reason, 'stage': stage,
                 'calls_started': self.calls_started, 'input_calls': self.input_calls})
            raise RunLimitReached(reason)
        self.calls_started += 1
        self.input_calls += 1
        self.last_stage = stage
        self.last_slot = Path(out).name
        save(Path(out) / 'attempt_started.json', {'stage': stage,
             'run_attempt': self.calls_started, 'input_attempt': self.input_calls,
             'started_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
        old_timeout = getattr(self.client, 'timeout', None)
        if old_timeout is not None:
            self.client.timeout = min(old_timeout, max(0.001, remaining))
        try:
            return self.client.call(stage, prompt, user, schema, out, max_tokens, seed)
        finally:
            if old_timeout is not None:
                self.client.timeout = old_timeout


def output_availability(record_dir, result):
    """Expose intermediate artifacts without promoting an unchecked draft to final."""
    draft_path = record_dir / 'writer/parsed.json'
    review_path = record_dir / 'reviewer/parsed.json'
    revision_path = record_dir / 'revision/parsed.json'
    validation_path = record_dir / 'review_validation.json'
    validation = read(validation_path) if validation_path.exists() else {}
    review_state = validation.get('state')
    revision_attempted = (record_dir / 'revision/attempt_started.json').exists()
    draft = read(draft_path) if draft_path.exists() else {}
    draft_text = draft.get('output_text')
    draft_available = isinstance(draft_text, str) and bool(draft_text.strip())
    final_available = bool(result.get('pipeline_completed') and isinstance(result.get('output_text'), str)
                           and result['output_text'].strip())
    # Receiving JSON is not successful review validation. The pipeline may retain
    # a draft despite an unreliable review, without claiming it was reviewed well.
    review_complete = bool(review_state == 'valid' and result.get('pipeline_completed'))
    return {'draft_available': draft_available,
            'draft_text': draft_text if draft_available else None,
            'draft_artifact': 'writer/parsed.json' if draft_path.exists() else None,
            'review_response_available': review_path.exists(),
            'review_response_complete': review_path.exists(),
            'review_validation_state': review_state,
            'valid_review_issue_count': validation.get('valid_issue_count'),
            'invalid_review_issue_count': validation.get('invalid_issue_count'),
            'review_complete': review_complete,
            'revision_attempted': revision_attempted,
            'revision_response_available': revision_path.exists(),
            'final_available': final_available,
            'output_state': 'revision_written_not_rechecked' if final_available and revision_attempted else
            'draft_review_unreliable' if draft_available and review_state in ('partially_invalid', 'invalid') else
            'draft_reviewed' if final_available and review_complete else
            'draft_review_unverified' if final_available else
            'pipeline_failed_draft_preserved' if draft_available else 'no_draft_available'}


def execute(args):
    require(args.execute, 'Explicit --execute required')
    rows = load_jsonl(args.inputs)
    require(rows and len({r['id'] for r in rows}) == len(rows), 'Duplicate/empty inputs')
    require(all(isinstance(r.get('text'), str) and r['text'].strip() and
                re.fullmatch(r'[A-Za-z0-9_-]+', r['id']) for r in rows), 'Invalid input text or ID')
    separate_plan = bool(getattr(args, 'separate_plan', False))
    max_calls_per_input = 6 if separate_plan else 5
    require(args.max_calls >= max_calls_per_input * len(rows),
            'Budget must reserve all worker calls and one possible rewrite for every input')
    require(args.char_budget > 0, 'Knowledge character budget must be positive')
    end = dt.datetime.fromisoformat(args.deadline)
    require(end.tzinfo is not None and end > dt.datetime.now(dt.timezone.utc),
            'Deadline expired or missing timezone')
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'experiments/runs' / (stamp + '_qwen_multi_' + args.phase)
    (out / 'private').mkdir(parents=True, exist_ok=False)
    shutil.copy2(args.inputs, out / 'private/inputs.jsonl')
    config = {'program_id': PROGRAM_ID, 'phase': args.phase,
              'dataset_role': 'regression_exposed' if args.phase == 'regression' else 'development',
              'input_count': len(rows), 'input_sha256': sha(Path(args.inputs).read_bytes()),
              'model_id': args.model, 'seed': args.seed, 'max_calls': args.max_calls,
              'max_calls_per_input': max_calls_per_input, 'max_generation_repairs': 1,
              'separate_plan': separate_plan, 'worker_role_count': 5 if separate_plan else 4,
              'worker_roles': ['structure', 'meaning', 'plan', 'writer', 'review'] if separate_plan
              else ['structure', 'meaning', 'selection_and_writer', 'review'],
              'deadline': args.deadline, 'deadline_policy': 'guard_every_call_and_bound_transport_timeout',
              'automatic_transport_retries': 0, 'final_writer': 'Qwen_raw_output',
              'analysis_backend': 'Qwen_workers_no_Kiwi', 'knowledge_character_budget': args.char_budget,
              'reference_answers_in_request': False, 'metric_contract': 'qwen_multi_v1',
              'programmatic_original_text_fallback': False,
              'naturalness': 'not_evaluated', 'baseline': 'integration; not a causal multi-agent comparison',
              'python_version': platform.python_version()}
    save(out / 'config.json', config)
    results = []
    hashes = {}
    kg_hashes = {}
    start = time.perf_counter()
    stop = None
    client = None
    work = None
    consecutive = 0

    def progress_event(done, status, message):
        if work is None:
            return
        try:
            work.task({'id': out.name, 'title': 'Qwen 분업 ' + args.phase,
                       'actor': 'Qwen / 연구 리드', 'stage': '구조·의미→KG→계획·작성·검토',
                       'status': status, 'done': done, 'total': len(rows), 'unit': '입력',
                       'unit_key': out.name, 'message': message})
        except Exception as exc:
            save(out / 'progress_registration_error.json', {'error_type': type(exc).__name__})

    try:
        work = WorkStore(ROOT)
        progress_event(0, 'running', '새 분업 경로를 시작합니다. 기존 출력이나 정답 문장은 전달하지 않습니다.')
        if not args.graph:
            args.graph = str(ROOT / read(ROOT / 'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')['graph'])
        graph_path = Path(args.graph)
        graph = read(graph_path)
        reader = IntegratedReader(graph)
        shutil.copy2(graph_path, out / 'private/graph.json')
        kg_hashes['graph'] = sha(graph_path.read_bytes())
        if graph.get('storage_format') == SEPARATED_FORMAT:
            parent = graph_path.parent
            manifest = read(parent / 'manifest.json')
            require(kg_hashes['graph'] == manifest['graph_sha256'], 'Separated graph hash mismatch')
            require(sha((parent / 'audit.json').read_bytes()) == manifest['audit_sha256'], 'Separated audit hash mismatch')
            restore(graph, read(parent / 'audit.json'))
            for source, dest in [('audit.json', 'kg_audit.json'), ('manifest.json', 'kg_manifest.json')]:
                shutil.copy2(parent / source, out / 'private' / dest)
                kg_hashes[source] = sha((parent / source).read_bytes())
        save(out / 'kg_hashes.json', kg_hashes)
        from kg_pipeline.multi_agent import PROMPTS, run_sentence
        config.update(kg_dataset=graph['version'], graph_sha256=kg_hashes['graph'],
                      prompt_sha256={k: sha(v.encode()) for k, v in PROMPTS.items()})
        save(out / 'config.json', config)
        for name, prompt in PROMPTS.items():
            require(re.fullmatch(r'[A-Za-z0-9_-]+', name) is not None, 'Unsafe prompt name')
            path = out / 'prompts' / (name + '.txt')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(prompt, encoding='utf-8')
        for rel in ['tools/run_qwen_multi.py', 'src/kg_pipeline/multi_agent.py',
                    'src/kg_pipeline/integrated.py', 'src/kg_pipeline/separated_graph.py',
                    'src/kg_pipeline/io.py', 'src/kg_pipeline/validation.py',
                    'src/kg_pipeline/runner.py', 'src/research_management/core.py',
                    'src/research_management/work.py']:
            source = ROOT / rel
            dest = out / 'code_snapshot' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            hashes[rel] = sha(source.read_bytes())
        save(out / 'code_hashes.json', hashes)
        register_run(ROOT, out)
        require(dt.datetime.now(dt.timezone.utc) < end, 'Deadline expired during setup')
        transport = Qwen(ROOT / 'test.py', model=args.model, timeout=120)
        save(out / 'server_models.json', transport.models)
        client = GuardedClient(transport, end, args.max_calls, max_calls_per_input)
        for row in rows:
            if dt.datetime.now(dt.timezone.utc) >= end:
                stop = 'deadline'
                break
            if client.calls_started + max_calls_per_input > args.max_calls:
                stop = 'insufficient_remaining_call_reserve'
                break
            if consecutive >= 3:
                stop = 'consecutive_failures'
                break
            rd = out / 'private/records' / row['id']
            save(rd / 'input.json', row)
            result = {'id': row['id'], 'input_text': row['text'], 'output_text': None,
                      'status': 'started', 'human_evaluation': None}
            t0 = time.perf_counter()
            client.begin_input()
            try:
                generated = run_sentence(client, reader, row['text'], rd, seed=args.seed,
                                         char_budget=args.char_budget, max_repairs=1,
                                         separate_plan=separate_plan)
                result.update(generated)
                # IDs and source text are controlled by this input, not the worker return.
                result.update(id=row['id'], input_text=row['text'])
                require(isinstance(result.get('output_text'), str) and result['output_text'].strip(),
                        'Missing final model output')
                result['unchanged'] = result['output_text'] == row['text']
                result['pipeline_completed'] = True
                consecutive = 0
            except KeyboardInterrupt:
                stop = 'interrupted'
                result.update(status='interrupted', error_type='KeyboardInterrupt', pipeline_completed=False)
            except RunLimitReached as exc:
                stop = str(exc)
                result.update(status='failed', error_type=type(exc).__name__, pipeline_completed=False)
                consecutive += 1
            except Exception as exc:
                # No raw exception/repr: transport messages may contain network/credential details.
                result.update(status='failed', error_type=type(exc).__name__, pipeline_completed=False)
                consecutive += 1
            result.update(output_availability(rd, result))
            stage_path = rd / 'pipeline_stage.json'
            current_stage = read(stage_path).get('stage', 'unknown') if stage_path.exists() else 'unknown'
            result.update(last_model_stage=client.last_stage, last_call_slot=client.last_slot,
                          current_pipeline_stage=current_stage,
                          api_attempts=client.input_calls,
                          total_seconds=round(time.perf_counter() - t0, 4))
            save(rd / 'result.json', result)
            results.append(result)
            save(out / 'private/results.json', results)
            elapsed = time.perf_counter() - start
            progress = {'done': len(results), 'total': len(rows), 'id': row['id'], 'status': result['status'],
                        'elapsed_seconds': round(elapsed, 1),
                        'eta_seconds': round(elapsed / len(results) * (len(rows) - len(results)), 1)
                        if len(results) >= 3 else None,
                        'eta_basis': 'observed_average_after_three_inputs', 'calls_started': client.calls_started}
            save(out / 'progress.json', progress)
            print(dumps(progress), flush=True)
            progress_event(len(results), 'running', row['id'] + ': ' + result['status'])
            if stop:
                break
    except KeyboardInterrupt:
        stop = 'interrupted'
        save(out / 'failure.json', {'stage': 'setup_or_between_inputs', 'error_type': 'KeyboardInterrupt'})
    except Exception as exc:
        stop = 'setup_failure'
        save(out / 'failure.json', {'stage': 'setup_or_between_inputs', 'error_type': type(exc).__name__})
    finally:
        save(out / 'private/results.json', results)
        metas = [read(p) for p in (out / 'private/records').rglob('meta.json')]
        attempted = client.calls_started if client else 0
        completed = [r for r in results if r.get('pipeline_completed')]
        metrics = {'records': len(results), 'planned_inputs': len(rows),
                   'unattempted_inputs': len(rows) - len(results), 'valid_output_records': len(completed),
                   'failed_input_records': sum(not r.get('pipeline_completed') for r in results),
                   'draft_available_records': sum(r.get('draft_available', False) for r in results),
                   'draft_only_records': sum(r.get('draft_available', False) and not r.get('final_available', False)
                                             for r in results),
                   'review_complete_records': sum(r.get('review_complete', False) for r in results),
                   'review_response_complete_records': sum(r.get('review_response_complete', False) for r in results),
                   'review_validation_counts': dict(collections.Counter(r.get('review_validation_state') or 'not_recorded' for r in results)),
                   'revision_attempted_records': sum(r.get('revision_attempted', False) for r in results),
                   'revision_written_not_rechecked_records': sum(r.get('output_state') == 'revision_written_not_rechecked'
                                                                  for r in results),
                   'final_available_records': sum(r.get('final_available', False) for r in results),
                   'changed_records': sum(r['output_text'] != r['input_text'] for r in completed),
                   'status_counts': dict(collections.Counter(r['status'] for r in results)),
                   'failure_stages': dict(collections.Counter(r.get('current_pipeline_stage') or 'unknown' for r in results
                                                             if not r.get('pipeline_completed'))),
                   'last_call_failure_slots': dict(collections.Counter(r.get('last_call_slot') or 'unknown' for r in results
                                                                      if not r.get('pipeline_completed'))),
                   'api_attempts': attempted, 'transport_meta_records': len(metas),
                   'attempts_missing_transport_meta': attempted - len(metas),
                   'api_failures': sum(m.get('status') == 'failed' for m in metas),
                   'calls_by_stage': dict(collections.Counter(m.get('stage') for m in metas)),
                   'stage_seconds': {stage: round(sum(m.get('seconds', 0) for m in metas if m.get('stage') == stage), 4)
                                     for stage in sorted({m.get('stage', 'unknown') for m in metas})},
                   'reported_usage': {k: sum((m.get('usage') or {}).get(k, 0) or 0 for m in metas)
                                      for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
                   'calls_without_usage': sum(not m.get('usage') for m in metas),
                   'usage_completeness': 'complete' if metas and len(metas) == attempted and
                   all(m.get('usage') for m in metas) else 'partial_or_absent_reported_sum_only',
                   'wall_seconds': round(time.perf_counter() - start, 4),
                   'mean_record_seconds': round(statistics.mean(r['total_seconds'] for r in results), 4) if results else None,
                   'stop_reason': stop, 'naturalness': None, 'independent_accuracy': None,
                   'automatic_transport_retries': 0, 'model_review_is_independent_human_evaluation': False}
        save(out / 'metrics.json', metrics)
        if stop:
            previous = read(out / 'failure.json') if (out / 'failure.json').exists() else {}
            save(out / 'failure.json', {**previous, 'stop_reason': stop})
        save(out / 'postflight.json', {
            'graph_unchanged': sha(Path(args.graph).read_bytes()) == kg_hashes['graph']
            if args.graph and Path(args.graph).exists() and 'graph' in kg_hashes else None,
            'code_unchanged': all((ROOT / rel).exists() and sha((ROOT / rel).read_bytes()) == h
                                  for rel, h in hashes.items()) if hashes else None})
        save(out / 'artifact_hashes.json', {p.relative_to(out).as_posix(): sha(p.read_bytes())
                                          for p in out.rglob('*') if p.is_file() and p.name != 'artifact_hashes.json'})
        register_run(ROOT, out)
        progress_event(len(results), 'failed' if stop else 'completed',
                       '중단: ' + stop if stop else '실행 기록 저장 완료. 번역 품질은 별도 검토가 필요합니다.')
    print(dumps({'run_id': out.name, 'directory': str(out), 'metrics': metrics}), flush=True)
    return out, metrics


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true', required=True)
    p.add_argument('--inputs', required=True)
    p.add_argument('--phase', choices=['smoke', 'development', 'regression'], required=True)
    p.add_argument('--graph', help='Explicit graph file; defaults to separated latest')
    p.add_argument('--model', default='Qwen3.8-27B')
    p.add_argument('--deadline', required=True, help='ISO time with explicit timezone')
    p.add_argument('--max-calls', type=int, required=True)
    p.add_argument('--seed', type=int, default=20261107)
    p.add_argument('--char-budget', type=int, default=18000)
    p.add_argument('--separate-plan', action='store_true',
                   help='Comparison variant: add a separate planning worker (five roles, up to six calls)')
    return p


if __name__ == '__main__':
    _, metrics = execute(parser().parse_args())
    if metrics['stop_reason']:
        sys.exit(2)
