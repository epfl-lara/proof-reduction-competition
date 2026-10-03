"""Offline audits of deterministic edit evidence, policy gates and shared jobs."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import audit_combined_matrix as audit
import proof_eval.experiments as experiments
import run_combined_matrix as runner
from proof_eval.one_shot import fingerprint
from proof_eval.optimizer import Edit
from test_one_shot_audit import evidence, read, write
from test_validity_repair_audit import repair


@pytest.fixture
def combined(repair, monkeypatch):
    base = repair.base
    repair.execute()
    real_root = Path(runner.__file__).resolve().parent.parent
    for path in ('src/run_combined_matrix.py', 'src/run_repair_matrix.py'):
        (base.repo / path).write_bytes((real_root / path).read_bytes())
    monkeypatch.setattr(runner, 'ROOT', base.repo)
    monkeypatch.setattr(audit, 'ROOT', base.repo)
    source_paths = ('src/run_repair_matrix.py', 'src/run_validity_repair.py', 'src/validity_feedback.py')
    prior = {
        'base_directory': str(base.root), 'base_config_sha256': audit.digest(base.root / 'config.json'),
        'base_index_sha256': audit.digest(base.root / 'cell_index.json'),
        'base_input_hashes_sha256': audit.digest(base.root / 'input_hashes.json'),
        'input_files_sha256': {'inputs/sample.json': audit.digest(base.input_path)},
        'input_sha256': {'sample': fingerprint(base.pack)},
        'cells': [{'key': repair.key, 'logical': ['sample', 'plain', 'fixture/model']}],
        'code_sha256': {p: audit.digest(base.repo / p) for p in source_paths},
    }
    write(repair.output / 'matrix_config.json', prior)
    args = SimpleNamespace(input=repair.output, output=base.repo.parent / 'combined', workers=2, watch=True,
                           poll_seconds=1, dataset=base.dataset_path, environments=base.environment_path,
                           cache=base.repo / '.proof-eval')
    _, _, root, _, matrix, packs = runner.prepare(args)
    write(root / 'matrix_config.json', matrix)
    better = base.record['extracted_proof']

    class Evaluator:
        def evaluate(self, name, code, *, versions='all'):
            assert name == 'sample'
            result = repair.evaluation(code, factor=.5 if code == better else 1)
            for item in result['per_version'].values():
                item.update(cached=True, elapsed_seconds=0.0, diagnostics=[])
            if versions == 'primary':
                result['per_version'] = {'v1': result['per_version']['v1']}
                result['scores'].update(combined_pct=None, compatibility_pct=None)
                result['status'] = 'incomplete'
            return result

    def discovery(evaluator, row, code, method, budget, **kwargs):
        edits = [[Edit(0, len(code), better, 'fixture improvement')]] if method == 'lint' and code != better else []
        return edits, 'best_pool', {'analysis_requests': 0}

    monkeypatch.setattr(experiments, 'discovery', discovery)
    control_key = runner.job_key('sample', base.pack['proof'])
    proposal_key = runner.job_key('sample', better)
    results = {}
    jobs = {}
    for key, proof, origin in (
        (control_key, base.pack['proof'], {'kind': 'control', 'name': 'sample'}),
        (proposal_key, better, {'kind': 'proposal', 'cell_key': repair.key}),
    ):
        jobs[key] = {'name': 'sample', 'proof': proof, 'proof_sha256': runner.sha(proof), 'origins': [origin]}
        results[key] = runner.cleanup_proof(evaluator=Evaluator(), row=base.pack['row'], proof=proof,
                                            folder=root / 'jobs' / key,
                                            provenance=runner.cleanup_provenance(matrix, 'sample'))
    cell = matrix['cells'][0]
    snapshot, repair_record = runner.snapshot_repair(repair.output, cell, base.pack)
    write(root / 'repair_snapshots' / (repair.key + '.json'), snapshot)
    record = runner.select_cell(cell=cell, pack=base.pack, repair=repair_record, snapshot=snapshot,
                                control=results[control_key], proposal=results[proposal_key])
    write(root / 'cells' / repair.key / 'result.json', record)
    runner.publish(root, matrix, jobs, results, {repair.key: snapshot}, {repair.key: record}, {}, 'complete', 'complete')
    return SimpleNamespace(root=root, matrix=matrix, base=base, repair=repair, row=base.pack['row'],
                           reference=json.loads(base.reference_path.read_text().splitlines()[0]),
                           control=root / 'jobs' / control_key, proposal=root / 'jobs' / proposal_key,
                           control_key=control_key, proposal_key=proposal_key, record=record)


def check_job(fixture, complete=True):
    return audit.audit_cleanup_job(fixture.control, fixture.row, fixture.reference,
                                   initial=fixture.base.pack['proof'],
                                   provenance=runner.cleanup_provenance(fixture.matrix, 'sample'), complete=complete)


def edit_events(path, mutate):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    mutate(rows)
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))


def test_complete_matrix_checks_real_optimizer_events_without_lean_or_models(combined):
    before = {p: p.read_bytes() for p in combined.root.rglob('*.json')}
    report = audit.audit_combined_matrix(combined.root, complete=True)
    assert report['checked_cells'] == report['checked_controls'] == 1
    assert report['checked_jobs'] == 2 and report['checked_stages'] == 20
    assert report['accepted_transitions'] == 1
    assert report['unchanged_cached_references_checked'] == 2
    assert before == {p: p.read_bytes() for p in combined.root.rglob('*.json')}


def test_engineering_job_audit_does_not_require_published_registry_or_cells(combined):
    for filename in ('jobs.json', 'controls.json', 'arrivals.json', 'summary.json'):
        (combined.root / filename).unlink()
    (combined.root / 'cells' / combined.repair.key / 'result.json').unlink()
    report = audit.audit_combined_matrix(combined.root)
    assert report['checked_jobs'] == 2 and report['checked_cells'] == report['checked_controls'] == 0
    with pytest.raises(ValueError, match='Missing complete job registry'):
        audit.audit_combined_matrix(combined.root, complete=True)


def test_job_budget_cannot_change(combined):
    path = combined.control / 'job_config.json'
    spec = read(path)
    spec['budget']['trials'] = 64
    write(path, spec)
    with pytest.raises(ValueError, match='method order or budget changed'):
        check_job(combined)


def test_matrix_budget_cannot_change(combined):
    path = combined.root / 'matrix_config.json'
    matrix = read(path)
    matrix['budget']['rounds'] = 6
    write(path, matrix)
    with pytest.raises(ValueError, match='Matrix method budget changed'):
        audit.audit_combined_matrix(combined.root)


def test_accepted_score_is_recomputed(combined):
    path = combined.control / 'stages/01_lint/trials.jsonl'
    def mutate(rows):
        next(row for row in rows if row['kind'] == 'accepted')['score'] += 1
    edit_events(path, mutate)
    with pytest.raises(ValueError, match='Accepted score'):
        check_job(combined)


def test_accepted_edit_must_produce_exact_candidate(combined):
    path = combined.control / 'stages/01_lint/trials.jsonl'
    def mutate(rows):
        next(row for row in rows if row['kind'] == 'accepted')['edits'][0]['replacement'] = combined.base.pack['proof']
    edit_events(path, mutate)
    with pytest.raises(ValueError, match='Acceptance edits differ'):
        check_job(combined)


def test_authoritative_policy_evidence_cannot_be_silently_replaced(combined):
    path = combined.control / 'stages/01_lint/trials.jsonl'
    def mutate(rows):
        candidate = next(row for row in rows if row['kind'] == 'candidate')
        candidate['authoritative_evaluation']['scores']['combined_pct'] += 1
    edit_events(path, mutate)
    with pytest.raises(ValueError, match='matching authoritative policy evidence'):
        check_job(combined)


def test_true_raw_pass_cannot_be_labeled_ineligible(combined):
    path = combined.control / 'policy_events.jsonl'
    edit_events(path, lambda rows: rows[0].update(eligible=False))
    with pytest.raises(ValueError, match='Eligibility policy differs'):
        check_job(combined)


def test_full_version_failure_cannot_be_hidden_by_compatibility_score(combined):
    path = combined.control / 'initial_evaluation.json'
    evaluation = read(path)
    evaluation['per_version']['v2'].update(status='failed', passed=False, heartbeats=None, heartbeat_reduction_pct=None)
    evaluation['scores']['compatibility_pct'] = 50
    evaluation['scores']['combined_pct'] = sum(evaluation['scores'][f] for f in audit.FIELDS[:3]) / 3
    write(path, evaluation)
    with pytest.raises(ValueError, match='not all required versions passed'):
        check_job(combined)


def test_deduplicated_origin_mapping_is_audited(combined):
    path = combined.root / 'jobs.json'
    manifest = read(path)
    manifest['jobs'][combined.control_key]['origins'].append({'kind': 'proposal', 'cell_key': combined.repair.key})
    write(path, manifest)
    with pytest.raises(ValueError, match='job origins differ'):
        audit.audit_combined_matrix(combined.root)


def test_result_selected_branch_and_rescue_flags_are_reconstructed(combined):
    path = combined.root / 'cells' / combined.repair.key / 'result.json'
    record = read(path)
    record['rescued_vs_d1'] = not record['rescued_vs_d1']
    write(path, record)
    with pytest.raises(ValueError, match='selection, rescue eligibility, or provenance changed'):
        audit.audit_combined_matrix(combined.root)


def test_cached_reference_invariance_is_exact(combined):
    path = combined.base.repo / '.proof-eval/references/context-v2.json'
    record = read(path)
    record['measured_at'] = 'changed'
    write(path, record)
    with pytest.raises(ValueError, match='Cached reference bytes/fields changed'):
        audit.audit_combined_matrix(combined.root)


def test_incomplete_discovery_cannot_be_labeled_complete(combined):
    path = combined.proposal / 'stages/01_lint/result.json'
    stage = read(path)
    stage['stop_reason'] = 'discovery_unavailable'
    write(path, stage)
    job_path = combined.proposal / 'result.json'
    job = read(job_path)
    job['stages'][0] = stage
    job['stage_result_sha256']['stages/01_lint/result.json'] = audit.digest(path)
    write(job_path, job)
    with pytest.raises(ValueError, match='Incomplete discovery mislabeled complete'):
        audit.audit_cleanup_job(combined.proposal, combined.row, combined.reference)


def test_raw_job_identity_and_normalized_evaluator_identity_are_both_checked(combined):
    path = combined.control / 'input.lean'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='raw input hash changed'):
        check_job(combined)


@pytest.mark.parametrize('field', ('code_sha256', 'contexts', 'input_files_sha256'))
def test_inherited_provenance_cannot_be_removed_or_replaced(combined, field):
    path = combined.root / 'matrix_config.json'
    matrix = read(path)
    matrix[field] = {}
    write(path, matrix)
    with pytest.raises(ValueError, match='manifest changed|contexts changed|input pin changed'):
        audit.audit_combined_matrix(combined.root)


def test_partial_audit_allows_a_new_locked_job_before_configuration(combined):
    shutil.rmtree(combined.proposal)
    combined.proposal.mkdir()
    (combined.proposal / '.job.lock').touch()
    (combined.root / 'cells' / combined.repair.key / 'result.json').unlink()
    report = audit.audit_combined_matrix(combined.root)
    assert report['checked_jobs'] == 1 and report['checked_cells'] == 0
    with pytest.raises(ValueError, match='Cleanup job missing configuration'):
        audit.audit_combined_matrix(combined.root, complete=True)


@pytest.fixture
def exported(combined):
    from report_combined_matrix import build_report, export_conditions
    report, config, records, *_ = build_report(combined.root)
    exports = export_conditions(combined.root, combined.root, report, config, records)
    assert len(exports) == 1
    return combined, combined.root / exports[0]['manifest']


def test_complete_export_evidence_is_audited(exported):
    combined, _ = exported
    assert audit.audit_combined_matrix(combined.root, complete=True)['checked_exports'] == 1


@pytest.mark.parametrize('mutation,match', (
    ('mean', 'Export score arithmetic'),
    ('gain', 'Export gain arithmetic'),
    ('problems', 'Export evidence'),
    ('job_hashes', 'Export job hashes changed'),
    ('selected_from', 'Export branch identity changed'),
))
def test_export_cannot_drop_evidence_or_misstate_means(exported, mutation, match):
    combined, path = exported
    manifest = read(path)
    if mutation == 'mean':
        manifest['selected_mean']['combined_pct'] += .2
    elif mutation == 'gain':
        manifest['gain_over_control_pp'] += .2
    elif mutation == 'problems':
        manifest['problems'] = []
    elif mutation == 'job_hashes':
        manifest['problems'][0]['job_result_sha256'] = {}
    else:
        manifest['problems'][0]['selected_from'] = 'f'
    write(path, manifest)
    with pytest.raises(ValueError, match=match):
        audit.audit_combined_matrix(combined.root)
