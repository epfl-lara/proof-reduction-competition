from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading

import pytest

import proof_agent_tools as toolmod
from proof_agent_tools import ProofSession, ProofToolService
from proof_agent_proposal import command, tool_instructions
from codex_proposal import cli_identity, parse_events
from run_agent_harness import load_inputs, messages

ORIGINAL = 'theorem x : True := by trivial'
GOOD = 'theorem x : True := by exact True.intro'
WORSE = 'theorem x : True := by constructor'
INVALID = 'theorem x : True := by sorry'
CLEANED = 'theorem x : True := by exact ⟨⟩'


def evaluation(score, *, statuses=('passed', 'passed')):
    return {'status': 'passed', 'primary_version': 'v1',
            'candidate': {'length': 3},
            'scores': {'length_reduction_pct': 3 * score - 120,
                       'heartbeat_reduction_pct': 20., 'compatibility_pct': 100., 'combined_pct': score},
            'per_version': {v: {'status': s, 'passed': s == 'passed', 'heartbeats': 100,
                               'diagnostics': []} for v, s in zip(('v1', 'v2'), statuses)}}


@pytest.fixture
def make_session(tmp_path, monkeypatch):
    seed = evaluation(100 / 3)
    seed['scores'].update(length_reduction_pct=0., heartbeat_reduction_pct=0.)
    monkeypatch.setattr(toolmod, 'original_evaluation', lambda _: deepcopy(seed))
    pack = {'name': 'x', 'row': {'name': 'x', 'source': 'test', 'statement': 'theorem x : True',
                               'src': ORIGINAL, 'file_path': 'Example.lean',
                               'version_info': [{'v1': 'a'}, {'v2': 'b'}]}}
    project = tmp_path / 'project'
    project.mkdir()

    class Evaluator:
        projects = {('test', 'v1'): project, ('test', 'v2'): project}

        def __init__(self):
            self.calls = []
            self.values = {GOOD: evaluation(70), WORSE: evaluation(50),
                           INVALID: {'status': 'invalid', 'per_version': {}, 'diagnostics': ['sorry forbidden'],
                                     'scores': {k: 0. for k in seed['scores']}}}

        def evaluate(self, name, code, **kwargs):
            assert name == 'x' and kwargs == {'versions': 'all'}
            assert code != ORIGINAL, 'Reference must never be measured again'
            self.calls.append(code)
            return deepcopy(self.values[code])

    evaluator = Evaluator()
    seed['candidate']['code_sha256'] = toolmod.code_identity(pack['row'], ORIGINAL)
    for code, value in evaluator.values.items():
        if 'candidate' in value:
            value['candidate']['code_sha256'] = toolmod.code_identity(pack['row'], code)

    def make(mode='score', folder=None, **kwargs):
        return ProofSession(folder or tmp_path / 'ledger', pack, evaluator, mode, **kwargs)
    make.evaluator, make.project, make.pack, make.seed = evaluator, project, pack, seed
    return make


def test_score_tuple_and_best_survive_invalid_worse_and_duplicate(make_session):
    session = make_session()
    seed = session.check(ORIGINAL)
    assert seed['score_tuple'] == [0., 0., 100.]
    assert not make_session.evaluator.calls
    good = session.check(GOOD)
    assert good['score_tuple'] == [90., 20., 100.]
    assert good['total_score'] == 70 and good['accepted_as_best']
    for code in (WORSE, INVALID, GOOD):
        response = session.check(code)
        assert not response['accepted_as_best']
        assert response['best_proof'] == GOOD
        assert response['best_scores']['combined_pct'] == 70
    assert len(make_session.evaluator.calls) == 3
    assert session.checks[-1]['duplicate']
    resumed = make_session()
    assert resumed.best_code == GOOD and len(resumed.checks) == 5
    resumed.check(GOOD)
    assert len(make_session.evaluator.calls) == 3


def test_correctness_mode_never_returns_scores_or_allows_second_valid_search(make_session):
    session = make_session('correctness')
    session.check(INVALID)
    response = session.check(GOOD)
    assert response['all_versions_passed']
    text = json.dumps([response, session.status(), session.dispatch({'op': 'finish', 'reason': 'valid proposal'})])
    assert all(word not in text for word in ('heartbeats', 'score_tuple', 'best_scores', 'combined_pct', 'source_tokens'))
    assert session.check(WORSE, origin='final_harness')['kind'] == 'proposal_already_valid'
    assert make_session.evaluator.calls == [INVALID, GOOD]


def test_high_score_with_failed_version_cannot_replace_best(make_session):
    session = make_session()
    make_session.evaluator.values[GOOD] = evaluation(95, statuses=('passed', 'failed'))
    response = session.check(GOOD)
    assert not response['all_versions_passed'] and not response['accepted_as_best']
    assert response['passing_rate_pct'] == 50
    assert session.best_code == ORIGINAL


def test_primary_failure_reports_actual_pass_rate_and_gated_score(make_session):
    session = make_session()
    failed = evaluation(0, statuses=('failed', 'passed'))
    failed['status'] = 'failed'
    failed['scores'] = dict.fromkeys(failed['scores'], 0.)
    make_session.evaluator.values[GOOD] = failed
    response = session.check(GOOD)
    assert response['score_tuple'] == [0., 0., 0.] and response['total_score'] == 0
    assert response['passing_rate_pct'] == 50 and not response['accepted_as_best']


def test_unknown_measurements_remain_unknown(make_session):
    session = make_session()
    pending = evaluation(70, statuses=('unavailable', 'passed'))
    pending['status'] = 'incomplete'
    pending['scores'] = dict.fromkeys(pending['scores'], None)
    make_session.evaluator.values[GOOD] = pending
    response = session.check(GOOD)
    assert response['score_tuple'] == [None, None, None]
    assert response['total_score'] is None and not response['accepted_as_best']


def cleanup_result(make_session, code=CLEANED, score=85):
    result = evaluation(score)
    result['candidate']['code_sha256'] = toolmod.code_identity(make_session.pack['row'], code)
    return {'status': 'complete', 'proof': code, 'evaluation': result,
            'job_path': '/test/job', 'job_result_sha256': 'test', 'counters': {}, 'reused': False}


def test_deterministic_seed_requires_all_versions_and_preserves_original_denominators(make_session, monkeypatch):
    import run_agent_harness as runner
    monkeypatch.setattr(runner, 'original_evaluation', lambda _: deepcopy(make_session.seed))
    pack = {**make_session.pack, 'proof': WORSE, 'incumbent': make_session.evaluator.values[WORSE]}
    seed = runner.starting_point(pack, 'score_edges')
    assert seed[0] == WORSE
    session = make_session('score_edges', seed=seed)
    assert session.best_evaluation['scores']['combined_pct'] == 50
    assert session.check(ORIGINAL)['total_score'] == 100 / 3
    assert session.best_code == WORSE and not make_session.evaluator.calls
    pack['incumbent'] = evaluation(95, statuses=('passed', 'failed'))
    assert runner.starting_point(pack, 'score_edges')[0] == ORIGINAL
    pack['incumbent'] = evaluation(20)
    assert runner.starting_point(pack, 'score_edges')[0] == ORIGINAL
    with pytest.raises(ValueError, match='Seed may not regress'):
        make_session('score_edges', seed=(WORSE, cleanup_result(make_session, WORSE, 20)['evaluation']))


def test_deterministic_feedback_retains_raw_and_cleaned_best_and_resumes(make_session):
    calls = []

    def cleanup(code):
        calls.append(code)
        return cleanup_result(make_session, **({'code': WORSE, 'score': 50} if code == WORSE else {}))

    session = make_session('score_edges', cleanup=cleanup)
    response = session.deterministic(GOOD, origin='final_harness')
    assert response['before']['total_score'] == 70 and response['after']['total_score'] == 85
    assert response['accepted_as_best'] and response['gain_over_input_pp'] == 15
    assert response['best_proof'] == CLEANED
    assert session.checks[0]['accepted'] and session.checks[1]['accepted']
    assert [c['origin'] for c in session.checks] == ['deterministic_input', 'deterministic_final_harness']
    session.deterministic(WORSE, origin='final_harness')
    skipped = session.deterministic(INVALID, origin='final_harness')
    assert skipped['status'] == 'skipped_invalid' and skipped['after'] is None
    assert calls == [GOOD, WORSE]
    assert session.best_code == CLEANED
    assert make_session.evaluator.calls == [GOOD, WORSE, INVALID]
    resumed = make_session('score_edges', cleanup=cleanup)
    assert resumed.best_code == CLEANED and len(resumed.cleanup_calls) == 3
    assert resumed.check(CLEANED)['duplicate']
    assert make_session.evaluator.calls == [GOOD, WORSE, INVALID]


def test_deterministic_cannot_discard_a_better_raw_proposal(make_session):
    session = make_session('score_edges', cleanup=lambda _: cleanup_result(make_session, WORSE, 50))
    response = session.deterministic(GOOD, origin='final_harness')
    assert response['gain_over_input_pp'] == -20
    assert not response['accepted_as_best'] and session.best_code == GOOD


@pytest.mark.parametrize('mode', ['score', 'correctness', 'score_edges'])
def test_deterministic_tool_is_unavailable_to_agents(make_session, mode):
    session = make_session(mode, cleanup=lambda _: cleanup_result(make_session))
    with pytest.raises(ValueError, match='Unknown operation'):
        session.dispatch({'op': 'deterministic', 'code': GOOD})
    with pytest.raises(ValueError, match='only to the host'):
        session.deterministic(GOOD)
    assert not session.checks
    if mode == 'score_edges':
        assert session.deterministic(GOOD, origin='final_harness')['best_proof'] == CLEANED


def test_retired_mode_cannot_start_a_session_or_transport(make_session, tmp_path):
    with pytest.raises(ValueError, match='Unknown feedback mode'):
        make_session('score_each')
    with pytest.raises(ValueError, match='Unsupported'):
        command(binary='codex', workspace=tmp_path, system_file=tmp_path / 'system',
                last_message=tmp_path / 'final', model='gpt-6-astra', effort='max', mode='score_each')
    proc = subprocess.run([sys.executable, 'src/run_agent_harness.py', '--mode', 'score_each'],
                          text=True, capture_output=True)
    assert proc.returncode == 2 and 'invalid choice' in proc.stderr


def test_cleanup_cache_identity_and_original_reference_reuse(make_session, tmp_path, monkeypatch):
    from proof_eval.metrics import validate_candidate
    seen = []

    def cleanup(**kwargs):
        seen.append(kwargs)
        evaluator = kwargs['evaluator']
        for versions in ('primary', 'all'):
            assert evaluator.evaluate('x', ORIGINAL + '\n', versions=versions) == make_session.seed
        assert evaluator.projects == make_session.evaluator.projects
        result = cleanup_result(make_session)
        (kwargs['folder'] / 'result.json').write_text(json.dumps(result))
        return result

    monkeypatch.setattr(toolmod, 'cleanup_proof', cleanup)
    root = tmp_path / 'jobs'
    first = toolmod.DeterministicCleanup(root, make_session.pack, make_session.evaluator, {'pin': 1}, lambda: None)
    second = toolmod.DeterministicCleanup(root, make_session.pack, make_session.evaluator, {'pin': 1}, lambda: None)
    a, b = first(GOOD), second(GOOD + '\n')
    assert a['job_path'] == b['job_path'] and not a['reused'] and b['reused']
    assert seen[0]['proof'] == validate_candidate(make_session.pack['row'], GOOD)[0]
    changed = toolmod.DeterministicCleanup(root, make_session.pack, make_session.evaluator, {'pin': 2}, lambda: None)
    assert changed(GOOD)['job_path'] != a['job_path']
    assert not make_session.evaluator.calls


def test_gain_attribution_excludes_seed_checks_and_final_cleanup(make_session):
    from summarize_agent_harness import trajectory
    cleanup = lambda _: cleanup_result(make_session)
    seed = (WORSE, make_session.evaluator.values[WORSE])
    session = make_session('score_edges', seed=seed, cleanup=cleanup)
    session.check(WORSE)
    session.check(GOOD)
    session.deterministic(GOOD, origin='final_harness')
    # Historical in-loop evidence remains readable even though it cannot run.
    session.checks[-1]['origin'] = 'deterministic_agent_tool'
    # Distinct code keeps the original identity tied to its cached reference.
    final = 'theorem x : True := by apply True.intro'
    session.cleanup = lambda _: cleanup_result(make_session, final, 90)
    session.deterministic(CLEANED, origin='final_harness')
    records, gains = trajectory(make_session.pack['row'], *seed, session.checks)
    assert records[0]['best_score'] == 50 and not records[0]['changed']
    assert gains == {'first_changed_valid_raw_score': 70, 'best_after_first_changed_valid': 70,
                     'further_search_gain_pp': 15, 'model_gain_pp': 20,
                     'in_loop_cleanup_gain_pp': 15, 'final_cleanup_gain_pp': 5}
    assert seed[1]['scores']['combined_pct'] + sum(gains[k] for k in
        ('model_gain_pp', 'in_loop_cleanup_gain_pp', 'final_cleanup_gain_pp')) == 90


def test_controller_adoption_checks_process_identity_and_terminal_evidence(tmp_path, monkeypatch):
    import continue_agent_harness as controller
    args = [sys.executable, '-c', 'import time; print("ready", flush=True); time.sleep(30)']
    child = subprocess.Popen(args, stdout=subprocess.PIPE, text=True)
    step = {'pid': child.pid, 'command': args}
    try:
        assert child.stdout.readline().strip() == 'ready'
        assert controller.runner_active(step)
        with pytest.raises(RuntimeError, match='different command'):
            controller.runner_active({**step, 'command': ['wrong']})
    finally:
        child.terminate()
        child.wait()
    assert not controller.runner_active(step)
    (tmp_path / 'run.json').write_text(json.dumps({'status': 'finished'}))
    assert controller.wait_for_runner(step, tmp_path) == 0
    (tmp_path / 'run.json').write_text(json.dumps({'status': 'running'}))
    with pytest.raises(RuntimeError, match='without terminal evidence'):
        controller.wait_for_runner(step, tmp_path)


def test_controller_checks_both_model_pilots_before_full_cohort(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import continue_agent_harness as controller
    monkeypatch.setattr(controller, 'ROOT', tmp_path)
    monkeypatch.setattr(controller, 'BASE', tmp_path)
    (tmp_path / 'config.json').write_text(json.dumps({'names': ['x']}))
    outputs = {'model_config': tmp_path / 'model_config'}
    conditions = [('gpt-6.1-sol', 'max'), ('gpt-6-astra', 'high')]
    outputs['model_config'].mkdir()
    (outputs['model_config'] / 'config.json').write_text(json.dumps({'conditions': conditions}))
    monkeypatch.setattr(controller, 'OUTPUTS', outputs)
    monkeypatch.setattr(sys, 'argv', ['controller', '--suite', 'models', '--workers', '10'])
    started, audits = [], []

    class Child:
        def __init__(self, args, **kwargs):
            self.mode = args[args.index('--mode') + 1]
            assert self.mode == 'score_edges' and args[args.index('--workers') + 1] == '10'
            self.phase = 'pilot' if '--name' in args else 'full'
            if self.phase == 'full':
                assert len(audits) == 1, 'The two-model pilot audit must finish before the full run'
            self.pid = 100 + len(started)
            started.append((self.mode, self.phase))

        def wait(self):
            if self.phase == 'pilot':
                for model, effort in conditions:
                    folder = outputs['model_config'] / 'cells' / model
                    folder.mkdir(parents=True)
                    (folder / 'result.json').write_text(json.dumps(
                        {'name': 'x', 'model': model, 'effort': effort, 'status': 'complete',
                         'agent_tool_checks': 1, 'deterministic_tool_calls': 0,
                         'deterministic_calls': 1, 'cost': {'status': 'estimated'}}))
            return 0

    def audit(args, **kwargs):
        audits.append(args[-1])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(controller.subprocess, 'Popen', Child)
    monkeypatch.setattr(controller.subprocess, 'run', audit)
    controller.main()
    state = json.loads((tmp_path / 'results/harness/model_config_controller.json').read_text())
    assert state['status'] == 'finished'
    assert started == [('score_edges', 'pilot'), ('score_edges', 'full')]
    assert len(started) == len(audits) == 2
    controller.main()  # Completed stages are neither relaunched nor re-audited.
    assert len(started) == len(audits) == 2


def test_source_tools_search_read_outline_and_reject_scope_escape(make_session, tmp_path):
    session = make_session()
    (make_session.project / 'Example.lean').write_text('def sample := 1\ntheorem helper : True := by trivial\n')
    found = session.dispatch({'op': 'search', 'query': 'helper', 'limit': 1})
    assert 'Example.lean:2:' in found['matches'][0]
    outline = session.dispatch({'op': 'outline', 'path': 'Example.lean'})
    assert [d['line'] for d in outline['declarations']] == [1, 2]
    assert session.dispatch({'op': 'read', 'path': 'Example.lean', 'start': 2, 'end': 2})['text'].startswith('2: theorem')
    outside = tmp_path / 'secret.lean'
    outside.write_text('not available')
    (make_session.project / 'escape.lean').symlink_to(outside)
    for path in ('../secret.lean', 'escape.lean', str(outside)):
        with pytest.raises(ValueError, match='pinned Lean'):
            session.dispatch({'op': 'read', 'path': path})
    with pytest.raises(ValueError, match='Version outside'):
        session.dispatch({'op': 'search', 'query': 'helper', 'version': 'v3'})
    with pytest.raises(ValueError, match='invalid fields'):
        session.dispatch({'op': 'check', 'code': GOOD, 'name': 'another theorem'})


@pytest.mark.parametrize('operation', ['check'])
def test_actual_workspace_client_and_host_ledger(make_session, tmp_path, operation):
    session = make_session('score_edges', cleanup=lambda _: cleanup_result(make_session))
    work = tmp_path / 'workspace'
    work.mkdir()
    (work / 'tools.py').write_text((Path(__file__).parents[1] / 'src/proof_agent_client.py').read_text())
    (work / 'candidate.lean').write_text(GOOD)
    with ProofToolService(session, work):
        proc = subprocess.run([sys.executable, str(work / 'tools.py'), operation, 'candidate.lean'],
                              cwd=tmp_path, text=True, capture_output=True, timeout=15)
    assert proc.returncode == 0, proc.stderr
    if operation == 'check':
        assert json.loads(proc.stdout)['total_score'] == 70
        assert session.best_code == GOOD
    else:
        assert json.loads(proc.stdout)['after']['total_score'] == 85
        assert session.best_code == CLEANED
    assert (session.folder / 'checks.jsonl').exists()
    assert not (work / 'checks.jsonl').exists()


def test_prompts_have_tools_and_no_target_answer_examples():
    packs = load_inputs()
    pack = next(iter(packs.values()))
    prompt = messages(pack)
    assert 'no tool calls or repair turn' not in prompt[0]['content']
    payload = json.loads(prompt[1]['content'].split('\n', 1)[1])
    assert payload['incumbent_declaration'] == pack['row']['src']
    bank = payload['structural_strategy_cards']
    assert len(bank) == 5
    for name in packs:
        assert name not in json.dumps(bank)
    assert 'best_proof' not in payload
    assert 'no fixed total attempt, token or wall-time budget' in tool_instructions('score')


@pytest.mark.parametrize('mode', ['correctness', 'score', 'score_edges'])
@pytest.mark.parametrize('model,effort', [('gpt-6-astra', 'max'), ('gpt-6.1-sol', 'max'), ('gpt-6-astra', 'high')])
def test_runner_repairs_or_searches_and_resume_does_not_regenerate(make_session, tmp_path, monkeypatch, mode, model, effort):
    import run_agent_harness as runner
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'guard', lambda *a: None)
    monkeypatch.setattr(runner, 'messages', lambda _, **kw: [{'role': 'system', 'content': 'system'}, {'role': 'user', 'content': 'task'}])
    monkeypatch.setattr(runner, 'original_evaluation', lambda _: deepcopy(make_session.seed))
    control_path = tmp_path / 'control.json'
    control_path.write_text('{}')
    has_control = (model, effort) == ('gpt-6-astra', 'max')
    monkeypatch.setattr(runner, 'historical', lambda *a: (control_path, {'selected_evaluation': evaluation(55)}) if has_control else (None, None))
    monkeypatch.setattr(runner, 'structural_control', lambda *a: (None, None))
    config = {'mode': mode, 'max_outer_correctness_repairs': 3 if mode == 'correctness' else 0,
              'cli': {}, 'historical_control_sha256': {'control.json': runner.digest(control_path)},
              'structural_control_sha256': {}, 'cost_assumptions': {}, 'budget_usd_per_problem': 3.}
    if mode in runner.DETERMINISTIC_MODES:
        monkeypatch.setattr(runner, 'starting_point', lambda *_: (WORSE, make_session.evaluator.values[WORSE]))
        monkeypatch.setattr(runner, 'DeterministicCleanup', lambda *a: lambda code: cleanup_result(make_session))
        monkeypatch.setattr(runner, 'score_control', lambda *a: (control_path, {'selected_evaluation': evaluation(72)}) if has_control else (None, None))
        (tmp_path / 'config.json').write_text(json.dumps({'contexts': {'x': {}}}))
        monkeypatch.setattr(runner, 'BASE', tmp_path)
        make_session.pack['incumbent'] = {'per_version': {'v1': {'reference': {}}}}
        config.update(deterministic_jobs=str(tmp_path / 'jobs'), code_sha256={}, input_sha256={'x': 'hash'},
                      score_control_sha256={'control.json': runner.digest(control_path)})
    calls = []

    def generate(**kwargs):
        calls.append(kwargs['messages'])
        session = kwargs['session']
        if mode == 'correctness':
            code = INVALID if len(calls) == 1 else GOOD
            session.check(code)
        else:
            session.check(GOOD)
            session.check(INVALID)
            session.check(WORSE)
            code = WORSE  # Regression in final text must not discard best proof.
        session.dispatch({'op': 'finish', 'reason': 'test finished'})
        return {'status': 'received', 'content': code, 'finish_reason': 'stop', 'usage': {'completion_tokens': 10},
                'codex_usage': {'input_tokens': 100, 'cached_input_tokens': 50, 'cache_write_input_tokens': 0,
                                'output_tokens': 10, 'reasoning_output_tokens': 5}}

    output = tmp_path / 'run'
    result = runner.run_cell(output, config, make_session.pack, model, effort, make_session.evaluator, generator=generate)
    expected = CLEANED if mode in runner.DETERMINISTIC_MODES else GOOD
    assert result['selected_proof'] == expected
    assert result['selected_evaluation']['scores']['combined_pct'] == (85 if expected == CLEANED else 70)
    assert result['status'] == 'complete'
    assert result['cost']['status'] == 'estimated' and result['cost']['total_usd'] > 0
    if not has_control:
        assert result['historical_score'] is None and result['gain_over_historical_pp'] is None
    assert len(calls) == (2 if mode == 'correctness' else 1)
    if mode == 'correctness':
        assert 'correctness_feedback' in calls[1][1]['content']
        assert 'heartbeat' not in calls[1][1]['content']
    if mode in runner.DETERMINISTIC_MODES:
        assert result['seed_proof'] == WORSE
        assert result['final_cleanup_gain_pp'] == 15
        assert result['deterministic_calls'] == 1
        assert result['deterministic_tool_coverage_pct'] == 0
        assert result['gain_over_score_control_pp'] == (13 if has_control else None)
    again = runner.run_cell(output, config, make_session.pack, model, effort, make_session.evaluator, generator=generate)
    assert again == result and len(calls) == (2 if mode == 'correctness' else 1)


@pytest.mark.skipif(shutil.which('codex') is None, reason='Installed CLI unavailable')
@pytest.mark.parametrize('model,effort,mode', [('gpt-6-astra', 'low', 'correctness'),
                                            ('gpt-6-astra', 'max', 'score'),
                                            ('gpt-6-luna', 'max', 'score'),
                                            ('gpt-6-astra', 'max', 'score_edges'),
                                            ('gpt-6-astra', 'low', 'score_edges'),
                                            ('gpt-6-luna', 'max', 'score_edges'),
                                            ('gpt-6.1-sol', 'max', 'score_edges'),
                                            ('gpt-6-astra', 'high', 'score_edges')])
def test_real_cli_request_preserves_requested_model_effort_and_mode(tmp_path, model, effort, mode):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            if self.headers.get('Content-Encoding') == 'zstd':
                import zstandard
                raw = zstandard.ZstdDecompressor().decompress(raw)
            received.append(json.loads(raw))
            msg = {'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'status': 'completed',
                   'content': [{'type': 'output_text', 'text': GOOD, 'annotations': []}]}
            response = {'id': 'resp_1', 'object': 'response', 'status': 'completed', 'output': [msg],
                        'usage': {'input_tokens': 20, 'output_tokens': 10, 'total_tokens': 30}}
            payload = ''.join('event: ' + kind + '\ndata: ' + json.dumps(value) + '\n\n' for kind, value in [
                ('response.output_item.added', {'type': 'response.output_item.added', 'output_index': 0, 'item': {**msg, 'status': 'in_progress', 'content': []}}),
                ('response.output_text.delta', {'type': 'response.output_text.delta', 'item_id': 'msg_1', 'output_index': 0, 'content_index': 0, 'delta': GOOD}),
                ('response.output_item.done', {'type': 'response.output_item.done', 'output_index': 0, 'item': msg}),
                ('response.completed', {'type': 'response.completed', 'response': response})])
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Content-Length', str(len(payload.encode())))
            self.end_headers()
            self.wfile.write(payload.encode())

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (tmp_path / 'system.txt').write_text('Exact structural benchmark system')
    args = command(binary=cli_identity()['path'], workspace=tmp_path, system_file=tmp_path / 'system.txt',
                   last_message=tmp_path / 'final.txt', model=model, effort=effort, mode=mode)
    overrides = {'model_provider': 'local_test', 'model_providers.local_test.name': 'Local test only',
                 'model_providers.local_test.base_url': f'http://127.0.0.1:{server.server_port}/v1',
                 'model_providers.local_test.wire_api': 'responses',
                 'model_providers.local_test.request_max_retries': 0,
                 'model_providers.local_test.stream_max_retries': 0,
                 'features.enable_request_compression': False}
    args = args[:-1] + [v for k, value in overrides.items() for v in ('-c', k + '=' + json.dumps(value))] + ['-']
    try:
        proc = subprocess.run(args, input='Exact task context', text=True, capture_output=True, timeout=30, cwd=tmp_path)
    finally:
        server.shutdown()
        server.server_close()
    assert proc.returncode == 0, proc.stderr
    assert len(received) == 1
    request = received[0]
    assert request['model'] == model and request['reasoning']['effort'] == effort
    assert request.get('tools') or any(item.get('tools') for item in request['input'])
    sent = [item for item in request['input'] if item.get('type') == 'message']
    assert [m['content'][0]['text'] for m in sent] == ['Exact structural benchmark system', tool_instructions(mode), 'Exact task context']
    assert parse_events([json.loads(line) for line in proc.stdout.splitlines()], GOOD, 0)['status'] == 'received'
