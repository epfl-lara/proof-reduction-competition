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

    def make(mode='score', folder=None):
        return ProofSession(folder or tmp_path / 'ledger', pack, evaluator, mode)
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


def test_actual_workspace_client_and_host_ledger(make_session, tmp_path):
    session = make_session()
    work = tmp_path / 'workspace'
    work.mkdir()
    (work / 'tools.py').write_text((Path(__file__).parents[1] / 'src/proof_agent_client.py').read_text())
    (work / 'candidate.lean').write_text(GOOD)
    with ProofToolService(session, work):
        proc = subprocess.run([sys.executable, str(work / 'tools.py'), 'check', 'candidate.lean'],
                              cwd=tmp_path, text=True, capture_output=True, timeout=15)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['total_score'] == 70
    assert session.best_code == GOOD
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


@pytest.mark.parametrize('mode', ['correctness', 'score'])
def test_runner_repairs_or_searches_and_resume_does_not_regenerate(make_session, tmp_path, monkeypatch, mode):
    import run_agent_harness as runner
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'guard', lambda *a: None)
    monkeypatch.setattr(runner, 'messages', lambda _: [{'role': 'system', 'content': 'system'}, {'role': 'user', 'content': 'task'}])
    monkeypatch.setattr(runner, 'original_evaluation', lambda _: deepcopy(make_session.seed))
    control_path = tmp_path / 'control.json'
    control_path.write_text('{}')
    monkeypatch.setattr(runner, 'historical', lambda *a: (control_path, {'selected_evaluation': evaluation(55)}))
    monkeypatch.setattr(runner, 'structural_control', lambda *a: (None, None))
    config = {'mode': mode, 'max_outer_correctness_repairs': 3 if mode == 'correctness' else 0,
              'cli': {}, 'historical_control_sha256': {'control.json': runner.digest(control_path)},
              'structural_control_sha256': {}}
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
        return {'status': 'received', 'content': code, 'finish_reason': 'stop', 'usage': {'completion_tokens': 10}}

    output = tmp_path / 'run'
    result = runner.run_cell(output, config, make_session.pack, 'gpt-6-astra', 'max', make_session.evaluator, generator=generate)
    assert result['selected_proof'] == GOOD and result['selected_evaluation']['scores']['combined_pct'] == 70
    assert result['status'] == 'complete'
    assert len(calls) == (2 if mode == 'correctness' else 1)
    if mode == 'correctness':
        assert 'correctness_feedback' in calls[1][1]['content']
        assert 'heartbeat' not in calls[1][1]['content']
    again = runner.run_cell(output, config, make_session.pack, 'gpt-6-astra', 'max', make_session.evaluator, generator=generate)
    assert again == result and len(calls) == (2 if mode == 'correctness' else 1)


@pytest.mark.skipif(shutil.which('codex') is None, reason='Installed CLI unavailable')
@pytest.mark.parametrize('model,effort,mode', [('gpt-6-astra', 'low', 'correctness'),
                                            ('gpt-6-astra', 'max', 'score'),
                                            ('gpt-6-luna', 'max', 'score')])
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
