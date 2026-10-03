"""Check saved one-shot request identities, decisions and score arithmetic read-only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from audit_experiments import _close, _evaluation, _named, _number, _proof, _rows, _require
from proof_eval import Evaluator
from proof_eval.dataset import Dataset
from proof_eval.one_shot import build_messages, extract_declaration, fingerprint, FIELDS
from proof_eval.optimizer import score_improves
from proof_eval.rcp import map_rcp_reasoning
from run_deterministic import digest, write_json


ROOT = Path(__file__).resolve().parent.parent


def audit_one_shot(root, *, complete=False):
    root = Path(root)
    read = lambda path: json.loads(path.read_text())
    config = read(root / 'config.json')
    for label in ('names', 'arms', 'models'):
        values = config[label]
        _require(values and len(set(values)) == len(values), f'Configured {label} must be unique and nonempty')
    _require(_number(config['min_gain_pp'], 'Acceptance margin') >= 0, 'Negative acceptance margin')
    artifact_paths = {
        'dataset_sha256': ROOT / 'data/benchmark_data_warmup.jsonl',
        'input_sha256': ROOT / 'results/deterministic/selected_candidates.jsonl',
        'environment_config_sha256': ROOT / 'environments.local.json',
    }
    for key, path in artifact_paths.items():
        _require(digest(path) == config[key], f'Frozen artifact changed: {key}')
    for path, expected in config['code_sha256'].items():
        _require(digest(ROOT / path) == expected, f'Experiment implementation changed: {path}')
    _require(digest(ROOT / 'prompts/one_shot_system.md') == config['system_sha256'], 'System prompt changed')
    _require(digest(ROOT / 'prompts/strategy_bank.json') == config['bank_sha256'], 'Bank changed')
    dataset_rows = _rows(artifact_paths['dataset_sha256'])
    dataset = _named(dataset_rows, [r['name'] for r in dataset_rows], 'Dataset')
    _require(set(config['names']) <= set(dataset), 'Configured problem is absent from dataset')
    originals = _named(_rows(artifact_paths['input_sha256']), dataset, 'Incumbent input')
    references = _named(_rows(ROOT / 'results/deterministic/00_reference_baseline/reference_values.jsonl'),
                        dataset, 'Reference export')
    evaluator = Evaluator(ROOT / 'data/benchmark_data_warmup.jsonl', ROOT / 'environments.local.json', ROOT / '.proof-eval')
    loaded_dataset = Dataset(artifact_paths['dataset_sha256'])
    inputs = _named([read(p) for p in (root / 'inputs').glob('*.json')], config['names'], 'Prepared inputs')
    recorded_hashes = read(root / 'input_hashes.json')
    _require(set(inputs) == set(config['names']) == set(recorded_hashes), 'Input cohort differs')
    reference_count = 0
    for name, pack in inputs.items():
        _require(fingerprint(pack) == recorded_hashes[name], f'Input changed: {name}')
        _require(pack['row'] == loaded_dataset.get(name), f'Prepared dataset row changed: {name}')
        _require(pack['proof'] == originals[name]['proof'], f'Prepared incumbent changed: {name}')
        reference = references[name]
        _require(reference['status'] == 'prepared' and reference['dataset_sha256'] == config['dataset_sha256'],
                 f'Reference export dataset mismatch: {name}')
        _require(reference['reference_length_tokens'] == dataset[name]['proof_length'],
                 f'Reference token denominator changed: {name}')
        _require(reference['reference_code_sha256'] == hashlib.sha256(dataset[name]['src'].encode()).hexdigest(),
                 f'Reference source changed: {name}')
        versions = {v for entry in dataset[name]['version_info'] for v in entry}
        _require(set(reference['per_version']) == versions == set(config['contexts'][name]),
                 f'Reference/context versions differ: {name}')
        for version, value in reference['per_version'].items():
            _require(value['status'] == 'prepared' and _number(value['heartbeats'], 'Reference heartbeat') > 0,
                     f'Reference unavailable: {name}/{version}')
            _close(value['heartbeats_raw'] / 1000, value['heartbeats'], f'Reference units: {name}/{version}')
            _require(value['provenance']['details']['backend_implementation_sha256'] ==
                     config['code_sha256']['src/proof_eval/lean_backend.py'],
                     f'Reference measurement implementation changed: {name}/{version}')
        _evaluation(dataset[name], references[name], pack['proof'], pack['incumbent'], 'incumbent/'+name)
        current = evaluator.get_reference(name)['versions']
        _require(set(current) == versions, f'Cached reference versions changed: {name}')
        for version, value in pack['incumbent']['per_version'].items():
            _require(current[version]['status'] == 'prepared', f'Cached reference unavailable: {name}/{version}')
            _require(evaluator._context(pack['row'], version)[2] == config['contexts'][name][version],
                     f'Environment context changed: {name}/{version}')
            for key in ('measured_at','heartbeats','heartbeats_raw','environment_fingerprint','reference_code_sha256'):
                _require(current[version][key] == value['reference'][key], f'Cached reference changed: {name}/{version}/{key}')
                exported = reference['per_version'][version]
                exported_value = exported[key] if key in ('heartbeats', 'heartbeats_raw') else exported['provenance'][key]
                _require(exported_value == value['reference'][key], f'Reference export changed: {name}/{version}/{key}')
            reference_count += 1
    index = read(root / 'cell_index.json')
    expected = {(name, arm, model) for name in config['names'] for arm in config['arms'] for model in config['models']}
    _require({tuple(json.loads(k)) for k in index} == expected, 'Cell index cohort differs')
    _require(len(set(index.values())) == len(index), 'Logical cells share a request directory')
    result_directories = {path.parent.name for path in (root / 'cells').glob('*/result.json')}
    _require(result_directories <= set(index.values()), 'Unindexed result artifact')
    checked, accepted = 0, 0
    for logical, key in index.items():
        name, arm, model = json.loads(logical)
        folder = root / 'cells' / key
        request = read(folder / 'request.json')
        payload = {k: v for k, v in request.items() if k not in ('name','arm','request_sha256')}
        _require(fingerprint(payload) == key == request['request_sha256'], 'Request hash mismatch')
        pack = inputs[name]
        messages = build_messages((ROOT / 'prompts/one_shot_system.md').read_text(), pack['row'], pack['proof'],
                                  pack['incumbent'], pack['source_context'], arm,
                                  read(ROOT / 'prompts/strategy_bank.json'), pack.get('context'))
        _require(request['messages'] == messages and request['model'] == model, 'Prompt/arm mismatch')
        _require(request['name'] == name and request['arm'] == arm, 'Request identity mismatch')
        expected_payload = {
            'model': model, 'messages': messages, 'temperature': config['temperature'],
            'reasoning': config['reasoning'], 'reasoning_effort': config['reasoning_effort'],
            'max_tokens': config['max_tokens'],
            'reasoning_payload': map_rcp_reasoning(model, config['reasoning'], config['reasoning_effort'])[1],
        }
        _require(payload == expected_payload, 'Request generation settings differ from frozen configuration')
        result_path = folder / 'result.json'
        if not result_path.exists():
            _require(not complete, f'Missing completed cell: {name}/{arm}/{model}')
            continue
        record = read(result_path)
        _require(record['request_sha256'] == key, 'Result identity mismatch')
        _require((record['name'], record['arm'], record['model'], record['source']) ==
                 (name, arm, model, dataset[name]['source']), 'Result logical identity mismatch')
        _require(record['generation'] == read(folder / 'generation.json'), 'Generation/result mismatch')
        _require((folder / 'request_started.json').is_file(), 'Missing request start marker')
        generation_status = record['generation']['status']
        _require(generation_status in ('received', 'transport_error', 'indeterminate'), 'Unknown generation status')
        _evaluation(dataset[name], references[name], record['selected_proof'], record['selected_evaluation'], 'selected/'+key)
        result = record['evaluation']
        _require(result['status'] in ('passed', 'invalid', 'failed', 'unavailable', 'incomplete'),
                 'Unknown evaluation status')
        if result['status'] == 'passed':
            _evaluation(dataset[name], references[name], record['extracted_proof'], result, 'candidate/'+key)
        elif result['status'] in ('invalid','failed'):
            _require(all(result['scores'][f] == 0 for f in FIELDS), 'Failed candidate does not score zero')
            if result['status'] == 'invalid':
                _require(not result['per_version'], 'Invalid candidate has compiler outcomes')
        elif result['status'] == 'unavailable':
            _require(all(result['scores'][f] is None for f in FIELDS), 'Unavailable output has invented scores')
        elif result['status'] == 'incomplete':
            _require(result['scores']['combined_pct'] is None and result['scores']['compatibility_pct'] is None,
                     'Incomplete evaluation has a completed score')
        if result['status'] in ('failed', 'incomplete'):
            _proof(dataset[name], record['extracted_proof'], result, 'candidate/'+key)
            primary = next(iter(dataset[name]['version_info'][0]))
            _require(result['primary_version'] == primary, 'Failed/incomplete primary version differs')
            versions = {v for entry in dataset[name]['version_info'] for v in entry}
            _require(set(result['per_version']) == versions, 'Failed/incomplete version keys differ')
            if result['status'] == 'failed':
                item = result['per_version'][primary]
                _require(item['status'] in ('failed', 'timeout') and item['passed'] is False,
                         'Failed candidate lacks primary failure evidence')
            else:
                item = result['per_version'][primary]
                if item.get('passed'):
                    _close(result['scores']['length_reduction_pct'],
                           100 * (1 - result['candidate']['length'] / dataset[name]['proof_length']),
                           'Incomplete length score')
                    if result['scores']['heartbeat_reduction_pct'] is not None:
                        _close(result['scores']['heartbeat_reduction_pct'],
                               100 * (1 - item['heartbeats'] / references[name]['per_version'][primary]['heartbeats']),
                               'Incomplete heartbeat score')
                else:
                    _require(result['scores']['length_reduction_pct'] is None and
                             result['scores']['heartbeat_reduction_pct'] is None,
                             'Unavailable primary has invented reduction scores')
        all_passed = (set(result['per_version']) == set(pack['incumbent']['per_version'])
                      and all(v.get('passed') is True for v in result['per_version'].values()))
        _require(record['all_versions_passed'] is all_passed, 'All-version passing flag differs from saved checks')
        if generation_status != 'received':
            _require(result['status'] == 'unavailable' and 'extracted_proof' not in record,
                     'Unreceived generation has a candidate evaluation')
        chosen = score_improves(pack['incumbent'], result, config['min_gain_pp'])
        _require(chosen == record['accepted'], 'Acceptance decision differs')
        if chosen:
            _require(record['selected_proof'] == record['extracted_proof'] and record['selected_evaluation'] == result,
                     'Selected candidate differs from evaluation')
            accepted += 1
        else:
            _require(record['selected_proof'] == pack['proof'] and record['selected_evaluation'] == pack['incumbent'],
                     'Fallback changed')
        if record['generation']['status'] == 'received':
            try:
                code = extract_declaration(record['generation']['content'], record['generation']['finish_reason'])
            except ValueError:
                _require(result['status'] == 'invalid', 'Rejected output was evaluated as a proof')
            else:
                _require(code == record['extracted_proof'], 'Extracted proof differs from raw output')
        checked += 1
    return {'status':'passed','audited_at':datetime.now(timezone.utc).isoformat(),
            'complete_required':complete,'expected_cells':len(expected),'checked_cells':checked,
            'accepted_candidates':accepted,'unchanged_cached_references_checked':reference_count,
            'scope':'Read-only saved-evidence and cache checks; no model calls or Lean compilation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--complete',action='store_true')
    args=parser.parse_args()
    report=audit_one_shot(args.input,complete=args.complete)
    output=args.input/'validation';output.mkdir(exist_ok=True)
    write_json(output/'evidence_audit.json',report)
    print(json.dumps(report))


if __name__=='__main__':main()
