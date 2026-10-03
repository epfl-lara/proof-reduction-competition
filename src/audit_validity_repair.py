"""Audit saved correctness-only repair evidence without models or Lean processes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from audit_experiments import _close, _evaluation, _named, _proof, _require, _rows
from proof_eval.dataset import Dataset
from proof_eval.metrics import validate_candidate
from proof_eval.one_shot import FIELDS, extract_declaration, fingerprint, zero_evaluation
from proof_eval.optimizer import score_improves
from proof_eval.rcp import map_rcp_reasoning
from run_deterministic import digest, write_json
from run_validity_repair import SYSTEM, build_repair_messages, required_versions, unavailable
from validity_feedback import all_versions_passed, build_validity_feedback


ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(Path(path).read_text())


def _saved_evaluation(row, reference, proof, evaluation, label):
    """Check identity/arithmetic; the recorded compiler checks are the evidence."""
    status = evaluation.get('status')
    _require(status in ('passed', 'failed', 'invalid', 'incomplete', 'unavailable'), label + ': unknown evaluation status')
    if status == 'passed':
        _evaluation(row, reference, proof, evaluation, label)
        return
    if status in ('invalid', 'failed'):
        _require(all(evaluation['scores'].get(f) == 0 for f in FIELDS), label + ': invalid/failed scores must be zero')
    if status in ('incomplete', 'unavailable'):
        _require(evaluation['scores'].get('combined_pct') is None and
                 evaluation['scores'].get('compatibility_pct') is None, label + ': unavailable completed score')
    if status == 'invalid':
        _require(not evaluation['per_version'], label + ': invalid candidate has compiler checks')
        return
    if status == 'unavailable':
        _require(all(evaluation['scores'].get(f) is None for f in FIELDS), label + ': unavailable output has scores')
        return
    length = _proof(row, proof, evaluation, label)
    versions = [v for entry in row['version_info'] for v in entry]
    primary = versions[0]
    _require(evaluation['primary_version'] == primary, label + ': wrong primary version')
    _require(set(evaluation['per_version']) == set(versions), label + ': required version checks differ')
    item = evaluation['per_version'][primary]
    if status == 'failed':
        _require(item['status'] in ('failed', 'timeout') and item['passed'] is False,
                 label + ': primary failure evidence is absent')
    elif item.get('passed'):
        _close(evaluation['scores']['length_reduction_pct'],
               100 * (1 - length / row['proof_length']), label + ': incomplete length')
        if evaluation['scores']['heartbeat_reduction_pct'] is not None:
            _close(evaluation['scores']['heartbeat_reduction_pct'],
                   100 * (1 - item['heartbeats'] / reference['per_version'][primary]['heartbeats']),
                   label + ': incomplete heartbeat')
    else:
        _require(evaluation['scores']['length_reduction_pct'] is None and
                 evaluation['scores']['heartbeat_reduction_pct'] is None, label + ': unavailable primary has reductions')


def _can_continue(evaluation, generation, code, versions):
    return (not all_versions_passed(evaluation, versions) and not unavailable(evaluation)
            and generation.get('status') == 'received' and bool(code.strip()))


def _check_generation(generation, label):
    _require(generation.get('status') in ('received', 'transport_error', 'indeterminate'), label + ': unknown generation status')
    if generation['status'] == 'received':
        _require(isinstance(generation.get('content'), str), label + ': final content is not text')


def _verify_round(folder, number, pack, base_request, evaluation, generation, code, reference):
    """Verify a complete round or an in-flight prefix; never request another."""
    versions = required_versions(pack)
    _require(_can_continue(evaluation, generation, code, versions),
             f'{folder}: repair round follows a valid, unavailable, or empty output')
    feedback = build_validity_feedback(evaluation, versions)
    request = {key: base_request[key] for key in
               ('model', 'temperature', 'reasoning', 'reasoning_effort', 'max_tokens')}
    request['messages'] = build_repair_messages(pack, code, feedback)
    request['reasoning_payload'] = map_rcp_reasoning(
        request['model'], request['reasoning'], request['reasoning_effort'])[1]
    feedback_path, request_path = folder / 'feedback.json', folder / 'request.json'
    result_path, generation_path = folder / 'result.json', folder / 'generation.json'
    if feedback_path.exists():
        _require(read(feedback_path) == feedback, f'{folder}: correctness feedback changed')
    if request_path.exists():
        _require(feedback_path.exists(), f'{folder}: request lacks feedback')
        _require(read(request_path) == request, f'{folder}: repair messages or inherited settings changed')
    if (folder / 'request_started.json').exists():
        _require(request_path.exists(), f'{folder}: request start lacks request')
    if generation_path.exists():
        _require(request_path.exists() and (folder / 'request_started.json').exists(),
                 f'{folder}: generation lacks request/start evidence')
        _check_generation(read(generation_path), str(folder))
    if not result_path.exists():
        return None
    _require(feedback_path.exists() and request_path.exists() and generation_path.exists(),
             f'{folder}: completed round lacks artifacts')
    trial = read(result_path)
    _require(trial['round'] == number and trial['request_sha256'] == fingerprint(request),
             f'{folder}: round/request identity differs')
    _require(trial['generation'] == read(generation_path), f'{folder}: generation/result differ')
    next_generation = trial['generation']
    if next_generation['status'] != 'received':
        _require(trial['proof'] == '' and trial['evaluation'] ==
                 {'status': 'unavailable', 'per_version': {}, 'scores': {}},
                 f'{folder}: unreceived response acquired a candidate')
    else:
        try:
            extracted = extract_declaration(next_generation['content'], next_generation['finish_reason'])
        except ValueError as exc:
            _require(trial['proof'] == next_generation['content'] and trial['evaluation'] == zero_evaluation(str(exc)),
                     f'{folder}: extraction failure was repaired or rescored')
        else:
            _require(trial['proof'] == extracted, f'{folder}: proof differs from final content')
            _saved_evaluation(pack['row'], reference, extracted, trial['evaluation'], str(folder))
            if trial['evaluation']['status'] == 'invalid':
                try:
                    validate_candidate(pack['row'], extracted)
                except ValueError:
                    pass
                else:
                    raise ValueError(f'{folder}: valid input labeled invalid')
    return trial


def audit_validity_repair(root, *, complete=False):
    root = Path(root).resolve()
    config = read(root / 'config.json')
    _require(type(config['max_rounds']) is int and 0 <= config['max_rounds'] <= 3, 'Repair round budget exceeds 0–3')
    base = Path(config['base_directory'])
    _require(digest(base / 'config.json') == config['base_config_sha256'], 'Base configuration changed')
    base_config = read(base / 'config.json')
    _require(config['base_names'] == base_config['names'], 'Base cohort changed')
    for label, sources in (('base', base_config['code_sha256']), ('repair', config['code_sha256'])):
        for path, expected in sources.items():
            _require(digest(ROOT / path) == expected, f'{label} implementation changed: {path}')
    _require(config['system_sha256'] == fingerprint(SYSTEM), 'Repair system prompt changed')
    artifacts = {
        'dataset_sha256': ROOT / 'data/benchmark_data_warmup.jsonl',
        'input_sha256': ROOT / 'results/deterministic/selected_candidates.jsonl',
        'environment_config_sha256': ROOT / 'environments.local.json',
        'system_sha256': ROOT / 'prompts/one_shot_system.md',
        'bank_sha256': ROOT / 'prompts/strategy_bank.json',
    }
    for key, path in artifacts.items():
        _require(digest(path) == base_config[key], 'Frozen base artifact changed: ' + key)
    dataset = Dataset(artifacts['dataset_sha256'])
    initial_proofs = _named(_rows(artifacts['input_sha256']), dataset.names, 'Initial incumbent proofs')
    references = _named(_rows(ROOT / 'results/deterministic/00_reference_baseline/reference_values.jsonl'),
                        dataset.names, 'Reference export')
    packs = _named([read(p) for p in (base / 'inputs').glob('*.json')], base_config['names'], 'Base inputs')
    input_hashes = read(base / 'input_hashes.json')
    _require(set(input_hashes) == set(packs), 'Base input hashes differ in coverage')
    for name, pack in packs.items():
        _require(fingerprint(pack) == input_hashes[name], 'Frozen base input changed: ' + name)
        _require(pack['row'] == dataset.get(name) and pack['proof'] == initial_proofs[name]['proof'],
                 'Base row/incumbent differs: ' + name)
    base_index = read(base / 'cell_index.json')
    selected = config['cells']
    _require(selected and len({c['key'] for c in selected}) == len(selected), 'Repair cells must be nonempty and unique')
    selected_keys = {c['key'] for c in selected}
    _require({p.name for p in (root / 'cells').glob('*') if p.is_dir()} <= selected_keys, 'Unconfigured repair cell directory')
    checked, round_count, request_count, cache_checked = [], 0, 0, set()
    partial_cells = 0
    for cell in selected:
        key, logical = cell['key'], cell['logical']
        name, arm, model = logical
        _require(base_index.get(json.dumps(logical)) == key, 'Base cell index identity changed')
        base_folder, folder = base / 'cells' / key, root / 'cells' / key
        _require(digest(base_folder / 'result.json') == cell['result_sha256'], 'Initial result bytes changed')
        _require(digest(base_folder / 'request.json') == cell['request_sha256'], 'Initial request bytes changed')
        base_record, base_request, pack = read(base_folder / 'result.json'), read(base_folder / 'request.json'), packs[name]
        _require(fingerprint(pack) == cell['input_sha256'], 'Selected input snapshot changed')
        payload = {k: v for k, v in base_request.items() if k not in ('name', 'arm', 'request_sha256')}
        _require(fingerprint(payload) == key == base_request['request_sha256'] == base_record['request_sha256'],
                 'Base request fingerprint mismatch')
        _require([base_record['name'], base_record['arm'], base_record['model']] == logical and
                 [base_request['name'], base_request['arm'], base_request['model']] == logical,
                 'Base logical identity mismatch')
        _require(base_record['generation'] == read(base_folder / 'generation.json'), 'Base generation changed')
        _require((base_folder / 'request_started.json').is_file(), 'Initial request start marker missing')
        for setting in ('temperature', 'reasoning', 'reasoning_effort', 'max_tokens'):
            _require(base_request[setting] == base_config[setting], 'Initial request setting differs: ' + setting)
        versions = required_versions(pack)
        reference = references[name]
        _require(reference['status'] == 'prepared' and reference['dataset_sha256'] == base_config['dataset_sha256'],
                 'Reference export dataset changed')
        _require(reference['reference_code_sha256'] == hashlib.sha256(pack['row']['src'].encode()).hexdigest()
                 and reference['reference_length_tokens'] == pack['row']['proof_length'], 'Reference source/length changed')
        _require(set(reference['per_version']) == set(versions), 'Reference versions changed')
        for version, value in reference['per_version'].items():
            _require(value['status'] == 'prepared' and value['heartbeats'] > 0, 'Reference export unavailable')
            _close(value['heartbeats_raw'] / 1000, value['heartbeats'], 'Reference heartbeat units')
            _require(value['provenance']['details']['backend_implementation_sha256'] ==
                     base_config['code_sha256']['src/proof_eval/lean_backend.py'], 'Reference backend changed')
        _evaluation(pack['row'], reference, pack['proof'], pack['incumbent'], 'incumbent/' + name)
        for version in versions:
            context_key = base_config['contexts'][name][version]
            cache_path = ROOT / '.proof-eval/references' / (context_key + '.json')
            cached = read(cache_path)
            _require(cached['status'] == 'prepared', 'Cached reference unavailable')
            for field in ('measured_at', 'heartbeats', 'heartbeats_raw', 'environment_fingerprint', 'reference_code_sha256'):
                saved = pack['incumbent']['per_version'][version]['reference'][field]
                _require(cached[field] == saved, f'Cached reference changed: {name}/{version}/{field}')
                exported = reference['per_version'][version]
                value = exported[field] if field in ('heartbeats', 'heartbeats_raw') else exported['provenance'][field]
                _require(value == saved, f'Reference export changed: {name}/{version}/{field}')
            cache_checked.add((name, version))
        if not folder.exists():
            _require(not complete, 'Missing repair cell: ' + key)
            partial_cells += 1
            continue
        spec = {
            'initial_result_sha256': fingerprint(base_record), 'initial_request_sha256': fingerprint(base_request),
            'input_sha256': fingerprint(pack), 'max_rounds': config['max_rounds'], 'timeout': config['timeout'],
            'system_sha256': fingerprint(SYSTEM), 'implementation_sha256': {
                path: config['code_sha256'][path] for path in
                ('src/run_validity_repair.py', 'src/validity_feedback.py')},
        }
        if not (folder / 'cell_config.json').exists():
            _require(not complete and not list(folder.iterdir()), 'Repair cell lacks configuration')
            partial_cells += 1
            continue
        _require(read(folder / 'cell_config.json') == spec, 'Repair cell configuration changed')
        if not (folder / 'initial_result.json').exists():
            _require(not complete and not (folder / 'result.json').exists()
                     and not list((folder / 'rounds').glob('*')), 'Missing saved initial result')
            partial_cells += 1
            continue
        _require(read(folder / 'initial_result.json') == base_record, 'Saved initial result differs from base')
        evaluation, generation = base_record['evaluation'], base_record['generation']
        code = base_record.get('extracted_proof', generation.get('content', ''))
        _check_generation(generation, 'initial/' + key)
        _saved_evaluation(pack['row'], reference, code, evaluation, 'initial/' + key)
        if generation['status'] == 'received':
            try:
                extracted = extract_declaration(generation['content'], generation['finish_reason'])
            except ValueError as exc:
                _require('extracted_proof' not in base_record and evaluation == zero_evaluation(str(exc)),
                         'Initial extraction failure differs from recorded evaluation')
            else:
                _require(base_record.get('extracted_proof') == extracted, 'Initial extracted proof differs from raw output')
        else:
            _require(not code.strip() and evaluation['status'] == 'unavailable', 'Initial unavailable generation has a candidate')
        initial_valid = all_versions_passed(evaluation, versions)
        initial_kind = ('already_valid' if initial_valid else 'no_candidate' if not code.strip()
                        else 'compiler_repair' if evaluation.get('per_version') else 'output_recovery')
        round_folders = sorted(p for p in (folder / 'rounds').glob('*') if p.is_dir())
        _require(len(round_folders) <= config['max_rounds'], 'Too many repair rounds')
        _require([p.name for p in round_folders] == [f'{n:02d}' for n in range(1, len(round_folders) + 1)],
                 'Repair round sequence is not a contiguous prefix')
        trials, unfinished = [], False
        for number, round_folder in enumerate(round_folders, 1):
            trial = _verify_round(round_folder, number, pack, base_request, evaluation, generation, code, reference)
            request_count += int((round_folder / 'request_started.json').is_file())
            if trial is None:
                _require(number == len(round_folders) and not (folder / 'result.json').exists(),
                         'An unfinished round has a successor or final result')
                unfinished = True
                break
            trials.append(trial)
            generation, evaluation, code = trial['generation'], trial['evaluation'], trial['proof']
            round_count += 1
        if not (folder / 'result.json').exists():
            _require(not complete, 'Missing completed repair cell: ' + key)
            partial_cells += 1
            continue
        _require(not unfinished, 'Final result precedes completion of a round')
        final_valid = all_versions_passed(evaluation, versions)
        if final_valid:
            outcome = 'already_valid' if initial_valid else 'repaired_valid'
        elif unavailable(evaluation) or generation.get('status') != 'received':
            outcome = 'unavailable'
        elif not code.strip():
            outcome = 'repair_returned_no_candidate' if trials else 'no_candidate'
        else:
            _require(len(trials) == config['max_rounds'], 'Repair stopped before its correctness round budget')
            outcome = 'repair_budget_exhausted'
        accepted = bool(final_valid and score_improves(pack['incumbent'], evaluation, .05))
        expected_record = {
            'name': name, 'source': pack['row']['source'], 'model': model, 'arm': arm,
            'base_request_sha256': key, 'initial_kind': initial_kind, 'initial_valid': initial_valid,
            'round_count': len(trials), 'max_rounds': config['max_rounds'], 'outcome': outcome,
            'final_valid': final_valid, 'final_proof': code, 'final_evaluation': evaluation,
            'returned_incumbent': final_valid and code.strip() == pack['proof'].strip(), 'accepted': accepted,
            'selected_proof': code if accepted else pack['proof'],
            'selected_evaluation': evaluation if accepted else pack['incumbent'],
            'rounds': [{'round': t['round'], 'request_sha256': t['request_sha256'],
                        'generation_status': t['generation']['status'], 'finish_reason': t['generation'].get('finish_reason'),
                        'usage': t['generation'].get('usage'), 'evaluation_status': t['evaluation']['status']} for t in trials],
        }
        record = read(folder / 'result.json')
        _require(record == expected_record, 'Final repair record differs from reconstructed correctness loop')
        _evaluation(pack['row'], reference, record['selected_proof'], record['selected_evaluation'], 'selected/' + key)
        checked.append(record)
    return {
        'status': 'passed', 'audited_at': datetime.now(timezone.utc).isoformat(), 'complete_required': complete,
        'expected_cells': len(selected), 'checked_cells': len(checked), 'partial_cells': partial_cells,
        'checked_rounds': round_count, 'started_repair_requests': request_count,
        'accepted_improvements': sum(r['accepted'] for r in checked),
        'returned_incumbents': sum(r['returned_incumbent'] for r in checked),
        'unchanged_cached_references_checked': len(cache_checked),
        'scope': 'Saved-evidence and reference JSON audit only; no model calls, Lean execution, or reference measurements.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    result = audit_validity_repair(args.input, complete=args.complete)
    output = args.input / 'validation'
    output.mkdir(exist_ok=True)
    write_json(output / 'repair_evidence_audit.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
