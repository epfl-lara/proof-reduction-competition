"""Offline audit of source identity, saved score arithmetic and best-proof selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_experiments import _evaluation, _implementation
from proof_agent_tools import code_identity
from proof_eval.costs import CostConfig, generations_cost, rate_card
from proof_eval.one_shot import FIELDS, fingerprint
from run_agent_harness import ROOT, read
from run_deterministic import digest, write_json
from validity_feedback import all_versions_passed


def audit(output):
    config = read(output / 'config.json')
    if 'cost_estimate_sha256' in config:
        costs = read(output / 'cost_estimate.json')
        assert fingerprint(costs) == config['cost_estimate_sha256']
        assert costs['rate_card'] == config['rate_card'] == rate_card()
        for rel, expected in costs['source_result_sha256'].items():
            assert digest(ROOT / rel) == expected
    for rel, expected in config['code_sha256'].items():
        _implementation(rel, expected, ROOT, ROOT / 'results/deterministic/validation/implementation_snapshots', str(output))
    for rel, expected in {**config['historical_control_sha256'], **config['structural_control_sha256'],
                          **config.get('score_control_sha256', {})}.items():
        assert digest(ROOT / rel) == expected, rel
    rows = {r['name']: r for r in map(json.loads, (ROOT / 'data/benchmark_data_warmup.jsonl').read_text().splitlines())}
    refs = {r['name']: r for r in map(json.loads, (ROOT / 'results/deterministic/00_reference_baseline/reference_values.jsonl').read_text().splitlines())}
    outcomes, trials, requests, cells, seen = 0, 0, 0, 0, set()
    cleanup_jobs = set()
    for path in sorted((output / 'cells').glob('*/result.json')):
        result = read(path)
        name = result['name']
        key = (name, result['model'], result['effort'], result['mode'])
        assert key not in seen and path.parent.name == fingerprint(key)
        seen.add(key)
        assert name in config['names'] and [result['model'], result['effort']] in config['conditions']
        assert result['mode'] == config['mode']
        inp = read(path.parent / 'input.json')
        best_code, best_evaluation = inp.get('seed_proof', rows[name]['src']), inp['seed_evaluation']
        outcomes += _evaluation(rows[name], refs[name], best_code, best_evaluation, str(key))
        checks = [json.loads(line) for line in (path.parent / 'evidence/checks.jsonl').read_text().splitlines()] if (path.parent / 'evidence/checks.jsonl').exists() else []
        versions = [v for spec in rows[name]['version_info'] for v in spec]
        valid_code = None
        valid_evaluation = None
        best_at = {0: (best_code, best_evaluation)}
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
            best_at[i] = (best_code, best_evaluation)
            trials += 1
        assert result['selected_proof'] == best_code and result['selected_evaluation'] == best_evaluation
        assert result['first_valid_proof'] == valid_code and result['first_valid_evaluation'] == valid_evaluation
        assert result['checks'] == len(checks)
        assert result['agent_tool_checks'] == sum(c['origin'] == 'agent_tool' for c in checks)
        assert result['valid_checks'] == sum(c['all_versions_passed'] for c in checks)
        assert result['improvements'] == sum(c['accepted'] for c in checks)
        if config.get('deterministic_cleanup'):
            cleanup_calls = [json.loads(line) for line in (path.parent / 'evidence/deterministic.jsonl').read_text().splitlines()]
            assert result['deterministic_calls'] == len(cleanup_calls)
            assert result['deterministic_tool_calls'] == sum(c['origin'] == 'agent_tool' for c in cleanup_calls)
            assert len([c for c in cleanup_calls if c['origin'] == 'final_harness']) == 1
            assert result['seed_proof'] == inp['seed_proof'] and result['seed_evaluation'] == inp['seed_evaluation']
            valid_proposals = {c['code_sha256'] for c in checks
                               if c['origin'] in ('agent_tool', 'deterministic_input', 'final_harness')
                               and c['all_versions_passed'] and not c['duplicate']
                               and c['code_sha256'] != code_identity(rows[name], inp['seed_proof'])}
            covered = valid_proposals & {c['input_code_sha256'] for c in cleanup_calls
                                         if c['origin'] == 'agent_tool' and c['status'] != 'skipped_invalid'}
            assert result['valid_changed_proposals'] == len(valid_proposals)
            assert result['proposals_with_tool_cleanup'] == len(covered)
            assert result['deterministic_tool_coverage_pct'] == (100 * len(covered) / len(valid_proposals) if valid_proposals else None)
            assert result['incomplete_cleanups'] == sum(c['status'] not in ('complete', 'skipped_invalid') for c in cleanup_calls)
            if result['score_control_score'] is not None:
                assert abs(result['gain_over_score_control_pp'] - (best_evaluation['scores']['combined_pct'] - result['score_control_score'])) < 1e-9
            else:
                assert result['gain_over_score_control_pp'] is None
            for i, c in enumerate(cleanup_calls, 1):
                assert c['number'] == i
                before = checks[c['input_check'] - 1]
                assert before['code_sha256'] == c['input_code_sha256']
                if c['status'] == 'skipped_invalid':
                    assert not before['all_versions_passed'] and c['output_check'] is None
                    continue
                job_folder = Path(c['job_path'])
                assert job_folder.resolve().is_relative_to(Path(config['deterministic_jobs']).resolve())
                assert digest(job_folder / 'result.json') == c['job_result_sha256']
                job = read(job_folder / 'result.json')
                after = checks[c['output_check'] - 1]
                assert after['code'] == job['proof'] and after['evaluation'] == job['evaluation']
                assert c['status'] == job['status'] and c['counters'] == job['counters']
                assert code_identity(rows[name], job['input_proof']) == c['input_code_sha256']
                assert before['all_versions_passed'] and after['all_versions_passed']
                if str(job_folder) not in cleanup_jobs:
                    spec = read(job_folder / 'job_config.json')
                    assert job['job_config_sha256'] == fingerprint(spec)
                    assert spec['methods'] == config['deterministic_methods'] and spec['budget'] == config['deterministic_budget']
                    for relative, expected in job['stage_result_sha256'].items():
                        assert digest(job_folder / relative) == expected
                    code = job['input_proof']
                    for stage in job['stages']:
                        outcomes += _evaluation(rows[name], refs[name], code, stage['initial'], 'cleanup initial')
                        outcomes += _evaluation(rows[name], refs[name], stage['proof'], stage['final'], 'cleanup final')
                        assert stage['final']['scores']['combined_pct'] >= stage['initial']['scores']['combined_pct']
                        code = stage['proof']
                    assert code == job['proof']
                    cleanup_jobs.add(str(job_folder))
                if c['origin'] == 'final_harness':
                    prior_code, prior_eval = best_at[c['input_check'] - 1]
                    assert result['before_final_cleanup'] == {'proof': prior_code, 'evaluation': prior_eval}
            assert abs(result['final_cleanup_gain_pp'] - (best_evaluation['scores']['combined_pct'] - result['before_final_cleanup']['evaluation']['scores']['combined_pct'])) < 1e-9
            assert result['final_cleanup_gain_pp'] >= 0
            if config['mode'] == 'score_edges':
                assert result['deterministic_tool_calls'] == 0
        if result['historical_score'] is not None:
            assert abs(result['gain_over_historical_pp'] - (best_evaluation['scores']['combined_pct'] - result['historical_score'])) < 1e-9
        else:
            assert result['gain_over_historical_pp'] is None
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
                if 'cost_assumptions' in config:
                    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
                    usage = [e['usage'] for e in events if e.get('type') == 'turn.completed']
                    assert len(usage) == 1 and gen['codex_usage'] == usage[0]
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
        if 'cost_assumptions' in config:
            assert result['cost'] == generations_cost(
                CostConfig(result['model'], result['effort'], **config['cost_assumptions']),
                cell_generations, budget_usd=config['budget_usd_per_problem'])
        cells += 1
    return {'status': 'passed', 'completed_cells': cells, 'saved_checks': trials,
            'checked_version_outcomes': outcomes, 'requests': requests,
            'unique_cleanup_jobs': len(cleanup_jobs),
            'scope': 'Saved evidence and arithmetic; no new Lean or model calls.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = audit(args.output.resolve())
    write_json(args.output / 'audit.json', result)
    print(json.dumps(result))
