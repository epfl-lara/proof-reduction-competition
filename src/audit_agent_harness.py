"""Offline audit of source identity, saved score arithmetic and best-proof selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_experiments import _evaluation
from proof_eval.one_shot import FIELDS, fingerprint
from run_agent_harness import ROOT, read
from run_deterministic import digest, write_json
from validity_feedback import all_versions_passed


def audit(output):
    config = read(output / 'config.json')
    for rel, expected in {**config['code_sha256'], **config['historical_control_sha256'],
                          **config['structural_control_sha256']}.items():
        assert digest(ROOT / rel) == expected, rel
    rows = {r['name']: r for r in map(json.loads, (ROOT / 'data/benchmark_data_warmup.jsonl').read_text().splitlines())}
    refs = {r['name']: r for r in map(json.loads, (ROOT / 'results/deterministic/00_reference_baseline/reference_values.jsonl').read_text().splitlines())}
    outcomes, trials, requests, cells, seen = 0, 0, 0, 0, set()
    for path in sorted((output / 'cells').glob('*/result.json')):
        result = read(path)
        name = result['name']
        key = (name, result['model'], result['effort'], result['mode'])
        assert key not in seen and path.parent.name == fingerprint(key)
        seen.add(key)
        assert name in config['names'] and [result['model'], result['effort']] in config['conditions']
        assert result['mode'] == config['mode']
        inp = read(path.parent / 'input.json')
        best_code, best_evaluation = rows[name]['src'], inp['seed_evaluation']
        outcomes += _evaluation(rows[name], refs[name], best_code, best_evaluation, str(key))
        checks = [json.loads(line) for line in (path.parent / 'evidence/checks.jsonl').read_text().splitlines()] if (path.parent / 'evidence/checks.jsonl').exists() else []
        versions = [v for spec in rows[name]['version_info'] for v in spec]
        valid_code = None
        valid_evaluation = None
        for i, c in enumerate(checks, 1):
            assert c['number'] == i
            ev = c['evaluation']
            if ev['status'] == 'passed':
                outcomes += _evaluation(rows[name], refs[name], c['code'], ev, str(key) + f'/check{i}')
            elif ev['status'] in ('failed', 'invalid'):
                assert all(ev['scores'][f] == 0 for f in FIELDS)
            valid = all_versions_passed(ev, versions)
            assert c['all_versions_passed'] == valid
            previous = best_evaluation['scores']['combined_pct']
            accepted = valid and ev['scores']['combined_pct'] is not None and ev['scores']['combined_pct'] > previous + config['selection_margin_pp']
            assert c['accepted'] == accepted and c['previous_best_score'] == previous
            if valid and valid_code is None:
                valid_code, valid_evaluation = c['code'], ev
            if config['mode'] == 'correctness' and valid_code is not None:
                from proof_eval.metrics import validate_candidate
                assert validate_candidate(rows[name], c['code'])[0] == validate_candidate(rows[name], valid_code)[0]
            if accepted:
                best_code, best_evaluation = c['code'], ev
            trials += 1
        assert result['selected_proof'] == best_code and result['selected_evaluation'] == best_evaluation
        assert result['first_valid_proof'] == valid_code and result['first_valid_evaluation'] == valid_evaluation
        assert result['checks'] == len(checks)
        assert result['agent_tool_checks'] == sum(c['origin'] == 'agent_tool' for c in checks)
        assert result['valid_checks'] == sum(c['all_versions_passed'] for c in checks)
        assert result['improvements'] == sum(c['accepted'] for c in checks)
        assert abs(result['gain_over_historical_pp'] - (best_evaluation['scores']['combined_pct'] - result['historical_score'])) < 1e-9
        if result['structural_control_score'] is not None:
            assert abs(result['gain_over_structural_control_pp'] - (best_evaluation['scores']['combined_pct'] - result['structural_control_score'])) < 1e-9
        outcomes += _evaluation(rows[name], refs[name], best_code, best_evaluation, str(key) + '/selected')
        cell_generations = []
        for folder in sorted(path.parent.glob('attempt_*')):
            req = read(folder / 'request.json')
            gen = read(folder / 'generation.json')
            cell_generations.append(gen)
            assert (req['model'], req['reasoning_effort'], req['mode']) == key[1:]
            assert req['tool_instructions'] == config['tool_instructions']
            assert req['messages'][0] == inp['messages'][0]
            assert req['max_output_tokens'] is None and req['max_attempts'] is None
            assert req['timeout'] == config['generation_timeout']
            if folder.name == 'attempt_00':
                assert req['messages'] == inp['messages']
            if gen['status'] == 'received':
                assert (folder / 'workspace/final.txt').read_text().strip() == gen['content'].strip()
            if config['mode'] == 'correctness':
                for line in (folder / 'events.jsonl').read_text().splitlines():
                    event = json.loads(line)
                    item = event.get('item', {})
                    if event.get('type') != 'item.completed' or item.get('type') != 'command_execution':
                        continue
                    text = item.get('aggregated_output', '')
                    assert '"kind": "lean_score_feedback"' not in text
            requests += 1
        assert cell_generations == result['generations'] and cell_generations
        cells += 1
    return {'status': 'passed', 'completed_cells': cells, 'saved_checks': trials,
            'checked_version_outcomes': outcomes, 'requests': requests,
            'scope': 'Saved evidence and arithmetic; no new Lean or model calls.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = audit(args.output.resolve())
    write_json(args.output / 'audit.json', result)
    print(json.dumps(result))
