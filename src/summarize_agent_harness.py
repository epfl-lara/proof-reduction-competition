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
from run_agent_harness import BASE, CONDITIONS, OUTPUTS, ROOT, historical, load_inputs, read
from run_deterministic import write_json
from run_validity_repair import now


def summarize():
    packs = load_inputs()
    names = read(BASE / 'config.json')['names']
    rows, trajectories = [], []
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
                folder = output / 'cells' / fingerprint((name, model, effort, mode))
                checks_path = folder / 'evidence/checks.jsonl'
                checks = [json.loads(s) for s in checks_path.read_text().splitlines()] if checks_path.exists() else []
                original_identity = code_identity(packs[name]['row'], packs[name]['row']['src'])
                best = 100 / 3
                best_after_first_changed_valid = None
                first_changed_valid_raw = None
                for c in checks:
                    if c['accepted']:
                        best = c['evaluation']['scores']['combined_pct']
                    changed = c['code_sha256'] != original_identity
                    if c['all_versions_passed'] and changed and best_after_first_changed_valid is None:
                        best_after_first_changed_valid = best
                        first_changed_valid_raw = c['evaluation']['scores']['combined_pct']
                    trajectories.append({'mode': mode, 'name': name, 'model': model, 'effort': effort,
                        'number': c['number'], 'origin': c['origin'], 'valid': c['all_versions_passed'],
                        'duplicate': c['duplicate'], 'changed': changed, 'accepted': c['accepted'],
                        'candidate_score': c['evaluation']['scores']['combined_pct'], 'best_score': best})
                selected = r['selected_evaluation']['scores']['combined_pct']
                assert abs(best - selected) < 1e-9
                structural = controls.get(('correctness', name, model, effort)) if mode == 'score' else None
                structural_score = structural['selected_evaluation']['scores']['combined_pct'] if structural else None
                rows.append({'mode': mode, 'name': name, 'model': model, 'effort': effort,
                    'status': r['status'], 'historical_score': r['historical_score'],
                    'selected_score': selected, 'gain_over_historical_pp': selected - r['historical_score'],
                    'length_reduction_pct': r['selected_evaluation']['scores']['length_reduction_pct'],
                    'heartbeat_reduction_pct': r['selected_evaluation']['scores']['heartbeat_reduction_pct'],
                    'compatibility_pct': r['selected_evaluation']['scores']['compatibility_pct'],
                    'structural_control_score': structural_score,
                    'gain_over_structural_control_pp': None if structural_score is None else selected - structural_score,
                    'first_changed_valid_raw_score': first_changed_valid_raw,
                    'best_after_first_changed_valid': best_after_first_changed_valid,
                    'further_search_gain_pp': None if best_after_first_changed_valid is None else selected - best_after_first_changed_valid,
                    'returned_original': code_identity(packs[name]['row'], r['selected_proof']) == original_identity,
                    'agent_tool_checks': r['agent_tool_checks'],
                    'completion_tokens': sum((g.get('usage') or {}).get('completion_tokens') or 0 for g in r['generations'])})
    conditions = []
    for mode, specs in CONDITIONS.items():
        for model, effort in specs:
            group = [r for r in rows if (r['mode'], r['model'], r['effort']) == (mode, model, effort)]
            complete = len(group) == len(names) and all(r['status'] == 'complete' for r in group)
            baseline = mean(historical(n, model, effort)[1]['selected_evaluation']['scores']['combined_pct'] for n in names)
            structural = [r['structural_control_score'] for r in group]
            conditions.append({'mode': mode, 'model': model, 'effort': effort, 'terminal': len(group),
                               'expected': len(names), 'complete': complete, 'historical_score': baseline,
                               'selected_score': mean(r['selected_score'] for r in group) if complete else None,
                               'gain_over_historical_pp': mean(r['gain_over_historical_pp'] for r in group) if complete else None,
                               'structural_control_score': mean(structural) if complete and all(s is not None for s in structural) else None,
                               'gain_over_structural_control_pp': mean(r['gain_over_structural_control_pp'] for r in group) if complete and all(s is not None for s in structural) else None,
                               'returned_original': sum(r['returned_original'] for r in group),
                               'agent_tool_checks': sum(r['agent_tool_checks'] for r in group),
                               'completion_tokens': sum(r['completion_tokens'] for r in group),
                               'mean_further_search_gain_pp': mean(r['further_search_gain_pp'] or 0 for r in group) if complete else None})
    destination = ROOT / 'results/harness'
    write_json(destination / 'comparison.json', {'at': now(), 'conditions': conditions, 'cells': rows,
               'note': 'Further-search gain is final best minus best after the first changed valid proposal. Original fallback gains and mere checks of the original are excluded.'})
    for filename, items in [('per_problem.csv', rows), ('trajectories.csv', trajectories)]:
        if items:
            with (destination / filename).open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(items[0]))
                writer.writeheader()
                writer.writerows(items)
    lines = ['# Harness comparison snapshot', '', f'Updated {now()}. Full means are shown only for complete conditions.', '',
             '| Stage | Model / effort | Terminal | Historical score | New score |', '| --- | --- | ---: | ---: | ---: |']
    for c in conditions:
        score = f"{c['selected_score']:.6f}%" if c['selected_score'] is not None else 'pending'
        lines.append(f"| {c['mode']} | {c['model']} / {c['effort']} | {c['terminal']}/{c['expected']} | {c['historical_score']:.6f}% | {score} |")
    finished_search = [c for c in conditions if c['mode'] == 'score' and c['complete']]
    if finished_search:
        lines += ['', '| Model / effort | Gain over stage 01 | Mean gain after first changed valid proposal | Agent checks | Completion tokens |',
                  '| --- | ---: | ---: | ---: | ---: |']
        for c in finished_search:
            control_gain = c['gain_over_structural_control_pp']
            gain = f'{control_gain:+.6f} pp' if control_gain is not None else 'no stage-01 control'
            lines.append(f"| {c['model']} / {c['effort']} | {gain} | {c['mean_further_search_gain_pp']:+.6f} pp | {c['agent_tool_checks']} | {c['completion_tokens']:,} |")
    lines += ['', 'The two stages use independent generations. Stage 02 adds performance feedback and additional inference; this is not a budget-matched comparison.', '',
              'The per-problem CSV includes stage-01 comparisons and within-trajectory gains after the first changed valid proposal. This last calculation uses the best score already available at that point, so fallback to the original is not counted as a subsequent search gain.', '',
              'Completion-token counts use provider-reported usage, including reasoning, across completed CLI calls. Tool checks count agent requests, including duplicate code; trajectories mark duplicates. Neither number is a dollar cost.', '',
              'This is a snapshot. The per-stage README/report files refresh automatically while runs continue. Regenerate with `python src/summarize_agent_harness.py`, or add `--watch` to refresh until the controller finishes.']
    (destination / 'COMPARISON.md').write_text('\n'.join(lines) + '\n')
    return conditions


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true', help='Refresh every 30 seconds until the controller finishes or fails')
    args = parser.parse_args()
    while True:
        print(json.dumps(summarize()), flush=True)
        controller = ROOT / 'results/harness/controller.json'
        if not args.watch or not controller.exists() or read(controller).get('status') in ('finished', 'failed'):
            break
        time.sleep(30)
