"""Analyze completed Codex proof/trace evidence without model or Lean calls.

Only the four completed Astra/max, Astra/low, Luna/max and Luna/high cohorts
are included. Live Luna/medium files are not inputs. Outputs are reproducible
JSON/CSV, proof snapshots/diffs, command/feedback traces and standalone figures.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
from statistics import mean

from audit_experiments import _evaluation
from proof_eval.metrics import validate_candidate

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'results/one_shot'
COHORTS = [('astra_max', '09_codex_tools_baselines', 'gpt-6-astra', 'max'),
           ('astra_low', '10_astra_low', 'gpt-6-astra', 'low'),
           ('luna_max', '09_codex_tools_baselines', 'gpt-6-luna', 'max'),
           ('luna_high', '09_codex_tools_baselines', 'gpt-6-luna', 'high')]
SEEDS = ('original', 'deterministic')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def score(evaluation):
    return evaluation['scores']['combined_pct']


def analyze(output):
    output.mkdir(parents=True, exist_ok=True)
    hashes = {}

    def read(path, lines=False):
        body = path.read_bytes()
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(body).hexdigest()
        return [json.loads(s) for s in body.splitlines() if s.strip()] if lines else json.loads(body)

    rows = {r['name']: r for r in read(ROOT / 'data/benchmark_data_warmup.jsonl', True)}
    references = {r['name']: r for r in read(ROOT / 'results/deterministic/00_reference_baseline/reference_values.jsonl', True)}
    names = read(BASE / '01_context_ablation/config.json')['names']
    packs = {p['name']: p for f in sorted((BASE / '01_context_ablation/inputs').glob('*.json')) if (p := read(f))}
    slugs = {n: f'{i + 1:02d}_' + re.sub(r'[^a-zA-Z0-9_]+', '_', n.split('.')[-1]).strip('_')
             for i, n in enumerate(names)}
    for name in names:
        folder = output / 'cases' / slugs[name]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'original.lean').write_text(rows[name]['src'] + '\n')
        (folder / 'D0.lean').write_text(packs[name]['proof'] + '\n')
    records = []
    version_checks = 0
    for label, stage, model, effort in COHORTS:
        found = []
        for path in sorted((BASE / stage / 'cells').glob('*/result.json')):
            # Read identity before recording provenance: exclude live cohorts.
            identity = json.loads(path.read_text())
            if (identity['model'], identity['effort']) != (model, effort):
                continue
            d = read(path)
            name, seed = d['name'], d['seed']
            assert name in names and seed in SEEDS
            found.append((name, seed))
            key = (label, seed, name)
            repair = d['repair']
            row = rows[name]
            for proof, ev in [(d['selected_proof'], d['selected_evaluation']),
                              (repair['final_proof'], repair['final_evaluation'])]:
                version_checks += _evaluation(row, references[name], proof, ev, '/'.join(key))
                assert ev['scores']['compatibility_pct'] == 100
            folder = output / 'cases' / slugs[name]
            stem = label + '_' + seed
            (folder / (stem + '.lean')).write_text(d['selected_proof'] + '\n')
            (folder / (stem + '_model.lean')).write_text(repair['final_proof'] + '\n')
            diff = difflib.unified_diff((row['src'].rstrip() + '\n').splitlines(True),
                                       (d['selected_proof'].rstrip() + '\n').splitlines(True),
                                       fromfile='original.lean', tofile=stem + '.lean')
            (folder / (stem + '.diff')).write_text(''.join(diff))
            commands, feedbacks, saved_feedbacks, generations = [], [], [], []
            outside_metrics_reads = []
            passed_codes = []
            for number in range(repair['round_count'] + 1):
                attempt = path.parent / ('initial' if number == 0 else f'repair_{number:02d}')
                generation = read(attempt / 'generation.json')
                assert generation['status'] == 'received'
                generations.append(generation)
                read(attempt / 'request.json')
                events = read(attempt / 'events.jsonl', True)
                for line, event in enumerate(events, 1):
                    item = event.get('item', {})
                    if event.get('type') != 'item.completed' or item.get('type') != 'command_execution':
                        continue
                    command = {'round': number, 'event_line': line, 'id': item['id'],
                               'command': item['command'], 'exit_code': item.get('exit_code')}
                    text = item.get('aggregated_output', '')
                    start = text.find('{"kind": "lean_correctness_feedback"')
                    if start >= 0:
                        feedback = json.JSONDecoder().raw_decode(text[start:])[0]
                        command['validity_passed'] = feedback['all_versions_passed']
                        feedbacks.append(feedback['all_versions_passed'])
                    if '/src/proof_eval/metrics.py' in item['command']:
                        outside_metrics_reads.append(command)
                    commands.append(command)
                for check in sorted((attempt / 'workspace/validity_checks').glob('*.json')):
                    check_record = read(check)
                    saved_feedbacks.append(check_record['feedback']['all_versions_passed'])
                    if check_record['feedback']['all_versions_passed']:
                        passed_codes.append(validate_candidate(row, check_record['code'])[0])
            # Verify event-derived counts independently against saved checker output.
            assert Counter(feedbacks) == Counter(saved_feedbacks), key
            final_normalized = validate_candidate(row, repair['final_proof'])[0]
            usage = [g['usage'] for g in generations]
            assert all(u and u['completion_tokens'] is not None for u in usage)
            ev = d['selected_evaluation']
            primary = ev['primary_version']
            pre = score(repair['selected_evaluation'])
            cleanup_gain = score(ev) - pre if seed == 'deterministic' else 0.0
            r = {'cohort': label, 'model': model, 'effort': effort, 'seed': seed, 'name': name,
                 'source_cell': str(path.parent.relative_to(ROOT)), 'case_folder': 'cases/' + slugs[name],
                 'reference_length': row['proof_length'], 'selected_length': ev['candidate']['length'],
                 'reference_heartbeats': ev['per_version'][primary]['reference']['heartbeats'],
                 'selected_heartbeats': ev['per_version'][primary]['heartbeats'],
                 'primary_version': primary, 'd0_score': score(packs[name]['incumbent']),
                 **ev['scores'], 'model_final_score': score(repair['final_evaluation']),
                 'model_stage_selected_score': pre, 'cleanup_gain_pp': cleanup_gain,
                 'model_calls': len(generations), 'outer_repairs': repair['round_count'],
                 'initial_valid': repair['initial_valid'], 'final_valid': repair['final_valid'],
                 'returned_incumbent': repair['returned_incumbent'],
                 'completion_tokens': sum(u['completion_tokens'] for u in usage),
                 'tool_items': sum(g.get('tool_items', 0) for g in generations),
                 'shell_commands': len(commands), 'validity_checks': len(feedbacks),
                 'failed_validity_checks': feedbacks.count(False),
                 'first_tool_check_failed': bool(feedbacks and not feedbacks[0]),
                 'additional_check_after_pass': True in feedbacks and feedbacks.index(True) < len(feedbacks) - 1,
                 'uses_rg_or_sed': any(re.search(r'\brg\s|\bsed\s+-n', c['command']) for c in commands),
                 'metrics_implementation_read_commands': len(outside_metrics_reads),
                 'all_passing_tool_proofs_match_final': bool(passed_codes) and all(c == final_normalized for c in passed_codes),
                 'passing_tool_proofs_match_ignoring_whitespace': bool(passed_codes) and all(
                     c.split() == final_normalized.split() for c in passed_codes)}
            save(folder / (stem + '_trace.json'), {'source_events': [str((path.parent / ('initial' if n == 0 else f'repair_{n:02d}') / 'events.jsonl').relative_to(ROOT)) for n in range(len(generations))],
                 'commands': commands, 'feedback_sequence': feedbacks,
                 'method_note': 'Shell commands and visible correctness outcomes only; no reasoning text. rg/sed is a literal command-presence indicator, not a semantic retrieval score.'})
            records.append(r)
        assert len(found) == 30 and set(found) == {(n, s) for n in names for s in SEEDS}, label
    table = {(r['cohort'], r['seed'], r['name']): r for r in records}
    # Match initial prompts/model settings between the most informative controls.
    for name in names:
        for seed in SEEDS:
            original = read(ROOT / table[('astra_max', seed, name)]['source_cell'] / 'initial/request.json')
            for label in ('astra_low', 'luna_max', 'luna_high'):
                other = read(ROOT / table[(label, seed, name)]['source_cell'] / 'initial/request.json')
                assert {k: v for k, v in original.items() if k not in ('model', 'reasoning_effort')} == {
                    k: v for k, v in other.items() if k not in ('model', 'reasoning_effort')}, (label, name, seed)
    conditions = []
    for label, _, _, _ in COHORTS:
        for seed in SEEDS:
            items = [r for r in records if (r['cohort'], r['seed']) == (label, seed)]
            aggregate = {'cohort': label, 'seed': seed, 'n': len(items)}
            for field in ('combined_pct', 'length_reduction_pct', 'heartbeat_reduction_pct', 'compatibility_pct',
                          'model_final_score', 'model_stage_selected_score', 'cleanup_gain_pp'):
                aggregate[field] = mean(r[field] for r in items)
            for field in ('completion_tokens', 'model_calls', 'outer_repairs', 'tool_items', 'shell_commands',
                          'validity_checks', 'failed_validity_checks', 'first_tool_check_failed',
                          'initial_valid', 'final_valid', 'returned_incumbent', 'uses_rg_or_sed',
                          'metrics_implementation_read_commands', 'additional_check_after_pass',
                          'all_passing_tool_proofs_match_final', 'passing_tool_proofs_match_ignoring_whitespace'):
                aggregate[field] = sum(r[field] for r in items)
            aggregate['cleanup_improved_cases'] = sum(r['cleanup_gain_pp'] > 1e-8 for r in items)
            aggregate['beats_d0_cases'] = sum(r['combined_pct'] > r['d0_score'] + .05 for r in items)
            conditions.append(aggregate)
    paired = []
    for name in names:
        original, combined = [table[('astra_max', s, name)] for s in SEEDS]
        paired.append({'name': name, 'case_folder': original['case_folder'],
            'pure_score': original['combined_pct'], 'seeded_model_score': combined['model_final_score'],
            'combined_score': combined['combined_pct'], 'cleanup_gain_pp': combined['cleanup_gain_pp'],
            'combined_minus_pure_pp': combined['combined_pct'] - original['combined_pct'],
            'max_minus_low_original_pp': original['combined_pct'] - table[('astra_low', 'original', name)]['combined_pct'],
            'max_minus_luna_max_original_pp': original['combined_pct'] - table[('luna_max', 'original', name)]['combined_pct']})
    paired_summary = {field: {'mean_pp': mean(p[field] for p in paired),
                             'positive_cases': sum(p[field] > 0 for p in paired),
                             'negative_cases': sum(p[field] < 0 for p in paired)}
                      for field in ('combined_minus_pure_pp', 'max_minus_low_original_pp',
                                    'max_minus_luna_max_original_pp')}
    by_family = []
    for label, *_ in COHORTS:
        for family, putnam in [('project_declarations', False), ('putnam', True)]:
            items = [r for r in records if r['cohort'] == label and r['seed'] == 'original'
                     and r['name'].startswith('putnam_') == putnam]
            by_family.append({'cohort': label, 'family': family, 'n': len(items),
                              'combined_pct': mean(r['combined_pct'] for r in items)})
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'complete',
              'scope': '120 completed cells; Luna/medium excluded even if it later completes. No model calls, Lean compilation or reference measurement.',
              'audit': {'status': 'passed', 'checked_cells': len(records), 'checked_selected_and_final_version_outcomes': version_checks,
                        'request_parity_pairs': 90, 'event_feedback_matches_saved_feedback': True},
              'deterministic_baseline': mean(score(packs[n]['incumbent']) for n in names),
              'conditions': conditions, 'paired_astra': paired, 'paired_summary': paired_summary,
              'by_problem_family': by_family, 'cells': records}
    save(output / 'report.json', report)
    for filename, items in [('per_problem.csv', records), ('conditions.csv', conditions), ('paired_astra.csv', paired)]:
        with (output / filename).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(items[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(items)
    save(output / 'input_manifest.json', {'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                        'input_sha256': hashes})
    figures(output, names, table, conditions)
    return report


def figures(output, names, table, conditions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    labels = ['Old substitution', 'Old-variable extraction', 'Store updates', 'Variational calculus',
              'Electric-field derivative', 'Wick time ordering', 'Fsub progress', 'SKI diamond',
              'CCS choice', 'Fiberwise distance', 'Polynomial fold', 'Affine/tensor gaps',
              'Putnam 1964 A4', 'Putnam 1964 B2', 'Putnam 1995 A3']
    # Display names are tied to the explicit theorem order, not file glob order.
    short = {n: n.split('.')[-1] for n in names}
    for n in names:
        matches = [('substOldPostSubset', labels[0]), ('extractedOldExprInVars', labels[1]),
                   ('InitsUpdatesComm', labels[2]), ('fundamental_theorem', labels[3]),
                   ('electricField', labels[4]), ('ι_timeOrder', labels[5]), ('Typing.progress', labels[6]),
                   ('parallelReduction_diamond', labels[7]), ('bisimilarity_congr_choice', labels[8]),
                   ('fiberwise_dist', labels[9]), ('fold_advances', labels[10]), ('interleaved_affine', labels[11]),
                   ('1964_a4', labels[12]), ('1964_b2', labels[13]), ('1995_a3', labels[14])]
        short[n] = next((s for k, s in matches if k in n), short[n])
    columns = [('astra_max', 'original'), ('astra_max', 'deterministic'),
               ('astra_low', 'original'), ('luna_max', 'original'), ('luna_high', 'original')]
    values = np.array([[table[(m, s, n)]['combined_pct'] for m, s in columns] for n in names])
    fig, ax = plt.subplots(figsize=(10, 8.2), layout='constrained')
    im = ax.imshow(values, vmin=30, vmax=100, cmap='YlGnBu', aspect='auto')
    ax.set_yticks(range(len(names)), [short[n] for n in names])
    ax.set_xticks(range(len(columns)), ['Astra max\noriginal', 'Astra max\ncombined',
                                      'Astra low\noriginal', 'Luna max\noriginal', 'Luna high\noriginal'])
    ax.tick_params(axis='both', length=0)
    for y in range(len(names)):
        for x in range(len(columns)):
            ax.text(x, y, f'{values[y, x]:.1f}', ha='center', va='center',
                    color='white' if values[y, x] > 70 else 'black', fontsize=10)
    ax.set_title('Local warm-up score by problem\n15 problems, one proposal with correctness debugging per condition', pad=15)
    fig.colorbar(im, ax=ax, shrink=.65, label='Combined score (%)')
    for suffix in ('png', 'svg'):
        fig.savefig(output / ('per_problem_scores.' + suffix), dpi=160)
    plt.close(fig)
    pure = [next(c for c in conditions if (c['cohort'], c['seed']) == (label, 'original')) for label, *_ in COHORTS]
    fig, ax = plt.subplots(figsize=(8.5, 4.5), layout='constrained')
    y = np.arange(len(pure));height=.34
    ax.barh(y-height/2, [c['length_reduction_pct'] for c in pure], height, label='Source-token reduction', color='#4178a5')
    ax.barh(y+height/2, [c['heartbeat_reduction_pct'] for c in pure], height, label='Heartbeat reduction', color='#20928c')
    ax.set_yticks(y, ['Astra max', 'Astra low', 'Luna max', 'Luna high']);ax.invert_yaxis()
    ax.set_xlim(0,100);ax.set_xlabel('Mean reduction against fixed original reference (%)')
    ax.set_title('Original-proof arm: Astra improves both score components\nCompatibility is 100% for every completed condition')
    ax.legend(loc='lower right');ax.spines[['top','right']].set_visible(False)
    for suffix in ('png', 'svg'):
        fig.savefig(output / ('score_components.' + suffix), dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE / '11_astra_analysis')
    result = analyze(parser.parse_args().output.resolve())
    print(json.dumps({'status': result['status'], 'audit': result['audit']}))
