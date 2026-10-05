"""Compare completed harness cells without new model calls or Lean measurements."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean
import time

from proof_agent_tools import code_identity
from proof_eval.one_shot import fingerprint
from proof_eval.costs import CostConfig, generations_cost, summarize_costs
from run_agent_harness import BASE, CONDITIONS, OUTPUTS, ROOT, control_mean, display, historical, load_inputs, read
from run_deterministic import write_json
from run_validity_repair import now


def trajectory(row, seed_code, seed_evaluation, checks):
    """Attribute accepted score increments; seed checks and final cleanup are distinct."""
    seed_identity = code_identity(row, seed_code)
    best = seed_evaluation['scores']['combined_pct']
    first_best = first_raw = None
    gains = {'model_gain_pp': 0., 'in_loop_cleanup_gain_pp': 0., 'final_cleanup_gain_pp': 0.}
    records = []
    for c in checks:
        numeric = c['evaluation']['scores']['combined_pct']
        if c['accepted']:
            kind = {'deterministic_agent_tool': 'in_loop_cleanup_gain_pp',
                    'deterministic_final_harness': 'final_cleanup_gain_pp'}.get(c['origin'], 'model_gain_pp')
            gains[kind] += numeric - best
            best = numeric
        changed = c['code_sha256'] != seed_identity
        if (c['all_versions_passed'] and changed and first_best is None
                and c['origin'] in ('agent_tool', 'deterministic_input', 'final_harness')):
            first_best, first_raw = best, numeric
        records.append({'number': c['number'], 'origin': c['origin'], 'valid': c['all_versions_passed'],
                        'duplicate': c['duplicate'], 'changed': changed, 'accepted': c['accepted'],
                        'candidate_score': numeric, 'best_score': best})
    return records, {'first_changed_valid_raw_score': first_raw, 'best_after_first_changed_valid': first_best,
                     'further_search_gain_pp': None if first_best is None else best - gains['final_cleanup_gain_pp'] - first_best,
                     **gains}


def summarize():
    packs = load_inputs()
    names = read(BASE / 'config.json')['names']
    rows, trajectories, cleanup_jobs = [], [], set()
    controls = {}
    for mode, output in OUTPUTS.items():
        for path in sorted((output / 'cells').glob('*/result.json')):
            r = read(path)
            controls[(mode, r['name'], r['model'], r['effort'])] = r
    for mode, output in OUTPUTS.items():
        for name in names:
            for model, effort in CONDITIONS[mode]:
                key = (mode, name, model, effort)
                if key not in controls:
                    continue
                r = controls[key]
                folder = output / 'cells' / fingerprint((name, model, effort, r['mode']))
                checks_path = folder / 'evidence/checks.jsonl'
                checks = [json.loads(s) for s in checks_path.read_text().splitlines()] if checks_path.exists() else []
                original_identity = code_identity(packs[name]['row'], packs[name]['row']['src'])
                inp = read(folder / 'input.json')
                seed_code = inp.get('seed_proof', packs[name]['row']['src'])
                seed_score = inp['seed_evaluation']['scores']['combined_pct']
                trace, attribution = trajectory(packs[name]['row'], seed_code, inp['seed_evaluation'], checks)
                trajectories.extend({'mode': mode, 'name': name, 'model': model, 'effort': effort, **c} for c in trace)
                selected = r['selected_evaluation']['scores']['combined_pct']
                assert abs((trace[-1]['best_score'] if trace else seed_score) - selected) < 1e-9
                structural = controls.get(('correctness', name, model, effort)) if mode != 'correctness' else None
                structural_score = structural['selected_evaluation']['scores']['combined_pct'] if structural else None
                cleanup_path = folder / 'evidence/deterministic.jsonl'
                cleanups = [json.loads(s) for s in cleanup_path.read_text().splitlines()] if cleanup_path.exists() else []
                jobs = {c['job_path'] for c in cleanups if c['job_path']}
                cleanup_jobs.update(jobs)
                rows.append({'mode': mode, 'name': name, 'model': model, 'effort': effort,
                    'status': r['status'], 'historical_score': r['historical_score'],
                    'selected_score': selected, 'gain_over_historical_pp': None if r['historical_score'] is None else selected - r['historical_score'],
                    'length_reduction_pct': r['selected_evaluation']['scores']['length_reduction_pct'],
                    'heartbeat_reduction_pct': r['selected_evaluation']['scores']['heartbeat_reduction_pct'],
                    'compatibility_pct': r['selected_evaluation']['scores']['compatibility_pct'],
                    'structural_control_score': structural_score,
                    'gain_over_structural_control_pp': None if structural_score is None else selected - structural_score,
                    'seed_score': seed_score, **attribution,
                    'score_control_score': r.get('score_control_score'),
                    'gain_over_score_control_pp': r.get('gain_over_score_control_pp'),
                    'deterministic_tool_calls': r.get('deterministic_tool_calls', 0),
                    'valid_changed_proposals': r.get('valid_changed_proposals', 0),
                    'proposals_with_tool_cleanup': r.get('proposals_with_tool_cleanup', 0),
                    'deterministic_tool_coverage_pct': r.get('deterministic_tool_coverage_pct'),
                    'unique_cleanup_jobs': len(jobs),
                    'reused_cleanup_calls': sum(c['reused'] for c in cleanups),
                    'returned_original': code_identity(packs[name]['row'], r['selected_proof']) == original_identity,
                    'agent_tool_checks': r['agent_tool_checks'],
                    'completion_tokens': sum((g.get('usage') or {}).get('completion_tokens') or 0 for g in r['generations'])})
                cost = r.get('cost') or generations_cost(CostConfig(model, effort), r['generations'])
                rows[-1].update(cost_usd=cost['total_usd'], cost_status=cost['status'])
    conditions = []
    for mode, specs in CONDITIONS.items():
        for model, effort in specs:
            group = [r for r in rows if (r['mode'], r['model'], r['effort']) == (mode, model, effort)]
            complete = len(group) == len(names) and all(r['status'] == 'complete' for r in group)
            baseline = control_mean(historical, names, model, effort)
            structural = [r['structural_control_score'] for r in group]
            score_controls = [r['score_control_score'] for r in group]
            proposal_count = sum(r['valid_changed_proposals'] for r in group)
            conditions.append({'mode': mode, 'model': model, 'effort': effort, 'terminal': len(group),
                               'expected': len(names), 'complete': complete, 'historical_score': baseline,
                               'selected_score': mean(r['selected_score'] for r in group) if complete else None,
                               'gain_over_historical_pp': mean(r['gain_over_historical_pp'] for r in group) if complete and baseline is not None else None,
                               'structural_control_score': mean(structural) if complete and all(s is not None for s in structural) else None,
                               'gain_over_structural_control_pp': mean(r['gain_over_structural_control_pp'] for r in group) if complete and all(s is not None for s in structural) else None,
                               'returned_original': sum(r['returned_original'] for r in group),
                               'agent_tool_checks': sum(r['agent_tool_checks'] for r in group),
                               'completion_tokens': sum(r['completion_tokens'] for r in group),
                               'score_control_score': mean(score_controls) if complete and all(s is not None for s in score_controls) else None,
                               'gain_over_score_control_pp': mean(r['gain_over_score_control_pp'] for r in group) if complete and all(s is not None for s in score_controls) else None,
                               **{k: mean(r[k] for r in group) if complete else None for k in ('seed_score', 'model_gain_pp', 'in_loop_cleanup_gain_pp', 'final_cleanup_gain_pp')},
                               'deterministic_tool_calls': sum(r['deterministic_tool_calls'] for r in group),
                               'deterministic_tool_coverage_pct': 100 * sum(r['proposals_with_tool_cleanup'] for r in group) / proposal_count if proposal_count else None,
                               'mean_further_search_gain_pp': mean(r['further_search_gain_pp'] or 0 for r in group) if complete else None})
            conditions[-1]['cost'] = summarize_costs([{'name': r['name'], 'cost': {'total_usd': r['cost_usd']}} for r in group])
    destination = ROOT / 'results/harness'
    costs = {'unique_jobs': len(cleanup_jobs), 'reused_calls': sum(r['reused_cleanup_calls'] for r in rows),
             'optimizer_counters': {}}
    for path in sorted(cleanup_jobs):
        for key, count in read(Path(path) / 'result.json')['counters'].items():
            costs['optimizer_counters'][key] = costs['optimizer_counters'].get(key, 0) + count
    write_json(destination / 'comparison.json', {'at': now(), 'conditions': conditions, 'cells': rows,
               'deterministic_costs': costs,
               'note': 'Further-search gain excludes final cleanup and mere seed checks. Gains partition the monotone saved-best trajectory; they do not estimate causal effects. Cleanup counters count each shared job once across terminal cells.'})
    for filename, items in [('per_problem.csv', rows), ('trajectories.csv', trajectories)]:
        if items:
            with (destination / filename).open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(items[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(items)
    lines = ['# Harness comparison snapshot', '', f'Updated {now()}. Full means are shown only for complete conditions.', '',
             '| Stage | Model / effort | Terminal | Historical score | New score |', '| --- | --- | ---: | ---: | ---: |']
    for c in conditions:
        score = f"{c['selected_score']:.6f}%" if c['selected_score'] is not None else 'pending'
        lines.append(f"| {c['mode']} | {c['model']} / {c['effort']} | {c['terminal']}/{c['expected']} | {display(c['historical_score'])} | {score} |")
    finished_search = [c for c in conditions if c['mode'] == 'score' and c['complete']]
    if finished_search:
        lines += ['', '| Model / effort | Gain over stage 01 | Mean gain after first changed valid proposal | Agent checks | Completion tokens |',
                  '| --- | ---: | ---: | ---: | ---: |']
        for c in finished_search:
            control_gain = c['gain_over_structural_control_pp']
            gain = f'{control_gain:+.6f} pp' if control_gain is not None else 'no stage-01 control'
            lines.append(f"| {c['model']} / {c['effort']} | {gain} | {c['mean_further_search_gain_pp']:+.6f} pp | {c['agent_tool_checks']} | {c['completion_tokens']:,} |")
    finished_combined = [c for c in conditions if c['mode'] in ('score_edges', 'score_each') and c['complete']]
    if finished_combined:
        lines += ['', '| Mode / model / effort | Score-only control | Combined score | Change | Model gain above seed | In-loop cleanup gain | Final cleanup gain | Tool calls / coverage |',
                  '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for c in finished_combined:
            coverage = c['deterministic_tool_coverage_pct']
            coverage_text = f'{coverage:.1f}%' if coverage is not None else 'n/a'
            lines.append(f"| {c['mode']} / {c['model']} / {c['effort']} | {c['score_control_score']:.6f}% | {c['selected_score']:.6f}% | {c['gain_over_score_control_pp']:+.6f} pp | {c['model_gain_pp']:+.6f} pp | {c['in_loop_cleanup_gain_pp']:+.6f} pp | {c['final_cleanup_gain_pp']:+.6f} pp | {c['deterministic_tool_calls']} / {coverage_text} |")
    lines += ['', '## Cost comparison', '',
              'Estimates use public Standard API rates, short context per request and reported cache counters. They are API-equivalent estimates, not Codex invoices. Missing usage is unknown. Running cells are excluded until terminal usage is available. Reasoning is included in output; the $3 cap applies to every problem.', '',
              '| Stage / model / effort | Priced problems | Mean USD | Maximum USD | Over $3 |',
              '| --- | ---: | ---: | ---: | ---: |']
    for c in conditions:
        cost = c['cost']
        lines.append(f"| {c['mode']} / {c['model']} / {c['effort']} | {cost['known_cost_problems']}/{c['terminal']} | {display(cost['mean_observed_usd'], '')} | {display(cost['max_observed_usd'], '')} | {len(cost['over_budget_problems'])} |")
    lines += ['', 'In-loop cleanup is retired; stage 04 remains historical evidence. New model configurations use beginning/end cleanup. Refactoring is paused while selecting the model configuration.', '',
              'Stages use independent generations and measured inference varies. These are not budget-matched comparisons.', '',
              'The per-problem CSV separates the selected seed, model-generated gains, accepted in-loop cleanup gains and final cleanup. These increments describe the saved-best trajectory, not isolated causal effects. Further-search gain excludes final cleanup and merely checking the seed. Valid-proposal coverage measures unique changed valid proposals sent to the cleanup tool; it does not assume prompt compliance.', '',
              f"Across terminal cells there are {costs['unique_jobs']} unique cleanup jobs and {costs['reused_calls']} reused calls. The comparison JSON sums optimizer counters once per shared job across all conditions; do not add per-cell job counts to estimate total work. Initial/final evaluator validation and the original saved D0 construction are outside those counters.", '',
              'Completion-token counts use provider-reported usage, including reasoning, across completed CLI calls. Tool checks count agent requests, including duplicate code; trajectories mark duplicates. Cost estimation is documented in stage 05.', '',
              'This is a snapshot. The per-stage README/report files refresh automatically while runs continue. Regenerate with `python src/summarize_agent_harness.py`, or add `--watch --suite models` to refresh until the model-configuration controller finishes.']
    (destination / 'COMPARISON.md').write_text('\n'.join(lines) + '\n')
    return conditions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true', help='Refresh every 30 seconds until the controller finishes or fails')
    parser.add_argument('--suite', choices=('context', 'deterministic', 'models'), default='models')
    args = parser.parse_args()
    while True:
        print(json.dumps(summarize()), flush=True)
        controller = ROOT / 'results/harness' / {'context': 'controller.json', 'deterministic': 'deterministic_controller.json',
                                               'models': 'model_config_controller.json'}[args.suite]
        if not args.watch or not controller.exists() or read(controller).get('status') in ('finished', 'failed'):
            break
        time.sleep(30)
