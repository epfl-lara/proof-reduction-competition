from copy import deepcopy
import json
from pathlib import Path

import pytest

from run_codex_baselines import BASE, original_evaluation, paired_input, optimization_cell, read


@pytest.fixture
def pack():
    return next(read(p) for p in (BASE / 'inputs').glob('*.json') if read(p)['name'] == 'CallElimCorrect.substOldPostSubset')


def test_pair_changes_only_seed_and_seed_metrics(pack):
    index = read(BASE / 'cell_index.json')
    key = index[json.dumps([pack['name'], 'cards', 'deepseek-ai/DeepSeek-V4.1-Flash'])]
    saved = read(BASE / 'cells' / key / 'request.json')['messages']
    a, ma = paired_input(pack, saved, 'deterministic')
    b, mb = paired_input(pack, saved, 'original')
    assert ma == saved
    pa, pb = [json.loads(m[1]['content'].split('\n', 1)[1]) for m in [ma, mb]]
    assert {k for k in pa if pa[k] != pb[k]} == {'incumbent_declaration', 'incumbent_scores'}
    assert b['proof'] == pack['row']['src']
    assert a['proof'] == pack['proof']
    assert b['incumbent']['scores']['combined_pct'] == 100 / 3


def test_original_cache_identity_is_checked(pack):
    bad = deepcopy(pack)
    next(iter(bad['incumbent']['per_version'].values()))['reference']['reference_code_sha256'] = 'wrong'
    with pytest.raises(ValueError, match='identity'):
        original_evaluation(bad)


def test_valid_lower_score_stops_without_optimization_feedback(pack, tmp_path):
    class FakeEvaluator:
        projects = {(pack['row']['source'], v): Path('/tmp/project') for v in pack['incumbent']['all_versions']}

        def evaluate(self, *args, **kwargs):
            raise AssertionError('Do not remeasure the original reference')

    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return {'status': 'received', 'content': pack['row']['src'], 'finish_reason': 'stop'}

    result = optimization_cell(folder=tmp_path, pack=pack, messages=[{'role': 'system', 'content': 's'}, {'role': 'user', 'content': 'u'}],
                               model='gpt-6-astra', effort='max', evaluator=FakeEvaluator(), guard=lambda: None, cli={}, generate=generate)
    assert result['round_count'] == 0 and len(calls) == 1
    assert result['final_valid'] and not result['accepted']
    assert result['selected_proof'] == pack['proof']


def test_empty_delivery_never_resampled(pack, tmp_path):
    class FakeEvaluator:
        projects = {(pack['row']['source'], v): Path('/tmp/project') for v in pack['incumbent']['all_versions']}

    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return {'status': 'received', 'content': '', 'finish_reason': 'stop'}

    kw = dict(folder=tmp_path, pack=pack, messages=[], model='gpt-6-astra', effort='max', evaluator=FakeEvaluator(), guard=lambda: None, cli={}, generate=generate)
    result = optimization_cell(**kw)
    assert not result['final_valid'] and result['round_count'] == 0
    assert optimization_cell(**kw) == result
    assert len(calls) == 1
