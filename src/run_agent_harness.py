"""Run the structural-context control or unrestricted score-feedback search.

Both start from original warm-up proofs with fixed cached references. The
correctness study compares Astra/low and Luna/max with their historical original
arms. Score search adds Astra/max and reports the best checked proof, first valid
proposal, score trajectory and actual inference use separately.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import threading

from codex_proposal import cli_identity
from proof_agent_proposal import generate, tool_instructions
from proof_agent_tools import ProofSession
from proof_eval import Evaluator
from proof_eval.one_shot import FIELDS, extract_declaration, fingerprint
from run_codex_baselines import original_evaluation
from run_deterministic import digest, write_json
from run_repair_matrix import check_references
from run_validity_repair import now, required_versions
from validity_feedback import all_versions_passed, build_validity_feedback

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'results/one_shot/01_context_ablation'
OUTPUTS = {'correctness': ROOT / 'results/harness/01_structural_context',
           'score': ROOT / 'results/harness/02_score_search'}
CONDITIONS = {'correctness': [('gpt-6-astra', 'low'), ('gpt-6-luna', 'max')],
              'score': [('gpt-6-astra', 'max'), ('gpt-6-astra', 'low'), ('gpt-6-luna', 'max')]}
OWN_FILES = ['src/run_agent_harness.py', 'src/proof_agent_proposal.py',
             'src/proof_agent_tools.py', 'src/proof_agent_client.py',
             'src/codex_readonly.py', 'src/run_codex_baselines_isolated.py',
             'src/codex_proposal.py', 'src/run_codex_baselines.py', 'src/run_repair_matrix.py',
             'src/run_combined_matrix.py', 'src/run_validity_repair.py',
             'src/validity_feedback.py', 'src/proof_eval/model_context.py',
             'prompts/agent_refactor_system_v2.md', 'prompts/structural_strategy_bank_v2.json']
_REPORT_LOCK = threading.Lock()


def read(path):
    return json.loads(Path(path).read_text())


def load_inputs():
    return {p['name']: p for path in sorted((BASE / 'inputs').glob('*.json')) if (p := read(path))}


def historical(name, model, effort):
    stage = '10_astra_low' if (model, effort) == ('gpt-6-astra', 'low') else '09_codex_tools_baselines'
    path = ROOT / 'results/one_shot' / stage / 'cells' / fingerprint((name, model, effort, 'original')) / 'result.json'
    return path, read(path)


def structural_control(name, model, effort):
    if (model, effort) not in CONDITIONS['correctness']:
        return None, None
    path = OUTPUTS['correctness'] / 'cells' / fingerprint((name, model, effort, 'correctness')) / 'result.json'
    control = read(path)
    if control['status'] != 'complete':
        raise ValueError('Structural control is incomplete: ' + name)
    return path, control


def messages(pack):
    """Same enhanced task context for both feedback modes; no other-arm outputs."""
    original = original_evaluation(pack)
    primary = original['primary_version']
    payload = {'name': pack['name'], 'source': pack['row']['source'],
               'required_versions': pack['row']['version_info'], 'exact_statement': pack['row']['statement'],
               'incumbent_declaration': pack['row']['src'], 'incumbent_scores': original['scores'],
               'reference_denominators': {'tokens': pack['row']['proof_length'],
                   'primary_heartbeats': original['per_version'][primary]['heartbeats']},
               'preceding_source_excerpt': pack['source_context'],
               'source_excerpt_note': 'Partial preceding source, not part of your output. Tools provide further source and goal context.',
               'structural_strategy_cards': read(ROOT / 'prompts/structural_strategy_bank_v2.json')['cards']}
    return [{'role': 'system', 'content': (ROOT / 'prompts/agent_refactor_system_v2.md').read_text()},
            {'role': 'user', 'content': 'Optimize this declaration using the supplied tools.\n' + json.dumps(payload, ensure_ascii=False, indent=2)}]


def prepare(output, mode, packs):
    base = read(BASE / 'config.json')
    pins = {**base['code_sha256'], **{p: digest(ROOT / p) for p in OWN_FILES}}
    config = {'schema_version': 1, 'mode': mode, 'names': base['names'],
              'conditions': [list(c) for c in CONDITIONS[mode]], 'seed': 'original',
              'code_sha256': pins, 'input_sha256': {n: fingerprint(p) for n, p in packs.items()},
              'base_config_sha256': digest(BASE / 'config.json'),
              'dataset_sha256': base['dataset_sha256'], 'environment_config_sha256': base['environment_config_sha256'],
              'cli': cli_identity(), 'selection_margin_pp': .05, 'deterministic_cleanup': False,
              'candidate_feedback': mode, 'max_total_attempts': None, 'max_total_tokens': None,
              'generation_timeout': 1800 if mode == 'correctness' else None,
              'max_outer_correctness_repairs': 3 if mode == 'correctness' else 0,
              'stop': 'first valid proposal' if mode == 'correctness' else 'agent completion or explicit finish; provider failures remain distinct',
              'historical_control_sha256': {}, 'structural_control_sha256': {},
              'tool_instructions': tool_instructions(mode)}
    for name in config['names']:
        for model, effort in CONDITIONS[mode]:
            path, _ = historical(name, model, effort)
            config['historical_control_sha256'][str(path.relative_to(ROOT))] = digest(path)
            if mode == 'score':
                structural_path, _ = structural_control(name, model, effort)
                if structural_path:
                    config['structural_control_sha256'][str(structural_path.relative_to(ROOT))] = digest(structural_path)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'config.json'
    if path.exists() and read(path) != config:
        raise ValueError('Frozen experiment configuration changed')
    write_json(path, config)
    return config


def guard(config, pack, evaluator):
    for relative, expected in config['code_sha256'].items():
        if digest(ROOT / relative) != expected:
            raise ValueError('Frozen code changed: ' + relative)
    for relative, field in [('data/benchmark_data_warmup.jsonl', 'dataset_sha256'),
                            ('environments.local.json', 'environment_config_sha256')]:
        if digest(ROOT / relative) != config[field]:
            raise ValueError('Frozen input changed: ' + relative)
    if digest(BASE / 'config.json') != config['base_config_sha256'] or fingerprint(pack) != config['input_sha256'][pack['name']]:
        raise ValueError('Frozen preparation changed')
    check_references(evaluator, pack, read(BASE / 'config.json'))


def run_cell(output, config, pack, model, effort, evaluator, generator=generate):
    mode = config['mode']
    folder = output / 'cells' / fingerprint((pack['name'], model, effort, mode))
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / '.cell.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (folder / 'result.json').exists():
            return read(folder / 'result.json')
        checked_guard = lambda: guard(config, pack, evaluator)
        checked_guard()
        session = ProofSession(folder / 'evidence', pack, evaluator, mode, guard=checked_guard)
        context = {'name': pack['name'], 'source_file': pack['row']['file_path'],
                   'required_versions': required_versions(pack),
                   'source_projects': {v: str(evaluator.projects[(pack['row']['source'], v)]) for v in required_versions(pack)}}
        initial = messages(pack)
        write_json(folder / 'input.json', {'name': pack['name'], 'model': model, 'effort': effort,
                   'mode': mode, 'messages': initial, 'seed_evaluation': original_evaluation(pack)})
        generations = []
        final_code, final_feedback = '', None
        max_rounds = config['max_outer_correctness_repairs']
        for round_number in range(max_rounds + 1):
            checked_guard()
            request = deepcopy(initial)
            if round_number:
                request[1]['content'] += '\nCorrectness repair only. Repair this proposal using the following compiler feedback.\n' + json.dumps(
                    {'previous_declaration': final_code, 'correctness_feedback': final_feedback}, ensure_ascii=False)
                # A failed unverified final is allowed another correctness-only turn.
                session.finished = None
                (session.folder / 'finished.json').unlink(missing_ok=True)
            generation = generator(folder=folder / f'attempt_{round_number:02d}', messages=request,
                model=model, effort=effort, mode=mode, session=session, context=context, expected_cli=config['cli'])
            generations.append(generation)
            if generation['status'] != 'received':
                break
            try:
                final_code = extract_declaration(generation['content'], generation['finish_reason'])
            except ValueError:
                final_code = generation['content']
            before = len(session.checks)
            final_feedback = session.check(final_code, origin='final_harness')
            final_eval = session.checks[-1]['evaluation'] if len(session.checks) > before else None
            if mode == 'score' or session.first_valid_code is not None:
                break
            if final_eval is None or final_eval['status'] not in ('invalid', 'failed', 'passed'):
                break
            final_feedback = build_validity_feedback(final_eval, session.versions)
        checked_guard()
        control_path, control = historical(pack['name'], model, effort)
        if digest(control_path) != config['historical_control_sha256'][str(control_path.relative_to(ROOT))]:
            raise ValueError('Historical control changed')
        first_valid = next((r for r in session.checks if r['all_versions_passed']), None)
        unavailable = any(r['evaluation']['status'] == 'incomplete' for r in session.checks)
        structural_score = None
        if mode == 'score':
            structural_path, structural = structural_control(pack['name'], model, effort)
            if structural_path:
                if digest(structural_path) != config['structural_control_sha256'][str(structural_path.relative_to(ROOT))]:
                    raise ValueError('Structural control changed')
                structural_score = structural['selected_evaluation']['scores']['combined_pct']
        result = {'name': pack['name'], 'model': model, 'effort': effort, 'mode': mode,
                  'status': 'complete' if generations[-1]['status'] == 'received' and not unavailable else 'incomplete',
                  'generation_status': generations[-1]['status'], 'generations': generations,
                  'selected_proof': session.best_code, 'selected_evaluation': session.best_evaluation,
                  'first_valid_evaluation': first_valid['evaluation'] if first_valid else None,
                  'first_valid_proof': first_valid['code'] if first_valid else None,
                  'historical_score': control['selected_evaluation']['scores']['combined_pct'],
                  'gain_over_historical_pp': session.best_evaluation['scores']['combined_pct'] - control['selected_evaluation']['scores']['combined_pct'],
                  'structural_control_score': structural_score,
                  'gain_over_structural_control_pp': None if structural_score is None else session.best_evaluation['scores']['combined_pct'] - structural_score,
                  'score_gain_after_first_valid_pp': None if first_valid is None else session.best_evaluation['scores']['combined_pct'] - first_valid['evaluation']['scores']['combined_pct'],
                  'checks': len(session.checks), 'agent_tool_checks': sum(r['origin'] == 'agent_tool' for r in session.checks),
                  'valid_checks': sum(r['all_versions_passed'] for r in session.checks),
                  'improvements': sum(r['accepted'] for r in session.checks),
                  'stop': session.finished or {'kind': 'model_final' if generations[-1]['status'] == 'received' else 'infrastructure',
                                             'reason': 'Agent returned a final declaration' if generations[-1]['status'] == 'received' else generations[-1].get('error')},
                  'finished_at': now()}
        write_json(folder / 'result.json', result)
        return result


def report(output, config):
    with _REPORT_LOCK:
        return _report(output, config)


def _report(output, config):
    records = [read(p) for p in (output / 'cells').glob('*/result.json')]
    n = len(config['names'])
    result = {'at': now(), 'mode': config['mode'], 'planned_cells': len(config['conditions']) * n,
              'terminal_cells': len(records), 'conditions': [], 'active': []}
    for model, effort in config['conditions']:
        group = [r for r in records if (r['model'], r['effort']) == (model, effort)]
        complete = len(group) == n and all(r['status'] == 'complete' for r in group)
        summary = {'model': model, 'effort': effort, 'terminal': len(group), 'expected': n, 'complete': complete,
                   'incomplete_outcomes': sum(r['status'] != 'complete' for r in group),
                   'mean_scores': {f: sum(r['selected_evaluation']['scores'][f] for r in group) / n if complete else None for f in FIELDS},
                   'historical_mean_score': sum(historical(name, model, effort)[1]['selected_evaluation']['scores']['combined_pct'] for name in config['names']) / n,
                   'structural_control_mean_score': sum(structural_control(name, model, effort)[1]['selected_evaluation']['scores']['combined_pct'] for name in config['names']) / n
                       if config['mode'] == 'score' and (model, effort) in CONDITIONS['correctness'] else None,
                   'model_calls': sum(len(r['generations']) for r in group),
                   'completion_tokens': sum((g.get('usage') or {}).get('completion_tokens') or 0 for r in group for g in r['generations']),
                   'unknown_usage_calls': sum((g.get('usage') or {}).get('completion_tokens') is None for r in group for g in r['generations']),
                   'agent_tool_checks': sum(r['agent_tool_checks'] for r in group),
                   'improvements': sum(r['improvements'] for r in group)}
        result['conditions'].append(summary)
        if complete:
            destination = output / 'conditions' / (model + '__' + effort)
            destination.mkdir(parents=True, exist_ok=True)
            ordered = sorted(group, key=lambda r: config['names'].index(r['name']))
            (destination / 'selected_candidates.jsonl').write_text(''.join(json.dumps({'name': r['name'], 'proof': r['selected_proof']}, ensure_ascii=False) + '\n' for r in ordered))
    for path in sorted((output / 'cells').glob('*/evidence/state.json')):
        if not (path.parent.parent / 'result.json').exists():
            state = read(path)
            inp = path.parent.parent / 'input.json'
            result['active'].append({**{k: state[k] for k in ('name', 'checks', 'valid_checks', 'improvements', 'updated_at')},
                                    'model': read(inp)['model'] if inp.exists() else None,
                                    'effort': read(inp)['effort'] if inp.exists() else None,
                                    'best_score': state['best_evaluation']['scores']['combined_pct']})
    result['status'] = 'complete' if all(c['complete'] for c in result['conditions']) else 'partial'
    write_json(output / 'report.json', result)
    lines = ['# ' + ('Structural context and correctness tools' if config['mode'] == 'correctness' else 'Score-feedback optimization'), '',
             f"Updated {result['at']}. **{result['status']}**: {len(records)}/{result['planned_cells']} terminal cells.", '',
             'See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.', '',
             '| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |', '| --- | --- | ---: | ---: | ---: | ---: |']
    for c in result['conditions']:
        s = c['mean_scores']['combined_pct']
        structural = c['structural_control_mean_score']
        lines.append(f"| {c['model']} | {c['effort']} | {c['terminal']}/{n} | {f'{s:.6f}%' if s is not None else 'pending'} | {c['historical_mean_score']:.6f}% | {f'{structural:.6f}%' if structural is not None else '—'} |")
    lines += ['', '## Completed cells', '', '| Theorem | Model / effort | Score | Change from historical | Tool checks |', '| --- | --- | ---: | ---: | ---: |']
    for r in sorted(records, key=lambda r: (config['names'].index(r['name']), r['model'], r['effort'])):
        lines.append(f"| {r['name']} | {r['model']} / {r['effort']} | {r['selected_evaluation']['scores']['combined_pct']:.6f}% | {r['gain_over_historical_pp']:+.6f} pp | {r['agent_tool_checks']} |")
    lines += ['', '## Running cells', '', '| Theorem | Model / effort | Checks | Best score so far |', '| --- | --- | ---: | ---: |']
    for r in result['active']:
        lines.append(f"| {r['name']} | {r['model']} / {r['effort']} | {r['checks']} | {r['best_score']:.6f}% |")
    (output / 'README.md').write_text('\n'.join(lines) + '\n')
    return result


def run(args):
    output = (args.output or OUTPUTS[args.mode]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        packs = load_inputs()
        config = prepare(output, args.mode, packs)
        evaluator = Evaluator()
        for pack in packs.values():
            guard(config, pack, evaluator)
        if args.prepare_only or args.report_only:
            return report(output, config)
        if args.name and not set(args.name) <= set(config['names']):
            raise ValueError('Unknown theorem name')
        selected = [n for n in config['names'] if not args.name or n in args.name]
        work = [(name, model, effort) for name in selected for model, effort in config['conditions']]
        ended = threading.Event()
        failures = []

        def reporter():
            while not ended.wait(30):
                try:
                    report(output, config)
                except Exception as error:
                    write_json(output / 'reporter_error.json', {'at': now(), 'error': str(error)})

        thread = threading.Thread(target=reporter, daemon=True)
        thread.start()
        write_json(output / 'run.json', {'status': 'running', 'started_at': now(), 'workers': args.workers,
                                       'selected_names': selected, 'mode': args.mode})
        try:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {pool.submit(run_cell, output, config, packs[name], model, effort, evaluator):
                           (name, model, effort) for name, model, effort in work}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        print(json.dumps({k: result[k] for k in ('name', 'model', 'effort', 'status', 'gain_over_historical_pp', 'checks')}), flush=True)
                        if result['status'] != 'complete':
                            failures.append({'cell': futures[future], 'error': result['generation_status']})
                    except Exception as error:
                        failures.append({'cell': futures[future], 'error': f'{type(error).__name__}: {error}'})
                        for pending in futures:
                            pending.cancel()
                    report(output, config)
        finally:
            ended.set()
            thread.join()
            write_json(output / 'run.json', {'status': 'failed' if failures else 'finished', 'at': now(), 'failures': failures})
        result = report(output, config)
        if failures:
            raise RuntimeError('Some cells are incomplete; inspect run.json, saved requests are not resampled')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=OUTPUTS, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--name', action='append')
    parser.add_argument('--workers', type=int, default=5)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--report-only', action='store_true')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be positive')
    result = run(args)
    print(json.dumps({'status': result['status'], 'terminal_cells': result['terminal_cells'], 'planned_cells': result['planned_cells']}))


if __name__ == '__main__':
    main()
