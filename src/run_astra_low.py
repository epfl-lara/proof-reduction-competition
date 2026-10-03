"""Astra/low paired cohort using the frozen Codex benchmark's proof operations.

The stage-09 manifest and live Luna implementation remain unchanged. This entry
point adds only the low-effort cohort, reusing proposal/repair, scoring, cleanup,
selection, export and evidence-audit functions from that implementation.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
from pathlib import Path

import codex_proposal
import report_codex_baselines as reporting
import run_codex_baselines as benchmark
from run_codex_baselines_isolated import EXECUTION_FILES, protected_execution
from run_deterministic import digest, write_json

ROOT = benchmark.ROOT
PARENT = ROOT / 'results/one_shot/09_codex_tools_baselines'
OUTPUT = ROOT / 'results/one_shot/10_astra_low'
CONDITIONS = [('gpt-6-astra', 'low', seed) for seed in ('deterministic', 'original')]


@contextmanager
def cohort_context():
    """Scope the added cohort to this process, restoring globals on exit."""
    previous = codex_proposal.MODELS, benchmark.CONDITIONS, reporting.CONDITIONS
    codex_proposal.MODELS = {k: set(v) for k, v in codex_proposal.MODELS.items()}
    codex_proposal.MODELS['gpt-6-astra'].add('low')
    benchmark.CONDITIONS = reporting.CONDITIONS = CONDITIONS
    try:
        yield
    finally:
        codex_proposal.MODELS, benchmark.CONDITIONS, reporting.CONDITIONS = previous


def prepare(output):
    parent = benchmark.read(PARENT / 'config.json')
    if any(digest(ROOT / p) != h for p, h in parent['code_sha256'].items()):
        raise ValueError('Parent benchmark implementation changed')
    if codex_proposal.cli_identity() != parent['cli']:
        raise ValueError('Codex CLI differs from the Astra/max comparison')
    config = deepcopy(parent)
    config.update(conditions=[list(c) for c in CONDITIONS],
                  parent_config_sha256=digest(PARENT / 'config.json'),
                  execution_policy='readonly_sources_host_validity',
                  extension='Astra low reasoning, paired against completed stage-09 Astra/max')
    config['comparison_sha256'] = {}
    for name in config['names']:
        for _, _, seed in CONDITIONS:
            key = benchmark.fingerprint((name, 'gpt-6-astra', 'max', seed))
            for tail in ('initial/request.json', 'result.json'):
                path = f'cells/{key}/{tail}'
                config['comparison_sha256'][path] = digest(PARENT / path)
    config['code_sha256'].update({p: digest(ROOT / p) for p in
                                 (*EXECUTION_FILES, 'src/run_astra_low.py')})
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'config.json'
    if path.exists() and benchmark.read(path) != config:
        raise ValueError('Astra/low experiment configuration changed')
    write_json(path, config)
    return config


def worklist(names, selected=None):
    if selected and not set(selected) <= set(names):
        raise ValueError('Unknown theorem name')
    return [(name, 'gpt-6-astra', 'low', seed)
            for i, name in enumerate(names) if not selected or name in selected
            for seed in (('deterministic', 'original') if i % 2 == 0 else ('original', 'deterministic'))]


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.run.lock').open('a') as lock, cohort_context(), protected_execution():
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = prepare(output)
        base = benchmark.read(benchmark.BASE / 'config.json')
        matrix = benchmark.read(benchmark.COMBINED / 'matrix_config.json')
        packs = {p['name']: p for f in (benchmark.BASE / 'inputs').glob('*.json') if (p := benchmark.read(f))}
        index = benchmark.read(benchmark.BASE / 'cell_index.json')
        evaluator = benchmark.Evaluator()

        def guard(pack):
            if any(digest(ROOT / p) != h for p, h in config['code_sha256'].items()):
                raise ValueError('Pinned implementation changed')
            for path, field in [('data/benchmark_data_warmup.jsonl', 'dataset_sha256'),
                                ('environments.local.json', 'environment_config_sha256')]:
                if digest(ROOT / path) != config[field]:
                    raise ValueError('Pinned dataset/environment changed')
            if digest(PARENT / 'config.json') != config['parent_config_sha256']:
                raise ValueError('Parent manifest changed')
            if benchmark.fingerprint(pack) != config['input_sha256'][pack['name']]:
                raise ValueError('Prepared input changed')
            benchmark.check_references(evaluator, pack, base)

        for pack in packs.values():
            guard(pack)
            benchmark.original_evaluation(pack)

        def work(spec):
            name, model, effort, seed = spec
            pack = packs[name]
            guard(pack)
            key = benchmark.fingerprint(spec)
            folder = output / 'cells' / key
            folder.mkdir(parents=True, exist_ok=True)
            if (folder / 'result.json').exists():
                return benchmark.read(folder / 'result.json')
            source = benchmark.read(benchmark.BASE / 'cells' /
                index[json.dumps([name, 'cards', 'deepseek-ai/DeepSeek-V4.1-Flash'])] / 'request.json')
            paired, messages = benchmark.paired_input(pack, source['messages'], seed)
            write_json(folder / 'input.json', {'name': name, 'model': model, 'effort': effort, 'seed': seed,
                'messages': messages, 'seed_proof': paired['proof'], 'seed_evaluation': paired['incumbent']})
            repair = benchmark.optimization_cell(folder=folder, pack=paired, messages=messages,
                model=model, effort=effort, evaluator=evaluator, guard=lambda: guard(pack), cli=config['cli'])
            result = {'name': name, 'model': model, 'effort': effort, 'seed': seed, 'repair': repair,
                'seed_score': paired['incumbent']['scores']['combined_pct'],
                'selected_proof': repair['selected_proof'], 'selected_evaluation': repair['selected_evaluation']}
            if seed == 'deterministic':
                control_folder = benchmark.COMBINED / 'jobs' / benchmark.job_key(name, pack['proof'])
                control = benchmark.read(control_folder / 'result.json')
                spec = benchmark.read(control_folder / 'job_config.json')
                if (spec['provenance'] != benchmark.cleanup_provenance(matrix, name)
                        or control['job_config_sha256'] != benchmark.fingerprint(spec)):
                    raise ValueError('D1 control identity changed')
                benchmark.require_valid(control['evaluation'], pack['row'], control['proof'])
                if any(digest(control_folder / p) != h for p, h in control['stage_result_sha256'].items()):
                    raise ValueError('D1 control evidence changed')
                proposal = None
                if repair['final_valid']:
                    proof = repair['final_proof']
                    proposal = control if proof == pack['proof'] else benchmark.cleanup_proof(
                        evaluator=evaluator, row=pack['row'], proof=proof,
                        folder=output / 'cleanup' / benchmark.job_key(name, proof),
                        provenance=benchmark.cleanup_provenance(matrix, name), guard=lambda: guard(pack))
                selected = benchmark.select_cell(cell={'logical': [name, 'cards', model], 'key': key},
                    pack=pack, repair=repair, snapshot={}, control=control, proposal=proposal)
                result.update(selected_proof=selected['selected_proof'],
                              selected_evaluation=selected['selected_evaluation'], combined=selected)
            benchmark.require_valid(result['selected_evaluation'], pack['row'], result['selected_proof'])
            guard(pack)
            write_json(folder / 'result.json', result)
            print(json.dumps({k: result[k] for k in ('name', 'model', 'effort', 'seed')} |
                {'final_valid': repair['final_valid'], 'repair_rounds': repair['round_count'],
                 'score': result['selected_evaluation']['scores']['combined_pct']}), flush=True)
            return result

        specs = worklist(config['names'], args.name)
        write_json(output / 'run.json', {'status': 'running', 'started_at': benchmark.now(), 'scheduled_cells': len(specs)})
        try:
            with ThreadPoolExecutor(max_workers=config['workers']) as pool:
                for future in as_completed([pool.submit(work, spec) for spec in specs]):
                    future.result()
                    benchmark.publish(output, config, packs)
        finally:
            summary = benchmark.publish(output, config, packs)
            write_json(output / 'run.json', {'status': summary['status'], 'finished_at': benchmark.now(),
                'recorded_cells': summary['recorded_cells'], 'planned_cells': summary['planned_cells']})
        return summary


def report(output):
    output = Path(output).resolve()
    config = benchmark.read(output / 'config.json')
    if config['parent_config_sha256'] != digest(PARENT / 'config.json'):
        raise ValueError('Parent manifest changed')
    if any(digest(PARENT / p) != h for p, h in config['comparison_sha256'].items()):
        raise ValueError('Saved Astra/max comparison evidence changed')
    with cohort_context():
        result = reporting.audit_and_report(output)
    # Require exact initial prompt parity with the corresponding Astra/max cell.
    paired = []
    for low in result['per_case']:
        high_key = benchmark.fingerprint((low['name'], 'gpt-6-astra', 'max', low['seed']))
        low_key = benchmark.fingerprint((low['name'], 'gpt-6-astra', 'low', low['seed']))
        a = benchmark.read(output / 'cells' / low_key / 'initial/request.json')
        b = benchmark.read(PARENT / 'cells' / high_key / 'initial/request.json')
        if {k: v for k, v in a.items() if k != 'reasoning_effort'} != {k: v for k, v in b.items() if k != 'reasoning_effort'}:
            raise ValueError('Astra low/max initial requests differ beyond reasoning effort')
        if low['isolated_calls'] != low['outer_repairs'] + 1:
            raise ValueError('Low-effort call lacks source write isolation')
        high = benchmark.read(PARENT / 'cells' / high_key / 'result.json')
        paired.append({'name': low['name'], 'seed': low['seed'], 'low_score': low['selected_score'],
                       'max_score': high['selected_evaluation']['scores']['combined_pct'],
                       'low_minus_max_pp': low['selected_score'] - high['selected_evaluation']['scores']['combined_pct']})
    comparison = {'at': benchmark.now(), 'status': result['status'], 'paired_cases': paired, 'conditions': []}
    for _, _, seed in CONDITIONS:
        cases = [c for c in paired if c['seed'] == seed]
        complete = {c['name'] for c in cases} == set(config['names'])
        comparison['conditions'].append({'seed': seed, 'completed': len(cases), 'expected': len(config['names']),
            'mean_low_minus_max_pp': sum(c['low_minus_max_pp'] for c in cases) / len(config['names']) if complete else None})
    write_json(output / 'comparison.json', comparison)
    text = (output / 'README.md').read_text().replace('# Codex agent baseline results', '# Astra low-reasoning baseline')
    text = text.replace('(recovery/README.md)', '(../09_codex_tools_baselines/recovery/README.md)')
    text += '\n[Paired low/max differences](comparison.json) are reported per case. Full-benchmark differences remain null until all 15 cases in an arm finish. Initial requests match Astra/max exactly except reasoning effort. Low calls use source-write isolation; historical max calls preceded that fix.\n'
    (output / 'README.md').write_text(text)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--name', action='append')
    parser.add_argument('--report-only', action='store_true')
    args = parser.parse_args()
    result = report(args.output) if args.report_only else run(args)
    print(json.dumps({k: result[k] for k in ('status',) if k in result}))


if __name__ == '__main__':
    main()
