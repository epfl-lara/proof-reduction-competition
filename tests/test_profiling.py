"""Diagnostic profile boundaries, nested costs and bounded feedback."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.verification import profiling
from proof_eval.verification.api import _Store
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


def test_profile_cache_keeps_compilation_identity_and_private_scope(
    tmp_path, monkeypatch
):
    code = "theorem toy : True := by trivial"
    row = {
        "name": "toy",
        "statement": "theorem toy : True",
        "src": code,
        "version_info": [{"v1": "a"}, {"v2": "b"}],
    }
    project = tmp_path / "project"
    project.mkdir()
    revision, calls, failed = "original", [], False
    evaluator = SimpleNamespace(
        dataset=SimpleNamespace(get=lambda _: row),
        backend=SimpleNamespace(lake="unused-lake"),
        timeout=1,
        store=_Store(tmp_path / "cell-one"),
        _versions=lambda row, selected: (
            ["v1", "v2"],
            ["v1"] if selected == "primary" else selected,
        ),
        _context=lambda row, version: (project, revision + version, revision + version),
    )
    monkeypatch.setattr(
        profiling,
        "_profile_source",
        lambda row, code, project, nonce, config: (nonce, 0, "test"),
    )

    def compile_profile(args, cwd, timeout):
        nonce = (Path(cwd) / args[-1]).read_text()
        calls.append(nonce)
        trace = [node("trivial", 20_000), node("typechecking", 10_000, cls="Kernel")]
        messages = [
            {"data": f"PROOF_PROFILE_{nonce}_TRACE:" + json.dumps(trace)},
            {"data": f"PROOF_EVAL_{nonce}:30000"},
        ]
        if failed:
            messages.append({"severity": "error", "data": "fixture failure"})
        return SimpleNamespace(
            stdout="\n".join(json.dumps(message) for message in messages),
            stderr="",
            returncode=int(failed),
        )

    monkeypatch.setattr(profiling, "_run", compile_profile)
    first = profiling.profile(evaluator, "toy", code, config=ProfileConfig(limit=1))
    expanded = profiling.profile(
        evaluator, "toy", code, config=ProfileConfig(limit=100)
    )
    assert first["status"] == expanded["status"] == "ok"
    assert len(calls) == 1 and expanded["cached"]
    assert first["hotspots_truncated"] and not expanded["hotspots_truncated"]
    assert len(first["hotspots"]) == 1 and len(expanded["hotspots"]) == 2
    assert (
        first["profile_heartbeats_raw"] == expanded["profile_heartbeats_raw"] == 30_000
    )
    assert first["cache_key"] == expanded["cache_key"]

    profiling.profile(evaluator, "toy", code, config=ProfileConfig(threshold_raw=0))
    profiling.profile(evaluator, "toy", code, config=ProfileConfig(version="v2"))
    profiling.profile(evaluator, "toy", code.replace("trivial", "exact True.intro"))
    revision = "changed"
    profiling.profile(evaluator, "toy", code)
    assert len(calls) == 5
    evaluator.store = _Store(tmp_path / "cell-two")
    profiling.profile(evaluator, "toy", code)
    assert len(calls) == 6
    assert not (evaluator.store.root / "references").exists()
    assert not (evaluator.store.root / "candidates").exists()

    failed = True
    revision = "failed"
    for limit in (1, 100):
        result = profiling.profile(
            evaluator, "toy", code, config=ProfileConfig(limit=limit)
        )
        assert result["status"] == "failed" and not result["cached"]
    assert len(calls) == 8
