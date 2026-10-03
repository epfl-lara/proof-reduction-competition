"""Paired original vs deterministic-seeded Codex proposals, then validity repair.

One optimization sample; up to three correctness-only repairs. The pure arm has
no deterministic transforms. Every valid combined-arm final receives the same
bounded cleanup, including finals rejected before cleanup. References are read
from the existing cache, never remeasured. --name/--model/--effort select pending
work within one fixed manifest and do not create extra samples.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import fcntl
import json
from pathlib import Path

from codex_proposal import MODELS, cli_identity, generate_once
from proof_eval import Evaluator
from proof_eval.metrics import token_count, validate_candidate
from proof_eval.one_shot import FIELDS, extract_declaration, fingerprint, zero_evaluation
from proof_eval.optimizer import score_improves
from run_combined_matrix import cleanup_proof, cleanup_provenance, job_key, require_valid, select_cell, sha
from run_deterministic import digest, write_json
from run_repair_matrix import check_references
from run_validity_repair import build_repair_messages, now, required_versions, unavailable
from validity_feedback import all_versions_passed, build_validity_feedback

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'results/one_shot/01_context_ablation'
COMBINED = ROOT / 'results/one_shot/06_parallel_continuation/04_combined_deterministic'
CONDITIONS = [(model, effort, seed) for model, efforts in MODELS.items()
              for effort in ('max', 'high', 'medium') if effort in efforts
              for seed in ('deterministic', 'original')]


def read(path):
    return json.loads(Path(path).read_text())


def original_evaluation(pack):
    row = pack['row']
    normalized, body = validate_candidate(row, row['src'])
    if token_count(body) != row['proof_length']:
        raise ValueError('Original token count differs from the fixed denominator')
    ev = deepcopy(pack['incumbent'])
    ev.update(measurement='cached_reference_identity', candidate={'length': row['proof_length'], 'code_sha256': sha(normalized)},
              scores=dict(zip(FIELDS, (0.0, 0.0, 100.0, 100 / 3))))
    ev['diagnostics'] = []
    for version, previous in ev['per_version'].items():
        ref = previous['reference']
        if ref['status'] != 'prepared' or ref['reference_code_sha256'] != sha(row['src']):
            raise ValueError('Cached reference identity mismatch')
        ev['per_version'][version] = {'status': 'passed', 'passed': True, 'heartbeats': ref['heartbeats'],
            'heartbeats_raw': ref['heartbeats_raw'], 'reference': ref, 'heartbeat_reduction_pct': 0.0,
            'environment_fingerprint': ref['environment_fingerprint'], 'diagnostics': [], 'cached': True,
            'evidence': 'Existing prepared reference; no new compiler run or heartbeat measurement'}
    require_valid(ev, row, row['src'])
    return ev


def paired_input(pack, saved_messages, seed):
    if seed not in {'deterministic', 'original'}:
        raise ValueError('Unknown seed')
    payload = json.loads(saved_messages[1]['content'].split('\n', 1)[1])
    if payload['incumbent_declaration'] != pack['proof'] or payload['incumbent_scores'] != pack['incumbent']['scores']:
        raise ValueError('Saved cards request differs from the prepared D0 input')
    paired = deepcopy(pack)
    if seed == 'original':
        paired['proof'] = pack['row']['src']
        paired['incumbent'] = original_evaluation(pack)
        payload['incumbent_declaration'] = paired['proof']
        payload['incumbent_scores'] = paired['incumbent']['scores']
    # Keep the same strategy-card IDs/content in both arms. Do not retrieve
    # from the changed seed or expose deterministic results in the pure arm.
    messages = [deepcopy(saved_messages[0]), {'role': 'user', 'content': 'Optimize this declaration.\n' + json.dumps(payload, ensure_ascii=False, indent=2)}]
    paired.pop('context', None)
    return paired, messages


def evaluate_output(generation, pack, evaluator):
    if generation['status'] != 'received':
        return '', {'status': 'unavailable', 'scores': dict.fromkeys(FIELDS), 'per_version': {}}
    code = generation['content']
    try:
        code = extract_declaration(code, generation['finish_reason'])
    except ValueError as exc:
        return code, zero_evaluation(str(exc))
    # Returning the exact original is identity against an already measured
    # reference, not a reason to repeat reference measurement.
    try:
        same_original = validate_candidate(pack['row'], code)[0] == validate_candidate(pack['row'], pack['row']['src'])[0]
    except ValueError:
        same_original = False
    if same_original:
        return code, original_evaluation(pack)
    return code, evaluator.evaluate(pack['name'], code, versions='all')


def optimization_cell(*, folder, pack, messages, model, effort, evaluator, guard, cli, generate=generate_once):
    folder.mkdir(parents=True, exist_ok=True)
    terminal = folder / 'repair_result.json'
    if terminal.exists():
        return read(terminal)
    versions = required_versions(pack)
    rounds = []
    code, ev = '', None
    for number in range(4):
        guard()
        request_messages = messages if number == 0 else build_repair_messages(pack, code, build_validity_feedback(ev, versions))
        stage = folder / ('initial' if number == 0 else f'repair_{number:02d}')
        stage.mkdir(exist_ok=True)
        if number:
            write_json(stage / 'feedback.json', build_validity_feedback(ev, versions))
        if (stage / 'result.json').exists():
            trial = read(stage / 'result.json')
            if trial['messages_sha256'] != fingerprint(request_messages):
                raise ValueError('Saved repair feedback or prompt differs')
        else:
            tool_context = {'name': pack['name'], 'evaluator_root': str(ROOT), 'required_versions': versions,
                            'source_file': pack['row']['file_path'],
                            'source_projects': {v: str(evaluator.projects[(pack['row']['source'], v)]) for v in versions}}
            gen = generate(folder=stage, messages=request_messages, model=model, effort=effort, expected_cli=cli, tool_context=tool_context)
            guard()
            code, ev = evaluate_output(gen, pack, evaluator)
            trial = {'round': number, 'messages_sha256': fingerprint(request_messages), 'generation': gen, 'proof': code, 'evaluation': ev}
            write_json(stage / 'result.json', trial)
        rounds.append(trial)
        code, ev = trial['proof'], trial['evaluation']
        if all_versions_passed(ev, versions) or unavailable(ev) or trial['generation']['status'] != 'received' or not code.strip():
            break
    valid = all_versions_passed(ev, versions)
    accepted = valid and score_improves(pack['incumbent'], ev, .05)
    result = {'name': pack['name'], 'model': model, 'effort': effort,
              'initial_valid': all_versions_passed(rounds[0]['evaluation'], versions),
              'round_count': len(rounds) - 1, 'final_valid': valid, 'final_proof': code, 'final_evaluation': ev,
              'returned_incumbent': valid and code.strip() == pack['proof'].strip(), 'accepted': bool(accepted),
              'selected_proof': code if accepted else pack['proof'],
              'selected_evaluation': ev if accepted else pack['incumbent'],
              'attempts': [{k: r[k] for k in ('round', 'generation')} for r in rounds]}
    write_json(terminal, result)
    return result


def condition_label(model, effort, seed):
    return '__'.join((model, effort, seed))


def publish(output, config, packs):
    records = [read(p) for p in (output / 'cells').glob('*/result.json')]
    n = len(config['names'])
    summary = {'status': 'complete' if len(records) == len(CONDITIONS) * n else 'partial',
               'recorded_cells': len(records), 'planned_cells': len(CONDITIONS) * n,
               'original_baseline_pct': 100 / 3,
               'deterministic_baseline_pct': sum(p['incumbent']['scores']['combined_pct'] for p in packs.values()) / n,
               'conditions': []}
    for model, effort, seed in CONDITIONS:
        cells = [r for r in records if (r['model'], r['effort'], r['seed']) == (model, effort, seed)]
        complete = {r['name'] for r in cells} == set(config['names'])
        item = {'model': model, 'effort': effort, 'seed': seed, 'completed': len(cells), 'expected': n,
                'status': 'complete' if complete else 'partial',
                'initial_valid': sum(r['repair']['initial_valid'] for r in cells),
                'final_valid': sum(r['repair']['final_valid'] for r in cells),
                'returned_incumbent': sum(r['repair']['returned_incumbent'] for r in cells),
                'improved_over_seed': sum(r['selected_evaluation']['scores']['combined_pct'] > r['seed_score'] + .05 for r in cells),
                'selected_mean': {f: sum(r['selected_evaluation']['scores'][f] for r in cells) / n if complete else None for f in FIELDS},
                'model_calls': sum(len(r['repair']['attempts']) for r in cells)}
        attempts = [a['generation'] for r in cells for a in r['repair']['attempts']]
        item['known_completion_tokens'] = sum((a.get('usage') or {}).get('completion_tokens') or 0 for a in attempts)
        item['unknown_usage_calls'] = sum(not a.get('usage') or a['usage'].get('completion_tokens') is None for a in attempts)
        summary['conditions'].append(item)
        if complete:
            destination = output / 'conditions' / condition_label(model, effort, seed)
            destination.mkdir(parents=True, exist_ok=True)
            ordered = sorted(cells, key=lambda r: config['names'].index(r['name']))
            (destination / 'selected_candidates.jsonl').write_text(''.join(json.dumps({'name': r['name'], 'proof': r['selected_proof']}, ensure_ascii=False) + '\n' for r in ordered))
    write_json(output / 'summary.json', summary)
    return summary


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / '.run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        base_config = read(BASE / 'config.json')
        matrix = read(COMBINED / 'matrix_config.json')
        packs = {p['name']: p for f in (BASE / 'inputs').glob('*.json') if (p := read(f))}
        evaluator = Evaluator()
        index = read(BASE / 'cell_index.json')
        cli = cli_identity()
        pins = {**base_config['code_sha256'], **matrix['code_sha256']}
        for path in ['src/codex_proposal.py', 'src/codex_validity_tool.py', 'src/run_codex_baselines.py', 'src/run_validity_repair.py', 'src/validity_feedback.py']:
            pins.setdefault(path, digest(ROOT / path))
        config = {'schema_version': 1, 'names': base_config['names'], 'conditions': [list(c) for c in CONDITIONS],
                  'base_config_sha256': digest(BASE / 'config.json'), 'cli': cli, 'code_sha256': pins,
                  'input_sha256': {n: fingerprint(p) for n, p in packs.items()},
                  'dataset_sha256': base_config['dataset_sha256'], 'environment_config_sha256': base_config['environment_config_sha256'],
                  'workers': 2, 'max_repair_rounds': 3, 'request_timeout': 1800,
                  'protocol': 'Codex tools enabled for source inspection and validity debugging. One proposal, first all-version-valid final, correctness-only outer repairs, paired frozen cards; only deterministic seed gets cleanup. No cross-cell selection. CLI token/temperature controls unavailable.'}
        if (output / 'config.json').exists() and read(output / 'config.json') != config:
            raise ValueError('Experiment configuration changed')
        write_json(output / 'config.json', config)

        def guard(pack):
            if any(digest(ROOT / p) != h for p, h in pins.items()):
                raise ValueError('Pinned implementation changed')
            if digest(ROOT / 'data/benchmark_data_warmup.jsonl') != config['dataset_sha256'] or digest(ROOT / 'environments.local.json') != config['environment_config_sha256']:
                raise ValueError('Pinned dataset/environment changed')
            check_references(evaluator, pack, base_config)

        for pack in packs.values():
            guard(pack)
            original_evaluation(pack)

        def work(spec):
            name, model, effort, seed = spec
            pack = packs[name]
            guard(pack)
            key = fingerprint(spec)
            folder = output / 'cells' / key
            folder.mkdir(parents=True, exist_ok=True)
            if (folder / 'result.json').exists():
                return read(folder / 'result.json')
            source = read(BASE / 'cells' / index[json.dumps([name, 'cards', 'deepseek-ai/DeepSeek-V4.1-Flash'])] / 'request.json')
            paired, messages = paired_input(pack, source['messages'], seed)
            write_json(folder / 'input.json', {'name': name, 'model': model, 'effort': effort, 'seed': seed,
                                             'messages': messages, 'seed_proof': paired['proof'], 'seed_evaluation': paired['incumbent']})
            repair = optimization_cell(folder=folder, pack=paired, messages=messages, model=model, effort=effort,
                                       evaluator=evaluator, guard=lambda: guard(pack), cli=cli)
            result = {'name': name, 'model': model, 'effort': effort, 'seed': seed, 'repair': repair,
                      'seed_score': paired['incumbent']['scores']['combined_pct'],
                      'selected_proof': repair['selected_proof'], 'selected_evaluation': repair['selected_evaluation']}
            if seed == 'deterministic':
                control_folder = COMBINED / 'jobs' / job_key(name, pack['proof'])
                control = read(control_folder / 'result.json')
                control_spec = read(control_folder / 'job_config.json')
                if control_spec['provenance'] != cleanup_provenance(matrix, name) or control['job_config_sha256'] != fingerprint(control_spec):
                    raise ValueError('D1 control identity changed')
                require_valid(control['evaluation'], pack['row'], control['proof'])
                if any(digest(control_folder / path) != expected for path, expected in control['stage_result_sha256'].items()):
                    raise ValueError('D1 control evidence changed')
                proposal = None
                if repair['final_valid']:
                    proof = repair['final_proof']
                    proposal = control if proof == pack['proof'] else cleanup_proof(evaluator=evaluator, row=pack['row'], proof=proof,
                        folder=output / 'cleanup' / job_key(name, proof), provenance=cleanup_provenance(matrix, name), guard=lambda: guard(pack))
                selected = select_cell(cell={'logical': [name, 'cards', model], 'key': key}, pack=pack,
                                       repair=repair, snapshot={}, control=control, proposal=proposal)
                result.update(selected_proof=selected['selected_proof'], selected_evaluation=selected['selected_evaluation'], combined=selected)
            require_valid(result['selected_evaluation'], pack['row'], result['selected_proof'])
            guard(pack)
            write_json(folder / 'result.json', result)
            print(json.dumps({k: result[k] for k in ('name', 'model', 'effort', 'seed')} | {'final_valid': repair['final_valid'], 'repair_rounds': repair['round_count'], 'score': result['selected_evaluation']['scores']['combined_pct']}), flush=True)
            return result

        if args.name and not set(args.name) <= set(config['names']):
            raise ValueError('Unknown theorem name')
        worklist = []
        for i, name in enumerate(config['names']):
            if args.name and name not in args.name:
                continue
            for model, effort in [(m, e) for m in MODELS for e in ('max', 'high', 'medium') if e in MODELS[m]]:
                if args.model and model != args.model or args.effort and effort != args.effort:
                    continue
                for seed in (('deterministic', 'original') if i % 2 == 0 else ('original', 'deterministic')):
                    worklist.append((name, model, effort, seed))
        write_json(output / 'run.json', {'status': 'running', 'started_at': now(), 'scheduled_cells': len(worklist)})
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                for future in as_completed([pool.submit(work, spec) for spec in worklist]):
                    future.result()
                    publish(output, config, packs)
        finally:
            summary = publish(output, config, packs)
            write_json(output / 'run.json', {'status': summary['status'], 'finished_at': now(), 'recorded_cells': summary['recorded_cells'], 'planned_cells': summary['planned_cells']})
        return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'results/one_shot/09_codex_tools_baselines')
    p.add_argument('--model', choices=list(MODELS))
    p.add_argument('--effort', choices=['max', 'high', 'medium'])
    p.add_argument('--name', action='append')
    args = p.parse_args()
    if args.model and args.effort and args.effort not in MODELS[args.model]:
        p.error('Unsupported model/effort combination')
    run(args)


if __name__ == '__main__':
    main()
