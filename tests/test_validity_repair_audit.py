"""Offline reconstruction tests for correctness-only stopping and feedback."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import audit_validity_repair as audit
import run_validity_repair as runner
from proof_eval.metrics import token_count, validate_candidate
from proof_eval.one_shot import FIELDS, fingerprint, zero_evaluation
from test_one_shot_audit import evidence, read, sha, write


@pytest.fixture
def repair(evidence, monkeypatch):
    real_root = Path(runner.__file__).resolve().parent.parent
    for relative in ('src/run_validity_repair.py', 'src/validity_feedback.py'):
        target = evidence.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((real_root / relative).read_bytes())
    for version, record in evidence.references.items():
        write(evidence.repo / '.proof-eval/references' / ('context-' + version + '.json'), record)
    monkeypatch.setattr(runner, 'ROOT', evidence.repo)
    monkeypatch.setattr(audit, 'ROOT', evidence.repo)
    output = evidence.repo.parent / 'repair'
    key = evidence.cell.name
    folder = output / 'cells' / key
    state = SimpleNamespace(calls=0, evaluations=0)

    def evaluation(code, status='passed', factor=.5):
        result = deepcopy(evidence.pack['incumbent'])
        normalized, body = validate_candidate(evidence.row, code)
        length = token_count(body)
        result['candidate'] = {'length': length, 'code_sha256': sha(normalized)}
        result['status'] = status
        if status == 'passed':
            for version, item in result['per_version'].items():
                item['heartbeats'] = evidence.references[version]['heartbeats'] * factor
                item['heartbeat_reduction_pct'] = 100 * (1 - factor)
            result['scores']['length_reduction_pct'] = 100 * (1 - length / evidence.row['proof_length'])
            result['scores']['heartbeat_reduction_pct'] = 100 * (1 - factor)
            result['scores']['combined_pct'] = sum(result['scores'][f] for f in FIELDS[:3]) / 3
        else:
            result['scores'] = dict.fromkeys(FIELDS, 0.0)
            for item in result['per_version'].values():
                item.update(status='failed', passed=False, heartbeats=None, heartbeat_reduction_pct=None,
                            diagnostics=[{'severity': 'error', 'data': 'unsolved goals\n⊢ True'}])
        return result

    def initial(kind='failed'):
        record = deepcopy(evidence.record)
        if kind == 'valid':
            return record
        code = evidence.row['statement'] + ' := by exact missingProof'
        record.update(accepted=False, all_versions_passed=False, selected_proof=evidence.pack['proof'],
                      selected_evaluation=deepcopy(evidence.pack['incumbent']))
        record['generation'] = deepcopy(record['generation'])
        record['generation']['content'] = code
        record['extracted_proof'] = code
        record['evaluation'] = evaluation(code, 'failed')
        if kind == 'empty':
            record.pop('extracted_proof')
            record['generation']['content'] = ''
            record['evaluation'] = zero_evaluation('empty_final_content')
        elif kind == 'unavailable':
            record.pop('extracted_proof')
            record['generation'] = {'status': 'transport_error', 'error': 'mocked'}
            record['evaluation'] = {'status': 'unavailable', 'per_version': {}, 'scores': dict.fromkeys(FIELDS, None)}
        return record

    def configure(record, max_rounds=3):
        write(evidence.cell / 'result.json', record)
        write(evidence.cell / 'generation.json', record['generation'])
        config = {
            'schema_version': 1, 'base_directory': str(evidence.root),
            'base_config_sha256': audit.digest(evidence.root / 'config.json'), 'base_names': ['sample'],
            'cells': [{'key': key, 'logical': ['sample', 'plain', 'fixture/model'],
                       'result_sha256': audit.digest(evidence.cell / 'result.json'),
                       'request_sha256': audit.digest(evidence.cell / 'request.json'),
                       'input_sha256': fingerprint(evidence.pack)}],
            'max_rounds': max_rounds, 'timeout': 1800, 'system_sha256': fingerprint(runner.SYSTEM),
            'code_sha256': {p: audit.digest(evidence.repo / p)
                           for p in ('src/run_validity_repair.py', 'src/validity_feedback.py')},
            'protocol': 'correctness-only fixture',
        }
        write(output / 'config.json', config)
        return config

    def execute(record=None, responses=None, max_rounds=3):
        record = initial() if record is None else record
        responses = [(evidence.record['extracted_proof'], 'passed', .5)] if responses is None else responses
        configure(record, max_rounds)
        response_iter = iter(responses)
        pending = {}

        class Client:
            api_key = 'offline-test-dummy'

            def create_chat_completion(self, **kwargs):
                state.calls += 1
                response = next(response_iter)
                if isinstance(response, BaseException):
                    raise response
                code, status, factor = response
                pending[code] = evaluation(code, status, factor) if code else None
                return SimpleNamespace(content=code, finish_reason='stop', usage={}, model='fixture/model',
                                       raw={}, reasoning_content=None)

        class Evaluator:
            def evaluate(self, name, code, versions):
                assert name == 'sample' and versions == 'all'
                state.evaluations += 1
                return pending[code]

        return runner.repair_cell(base_record=record, base_request=read(evidence.cell / 'request.json'),
                                  pack=evidence.pack, folder=folder, client=Client(), evaluator=Evaluator(),
                                  max_rounds=max_rounds, timeout=1800)

    return SimpleNamespace(base=evidence, output=output, folder=folder, key=key, state=state,
                           evaluation=evaluation, initial=initial, configure=configure, execute=execute)


def test_complete_repair_audit_reconstructs_messages_and_selection_read_only(repair):
    result = repair.execute()
    assert result['outcome'] == 'repaired_valid' and repair.state.calls == 1
    before = {p: p.read_bytes() for p in repair.output.rglob('*.json')}
    report = audit.audit_validity_repair(repair.output, complete=True)
    assert report['checked_cells'] == 1 and report['checked_rounds'] == 1
    assert report['started_repair_requests'] == 1
    assert report['accepted_improvements'] == 1
    assert report['unchanged_cached_references_checked'] == 2
    assert before == {p: p.read_bytes() for p in repair.output.rglob('*.json')}
    assert repair.state.calls == repair.state.evaluations == 1


@pytest.mark.parametrize('kind,outcome', [('valid', 'already_valid'), ('empty', 'no_candidate'),
                                        ('unavailable', 'unavailable')])
def test_valid_empty_and_unavailable_controls_do_not_make_repair_calls(repair, kind, outcome):
    result = repair.execute(repair.initial(kind), responses=[])
    assert result['outcome'] == outcome and repair.state.calls == 0
    report = audit.audit_validity_repair(repair.output, complete=True)
    assert report['checked_rounds'] == 0


def test_first_valid_candidate_stops_even_when_score_is_worse(repair):
    code = repair.base.pack['proof']
    result = repair.execute(responses=[(code, 'passed', 10.0)])
    assert result['final_valid'] and result['returned_incumbent']
    assert not result['accepted'] and result['round_count'] == 1
    assert result['final_evaluation']['scores']['combined_pct'] < repair.base.pack['incumbent']['scores']['combined_pct']
    report = audit.audit_validity_repair(repair.output, complete=True)
    assert report['accepted_improvements'] == 0 and report['returned_incumbents'] == 1


def test_three_failed_repairs_stop_at_fixed_budget(repair):
    code = repair.initial()['extracted_proof']
    result = repair.execute(responses=[(code, 'failed', 1)] * 3)
    assert result['outcome'] == 'repair_budget_exhausted' and result['round_count'] == 3
    assert audit.audit_validity_repair(repair.output, complete=True)['checked_rounds'] == 3


def test_partial_missing_cell_is_allowed_only_without_complete(repair):
    repair.configure(repair.initial())
    report = audit.audit_validity_repair(repair.output)
    assert report['checked_cells'] == 0 and report['partial_cells'] == 1
    with pytest.raises(ValueError, match='Missing repair cell'):
        audit.audit_validity_repair(repair.output, complete=True)


def test_partial_inflight_round_is_allowed_without_fabricating_a_result(repair):
    repair.execute()
    (repair.folder / 'result.json').unlink()
    (repair.folder / 'rounds/01/result.json').unlink()
    report = audit.audit_validity_repair(repair.output)
    assert report['partial_cells'] == 1 and report['checked_rounds'] == 0
    assert report['started_repair_requests'] == 1
    with pytest.raises(ValueError, match='Missing completed repair cell'):
        audit.audit_validity_repair(repair.output, complete=True)


@pytest.mark.parametrize('mutation', ['feedback', 'messages', 'settings'])
def test_performance_feedback_or_changed_request_settings_are_rejected(repair, mutation):
    repair.execute()
    folder = repair.folder / 'rounds/01'
    if mutation == 'feedback':
        value = read(folder / 'feedback.json')
        value['candidate_score'] = 99
        write(folder / 'feedback.json', value)
    else:
        value = read(folder / 'request.json')
        if mutation == 'messages':
            value['messages'][1]['content'] += '\nYour combined score is 99; optimize again.'
        else:
            value['temperature'] = .9
        write(folder / 'request.json', value)
    with pytest.raises(ValueError, match='feedback changed|messages or inherited settings changed'):
        audit.audit_validity_repair(repair.output, complete=True)


def test_round_after_first_valid_candidate_is_rejected(repair):
    repair.execute()
    (repair.folder / 'rounds/02').mkdir()
    with pytest.raises(ValueError, match='round follows a valid, unavailable, or empty output'):
        audit.audit_validity_repair(repair.output)


def test_early_stop_before_correctness_budget_is_rejected(repair):
    code = repair.initial()['extracted_proof']
    repair.execute(responses=[(code, 'failed', 1)] * 3)
    for folder in (repair.folder / 'rounds/02', repair.folder / 'rounds/03'):
        for path in folder.iterdir():
            path.unlink()
        folder.rmdir()
    with pytest.raises(ValueError, match='stopped before its correctness round budget'):
        audit.audit_validity_repair(repair.output)


@pytest.mark.parametrize('field', ['accepted', 'returned_incumbent', 'round_count', 'outcome', 'final_proof'])
def test_final_decisions_are_recomputed_after_the_loop(repair, field):
    repair.execute()
    record = read(repair.folder / 'result.json')
    value = record[field]
    record[field] = not value if isinstance(value, bool) else 999 if isinstance(value, int) else 'wrong'
    write(repair.folder / 'result.json', record)
    with pytest.raises(ValueError, match='Final repair record differs'):
        audit.audit_validity_repair(repair.output, complete=True)


def test_round_proof_must_equal_extracted_generation(repair):
    repair.execute()
    path = repair.folder / 'rounds/01/result.json'
    trial = read(path)
    trial['proof'] = repair.base.pack['proof']
    write(path, trial)
    with pytest.raises(ValueError, match='proof differs from final content'):
        audit.audit_validity_repair(repair.output)


def test_round_evaluation_arithmetic_is_independently_checked(repair):
    repair.execute()
    path = repair.folder / 'rounds/01/result.json'
    trial = read(path)
    trial['evaluation']['scores']['combined_pct'] += 1
    write(path, trial)
    with pytest.raises(ValueError, match='combined_pct'):
        audit.audit_validity_repair(repair.output)


@pytest.mark.parametrize('artifact', ['source', 'base_result', 'base_config', 'cache'])
def test_frozen_implementation_initial_evidence_and_references_cannot_change(repair, artifact):
    repair.execute()
    if artifact == 'source':
        path = repair.base.repo / 'src/validity_feedback.py'
        path.write_text(path.read_text() + '\n# changed\n')
    elif artifact == 'base_result':
        path = repair.base.cell / 'result.json'
        path.write_text(path.read_text() + '\n')
    elif artifact == 'base_config':
        path = repair.base.root / 'config.json'
        path.write_text(path.read_text() + '\n')
    else:
        path = repair.base.repo / '.proof-eval/references/context-v2.json'
        value = read(path)
        value['measured_at'] = 'remeasured'
        write(path, value)
    with pytest.raises(ValueError, match='implementation changed|Initial result bytes changed|Base configuration changed|Cached reference changed'):
        audit.audit_validity_repair(repair.output)


def test_nonempty_truncated_initial_output_is_labeled_output_recovery(repair):
    record = repair.initial()
    record.pop('extracted_proof')
    record['generation']['finish_reason'] = 'length'
    record['evaluation'] = zero_evaluation('generation_truncated')
    result = repair.execute(record)
    assert result['initial_kind'] == 'output_recovery'
    assert audit.audit_validity_repair(repair.output, complete=True)['checked_rounds'] == 1


def test_primary_success_and_high_score_do_not_skip_required_version_repairs(repair):
    record = deepcopy(repair.base.record)
    result = deepcopy(record['evaluation'])
    result['per_version']['v2'].update(status='failed', passed=False, heartbeats=None, heartbeat_reduction_pct=None,
                                     diagnostics=[{'severity': 'error', 'data': 'unknown constant in older version'}])
    result['scores']['compatibility_pct'] = 50
    result['scores']['combined_pct'] = sum(result['scores'][field] for field in FIELDS[:3]) / 3
    assert result['scores']['combined_pct'] > repair.base.pack['incumbent']['scores']['combined_pct']
    record.update(evaluation=result, selected_evaluation=result, all_versions_passed=False)
    final = repair.execute(record)
    assert final['initial_kind'] == 'compiler_repair' and not final['initial_valid']
    assert final['round_count'] == 1 and repair.state.calls == 1
    assert audit.audit_validity_repair(repair.output, complete=True)['checked_rounds'] == 1


@pytest.mark.parametrize('kind', ['empty', 'unavailable'])
def test_no_round_may_follow_empty_or_unavailable_output(repair, kind):
    repair.execute(repair.initial(kind), responses=[])
    (repair.folder / 'rounds/01').mkdir(parents=True)
    with pytest.raises(ValueError, match='round follows a valid, unavailable, or empty output'):
        audit.audit_validity_repair(repair.output)


def test_transport_error_stops_repairs_and_keeps_candidate_scores_unknown(repair):
    result = repair.execute(responses=[RuntimeError('mocked transport failure')])
    assert result['outcome'] == 'unavailable' and result['round_count'] == 1
    assert not result['accepted'] and repair.state.evaluations == 0
    assert audit.audit_validity_repair(repair.output, complete=True)['checked_rounds'] == 1


def test_empty_repair_output_stops_instead_of_regenerating(repair):
    result = repair.execute(responses=[('', 'invalid', 1)])
    assert result['outcome'] == 'repair_returned_no_candidate' and result['round_count'] == 1
    assert repair.state.calls == 1 and repair.state.evaluations == 0
    assert audit.audit_validity_repair(repair.output, complete=True)['checked_rounds'] == 1


def test_wrapper_provenance_does_not_change_frozen_repair_cell_spec(repair):
    repair.execute()
    wrapper = repair.base.repo / 'src/run_repair_matrix.py'
    wrapper.write_text('# standalone matrix wrapper\n')
    config = read(repair.output / 'config.json')
    config['code_sha256']['src/run_repair_matrix.py'] = audit.digest(wrapper)
    write(repair.output / 'config.json', config)
    assert audit.audit_validity_repair(repair.output, complete=True)['checked_cells'] == 1
    wrapper.write_text('# changed matrix wrapper\n')
    with pytest.raises(ValueError, match='repair implementation changed'):
        audit.audit_validity_repair(repair.output, complete=True)
