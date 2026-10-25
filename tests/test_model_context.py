"""Original-proof context, bounded feedback, and independently cached metrics."""

import json
import shutil
import subprocess

import pytest

from proof_eval import Evaluator
from proof_eval.optimization.tactics import Site
from proof_eval.verification.api import EvaluationNotReady
from proof_eval.verification.context import (
    _instrument,
    _parse_observations,
    _truncate_goal,
    build_context,
)
from proof_eval.verification.metrics import token_count
from proof_eval.verification.profile_trace import profile_view
from proof_eval.verification.profiling import ProfileConfig, profile


def test_goal_truncation_preserves_target_under_long_context():
    text = "h : " + "Nat " * 300 + "\n⊢ n = n"
    bounded = _truncate_goal(text, 100)
    assert len(bounded) <= 100
    assert "⊢ n = n" in bounded
    assert "truncated" in bounded
    assert _truncate_goal("⊢ True", 100) == "⊢ True"


def test_cost_excludes_nested_observer_and_instrumentation_keeps_unicode_layout():
    code = "example : True := by exact (by trivial)"
    leaf = code.index("exact")
    inner = code.index("by", code.index("by") + 2)
    trivial = code.index("trivial")
    sites = [
        Site(leaf, len(code), "tactic", leaf, "exact"),
        Site(inner, len(code) - 1, "by_block", trivial, "by"),
    ]
    instrumented, measured = _instrument(code, sites, True)
    assert measured == set()
    assert "proof_context_cost" not in instrumented
    assert "proof_context_goals 0" in instrumented
    assert "proof_context_goals 1" in instrumented


def test_parser_bounds_repeated_sites_and_never_fakes_missing_costs():
    sites = [Site(0, 7, "tactic", 0, "trivial"), Site(0, 7, "by_block", 0, "by")]
    event = {
        "site": 0,
        "before_goals": ["h : True\n⊢ True"],
        "goal_count": 4,
        "tactic_allocations": 1500,
    }
    stdout = "\n".join(
        json.dumps({"data": "PROOF_CONTEXT:" + json.dumps(event)}) for _ in range(4)
    )
    result, diagnostics = _parse_observations(
        stdout,
        sites,
        "trivial",
        measured={0},
        max_goal_chars=10,
        max_snippet_chars=4,
        max_invocations=2,
    )
    assert not diagnostics
    assert result[0]["invocation_count"] == 4
    assert len(result[0]["invocations"]) == 2
    assert result[0]["invocations_truncated"]
    assert result[0]["goals_truncated"]
    assert result[0]["snippet_truncated"]
    assert result[0]["tactic_heartbeats"] == 1.5
    assert result[1]["status"] == "not_observed"
    assert result[1]["before_goals"] is None
    assert result[1]["tactic_heartbeats"] is None
    event["site"] = 42
    with pytest.raises(EvaluationNotReady, match="unknown site"):
        _parse_observations(
            json.dumps({"data": "PROOF_CONTEXT:" + json.dumps(event)}),
            sites,
            "trivial",
            measured={0},
            max_goal_chars=10,
            max_snippet_chars=4,
            max_invocations=2,
        )


@pytest.fixture
def context_fixture(tmp_path, request):
    options = getattr(request, "param", "v4.25.0")
    version = options["version"] if isinstance(options, dict) else options
    documentation = (
        options.get("documentation", "") if isinstance(options, dict) else ""
    )
    if not shutil.which("elan") or not shutil.which("lake"):
        pytest.skip("Lean/Lake unavailable")
    if f"leanprover/lean4:{version}" not in subprocess.check_output(
        ["elan", "toolchain", "list"], text=True
    ):
        pytest.skip(f"Lean {version} unavailable")
    project = tmp_path / "project"
    project.mkdir()
    (project / "lean-toolchain").write_text(f"leanprover/lean4:{version}\n")
    (project / "lakefile.toml").write_text('name = "context_test"\nversion = "0.1.0"\n')
    (project / "lake-manifest.json").write_text(
        json.dumps(
            {
                "version": "1.1.0",
                "name": "context_test",
                "lakeDir": ".lake",
                "packagesDir": ".lake/packages",
                "packages": [],
            }
        )
    )
    code = "theorem context_α (n : Nat) : n = n := by\n  have h : n = n := by rfl\n  exact h"
    (project / "Example.lean").write_text("import Lean\n" + documentation + code + "\n")

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(project), *args], text=True
        ).strip()

    git("init", "-q")
    git("add", ".")
    git(
        "-c",
        "user.name=Context Test",
        "-c",
        "user.email=context@example.invalid",
        "commit",
        "-qm",
        "Fixture",
    )
    row = {
        "name": "context_α",
        "source": "context_fixture",
        "statement": code.split(" := by")[0],
        "src": code,
        "proof_length": token_count(code.split(" :=", 1)[1]),
        "file_path": "Example.lean",
        "version_info": [{version: git("rev-parse", "HEAD")}],
    }
    dataset = tmp_path / "data.jsonl"
    dataset.write_text(json.dumps(row, ensure_ascii=False) + "\n")
    environments = tmp_path / "environments.json"
    environments.write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "source": row["source"],
                        "version": version,
                        "path": str(project),
                    }
                ]
            }
        )
    )
    return Evaluator(dataset, environments, tmp_path / "cache"), row, code


def test_real_goal_context_and_cost_context_observe_same_original_states(
    context_fixture, monkeypatch
):
    evaluator, row, code = context_fixture

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Context extraction must never prepare or score references"
        )

    monkeypatch.setattr(evaluator, "prepare_reference", forbidden)
    monkeypatch.setattr(evaluator, "evaluate", forbidden)
    plain = build_context(evaluator, row, code)
    costs = build_context(evaluator, row, code, measure_costs=True)
    assert plain["status"] == costs["status"] == "ok", (plain, costs)
    assert plain["cache_key"] != costs["cache_key"]
    assert plain["proof_sha256"] == costs["proof_sha256"]
    assert len(plain["sites"]) == len(costs["sites"]) > 1
    for left, right in zip(plain["sites"], costs["sites"]):
        assert left["status"] == right["status"] == "observed"
        assert left["before_goals"] == right["before_goals"]
        assert left["start"] == right["start"]
        assert left["tactic_heartbeats"] is None
        if right["kind"] == "tactic":
            assert right["tactic_allocations"] > 0
            assert right["tactic_heartbeats"] == right["tactic_allocations"] / 1000
        assert "⊢ n = n" in right["before_goals"][0]
    assert not (evaluator.store.root / "references").exists()
    monkeypatch.setattr("proof_eval.verification.context.analyze", forbidden)
    assert build_context(evaluator, row, code, measure_costs=True)["cached"]
    assert not list(
        evaluator.projects[(row["source"], "v4.25.0")].glob("_ProofEval_*.lean")
    )


def test_real_cache_invalidation_and_unavailable_are_explicit(context_fixture):
    evaluator, row, code = context_fixture
    before = build_context(evaluator, row, code)
    changed = build_context(evaluator, row, code.replace("exact h", "rfl"))
    bounded = build_context(evaluator, row, code, max_sites=1)
    assert before["cache_key"] != changed["cache_key"] != bounded["cache_key"]
    assert len(bounded["sites"]) == 1
    unavailable = build_context(
        evaluator, row, code.replace("exact h", "unknown_context_tactic")
    )
    assert unavailable["status"] == "unavailable"
    assert not evaluator.store.read("model_context", unavailable["cache_key"])
    for kwargs in (
        {"max_sites": 0},
        {"max_goals": True},
        {"timeout": float("nan")},
        {"measure_costs": "yes"},
    ):
        with pytest.raises(ValueError):
            build_context(evaluator, row, code, **kwargs)


@pytest.mark.parametrize(
    "context_fixture",
    [
        "v4.25.0",
        "v4.26.0",
        "v4.32.0",
        "v4.33.0-rc2",
    ],
    indirect=True,
)
def test_real_profile_and_labels_reuse_diagnostics_without_touching_scores(
    context_fixture, monkeypatch
):
    evaluator, row, code = context_fixture

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Profiling must never score candidates or prepare/read references"
        )

    monkeypatch.setattr(evaluator, "evaluate", forbidden)
    monkeypatch.setattr(evaluator, "prepare_reference", forbidden)
    monkeypatch.setattr(evaluator, "get_reference", forbidden)
    monkeypatch.setattr(evaluator.backend, "check", forbidden)
    original = profile(
        evaluator, row["name"], code, config=ProfileConfig(threshold_raw=0)
    )
    assert original["status"] == "ok", original["diagnostics"]
    assert any(item["snippet"] == "exact h" for item in original["hotspots"])
    labelled = code.replace("by rfl", 'by profile_tactic "inner" in rfl').replace(
        "exact h", 'profile_tactic "finish proof" in exact h'
    )
    marked = profile(
        evaluator, row["name"], labelled, config=ProfileConfig(threshold_raw=0)
    )
    assert marked["status"] == "ok", marked["diagnostics"]
    assert [mark["label"] for mark in marked["marks"]] == ["inner", "finish proof"]
    assert all(
        mark["succeeded"] and mark["heartbeats_raw"] > 0 for mark in marked["marks"]
    )
    assert marked["cache_key"] != original["cache_key"]
    assert original["profile_heartbeats"] == original["profile_heartbeats_raw"] / 1000
    assert not (evaluator.store.root / "references").exists()
    assert not (evaluator.store.root / "candidates").exists()
    assert not list(next(iter(evaluator.projects.values())).glob("_ProofEval_*.lean"))
    monkeypatch.setattr("proof_eval.verification.profiling._run", forbidden)
    assert profile(
        evaluator, row["name"], labelled, config=ProfileConfig(threshold_raw=0)
    )["cached"]
    # A display-only change must reuse the complete private trace, retaining
    # diagnostics, mark coordinates and measured values without another Lean run.
    smaller = profile(
        evaluator, row["name"], labelled, config=ProfileConfig(threshold_raw=0, limit=1)
    )
    larger = profile(
        evaluator,
        row["name"],
        labelled,
        config=ProfileConfig(threshold_raw=0, limit=100),
    )
    assert smaller["cached"] and larger["cached"]
    assert smaller["cache_key"] == larger["cache_key"] == marked["cache_key"]
    assert smaller["options"]["limit"] == 1 and larger["options"]["limit"] == 100
    assert len(smaller["hotspots"]) == 1 and smaller["hotspots_truncated"]
    assert smaller["marks_truncated"] and not larger["marks_truncated"]
    assert smaller["marks"] == larger["marks"] == marked["marks"]
    assert larger["trace"] == smaller["trace"] == marked["trace"]
    assert larger["profile_heartbeats_raw"] == marked["profile_heartbeats_raw"]
    assert len(profile_view(smaller)["marks"]) == 1


def test_real_profile_failure_is_partial_and_not_cached(context_fixture):
    evaluator, row, code = context_fixture
    failed = profile(
        evaluator, row["name"], code.replace("exact h", "unknown_profile_tactic")
    )
    assert failed["status"] == "failed", failed["diagnostics"]
    assert failed["partial"] and failed["diagnostics"]
    assert failed["profile_heartbeats"] is None
    assert not evaluator.store.read("profiles", failed["cache_key"])
    with pytest.raises(ValueError, match="preserve the exact"):
        profile(evaluator, row["name"], "theorem unrelated : True := by trivial")


def test_real_nested_profile_labels_preserve_both_branch_invocations(context_fixture):
    evaluator, row, _ = context_fixture
    code = row["statement"] + """ := by
  have h : True ∧ True := by
    profile_tactic "whole block" in (constructor <;> profile_tactic "branch" in trivial)
  rfl"""
    result = profile(evaluator, row["name"], code, config=ProfileConfig(limit=1))
    assert result["status"] == "ok", result["diagnostics"]
    assert [mark["label"] for mark in result["marks"]] == [
        "branch",
        "branch",
        "whole block",
    ]
    assert result["mark_count"] == 3 and result["marks_truncated"]
    assert result["marks"][0]["start"] == result["marks"][1]["start"]
    assert result["marks"][2]["heartbeats_raw"] > sum(
        mark["heartbeats_raw"] for mark in result["marks"][:2]
    )


@pytest.mark.parametrize(
    "context_fixture",
    [
        {
            "version": "v4.25.0",
            "documentation": "/-- A documented declaration with α. -/\n",
        }
    ],
    indirect=True,
)
def test_real_profile_labels_keep_coordinates_when_source_has_documentation(
    context_fixture,
):
    evaluator, row, code = context_fixture
    labelled = code.replace("exact h", 'profile_tactic "finish proof" in exact h')
    result = profile(evaluator, row["name"], labelled)
    assert result["status"] == "ok", result["diagnostics"]
    mark = result["marks"][0]
    assert mark["start"] == labelled.index("profile_tactic")
    assert mark["end"] == len(labelled) and mark["line"] == 3


def test_profile_cli_prints_bounded_feedback_and_saves_full_evidence(
    context_fixture, monkeypatch, tmp_path, capsys
):
    from proof_eval.interfaces import cli

    evaluator, row, code = context_fixture
    monkeypatch.setattr(cli, "Evaluator", lambda *args, **kwargs: evaluator)
    candidate = tmp_path / "candidate.lean"
    candidate.write_text(code)
    output = tmp_path / "profile.json"
    assert (
        cli.main(
            [
                "profile",
                row["name"],
                "--code-file",
                str(candidate),
                "--threshold-raw",
                "0",
                "--limit",
                "1",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    feedback = json.loads(capsys.readouterr().out)
    saved = json.loads(output.read_text())
    assert feedback["status"] == saved["status"] == "ok"
    assert "trace" not in feedback and saved["trace"]
    assert len(feedback["hotspots"]) == 1 and feedback["hotspots_truncated"]
