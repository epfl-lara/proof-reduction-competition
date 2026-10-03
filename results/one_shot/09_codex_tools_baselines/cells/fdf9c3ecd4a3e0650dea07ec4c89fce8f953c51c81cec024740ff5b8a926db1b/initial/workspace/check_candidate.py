"""Copied into a Codex workspace; exposes validity feedback, never a score."""
import json
from pathlib import Path
import sys
import uuid


def main():
    workspace = Path(__file__).resolve().parent
    config = json.loads((workspace / 'context.json').read_text())
    root = Path(config['evaluator_root'])
    sys.path.insert(0, str(root / 'src'))
    from proof_eval import Evaluator
    from proof_eval.metrics import validate_candidate
    from validity_feedback import build_validity_feedback
    code = Path(sys.argv[1]).read_text()
    evaluator = Evaluator(root / 'data/benchmark_data_warmup.jsonl', root / 'environments.local.json', root / '.proof-eval')
    row = evaluator.dataset.get(config['name'])
    try:
        is_original = validate_candidate(row, code)[0] == validate_candidate(row, row['src'])[0]
    except ValueError:
        is_original = False
    if is_original:
        references = evaluator.get_reference(config['name'])['versions']
        if any(r['status'] != 'prepared' for r in references.values()):
            raise RuntimeError('Prepared reference unavailable')
        evaluation = {'status': 'passed', 'per_version': {v: {'status': 'passed', 'passed': True, 'diagnostics': []} for v in references}}
    else:
        evaluation = evaluator.evaluate(config['name'], code, versions='all')
    feedback = build_validity_feedback(evaluation, config['required_versions'])
    evidence = workspace / 'validity_checks'
    evidence.mkdir(exist_ok=True)
    (evidence / (uuid.uuid4().hex + '.json')).write_text(json.dumps({'code': code, 'feedback': feedback}, ensure_ascii=False, indent=2))
    print(json.dumps(feedback, ensure_ascii=False))


if __name__ == '__main__':
    main()
