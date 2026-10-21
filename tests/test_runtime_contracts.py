"""Refactor regressions at the provider, experiment, and measurement boundaries."""

from __future__ import annotations

import ast
import json
import threading
from types import SimpleNamespace

import pytest

from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.harness import cli, runner
from proof_eval.harness.config import RunConfig
from proof_eval.harness.configuration import load_inputs, starting_point
from proof_eval.harness.prompts import PROFILE_TOOLS, messages, tool_instructions
from proof_eval.paths import PACKAGE, ROOT
from proof_eval.providers import codex, execution


def test_measurement_source_still_matches_every_saved_reference():
    references = [
        json.loads(line)
        for line in (
            ROOT / "results/deterministic/00_reference_baseline/reference_values.jsonl"
        )
        .read_text()
        .splitlines()
    ]
    expected = digest(PACKAGE / "verification/backend.py")
    pins = [
        item["provenance"]["details"]["backend_implementation_sha256"]
        for row in references
        for item in row["per_version"].values()
    ]
    assert len(pins) == 36 and set(pins) == {expected}


def test_prompt_revision_preserves_frozen_task_inputs_and_safety_contract():
    old = ROOT / "results/harness/05_model_config"
    assert PROFILE_TOOLS in tool_instructions("score_edges")
    assert PROFILE_TOOLS not in tool_instructions("correctness")
    for name, pack in load_inputs().items():
        previous = read(
            old
            / "cells"
            / fingerprint((name, "gpt-6.1-sol", "max", "score_edges"))
            / "input.json"
        )
        current = messages(pack, starting_point(pack, "score_edges"))
        old_policy = previous["messages"][0]["content"].split("\n\n")
        new_policy = current[0]["content"].split("\n\n")
        assert new_policy[:3] == old_policy[:3]  # Task, output and scoring contract.
        assert new_policy[-2:] == old_policy[-2:]  # Proof safety and read scope.
        before = json.loads(previous["messages"][1]["content"].split("\n", 1)[1])
        after = json.loads(current[1]["content"].split("\n", 1)[1])
        before.pop("structural_strategy_cards")
        after.pop("structural_strategy_cards")
        assert after == before


def test_package_imports_only_maintained_library_modules():
    for path in PACKAGE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.split(".")[0].startswith(
                    ("run_", "report_", "audit_", "analyze_")
                ), path
            if isinstance(node, ast.Import):
                assert all(
                    not a.name.split(".")[0].startswith(
                        ("run_", "report_", "audit_", "analyze_")
                    )
                    for a in node.names
                ), path
    assert not list((ROOT / "src").glob("*.py"))


def test_started_codex_request_is_never_resampled(tmp_path, monkeypatch):
    identity = {"path": "/unused/codex", "version": "test", "sha256": "test"}
    monkeypatch.setattr(codex, "cli_identity", lambda: identity)

    def forbidden(*args, **kwargs):
        raise AssertionError("An indeterminate request must not launch another process")

    monkeypatch.setattr(execution.subprocess, "Popen", forbidden)
    (tmp_path / "request_started.json").write_text("{}")
    arguments = dict(
        folder=tmp_path,
        messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": "task"},
        ],
        model="gpt-6.1-sol",
        effort="max",
        mode="score_edges",
        session=SimpleNamespace(seed_code="theorem x : True := by trivial"),
        context={},
        expected_cli=identity,
        instructions="tools",
        tool_service=forbidden,
    )
    result = codex.generate(**arguments)
    assert result["status"] == "indeterminate"
    assert codex.generate(**arguments) == result
    with pytest.raises(ValueError, match="Saved agent request changed"):
        codex.generate(**{**arguments, "effort": "low"})


@pytest.mark.parametrize(
    "fields",
    [
        {"workers": 0},
        {"workers": True},
        {"problem_timeout_seconds": 0},
        {"problem_timeout_seconds": float("inf")},
        {"problem_timeout_seconds": float("nan")},
        {"problem_timeout_seconds": True},
        {"mode": "score_each"},
        {"conditions": (("gpt-6-astra", "high"),)},
        {"conditions": ()},
        {"conditions": (("gpt-6.1-sol", "max"),) * 2},
        {"names": ("x", "x")},
    ],
)
def test_harness_config_rejects_invalid_or_retired_conditions(fields):
    with pytest.raises(ValueError):
        RunConfig(**fields)


@pytest.mark.parametrize(
    "provider,workers,condition",
    [
        ("codex", 5, ("gpt-6.1-sol", "max")),
        ("lemex", 5, ("Qwen/Qwen3.8-Flash-Next", "xhigh")),
    ],
)
@pytest.mark.parametrize("failure", [None, "unknown_usage", "exception"])
def test_full_cohort_uses_fixed_parallel_slots_and_isolates_cell_failures(
    tmp_path, monkeypatch, provider, workers, condition, failure
):
    conditions = (condition,)
    names = [f"theorem_{index:02d}" for index in range(15)]
    packs = {name: {"name": name} for name in names}
    config = {"names": list(packs), "conditions": conditions, "mode": "score_edges"}
    monkeypatch.setattr(runner, "load_inputs", lambda _: packs)
    monkeypatch.setattr(runner, "prepare", lambda *a, **kw: config)
    monkeypatch.setattr(runner, "Evaluator", lambda *a: object())
    monkeypatch.setattr(runner, "guard", lambda *a: None)
    first_group = threading.Barrier(workers)
    failure_observed = threading.Event()
    release_followups = threading.Event()
    if failure is None:
        release_followups.set()
    lock = threading.Lock()
    started, ended, first_starts = [], set(), []
    active, maximum = 0, 0

    def report(*args):
        if failure_observed.is_set():
            release_followups.set()
        return {"status": "partial" if failure else "complete"}

    monkeypatch.setattr(runner, "report", report)

    def cell(output, cfg, pack, model, effort, evaluator):
        nonlocal active, maximum
        name = pack["name"]
        with lock:
            started.append(name)
            active += 1
            maximum = max(maximum, active)
            if not ended:
                first_starts.append(name)
        try:
            if names.index(name) < workers:
                first_group.wait(timeout=5)
            if name == names[0] and failure:
                failure_observed.set()
                if failure == "exception":
                    write_json(output / "failed_cell_started.json", {"name": name})
                    raise ValueError("One theorem worker failed")
            else:
                assert release_followups.wait(5)
            result = dict(
                name=name,
                model=model,
                effort=effort,
                status="incomplete" if name == names[0] and failure else "complete",
                generation_status="received",
                stop={
                    "kind": "unknown_usage",
                    "reason": "Cumulative spending is unknown",
                },
                gain_over_historical_pp=None,
                checks=1,
            )
            write_json(output / "cells" / name / "result.json", result)
            return result
        finally:
            with lock:
                active -= 1
                ended.add(name)

    monkeypatch.setattr(runner, "run_cell", cell)
    arguments = RunConfig(output=tmp_path, provider=provider, conditions=conditions)
    if failure:
        with pytest.raises(RuntimeError, match="Some cells are incomplete"):
            runner.run(arguments)
    else:
        runner.run(arguments)
    assert set(started) == ended == set(names) and len(started) == 15
    assert maximum == workers and len(first_starts) == workers
    assert not (tmp_path / "pilot_audit.json").exists()
    state = read(tmp_path / "run.json")
    assert len(state["failures"]) == (1 if failure else 0)
    if failure == "unknown_usage":
        assert state["failures"][0]["stop_kind"] == "unknown_usage"
        assert state["failures"][0]["error"] == "Cumulative spending is unknown"
    if failure == "exception":
        assert read(tmp_path / "failed_cell_started.json")["name"] == names[0]


@pytest.mark.parametrize(
    "provider,workers", [("codex", 5), ("lemex", 3), ("claude", 5), ("agy", 5)]
)
def test_provider_parallelism_defaults_and_overrides_in_python_and_cli(
    provider, workers, monkeypatch
):
    captured = []
    monkeypatch.setattr(
        cli, "run_pipeline", lambda args: captured.append(args.model) or {}
    )
    assert RunConfig(provider=provider).workers == workers
    assert cli.main(["run", "--provider", provider]) == 0
    assert captured[0].workers == workers
    assert RunConfig(provider=provider, workers=workers).workers == workers
    assert RunConfig(provider=provider, workers=workers + 1).workers == workers + 1
    assert cli.main(["run", "--provider", provider, "--workers", str(workers + 1)]) == 0


def test_model_run_rejects_removed_pilot_option(monkeypatch):
    def forbidden(*args):
        raise AssertionError("Invalid pilot flags must not dispatch model work")

    monkeypatch.setattr(cli, "run_pipeline", forbidden)
    with pytest.raises(SystemExit) as error:
        cli.main(["run", "--pilot"])
    assert error.value.code == 2
    with pytest.raises(TypeError, match="pilot"):
        RunConfig(pilot=True)


def test_model_handoff_cannot_be_launched_or_resumed(tmp_path, monkeypatch):
    from proof_eval.harness.search import _run_cell, run_cell

    def forbidden(*args, **kwargs):
        raise AssertionError("Retired handoffs must not dispatch requests")

    monkeypatch.setattr(cli, "run_pipeline", forbidden)
    with pytest.raises(SystemExit) as error:
        cli.main(["run", "--first-attempt-condition", "gpt-6-luna:max"])
    assert error.value.code == 2
    with pytest.raises(TypeError, match="first_attempt_condition"):
        RunConfig(first_attempt_condition=("gpt-6-luna", "max"))
    config = {"first_attempt_condition": ["gpt-6-luna", "max"]}
    for search in (run_cell, _run_cell):
        with pytest.raises(ValueError, match="retired"):
            search(
                tmp_path / "unused", config, {}, "gpt-6.1-sol", "max", None, forbidden
            )
    assert not (tmp_path / "unused").exists()


def test_retired_handoff_report_is_read_without_rewriting_evidence(tmp_path):
    from proof_eval.harness.reporting import report

    path = tmp_path / "report.json"
    original = '{"status":"partial","first_attempt_condition":["gpt-6-luna","max"]}\n'
    path.write_text(original)
    assert report(tmp_path, json.loads(original)) == json.loads(original)
    assert path.read_text() == original
    assert not (tmp_path / "conditions").exists()


@pytest.mark.parametrize("layout", ["bin", "codex-resources"])
def test_codex_preflight_requires_and_pins_its_companion(tmp_path, monkeypatch, layout):
    binary = tmp_path / "bin/codex"
    binary.parent.mkdir()
    binary.write_bytes(b"test CLI only")
    identity = {"path": str(binary), "version": "codex-cli 0.162.0", "sha256": "test"}
    monkeypatch.setattr(codex, "executable_identity", lambda: dict(identity))
    with pytest.raises(ValueError, match="Incomplete Codex CLI bundle"):
        codex.generate(folder=tmp_path / "attempt")
    assert not (tmp_path / "attempt").exists()
    companion = tmp_path / layout / "codex-code-mode-host"
    companion.parent.mkdir(exist_ok=True)
    companion.write_bytes(b"test companion only")
    companion.chmod(0o755)
    first = codex.cli_identity()
    assert first["companions"]["codex-code-mode-host"] == {
        "path": str(companion),
        "sha256": digest(companion),
    }
    companion.write_bytes(b"changed companion")
    assert codex.cli_identity() != first
