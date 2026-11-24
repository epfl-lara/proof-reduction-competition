"""Generic inference guidance and the narrow proof-local option boundary."""

import json
from unittest.mock import patch

import pytest

from proof_eval.harness.prompts import messages
from proof_eval.verification.metrics import token_count, validate_candidate

ROW = {"statement": "theorem option_example : True"}


@pytest.mark.parametrize(
    "body",
    [
        "by\n  set_option smartUnfolding false in exact True.intro",
        "set_option smartUnfolding false in (by trivial)",
        "by\n  set_option smartUnfolding true in exact True.intro",
        "by\n  set_option /- local -/ smartUnfolding false in exact True.intro",
        "by\n  set_option smartUnfolding false in\n    set_option smartUnfolding true in trivial",
    ],
)
def test_scoped_unfolding_is_a_normal_counted_proof_body(body):
    declaration, retained = validate_candidate(ROW, body, "body")
    assert declaration == ROW["statement"] + " := " + body
    assert retained == body
    assert token_count(retained) > token_count("by trivial")


@pytest.mark.parametrize(
    "body",
    [
        "by set_option smartUnfolding false\n  trivial",
        "by set_option smartUnfolding false in trivial\nset_option Elab.async true",
        "by set_option smartUnfolding false in set_option debug.skipKernelTC true in trivial",
        "by set_option smartUnfolding false in set_option maxHeartbeats 0 in trivial",
        "by set_option smartUnfolding false in set_option maxRecDepth 10000 in trivial",
        "by set_option smartUnfolding false in run_tac pure ()",
        "by set_option smartUnfolding false in by_elab pure ()",
        "by set_option smartUnfolding false in run_meta pure ()",
        "by set_option smartUnfolding false in eval% True.intro",
        "by set_option smartUnfolding false in trivial\nlemma injected : True := by trivial",
        "by set_option smartUnfolding false in trivial)\nexample : True := by trivial",
        "by set_option «smartUnfolding» false in trivial",
    ],
)
def test_local_option_does_not_allow_other_options_commands_or_metaprograms(body):
    with pytest.raises(ValueError):
        validate_candidate(ROW, body, "body")


def test_strategy_cards_reach_the_normal_model_request():
    pack = {
        "name": "option_example",
        "source_context": "",
        "row": {
            **ROW,
            "src": ROW["statement"] + " := by trivial",
            "source": "synthetic",
            "version_info": {"v4.31.0": {}},
            "proof_length": 2,
        },
    }
    original = {
        "primary_version": "v4.31.0",
        "per_version": {"v4.31.0": {"heartbeats": 100}},
        "scores": {"combined_pct": 33.333333333333336},
    }
    with patch("proof_eval.harness.prompts.original_evaluation", return_value=original):
        request = messages(pack)
    payload = json.loads(request[1]["content"].split("\n", 1)[1])
    cards = {card["id"]: card for card in payload["structural_strategy_cards"]}
    assert {"reduce_kernel_work", "scope_recursive_unfolding"} <= cards.keys()
    assert "smartUnfolding" in cards["scope_recursive_unfolding"]["action"]
    assert "Never disable kernel checking" in request[0]["content"]
    assert all(
        set(card) == {"id", "trigger", "action", "check"} for card in cards.values()
    )
