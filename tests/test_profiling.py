"""Diagnostic profile boundaries, nested costs and bounded feedback."""

import json

import pytest

from proof_eval.verification.profile_trace import profile_view, trace_hotspots
from proof_eval.verification.profiling import ProfileConfig, _parse_output


def node(header, raw, children=(), *, cls="Elab.step", tag="Lean.Parser.Tactic.simp"):
    return {
        "class": cls,
        "tag": tag,
        "header": header,
        "raw": raw,
        "children": list(children),
    }


def test_nested_tactic_costs_remain_inclusive_and_repeated_branches_are_distinct():
    trees = [
        node(
            "all_goals simp",
            280_000,
            [
                node("simp", 140_000, [node("simp", 139_000)]),
                node("simp", 130_000),
            ],
        )
    ]
    hotspots, count = trace_hotspots(trees, 20)
    assert count == 3
    assert [item["heartbeats"] for item in hotspots] == [280, 140, 130]
    assert (
        hotspots[1]["parent_id"] == hotspots[2]["parent_id"] == hotspots[0]["node_id"]
    )
    assert all(item["inclusive"] for item in hotspots)
    bounded, count = trace_hotspots(trees, 1)
    assert count == 3 and len(bounded) == 1
    assert profile_view({"trace": trees, "hotspots": bounded}) == {"hotspots": bounded}


def test_phases_are_retained_and_sequence_and_term_traces_do_not_hide_tactics():
    trees = [
        node(
            "ex",
            10_000,
            [
                node(
                    "simp\nexact h",
                    9_000,
                    [node("simp", 8_000)],
                    tag="Lean.Parser.Tactic.tacticSeq",
                ),
                node("expected type: True, term\nh", 500, tag="ident"),
            ],
            cls="Elab.definition.value",
        ),
        node("typechecking [ex]", 1_000, cls="Kernel"),
    ]
    hotspots, count = trace_hotspots(trees, 20)
    assert count == 3
    assert [item["kind"] for item in hotspots] == ["phase", "tactic", "phase"]


@pytest.mark.parametrize(
    "options",
    [
        {"threshold_raw": True},
        {"threshold_raw": -1},
        {"threshold_raw": 0.5},
        {"limit": False},
        {"limit": 0},
        {"limit": 101},
        {"version": ""},
    ],
)
def test_invalid_profile_options_are_rejected(options):
    with pytest.raises(ValueError):
        ProfileConfig(**options)


def test_marked_positions_use_unicode_character_offsets_and_raw_units():
    code = 'theorem α : True := by\n  profile_tactic "done" in trivial'
    start = code.index("profile_tactic")
    offset = 123
    event = {
        "label": "done",
        "heartbeats_raw": 1500,
        "succeeded": True,
        "start": offset + len(code[:start].encode()),
        "end": offset + len(code.encode()),
    }
    output = "\n".join(
        json.dumps({"data": data})
        for data in [
            "PROOF_PROFILE_test_MARK:" + json.dumps(event),
            "PROOF_PROFILE_test_TRACE:[]",
            "PROOF_EVAL_test:2000",
        ]
    )
    trees, marks, errors, total = _parse_output(output, "", "test", code, offset)
    assert trees == errors == [] and total == 2000
    assert marks[0]["start"] == start
    assert marks[0]["end"] == len(code)
    assert marks[0]["line"] == 2 and marks[0]["heartbeats"] == 1.5
    with pytest.raises(ValueError, match="exactly one"):
        _parse_output(
            output + '\n{"data":"PROOF_PROFILE_test_TRACE:[]"}',
            "",
            "test",
            code,
            offset,
        )
