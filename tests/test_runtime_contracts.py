"""Refactor regressions at the provider, experiment, and measurement boundaries."""

from __future__ import annotations

import ast
import json
from types import SimpleNamespace

import pytest

from proof_eval.evidence.io import digest, fingerprint, read
from proof_eval.harness.config import RunConfig
from proof_eval.harness.configuration import load_inputs, starting_point
from proof_eval.harness.prompts import messages, tool_instructions
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


def test_full_sol_prompt_and_tool_instructions_match_the_checkpoint():
    old = ROOT / "results/harness/05_model_config"
    assert (
        tool_instructions("score_edges")
        == read(old / "config.json")["tool_instructions"]
    )
    for name, pack in load_inputs().items():
        previous = read(
            old
            / "cells"
            / fingerprint((name, "gpt-6.1-sol", "max", "score_edges"))
            / "input.json"
        )
        assert (
            messages(pack, starting_point(pack, "score_edges")) == previous["messages"]
        )


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


def test_pilot_audit_precedes_the_remaining_batch(tmp_path, monkeypatch):
    from proof_eval.harness import audit as auditing
    from proof_eval.harness import runner

    conditions = (("gpt-6.1-sol", "max"), ("gpt-6-astra", "max"))
    packs = {name: {"name": name} for name in ("first", "second")}
    config = {"names": list(packs), "conditions": conditions, "mode": "score_edges"}
    monkeypatch.setattr(runner, "load_inputs", lambda _: packs)
    monkeypatch.setattr(runner, "prepare", lambda *a, **kw: config)
    monkeypatch.setattr(runner, "Evaluator", lambda *a: object())
    monkeypatch.setattr(runner, "guard", lambda *a: None)
    monkeypatch.setattr(runner, "report", lambda *a: {"status": "complete"})
    completed = set()
    audited = []

    def cell(output, cfg, pack, model, effort, evaluator):
        if pack["name"] == "second":
            assert audited, "Full batch must wait for a successful pilot audit"
        completed.add((pack["name"], model, effort))
        return dict(
            name=pack["name"],
            model=model,
            effort=effort,
            status="complete",
            gain_over_historical_pp=None,
            checks=1,
        )

    def audit(output):
        assert completed == {("first", model, effort) for model, effort in conditions}
        audited.append(True)
        return {"status": "passed"}

    monkeypatch.setattr(runner, "run_cell", cell)
    monkeypatch.setattr(auditing, "audit", audit)
    runner.run(RunConfig(output=tmp_path, conditions=conditions, workers=2, pilot=True))
    assert len(completed) == 4
    assert read(tmp_path / "pilot_audit.json")["status"] == "passed"
