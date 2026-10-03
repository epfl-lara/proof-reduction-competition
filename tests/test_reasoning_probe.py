from copy import deepcopy

import pytest

from proof_eval.one_shot import fingerprint
from proof_eval.rcp import map_rcp_reasoning
from run_reasoning_probe import derive_request, evaluate_generation


def request(model='Qwen/Qwen3.8-27B'):
    body = dict(model=model, temperature=.3, reasoning=True, reasoning_effort='high', max_tokens=32768,
                messages=[{'role': 'system', 'content': 'same'}, {'role': 'user', 'content': 'same input'}],
                reasoning_payload=map_rcp_reasoning(model, True, 'high')[1])
    return body | {'name': 'test', 'arm': 'plain', 'request_sha256': fingerprint(body)}


def test_changes_only_effort_and_mapping():
    before = request()
    after = derive_request(before, 'medium')
    assert {k for k in after if after[k] != before[k]} == {'reasoning_effort', 'reasoning_payload'}
    assert after['reasoning_payload']['reasoning_effort'] == 'medium'
    assert before['reasoning_payload']['reasoning_effort'] == 'xhigh'


def test_no_fake_deepseek_medium_ablation():
    with pytest.raises(ValueError, match='does not change'):
        derive_request(request('deepseek-ai/DeepSeek-V4.1-Flash'), 'medium')


def test_tampered_saved_request_rejected():
    data = request()
    data['messages'][1]['content'] = 'changed'
    with pytest.raises(ValueError, match='fingerprint'):
        derive_request(data, 'low')


def test_truncation_does_not_use_reasoning_as_proof():
    pack = {'name': 'test', 'proof': 'incumbent', 'incumbent': {'scores': {'combined_pct': 40}}}
    generation = {'status': 'received', 'finish_reason': 'length', 'content': '', 'reasoning_content': 'plausible Lean'}
    result = evaluate_generation(generation, pack, None)
    assert result['evaluation']['status'] == 'invalid'
    assert not result['accepted'] and result['selected_proof'] == 'incumbent'


def test_unknown_transport_stays_unavailable():
    pack = {'name': 'test', 'proof': 'incumbent', 'incumbent': {'scores': {'combined_pct': 40}}}
    result = evaluate_generation({'status': 'indeterminate'}, pack, None)
    assert result['evaluation']['scores']['combined_pct'] is None
