"""Read-only evidence audit for deterministic controls and model-proof cleanup.

The audit reconstructs accepted edits and score arithmetic from saved compiler
outcomes. It never launches Lean, calls a model, or refreshes reference values.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean

from audit_experiments import _close, _evaluation, _named, _proof, _require, _rows
from audit_validity_repair import _saved_evaluation
from proof_eval.dataset import Dataset
from proof_eval.experiments import compact
from proof_eval.one_shot import FIELDS, fingerprint
from proof_eval.optimizer import Edit, apply_edits
from run_combined_matrix import (BUDGET, COMPLETE_STOPS, COUNTERS, EXTRA_CODE, METHODS, cleanup_provenance,
                                 job_key, score, select_cell, sha, versions)
from run_deterministic import digest, write_json
from validity_feedback import all_versions_passed


ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(Path(path).read_text())


def valid(row, reference, proof, evaluation, label):
    _evaluation(row, reference, proof, evaluation, label)
    _require(all_versions_passed(evaluation, versions(row)), label + ': not all required versions passed')


def _policy(event, row, reference, proof):
    raw = event['evaluation']
    _require(event['kind'] == 'all_version_eligibility' and event['name'] == row['name']
             and event['proof_sha256'] == sha(proof), 'Policy proof identity changed')
    _require(event['required_versions'] == versions(row), 'Policy required versions changed')
    _saved_evaluation(row, reference, proof, raw, 'policy/' + sha(proof))
    eligible = raw['status'] == 'passed' and all_versions_passed(raw, versions(row))
    status = 'policy_compatibility_rejected' if raw['status'] == 'passed' and not eligible else raw['status']
    expected = {'eligible': eligible, 'optimizer_status': status, 'authoritative_status': raw['status'],
                'reason': None if eligible else 'exact_required_versions_not_all_passed_or_score_unavailable'}
    _require(all(event.get(k) == value for k, value in expected.items()), 'Eligibility policy differs from raw verification')
    return expected


def _primary(row, reference, proof, result):
    """Check score arithmetic of a candidate pruned after its primary check."""
    if result['status'] in ('invalid', 'failed'):
        _require(all(result['scores'][f] == 0 for f in FIELDS), 'Pruned failed candidate has nonzero scores')
        return
    if result['status'] == 'passed' and set(result['per_version']) == set(versions(row)):
        _evaluation(row, reference, proof, result, 'single-version primary candidate')
        return
    length = _proof(row, proof, result, 'primary candidate')
    primary = versions(row)[0]
    _require(set(result['per_version']) == {primary}, 'Pruned candidate has unexpected version checks')
    item = result['per_version'][primary]
    if item.get('passed'):
        _close(result['scores']['length_reduction_pct'], 100 * (1 - length / row['proof_length']), 'Primary length score')
        _close(result['scores']['heartbeat_reduction_pct'],
               100 * (1 - item['heartbeats'] / reference['per_version'][primary]['heartbeats']), 'Primary heartbeat score')
    _require(result['scores']['combined_pct'] is None, 'Pruned partial candidate has a full score')


def audit_cleanup_job(folder, row, reference, *, initial=None, provenance=None, complete=False):
    folder = Path(folder)
    spec = read(folder / 'job_config.json')
    _require(spec['name'] == row['name'] and spec['row_sha256'] == fingerprint(row), 'Cleanup row identity changed')
    _require(spec['methods'] == list(METHODS) and spec['budget'] == asdict(BUDGET), 'Cleanup method order or budget changed')
    _require(spec['required_versions'] == versions(row), 'Cleanup version cohort changed')
    if provenance is not None:
        _require(spec['provenance'] == provenance, 'Cleanup provenance changed')
    if not (folder / 'input.lean').exists():
        _require(not complete and not (folder / 'result.json').exists(), 'Missing cleanup input')
        return {'status': 'partial', 'checked_stages': 0, 'accepted_transitions': 0}
    proof = (folder / 'input.lean').read_text()
    _require(sha(proof) == spec['input_proof_sha256'] and (initial is None or proof == initial), 'Cleanup raw input hash changed')
    initial = proof
    initial_eval = read(folder / 'initial_evaluation.json')
    valid(row, reference, proof, initial_eval, 'job input')
    policy_events = _rows(folder / 'policy_events.jsonl') if (folder / 'policy_events.jsonl').exists() else []
    policy_lookup = {(event['proof_sha256'], fingerprint(event['evaluation'])): event for event in policy_events}
    proof_by_hash = {sha(proof): proof}
    stages, transitions, seen_partial = [], 0, False
    stage_folders = sorted(path for path in (folder / 'stages').glob('*') if path.is_dir())
    _require([p.name for p in stage_folders] == [f'{i:02d}_{method}' for i, method in enumerate(METHODS[:len(stage_folders)], 1)],
             'Cleanup stages are not an ordered method prefix')
    for index, stage in enumerate(stage_folders):
        _require(not seen_partial, 'Completed stage follows an unfinished method')
        method = METHODS[index]
        if not (stage / 'config.json').exists():
            _require(not complete and not list(stage.iterdir()), 'Method lacks configuration')
            seen_partial = True
            continue
        expected_config = {'method': method, 'input_sha256': sha(proof), 'job_config_sha256': fingerprint(spec)}
        _require(read(stage / 'config.json') == expected_config, 'Cleanup stage input/configuration changed')
        start = proof
        events = _rows(stage / 'trials.jsonl') if (stage / 'trials.jsonl').exists() else []
        candidates, accepted, edit_count = {}, {}, 0
        previous_score = score(stages[-1]['final'] if stages else initial_eval)
        for event in events:
            kind = event['kind']
            key = event.get('round'), event.get('trial')
            if kind == 'candidate':
                _require(type(event['round']) is int and 0 <= event['round'] < BUDGET.rounds
                         and type(event['trial']) is int and 1 <= event['trial'] <= BUDGET.trials,
                         'Candidate exceeds the frozen budget')
                proof_by_hash[sha(event['proof'])] = event['proof']
                if event.get('all_versions_requested'):
                    raw = event['authoritative_evaluation']
                    identity = sha(event['proof']), fingerprint(raw)
                    _require(identity in policy_lookup, 'Candidate lacks matching authoritative policy evidence')
                    policy = _policy(policy_lookup[identity], row, reference, event['proof'])
                    _require(event['eligibility_policy'] == policy, 'Candidate eligibility metadata differs')
                    exposed = deepcopy(raw)
                    exposed['status'] = policy['optimizer_status']
                    _require(event['evaluation'] == compact(exposed), 'Optimizer candidate differs from authoritative evidence')
                    improves = policy['eligible'] and score(raw) > previous_score + BUDGET.min_gain
                    _require(event['improves_incumbent'] is improves, 'Candidate improvement decision differs')
                else:
                    _primary(row, reference, event['proof'], event['evaluation'])
                    _require(event['improves_incumbent'] is False, 'Primary-only candidate was accepted')
                candidates[key] = event
            elif kind == 'accepted':
                if key in accepted:
                    _require(accepted[key] == event, 'Conflicting resumed acceptance event')
                    continue
                _require(key in candidates, 'Accepted edit lacks a candidate')
                candidate = candidates[key]
                _require(candidate.get('all_versions_requested') is True and candidate['improves_incumbent'] is True,
                         'Acceptance lacks full eligible improvement')
                _require(candidate['parent_sha256'] == sha(proof), 'Accepted edit has a different parent')
                _require(candidate['edits'] == event['edits'], 'Acceptance edits differ from candidate')
                edits = [Edit(**item) for item in event['edits']]
                _require(all(0 <= e.start <= e.end <= len(proof) for e in edits), 'Accepted edit outside parent')
                _require(apply_edits(proof, edits) == candidate['proof'], 'Accepted edits do not produce the proof')
                valid(row, reference, candidate['proof'], candidate['evaluation'], 'accepted candidate')
                next_score = score(candidate['evaluation'])
                _require(next_score > previous_score + BUDGET.min_gain, 'Accepted gain fails the frozen margin')
                _close(event['score'], next_score, 'Accepted score')
                proof, previous_score = candidate['proof'], next_score
                accepted[key] = event
                edit_count += len(edits)
        transitions += len(accepted)
        result_path = stage / 'result.json'
        if not result_path.exists():
            _require(not complete and not (folder / 'result.json').exists(), 'Missing completed cleanup method')
            seen_partial = True
            continue
        result = read(result_path)
        _require((result['name'], result['source'], result['method']) == (row['name'], row['source'], method), 'Method result identity changed')
        valid(row, reference, start, result['initial'], 'method input')
        valid(row, reference, proof, result['final'], 'method final')
        _require(result['proof'] == proof and result['changed'] is (proof != start), 'Method accepted chain differs from result')
        _require(result['accepted_transitions'] == len(accepted) and result['accepted_edits'] == edit_count,
                 'Method accepted transition counters differ')
        _require(0 <= result['attempts'] <= BUDGET.trials and 0 <= result['rounds'] <= BUDGET.rounds, 'Method budget exceeded')
        _close(score(result['final']), previous_score, 'Method terminal score')
        stages.append(result)
    for event in policy_events:
        if event['proof_sha256'] in proof_by_hash:
            _policy(event, row, reference, proof_by_hash[event['proof_sha256']])
        else:
            # A process can stop after a full evaluation but before its candidate
            # log is saved. Only an unfinished job may have that trailing event.
            _require(not complete and not (folder / 'result.json').exists(), 'Policy evidence has no recorded proof')
    if not (folder / 'result.json').exists():
        _require(not complete, 'Missing completed cleanup job')
        return {'status': 'partial', 'checked_stages': len(stages), 'accepted_transitions': transitions}
    result = read(folder / 'result.json')
    _require(not seen_partial and len(stages) == len(METHODS), 'Terminal job lacks all ten methods')
    _require(result['input_proof'] == initial and result['input_proof_sha256'] == sha(initial), 'Terminal job input changed')
    _require(result['initial_evaluation'] == initial_eval and result['job_config_sha256'] == fingerprint(spec), 'Terminal job provenance changed')
    _require(result['stages'] == stages and result['proof'] == proof, 'Terminal method chain changed')
    valid(row, reference, proof, result['evaluation'], 'job final')
    _close(score(result['evaluation']), score(stages[-1]['final']), 'Job final score')
    hashes = {str(p.relative_to(folder)): digest(p) for p in (folder / 'stages').glob('*/result.json')}
    _require(result['stage_result_sha256'] == hashes, 'Method artifact hashes changed')
    incomplete = [stage['method'] for stage in stages if stage.get('stop_reason') not in COMPLETE_STOPS]
    _require(result['incomplete_methods'] == incomplete and result['status'] ==
             ('incomplete_discovery' if incomplete else 'complete'), 'Incomplete discovery mislabeled complete')
    _require(result['all_versions_valid'] is True and result['changed'] is (proof != initial), 'Job validity/change flag differs')
    for counter in COUNTERS:
        _close(result['counters'][counter], sum(stage.get(counter, 0) for stage in stages), 'Job counter ' + counter)
    if complete:
        _require(not incomplete, 'Cleanup has incomplete discovery')
    return {'status': result['status'], 'checked_stages': len(stages), 'accepted_transitions': transitions}


def audit_combined_matrix(root, *, complete=False):
    root = Path(root).resolve()
    matrix = read(root / 'matrix_config.json')
    base, repair_root = Path(matrix['base_directory']), Path(matrix['repair_directory'])
    _require(matrix['budget'] == asdict(BUDGET) and matrix['methods'] == list(METHODS), 'Matrix method budget changed')
    _require(digest(base / 'config.json') == matrix['base_config_sha256'], 'Base config changed')
    _require(digest(repair_root / 'matrix_config.json') == matrix['repair_matrix_config_sha256'], 'Repair matrix changed')
    base_config, prior = read(base / 'config.json'), read(repair_root / 'matrix_config.json')
    _require(Path(prior['base_directory']).resolve() == base.resolve()
             and prior['base_config_sha256'] == matrix['base_config_sha256'], 'Repair/base provenance changed')
    _require(matrix['contexts'] == base_config['contexts'], 'Pinned compiler contexts changed')
    for field in ('base_index_sha256', 'base_input_hashes_sha256', 'input_files_sha256', 'input_sha256'):
        _require(matrix[field] == prior[field], 'Inherited input pin changed: ' + field)
    expected_code = {**base_config['code_sha256'], **prior['code_sha256'],
                     **{path: digest(ROOT / path) for path in EXTRA_CODE}}
    _require(matrix['code_sha256'] == expected_code, 'Frozen source manifest changed')
    for path, expected in matrix['code_sha256'].items():
        _require(digest(ROOT / path) == expected, 'Frozen source changed: ' + path)
    for field in ('names', 'models', 'arms'):
        _require(matrix[field] == base_config[field] and len(set(matrix[field])) == len(matrix[field]) > 0, 'Matrix cohort changed')
    _require(digest(base / 'cell_index.json') == prior['base_index_sha256'] and
             digest(base / 'input_hashes.json') == prior['base_input_hashes_sha256'], 'Base index/input hashes changed')
    expected = {tuple([name, arm, model]) for name in matrix['names'] for arm in matrix['arms'] for model in matrix['models']}
    planned = {cell['key']: cell for cell in matrix['cells']}
    _require(len(planned) == len(matrix['cells']) == len(expected) and
             {tuple(cell['logical']) for cell in planned.values()} == expected, 'Matrix is not the full declared cohort')
    _require(matrix['cells'] == prior['cells'], 'Declared repair cells changed')
    index = read(base / 'cell_index.json')
    _require({tuple(json.loads(logical)): key for logical, key in index.items()} ==
             {tuple(cell['logical']): key for key, cell in planned.items()}, 'Declared cells differ from the original request index')
    dataset_path, environments = ROOT / 'data/benchmark_data_warmup.jsonl', ROOT / 'environments.local.json'
    _require(digest(dataset_path) == base_config['dataset_sha256'] and
             digest(environments) == base_config['environment_config_sha256'], 'Dataset or environments changed')
    dataset = Dataset(dataset_path)
    references = _named(_rows(ROOT / 'results/deterministic/00_reference_baseline/reference_values.jsonl'), dataset.names, 'References')
    packs = _named([read(base / path) for path in prior['input_files_sha256']], matrix['names'], 'Base inputs')
    for relative, expected_hash in prior['input_files_sha256'].items():
        _require(digest(base / relative) == expected_hash, 'Base input bytes changed')
    cache_count = 0
    for name, pack in packs.items():
        _require(pack['row'] == dataset.get(name) and fingerprint(pack) == matrix['input_sha256'][name], 'Base input identity changed')
        reference = references[name]
        _require(reference['dataset_sha256'] == base_config['dataset_sha256'] and reference['status'] == 'prepared', 'Reference export changed')
        valid(pack['row'], reference, pack['proof'], pack['incumbent'], 'D0/' + name)
        saved = {v: item['reference'] for v, item in pack['incumbent']['per_version'].items()}
        _require(fingerprint(saved) == matrix['references_sha256'][name], 'Frozen reference hash changed')
        for version, value in saved.items():
            current = read(ROOT / '.proof-eval/references' / (matrix['contexts'][name][version] + '.json'))
            _require(current == value, f'Cached reference bytes/fields changed: {name}/{version}')
            exported = reference['per_version'][version]
            for field in ('measured_at', 'heartbeats', 'heartbeats_raw', 'environment_fingerprint', 'reference_code_sha256'):
                actual = exported[field] if field in ('heartbeats', 'heartbeats_raw') else exported['provenance'][field]
                _require(actual == value[field], f'Reference export fields changed: {name}/{version}/{field}')
            cache_count += 1
    _require(matrix['controls'] == {name: job_key(name, pack['proof']) for name, pack in packs.items()}, 'Control identity changed')
    snapshots = read(root / 'arrivals.json') if (root / 'arrivals.json').exists() else {}
    _require(set(snapshots) <= set(planned), 'Unexpected repair arrival')
    repairs, allowed_jobs, origins = {}, {}, {}

    def register(name, proof, origin):
        key = job_key(name, proof)
        allowed_jobs[key] = (name, proof)
        origins.setdefault(key, []).append(origin)

    for name, pack in packs.items():
        register(name, pack['proof'], {'kind': 'control', 'name': name})
    for key, cell in planned.items():
        path = repair_root / 'cells' / key / 'result.json'
        if not path.exists():
            _require(key not in snapshots, 'Frozen repair result disappeared')
            continue
        repair = read(path)
        name = cell['logical'][0]
        _require([repair['name'], repair['arm'], repair['model']] == cell['logical']
                 and repair['base_request_sha256'] == key, 'Repair logical identity changed')
        actual_snapshot = {'repair_result_sha256': digest(path),
                           'repair_cell_config_sha256': digest(path.parent / 'cell_config.json'),
                           'input_sha256': fingerprint(packs[name])}
        _require(read(path.parent / 'cell_config.json')['input_sha256'] == fingerprint(packs[name]),
                 'Repair input identity changed')
        if key in snapshots:
            _require(snapshots[key] == actual_snapshot, 'Consumed repair snapshot changed')
            _require(read(root / 'repair_snapshots' / (key + '.json')) == actual_snapshot, 'Repair snapshot copies differ')
        elif (root / 'jobs.json').exists():
            continue  # A concurrently arriving upstream result is not consumed yet.
        repairs[key] = repair
        valid(packs[name]['row'], references[name], repair['selected_proof'], repair['selected_evaluation'], 'L/' + key)
        is_valid = all_versions_passed(repair['final_evaluation'], versions(packs[name]['row']))
        _require(repair['final_valid'] is is_valid, 'Repair final-valid flag differs')
        if is_valid:
            valid(packs[name]['row'], references[name], repair['final_proof'], repair['final_evaluation'], 'F/' + key)
            register(name, repair['final_proof'], {'kind': 'proposal', 'cell_key': key})
    manifest_path = root / 'jobs.json'
    manifest = read(manifest_path)['jobs'] if manifest_path.exists() else None
    if manifest is not None:
        _require(set(manifest) == set(allowed_jobs), 'Deduplicated job registry differs')
        for key, (name, proof) in allowed_jobs.items():
            entry = manifest[key]
            _require(entry['name'] == name and entry['proof'] == proof and entry['proof_sha256'] == sha(proof), 'Job registry proof identity differs')
            _require(sorted(map(fingerprint, entry['origins'])) == sorted(map(fingerprint, origins[key])), 'Deduplicated job origins differ')
    elif complete:
        raise ValueError('Missing complete job registry')
    job_reports, results = {}, {}
    for folder in sorted(p for p in (root / 'jobs').glob('*') if p.is_dir()):
        _require(folder.name in allowed_jobs, 'Unregistered cleanup proof')
        name, proof = allowed_jobs[folder.name]
        if not (folder / 'job_config.json').exists():
            _require(not complete and all(p.name == '.job.lock' for p in folder.iterdir()), 'Cleanup job missing configuration')
            continue
        job_reports[folder.name] = audit_cleanup_job(folder, packs[name]['row'], references[name], initial=proof,
                                                     provenance=cleanup_provenance(matrix, name), complete=complete)
        if (folder / 'result.json').exists():
            results[folder.name] = read(folder / 'result.json')
    controls = read(root / 'controls.json') if (root / 'controls.json').exists() else {}
    for name, control in controls.items():
        key = matrix['controls'][name]
        _require(control['job_key'] == key and key in results, 'Control physical job differs')
        job = results[key]
        _require(control['proof'] == job['proof'] and control['evaluation'] == job['evaluation']
                 and control['cleanup_status'] == job['status']
                 and control['result_sha256'] == digest(root / 'jobs' / key / 'result.json'), 'Control result changed')
    records = {}
    for path in (root / 'cells').glob('*/result.json'):
        key = path.parent.name
        _require(key in snapshots and key in repairs, 'Combined cell lacks frozen repair input')
        cell, repair = planned[key], repairs[key]
        name = cell['logical'][0]
        control_key = matrix['controls'][name]
        proposal_key = job_key(name, repair['final_proof']) if repair['final_valid'] else None
        _require(control_key in results and (proposal_key is None or proposal_key in results), 'Combined cell lacks cleanup jobs')
        expected_record = select_cell(cell=cell, pack=packs[name], repair=repair, snapshot=snapshots[key],
                                      control=results[control_key], proposal=results.get(proposal_key))
        record = read(path)
        _require(record == expected_record, 'Combined selection, rescue eligibility, or provenance changed')
        valid(packs[name]['row'], references[name], record['selected_proof'], record['selected_evaluation'], 'H/' + key)
        records[key] = record
    if complete:
        _require(set(snapshots) == set(records) == set(planned), 'Combined matrix has missing cells')
        _require(set(controls) == set(matrix['names']) and set(results) == set(allowed_jobs), 'Combined matrix has missing controls/jobs')
        _require(all(r['complete_cleanup'] for r in records.values()), 'Combined matrix includes incomplete cleanup')
    exports = 0
    for path in (root / 'conditions').glob('*/manifest.json'):
        export = read(path)
        _require(export['model'] in matrix['models'] and export['arm'] in matrix['arms'], 'Exported condition is undeclared')
        cohort = {r['name']: r for r in records.values() if r['model'] == export['model'] and r['arm'] == export['arm']}
        _require(set(cohort) == set(matrix['names']) and all(r['complete_cleanup'] for r in cohort.values()), 'Exported condition is incomplete')
        _require(set(controls) == set(matrix['names']) and all(c['cleanup_status'] == 'complete' for c in controls.values()),
                 'Export lacks complete materialized controls')
        _require(export['problem_count'] == len(matrix['names']), 'Export problem count changed')
        _named(export['problems'], matrix['names'], 'Export evidence')
        target = path.parent / 'selected_candidates.jsonl'
        _require(export['matrix_config_sha256'] == digest(root / 'matrix_config.json')
                 and export['candidates_sha256'] == digest(target), 'Export hashes changed')
        rows = _named(_rows(target), matrix['names'], 'Submission')
        _require(all(rows[n]['proof'] == cohort[n]['selected_proof'] for n in matrix['names']), 'Exported proofs differ from selection')
        for label, branch in (('baseline_d0_mean', 'd0'), ('control_d1_mean', 'd1'), ('selected_mean', 'h')):
            for field in FIELDS:
                _close(export[label][field], mean(cohort[n][branch]['evaluation']['scores'][field] for n in matrix['names']),
                       'Export score arithmetic: ' + label + '/' + field)
        _close(export['gain_over_control_pp'], export['selected_mean']['combined_pct'] -
               export['control_d1_mean']['combined_pct'], 'Export gain arithmetic')
        for problem in export['problems']:
            n, record = problem['name'], cohort[problem['name']]
            _require(problem['base_request_sha256'] == record['key'] and problem['selected_from'] == record['selected_from']
                     and problem['control_job_key'] == record['control_job_key']
                     and problem['proposal_job_key'] == record['proposal_job_key'], 'Export branch identity changed')
            _require(problem['combined_result_sha256'] == digest(root / 'cells' / record['key'] / 'result.json'), 'Export cell hash changed')
            _require(problem['repair_result_sha256'] == record['repair_result_sha256'] and
                     problem['selected_scores'] == record['selected_evaluation']['scores'], 'Export selection evidence changed')
            expected_jobs = {job: digest(root / 'jobs' / job / 'result.json') for job in
                             (record['control_job_key'], record['proposal_job_key']) if job is not None}
            _require(problem['job_result_sha256'] == expected_jobs, 'Export job hashes changed')
        exports += 1
    return {'status': 'passed', 'audited_at': datetime.now(timezone.utc).isoformat(), 'complete_required': complete,
            'expected_cells': len(planned), 'checked_cells': len(records), 'expected_controls': len(matrix['names']),
            'checked_controls': len(controls), 'checked_jobs': len(job_reports),
            'checked_stages': sum(r['checked_stages'] for r in job_reports.values()),
            'accepted_transitions': sum(r['accepted_transitions'] for r in job_reports.values()),
            'incomplete_jobs': [key for key, report in job_reports.items() if report['status'] != 'complete'],
            'unchanged_cached_references_checked': cache_count, 'checked_exports': exports,
            'scope': 'Read-only saved compiler evidence and reference JSON; no Lean, model calls, or reference measurements.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    result = audit_combined_matrix(args.input, complete=args.complete)
    folder = args.input / 'validation'
    folder.mkdir(exist_ok=True)
    write_json(folder / 'combined_evidence_audit.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
