import json
from pathlib import Path

import pytest

from proof_eval.one_shot import build_messages, context_for_prompt, extract_declaration, select_cards, summarize, zero_evaluation


def test_extraction_never_repairs_or_uses_reasoning():
    code = 'theorem t : True := by trivial'
    assert extract_declaration(code, 'stop') == code
    assert extract_declaration('```lean\n'+code+'\n```', 'stop') == code
    for text, reason in [('', 'stop'), (code, 'length'), ('Here is it:\n```lean\n'+code+'\n```','stop'),
                         ('```lean\n'+code+'\n```\n```lean\n'+code+'\n```','stop'), ('by exact?', 'stop')]:
        with pytest.raises(ValueError):extract_declaration(text, reason)


def test_costs_are_absent_from_goal_only_context_and_do_not_mutate_source():
    context = {'status':'ok','sites':[{'before_goals':['⊢ True'],'tactic_heartbeats':3,
               'cost_status':'measured','invocations':[{'tactic_allocations':3000,'before_goals':['⊢ True']}]}]}
    plain = context_for_prompt(context)
    assert 'heartbeats' not in json.dumps(plain) and 'allocations' not in json.dumps(plain)
    assert plain['sites'][0]['before_goals'] == ['⊢ True']
    assert context_for_prompt(context,True)['sites'][0]['tactic_heartbeats'] == 3


def test_cards_are_deterministic_and_do_not_include_warmup_examples():
    bank=json.loads((Path(__file__).parents[1]/'prompts/strategy_bank.json').read_text())
    assert all(c['evidence']==[] for c in bank['cards'])
    assert select_cards(bank,'by simp; exact h') == select_cards(bank,'by simp; exact h')
    assert len(select_cards(bank,'by simp; exact h')) <= 4
    card={'id':'x','triggers':['have ','exact ']}
    assert select_cards({'cards':[card]},'by have h := trivial; exact h') == [card]


def test_missing_context_cannot_silently_become_plain():
    incumbent={'primary_version':'v1','per_version':{'v1':{'reference':{'heartbeats':20}}},'scores':{}}
    row={'name':'x','source':'x','version_info':[{'v1':'abc'}],'statement':'theorem x : True','proof_length':3}
    with pytest.raises(ValueError,match='unavailable'):
        build_messages('s',row,'code',incumbent,'','goals',{'cards':[]})


def test_raw_failure_and_incumbent_fallback_remain_separate():
    scores=dict.fromkeys(zero_evaluation('x')['scores'],40.0)
    baseline={'scores':scores}
    record={'evaluation':zero_evaluation('invalid'),'selected_evaluation':baseline,'accepted':False}
    summary=summarize([record],1,scores)
    assert summary['raw_mean']['combined_pct']==0
    assert summary['selected_mean']['combined_pct']==40
    assert summary['improved_problems']==0
