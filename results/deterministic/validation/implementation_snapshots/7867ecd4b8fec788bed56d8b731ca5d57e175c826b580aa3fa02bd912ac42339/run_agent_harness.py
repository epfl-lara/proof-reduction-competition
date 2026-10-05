"""Run proof search, defaulting to deterministic cleanup before and after it.

Original-reference denominators stay fixed. The deterministic modes seed score
search from the better original/D0 proof, then clean up at the end. All modes
retain the best proof passing every version. In-loop cleanup is retired.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict
import fcntl
import json
from pathlib import Path
import threading

from codex_proposal import cli_identity
from proof_agent_proposal import MODELS, generate, tool_instructions
from proof_agent_tools import DeterministicCleanup, ProofSession, code_identity
from proof_eval import Evaluator
from proof_eval.costs import CostConfig, estimate_configuration, generations_cost, rate_card, summarize_costs
from proof_eval.one_shot import FIELDS, extract_declaration, fingerprint
from run_codex_baselines import original_evaluation
from run_combined_matrix import BUDGET, METHODS, require_valid
from run_deterministic import digest, write_json
from run_repair_matrix import check_references
from run_validity_repair import now, required_versions
from validity_feedback import all_versions_passed, build_validity_feedback

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'results/one_shot/01_context_ablation'
OUTPUTS = {'correctness': ROOT / 'results/harness/01_structural_context',
           'score': ROOT / 'results/harness/02_score_search',
           'score_edges': ROOT / 'results/harness/03_deterministic_edges',
           'score_each': ROOT / 'results/harness/04_deterministic_each',  # Historical evidence only.
           'model_config': ROOT / 'results/harness/05_model_config'}
CONDITIONS = {'correctness': [('gpt-6-astra', 'low'), ('gpt-6-luna', 'max')],
              'score': [('gpt-6-astra', 'max'), ('gpt-6-astra', 'low'), ('gpt-6-luna', 'max')]}
CONDITIONS.update({mode: list(CONDITIONS['score']) for mode in ('score_edges', 'score_each')})
CONDITIONS['model_config'] = [('gpt-6.1-sol', 'max'), ('gpt-6-astra', 'high')]
RUN_MODES = ('correctness', 'score', 'score_edges')
DEFAULT_MODE = 'score_edges'
DEFAULT_OUTPUT = OUTPUTS['model_config']
DETERMINISTIC_MODES = ('score_edges',)
OWN_FILES = ['src/run_agent_harness.py', 'src/proof_agent_proposal.py',
             'src/proof_agent_tools.py', 'src/proof_agent_client.py',
             'src/codex_readonly.py', 'src/run_codex_baselines_isolated.py',
             'src/codex_proposal.py', 'src/run_codex_baselines.py', 'src/run_repair_matrix.py',
             'src/run_combined_matrix.py', 'src/run_validity_repair.py',
             'src/validity_feedback.py', 'src/proof_eval/model_context.py', 'src/proof_eval/costs.py',
             'prompts/agent_refactor_system_v2.md', 'prompts/structural_strategy_bank_v2.json']
_REPORT_LOCK = threading.Lock()


def read(path):
    return json.loads(Path(path).read_text())


def load_inputs():
    return {p['name']: p for path in sorted((BASE / 'inputs').glob('*.json')) if (p := read(path))}


def historical(name, model, effort):
    if (model, effort) not in CONDITIONS['score']:
        return None, None
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


def score_control(name, model, effort):
    if (model, effort) not in CONDITIONS['score']:
        return None, None
    path = OUTPUTS['score'] / 'cells' / fingerprint((name, model, effort, 'score')) / 'result.json'
    control = read(path)
    if control['status'] != 'complete':
        raise ValueError('Score-only control is incomplete: ' + name)
    return path, control


def starting_point(pack, mode):
    original = original_evaluation(pack)
    if mode in DETERMINISTIC_MODES:
        candidate = pack['incumbent']
        if (all_versions_passed(candidate, required_versions(pack))
                and candidate['scores']['combined_pct'] > original['scores']['combined_pct'] + .05):
            require_valid(candidate, pack['row'], pack['proof'])
            return pack['proof'], candidate
    return pack['row']['src'], original


def messages(pack, seed=None):
    """Same enhanced task context for both feedback modes; no other-arm outputs."""
    original = original_evaluation(pack)
    seed_code, seed_evaluation = seed or (pack['row']['src'], original)
    primary = original['primary_version']
    payload = {'name': pack['name'], 'source': pack['row']['source'],
               'required_versions': pack['row']['version_info'], 'exact_statement': pack['row']['statement'],
               'incumbent_declaration': seed_code, 'incumbent_scores': seed_evaluation['scores'],
               'reference_denominators': {'tokens': pack['row']['proof_length'],
                   'primary_heartbeats': original['per_version'][primary]['heartbeats']},
               'preceding_source_excerpt': pack['source_context'],
               'source_excerpt_note': 'Partial preceding source, not part of your output. Tools provide further source and goal context.',
               'structural_strategy_cards': read(ROOT / 'prompts/structural_strategy_bank_v2.json')['cards']}
    return [{'role': 'system', 'content': (ROOT / 'prompts/agent_refactor_system_v2.md').read_text()},
            {'role': 'user', 'content': 'Optimize this declaration using the supplied tools.\n' + json.dumps(payload, ensure_ascii=False, indent=2)}]


def preflight_costs(conditions):
    """No model calls or Lean measurements; use complete saved stage-03 traces."""
    source = OUTPUTS['score_edges']
    source_config = read(source / 'config.json')
    paths = sorted((source / 'cells').glob('*/result.json'))
    records = [read(p) for p in paths]
    scenarios = []
    for model, effort in conditions:
        for source_model, source_effort in source_config['conditions']:
            group = [r for r in records if (r['model'], r['effort']) == (source_model, source_effort)]
            if (len(group) != len(source_config['names']) or {r['name'] for r in group} != set(source_config['names'])
                    or any(r['status'] != 'complete' for r in group)):
                raise ValueError('Cost scenario needs a complete source cohort')
            scenarios.append(estimate_configuration(CostConfig(model, effort), group))
    return {'rate_card': rate_card(), 'scenarios': scenarios,
            'source_result_sha256': {str(p.relative_to(ROOT)): digest(p) for p in paths},
            'budget_policy': 'Report the $3 cap per problem; no stopping rule is imposed in this configuration comparison.',
            'pricing_assumptions': 'Standard, short context per request, no regional premium; API-equivalent, not a Codex invoice.'}


def prepare(output, mode, packs, conditions=None):
    if mode not in RUN_MODES:
        raise ValueError('Unsupported or retired search mode: ' + mode)
    conditions = conditions or (CONDITIONS['model_config'] if output == DEFAULT_OUTPUT else CONDITIONS[mode])
    if len({tuple(c) for c in conditions}) != len(conditions):
        raise ValueError('Duplicate model conditions')
    for model, effort in conditions:
        if model not in MODELS or effort not in MODELS[model]:
            raise ValueError('Unsupported model/effort condition')
    costs = preflight_costs(conditions)
    base = read(BASE / 'config.json')
    pins = {**base['code_sha256'], **{p: digest(ROOT / p) for p in OWN_FILES}}
    config = {'schema_version': 1, 'mode': mode, 'names': base['names'],
              'conditions': [list(c) for c in conditions],
              'seed': 'best_original_or_saved_deterministic' if mode in DETERMINISTIC_MODES else 'original',
              'code_sha256': pins, 'input_sha256': {n: fingerprint(p) for n, p in packs.items()},
              'base_config_sha256': digest(BASE / 'config.json'),
              'dataset_sha256': base['dataset_sha256'], 'environment_config_sha256': base['environment_config_sha256'],
              'cli': cli_identity(), 'selection_margin_pp': .05, 'deterministic_cleanup': mode in DETERMINISTIC_MODES,
              'candidate_feedback': mode, 'max_total_attempts': None, 'max_total_tokens': None,
              'generation_timeout': 1800 if mode == 'correctness' else None,
              'max_outer_correctness_repairs': 3 if mode == 'correctness' else 0,
              'stop': 'first valid proposal' if mode == 'correctness' else 'agent completion or explicit finish; provider failures remain distinct',
              'historical_control_sha256': {}, 'structural_control_sha256': {},
              'tool_instructions': tool_instructions(mode),
              'cost_estimate_sha256': fingerprint(costs),
              'cost_assumptions': {'service_tier': 'standard', 'context_band': 'short', 'regional_processing': False},
              'budget_usd_per_problem': 3., 'budget_enforced': False, 'rate_card': rate_card()}
    if mode in DETERMINISTIC_MODES:
        config.update(score_control_sha256={}, deterministic_methods=list(METHODS),
                      deterministic_budget=asdict(BUDGET),
                      deterministic_jobs=str((output.parent / 'deterministic_jobs').resolve()),
                      deterministic_placement='final_only')
    for name in config['names']:
        for model, effort in conditions:
            path, _ = historical(name, model, effort)
            if path:
                config['historical_control_sha256'][str(path.relative_to(ROOT))] = digest(path)
            if mode != 'correctness':
                structural_path, _ = structural_control(name, model, effort)
                if structural_path:
                    config['structural_control_sha256'][str(structural_path.relative_to(ROOT))] = digest(structural_path)
            if mode in DETERMINISTIC_MODES:
                score_path, _ = score_control(name, model, effort)
                if score_path:
                    config['score_control_sha256'][str(score_path.relative_to(ROOT))] = digest(score_path)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'config.json'
    if path.exists() and read(path) != config:
        raise ValueError('Frozen experiment configuration changed')
    write_json(output / 'cost_estimate.json', costs)
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
        seed = starting_point(pack, mode) if mode in DETERMINISTIC_MODES else None
        cleanup = None
        if seed is not None:
            base = read(BASE / 'config.json')
            provenance = {'input_sha256': config['input_sha256'][pack['name']],
                          'contexts': base['contexts'][pack['name']],
                          'references_sha256': fingerprint({v: e['reference'] for v, e in pack['incumbent']['per_version'].items()}),
                          'code_sha256': config['code_sha256']}
            cleanup = DeterministicCleanup(config['deterministic_jobs'], pack, evaluator, provenance, checked_guard)
        session = ProofSession(folder / 'evidence', pack, evaluator, mode, guard=checked_guard, seed=seed, cleanup=cleanup)
        context = {'name': pack['name'], 'source_file': pack['row']['file_path'],
                   'required_versions': required_versions(pack),
                   'source_projects': {v: str(evaluator.projects[(pack['row']['source'], v)]) for v in required_versions(pack)}}
        initial = messages(pack, seed=seed) if seed else messages(pack)
        write_json(folder / 'input.json', {'name': pack['name'], 'model': model, 'effort': effort,
                   'mode': mode, 'messages': initial, 'seed_proof': session.seed_code,
                   'seed_evaluation': session.seed_evaluation})
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
            if mode != 'correctness' or session.first_valid_code is not None:
                break
            if final_eval is None or final_eval['status'] not in ('invalid', 'failed', 'passed'):
                break
            final_feedback = build_validity_feedback(final_eval, session.versions)
        checked_guard()
        before_final_cleanup = {'proof': session.best_code, 'evaluation': deepcopy(session.best_evaluation)}
        if mode in DETERMINISTIC_MODES:
            session.deterministic(session.best_code, origin='final_harness')
        control_path, control = historical(pack['name'], model, effort)
        if control_path and digest(control_path) != config['historical_control_sha256'][str(control_path.relative_to(ROOT))]:
            raise ValueError('Historical control changed')
        historical_score = control['selected_evaluation']['scores']['combined_pct'] if control else None
        first_valid = next((r for r in session.checks if r['all_versions_passed']), None)
        unavailable = any(r['evaluation']['status'] == 'incomplete' for r in session.checks)
        structural_score = None
        if mode != 'correctness':
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
                  'historical_score': historical_score,
                  'gain_over_historical_pp': None if historical_score is None else session.best_evaluation['scores']['combined_pct'] - historical_score,
                  'structural_control_score': structural_score,
                  'gain_over_structural_control_pp': None if structural_score is None else session.best_evaluation['scores']['combined_pct'] - structural_score,
                  'score_gain_after_first_valid_pp': None if first_valid is None else session.best_evaluation['scores']['combined_pct'] - first_valid['evaluation']['scores']['combined_pct'],
                  'checks': len(session.checks), 'agent_tool_checks': sum(r['origin'] == 'agent_tool' for r in session.checks),
                  'valid_checks': sum(r['all_versions_passed'] for r in session.checks),
                  'improvements': sum(r['accepted'] for r in session.checks),
                  'stop': session.finished or {'kind': 'model_final' if generations[-1]['status'] == 'received' else 'infrastructure',
                                             'reason': 'Agent returned a final declaration' if generations[-1]['status'] == 'received' else generations[-1].get('error')},
                  'finished_at': now()}
        if 'cost_assumptions' in config:
            result['cost'] = generations_cost(CostConfig(model, effort, **config['cost_assumptions']), generations,
                                              budget_usd=config['budget_usd_per_problem'])
        if mode in DETERMINISTIC_MODES:
            score_path, control = score_control(pack['name'], model, effort)
            if score_path and digest(score_path) != config['score_control_sha256'][str(score_path.relative_to(ROOT))]:
                raise ValueError('Score-only control changed')
            control_score = control['selected_evaluation']['scores']['combined_pct'] if control else None
            valid_proposals = {r['code_sha256'] for r in session.checks
                               if r['origin'] in ('agent_tool', 'deterministic_input', 'final_harness')
                               and r['all_versions_passed'] and not r['duplicate']
                               and r['code_sha256'] != code_identity(pack['row'], session.seed_code)}
            tool_calls = [c for c in session.cleanup_calls if c['origin'] == 'agent_tool']
            covered = valid_proposals & {c['input_code_sha256'] for c in tool_calls if c['status'] != 'skipped_invalid'}
            result.update(seed_proof=session.seed_code, seed_evaluation=session.seed_evaluation,
                          before_final_cleanup=before_final_cleanup,
                          final_cleanup_gain_pp=session.best_evaluation['scores']['combined_pct'] - before_final_cleanup['evaluation']['scores']['combined_pct'],
                          score_control_score=control_score,
                          gain_over_score_control_pp=None if control_score is None else session.best_evaluation['scores']['combined_pct'] - control_score,
                          deterministic_calls=len(session.cleanup_calls), deterministic_tool_calls=len(tool_calls),
                          valid_changed_proposals=len(valid_proposals), proposals_with_tool_cleanup=len(covered),
                          deterministic_tool_coverage_pct=100 * len(covered) / len(valid_proposals) if valid_proposals else None,
                          incomplete_cleanups=sum(c['status'] not in ('complete', 'skipped_invalid') for c in session.cleanup_calls))
            if result['incomplete_cleanups']:
                result['status'] = 'incomplete'
        write_json(folder / 'result.json', result)
        return result


def report(output, config):
    with _REPORT_LOCK:
        return _report(output, config)


def control_mean(loader, names, model, effort):
    controls = [loader(name, model, effort)[1] for name in names]
    return (sum(c['selected_evaluation']['scores']['combined_pct'] for c in controls) / len(names)
            if controls and all(c is not None for c in controls) else None)


def display(value, suffix='%', *, signed=False):
    return '—' if value is None else (f'{value:+.6f}' if signed else f'{value:.6f}') + suffix


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
                   'historical_mean_score': control_mean(historical, config['names'], model, effort),
                   'structural_control_mean_score': sum(structural_control(name, model, effort)[1]['selected_evaluation']['scores']['combined_pct'] for name in config['names']) / n
                       if config['mode'] != 'correctness' and (model, effort) in CONDITIONS['correctness'] else None,
                   'model_calls': sum(len(r['generations']) for r in group),
                   'completion_tokens': sum((g.get('usage') or {}).get('completion_tokens') or 0 for r in group for g in r['generations']),
                   'unknown_usage_calls': sum((g.get('usage') or {}).get('completion_tokens') is None for r in group for g in r['generations']),
                   'agent_tool_checks': sum(r['agent_tool_checks'] for r in group),
                   'improvements': sum(r['improvements'] for r in group)}
        if config.get('deterministic_cleanup'):
            proposal_count = sum(r['valid_changed_proposals'] for r in group)
            summary.update(score_control_mean_score=control_mean(score_control, config['names'], model, effort),
                           mean_final_cleanup_gain_pp=sum(r['final_cleanup_gain_pp'] for r in group) / n if complete else None,
                           deterministic_tool_calls=sum(r['deterministic_tool_calls'] for r in group),
                           deterministic_tool_coverage_pct=100 * sum(r['proposals_with_tool_cleanup'] for r in group) / proposal_count if proposal_count else None,
                           incomplete_cleanups=sum(r['incomplete_cleanups'] for r in group))
        summary['cost'] = summarize_costs([{'name': r['name'], 'cost': r.get('cost') or
            generations_cost(CostConfig(model, effort), r['generations'])} for r in group])
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
        lines.append(f"| {c['model']} | {c['effort']} | {c['terminal']}/{n} | {f'{s:.6f}%' if s is not None else 'pending'} | {display(c['historical_mean_score'])} | {f'{structural:.6f}%' if structural is not None else '—'} |")
    if config.get('deterministic_cleanup'):
        lines += ['', f"Deterministic placement: `{config['mode']}`. Fixed reference denominators and saved original/D0 seeds.", '',
                  '| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |',
                  '| --- | ---: | ---: | ---: | ---: |']
        for c in result['conditions']:
            gain = c['mean_final_cleanup_gain_pp']
            coverage = c['deterministic_tool_coverage_pct']
            lines.append(f"| {c['model']} / {c['effort']} | {display(c['score_control_mean_score'])} | {f'{gain:+.6f} pp' if gain is not None else 'pending'} | {c['deterministic_tool_calls']} | {f'{coverage:.2f}%' if coverage is not None else '—'} |")
    lines += ['', '## Estimated API-equivalent cost', '',
              'Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.', '',
              '| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |',
              '| --- | ---: | ---: | ---: | ---: |']
    for c in result['conditions']:
        cost = c['cost']
        lines.append(f"| {c['model']} / {c['effort']} | {cost['known_cost_problems']}/{c['terminal']} | {display(cost['mean_observed_usd'], ' USD')} | {display(cost['max_observed_usd'], ' USD')} | {len(cost['over_budget_problems'])} |")
    lines += ['', '## Completed cells', '', '| Theorem | Model / effort | Score | Change from historical | Tool checks |', '| --- | --- | ---: | ---: | ---: |']
    for r in sorted(records, key=lambda r: (config['names'].index(r['name']), r['model'], r['effort'])):
        lines.append(f"| {r['name']} | {r['model']} / {r['effort']} | {r['selected_evaluation']['scores']['combined_pct']:.6f}% | {display(r['gain_over_historical_pp'], ' pp', signed=True)} | {r['agent_tool_checks']} |")
    lines += ['', '## Running cells', '', '| Theorem | Model / effort | Checks | Best score so far |', '| --- | --- | ---: | ---: |']
    for r in result['active']:
        lines.append(f"| {r['name']} | {r['model']} / {r['effort']} | {r['checks']} | {r['best_score']:.6f}% |")
    (output / 'README.md').write_text('\n'.join(lines) + '\n')
    return result


def run(args):
    output = (args.output or (DEFAULT_OUTPUT if args.mode == DEFAULT_MODE else OUTPUTS[args.mode])).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.report_only:
            return report(output, read(output / 'config.json'))
        conditions = [tuple(c.split(':')) for c in args.condition] if args.condition else None
        if args.estimate_only:
            result = preflight_costs(conditions or (CONDITIONS['model_config'] if output == DEFAULT_OUTPUT else CONDITIONS[args.mode]))
            write_json(output / 'cost_estimate.json', result)
            return result
        packs = load_inputs()
        config = prepare(output, args.mode, packs, conditions=conditions)
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
    parser.add_argument('--mode', choices=RUN_MODES, default=DEFAULT_MODE)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--condition', action='append', metavar='MODEL:EFFORT',
                        help='Repeat for each condition; defaults to Sol 6.1/max and Astra/high in the new cohort')
    parser.add_argument('--name', action='append')
    parser.add_argument('--workers', type=int, default=5)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--report-only', action='store_true')
    parser.add_argument('--estimate-only', action='store_true', help='Reprice saved usage before any model calls or Lean measurements')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be positive')
    if sum((args.estimate_only, args.prepare_only, args.report_only)) > 1:
        parser.error('Choose only one of --estimate-only, --prepare-only and --report-only')
    for condition in args.condition or []:
        if len(condition.split(':')) != 2 or condition.split(':')[1] not in MODELS.get(condition.split(':')[0], set()):
            parser.error('Unsupported MODEL:EFFORT: ' + condition)
    result = run(args)
    print(json.dumps([{'target': s['configuration'], 'source': s['source_configuration'], **s['summary']} for s in result['scenarios']]
                     if args.estimate_only else {k: result[k] for k in ('status', 'terminal_cells', 'planned_cells')}))


if __name__ == '__main__':
    main()
