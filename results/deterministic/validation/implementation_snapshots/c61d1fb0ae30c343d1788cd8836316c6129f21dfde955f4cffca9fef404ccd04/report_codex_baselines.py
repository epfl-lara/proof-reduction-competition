"""Read-only validation and reporting of completed Codex baseline cells."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from audit_experiments import _evaluation
from proof_eval import Evaluator
from proof_eval.one_shot import FIELDS, fingerprint
from proof_eval.optimizer import score_improves
from run_codex_baselines import BASE, CONDITIONS, ROOT, paired_input, read
from run_combined_matrix import require_valid, select_cell
from run_deterministic import digest, write_json
from run_repair_matrix import check_references
from run_validity_repair import build_repair_messages, required_versions, now
from run_codex_baselines_isolated import EXECUTION_FILES
from validity_feedback import all_versions_passed, build_validity_feedback


def require(value, message):
    if not value:
        raise ValueError(message)


def audit_and_report(output):
    output = Path(output).resolve()
    config = read(output / 'config.json')
    require(config['conditions'] == [list(c) for c in CONDITIONS], 'Condition cohort changed')
    for path, expected in config['code_sha256'].items():
        require(digest(ROOT / path) == expected, 'Source changed: ' + path)
    require(digest(BASE / 'config.json') == config['base_config_sha256'], 'Base configuration changed')
    base_config = read(BASE / 'config.json')
    packs = {p['name']: p for f in (BASE / 'inputs').glob('*.json') if (p := read(f))}
    saved_hashes = read(BASE / 'input_hashes.json')
    references = {r['name']: r for line in (ROOT / 'results/deterministic/00_reference_baseline/reference_values.jsonl').read_text().splitlines() if (r := json.loads(line))}
    evaluator = Evaluator()
    index = read(BASE / 'cell_index.json')
    for name, pack in packs.items():
        require(fingerprint(pack) == config['input_sha256'][name] == saved_hashes[name], 'Prepared input changed')
        check_references(evaluator, pack, base_config)
    paths = sorted((output / 'cells').glob('*/result.json'))
    records = []
    per_case = []
    version_checks = 0
    for path in paths:
        record = read(path)
        name, model, effort, seed = [record[k] for k in ('name', 'model', 'effort', 'seed')]
        require((model, effort, seed) in CONDITIONS and name in config['names'], 'Unexpected completed cell')
        require(path.parent.name == fingerprint((name, model, effort, seed)), 'Cell identity changed')
        pack = packs[name]
        request = read(BASE / 'cells' / index[json.dumps([name, 'cards', 'deepseek-ai/DeepSeek-V4.1-Flash'])] / 'request.json')
        paired, messages = paired_input(pack, request['messages'], seed)
        supplied = read(path.parent / 'input.json')
        require(supplied['messages'] == messages and supplied['seed_proof'] == paired['proof'] and supplied['seed_evaluation'] == paired['incumbent'], 'Paired input changed')
        repair = read(path.parent / 'repair_result.json')
        require(repair == record['repair'], 'Repair result changed')
        previous = None
        isolated_calls = 0
        for i in range(repair['round_count'] + 1):
            stage = path.parent / ('initial' if i == 0 else f'repair_{i:02d}')
            trial = read(stage / 'result.json')
            expected_messages = messages if i == 0 else build_repair_messages(paired, previous['proof'], build_validity_feedback(previous['evaluation'], required_versions(pack)))
            require(trial['messages_sha256'] == fingerprint(expected_messages), 'Round prompt fingerprint changed')
            sent = read(stage / 'request.json')
            require(sent['messages'] == expected_messages and sent['model'] == model and sent['reasoning_effort'] == effort and sent['cli'] == config['cli'], 'Model/effort/prompt identity changed')
            require(read(stage / 'generation.json') == trial['generation'], 'Saved generation changed')
            envelope_path = stage / 'execution_envelope.json'
            if envelope_path.exists():
                envelope = read(envelope_path)
                require(envelope['policy'] == 'readonly_sources_host_validity', 'Unknown tool isolation policy')
                require(set(envelope['code_sha256']) == set(EXECUTION_FILES), 'Execution adapter file set changed')
                require(all(digest(ROOT / p) == h for p, h in envelope['code_sha256'].items()), 'Execution adapter changed')
                require(envelope['request_sha256'] == digest(stage / 'request.json'), 'Isolated request changed')
                require(envelope['protected_projects'] == list(sent['tool_context']['source_projects'].values()), 'Protected projects changed')
                require(digest(stage / 'workspace/check_candidate.py') == digest(ROOT / 'src/codex_validity_client.py'), 'Validity client changed')
                argv = read(stage / 'command.json')['argv']
                require(argv[1] == str(ROOT / 'src/codex_readonly.py') and '--' in argv, 'Missing write-restriction launcher')
                inner = argv[argv.index('--') + 1:]
                require(inner[0] == config['cli']['path'] and inner[1] == 'exec', 'Inner Codex command changed')
                isolated_calls += 1
            if previous:
                require(not all_versions_passed(previous['evaluation'], required_versions(pack)), 'Continued past first valid proposal')
            if trial['evaluation']['status'] == 'passed':
                _evaluation(pack['row'], references[name], trial['proof'], trial['evaluation'], f'{name}/{seed}/round{i}')
            previous = trial
        require(previous['proof'] == repair['final_proof'] and previous['evaluation'] == repair['final_evaluation'], 'Final repair identity changed')
        valid = all_versions_passed(previous['evaluation'], required_versions(pack))
        accepted = valid and score_improves(paired['incumbent'], previous['evaluation'], .05)
        require(repair['final_valid'] == valid and repair['accepted'] == bool(accepted), 'Validity or acceptance policy changed')
        require(repair['selected_proof'] == (previous['proof'] if accepted else paired['proof'])
                and repair['selected_evaluation'] == (previous['evaluation'] if accepted else paired['incumbent']), 'Repair selection changed')
        if seed == 'original':
            require('combined' not in record, 'Pure arm has deterministic cleanup')
            require(record['selected_proof'] == repair['selected_proof'] and record['selected_evaluation'] == repair['selected_evaluation'], 'Pure selection differs')
        else:
            selected = record['combined']
            # Independently recompute eligibility/max selection from saved branches.
            control = selected['d1'] | {'status': 'complete' if selected['complete_cleanup'] else 'incomplete_discovery'}
            proposal = (selected['cleaned_f'] | {'status': 'complete' if selected['complete_cleanup'] else 'incomplete_discovery'}) if selected['cleaned_f'] else None
            recomputed = select_cell(cell={'logical': [name, 'cards', model], 'key': path.parent.name}, pack=pack, repair=repair, snapshot={}, control=control, proposal=proposal)
            require(recomputed['selected_proof'] == record['selected_proof'] and recomputed['selected_evaluation'] == record['selected_evaluation'], 'Combined selection differs')
        require_valid(record['selected_evaluation'], pack['row'], record['selected_proof'])
        version_checks += _evaluation(pack['row'], references[name], record['selected_proof'], record['selected_evaluation'], name + '/' + seed)
        checks = list(path.parent.glob('*/workspace/validity_checks/*.json'))
        for check in checks:
            feedback = read(check)['feedback']
            # The whitelist builder is separately tested; check stored feedback
            # has no newly introduced measurement fields.
            def keys(value):
                if isinstance(value, dict):
                    for k, v in value.items():
                        yield k
                        yield from keys(v)
                elif isinstance(value, list):
                    for v in value:
                        yield from keys(v)
            require(not any(any(t in k.lower() for t in ('heartbeat', 'score', 'token', 'elapsed')) for k in keys(feedback)), 'Performance field in tool feedback')
        generations = [read(path.parent / ('initial' if i == 0 else f'repair_{i:02d}') / 'generation.json') for i in range(repair['round_count'] + 1)]
        per_case.append({'name': name, 'model': model, 'effort': effort, 'seed': seed,
            'seed_score': record['seed_score'], 'd0_score': pack['incumbent']['scores']['combined_pct'],
            'model_final_score': repair['final_evaluation'].get('scores', {}).get('combined_pct'),
            'selected_score': record['selected_evaluation']['scores']['combined_pct'],
            'gain_over_d0_pp': record['selected_evaluation']['scores']['combined_pct'] - pack['incumbent']['scores']['combined_pct'],
            'initial_valid': repair['initial_valid'], 'final_valid': repair['final_valid'],
            'returned_seed': repair['returned_incumbent'], 'outer_repairs': repair['round_count'],
            'codex_tool_items': sum(g.get('tool_items', 0) for g in generations), 'validity_tool_checks': len(checks),
            'isolated_calls': isolated_calls,
            'known_completion_tokens': sum((g.get('usage') or {}).get('completion_tokens') or 0 for g in generations),
            'unknown_usage_calls': sum(not g.get('usage') or g['usage'].get('completion_tokens') is None for g in generations)})
        records.append(record)
    report = {'at': now(), 'status': 'complete' if len(records) == len(CONDITIONS) * len(config['names']) else 'partial',
              'completed_cells': len(records), 'planned_cells': len(CONDITIONS) * len(config['names']),
              'audit': {'status': 'passed', 'selected_version_checks': version_checks, 'cached_references_checked': 36,
                        'scope': 'Saved prompt/repair/selection identities, score arithmetic, all-version evidence and unchanged references; no model calls or Lean compilation. Tool actions need separate qualitative review.'},
              'budget_scope': 'Completed cells only; running attempts and excluded stage-08 requests are additional work.',
              'per_case': per_case, 'conditions': []}
    n = len(config['names'])
    lines = ['# Codex agent baseline results', '', f"**{report['status']}**: {len(records)}/{report['planned_cells']} cells at {report['at']}.", '',
             'Tools are enabled. One optimization proposal, correctness-only debugging, and paired original/deterministic seeds. See [protocol](PROTOCOL.md).', '',
             'All scores use fixed local original references. Original identity: 33.333333%; deterministic D0: 46.248122%. Partial conditions have no full-benchmark mean.', '',
             '| Model | Effort | Seed | Finished | Initial valid | Final valid | Selected mean | Gain over D0 |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for model, effort, seed in CONDITIONS:
        cells = [r for r in records if (r['model'], r['effort'], r['seed']) == (model, effort, seed)]
        full = {r['name'] for r in cells} == set(config['names'])
        mean = {f: sum(r['selected_evaluation']['scores'][f] for r in cells) / n if full else None for f in FIELDS}
        delta = mean['combined_pct'] - sum(p['incumbent']['scores']['combined_pct'] for p in packs.values()) / n if full else None
        r = {'model': model, 'effort': effort, 'seed': seed, 'completed': len(cells), 'expected': n,
             'initial_valid': sum(c['repair']['initial_valid'] for c in cells), 'final_valid': sum(c['repair']['final_valid'] for c in cells),
             'selected_mean': mean, 'gain_over_d0_pp': delta}
        report['conditions'].append(r)
        lines.append(f"| {model} | {effort} | {seed} | {len(cells)}/{n} | {r['initial_valid']} | {r['final_valid']} | " + (f"{mean['combined_pct']:.6f}% | {delta:+.6f} pp |" if full else 'pending | pending |'))
    lines += ['', '| Problem | Model / effort | Seed | Selected score | Gain over D0 | Tool checks |', '| --- | --- | --- | ---: | ---: | ---: |']
    for row in sorted(per_case, key=lambda r: (config['names'].index(r['name']), r['model'], r['effort'], r['seed'])):
        lines.append(f"| `{row['name']}` | {row['model']} / {row['effort']} | {row['seed']} | {row['selected_score']:.4f}% | {row['gain_over_d0_pp']:+.4f} pp | {row['validity_tool_checks']} |")
    lines += ['', 'New calls after the [Luna recovery](recovery/README.md) keep source projects read-only and route validity checks through the host. Prompts and scoring stay fixed; `isolated_calls` records the execution-policy change.', '',
              'Usage and tool counts in [per_problem.csv](per_problem.csv) cover terminal cells only. Pending work and excluded pilot usage are additional; unknown usage is never zero. The full report is [report.json](report.json).', '']
    (output / 'README.md').write_text('\n'.join(lines))
    write_json(output / 'report.json', report)
    if per_case:
        with (output / 'per_problem.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(per_case[0]))
            writer.writeheader()
            writer.writerows(per_case)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=ROOT / 'results/one_shot/09_codex_tools_baselines')
    report = audit_and_report(p.parse_args().input)
    print(json.dumps({k: report[k] for k in ('status', 'completed_cells', 'planned_cells', 'audit')}))
