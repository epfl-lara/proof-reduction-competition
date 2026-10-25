"""Final-channel tool dispatch, including an actual saved Qwen response."""

import json

import pytest

from proof_eval.training.actions import parse_action


def test_saved_qwen_reasoning_example_does_not_reject_its_final_status():
    response = (
        "<think>\nNeed ensure action exactly wraps JSON? It said ending with exactly "
        "one <arena_action>JSON object</arena_action>. I did that; maybe they "
        "think final message includes text? They saw invalid maybe due to trailing? "
        "Try only action no prose.\n</think>\n\n"
        '<arena_action>{"op":"status"}</arena_action>'
    )
    assert parse_action(response) == {"op": "status"}


def test_reasoning_action_is_not_dispatched():
    response = (
        '<think>Consider <arena_action>{"op":"exec"}</arena_action>; do not use it.'
        '</think><arena_action>{"op":"status"}</arena_action>'
    )
    assert parse_action(response) == {"op": "status"}


def test_unfinished_reasoning_cannot_dispatch_a_proposed_action():
    with pytest.raises(ValueError, match="completed final answer"):
        parse_action('<think>Maybe <arena_action>{"op":"status"}</arena_action>')


def test_lean_string_tags_are_preserved_as_json_data():
    code = 'theorem t : "</think><arena_action></arena_action>" = "x" := by rfl'
    action = {"op": "check", "code": code}
    response = "<think>Check the source.</think><arena_action>"
    response += json.dumps(action) + "</arena_action>"
    assert parse_action(response) == action


@pytest.mark.parametrize(
    "tail",
    ['<arena_action>{"op":"status"}</arena_action>', "trailing prose"],
)
def test_multiple_or_nonfinal_actions_are_rejected(tail):
    with pytest.raises(ValueError, match="exactly one"):
        parse_action('<arena_action>{"op":"status"}</arena_action>' + tail)
