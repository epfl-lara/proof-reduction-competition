"""Opt-in restarts, native spending stops and audited boundaries; no paid calls."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from copy import deepcopy
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.harness import cli, limits, search
from proof_eval.harness.audit import audit
from proof_eval.harness.configuration import load_inputs, prepare
from proof_eval.harness.service import ProofToolService
from proof_eval.paths import ROOT
from proof_eval.protocol import code_identity
from proof_eval.providers import agy, claude, codex, execution
from proof_eval.providers.costs import CostConfig, estimate_token_cost
from proof_eval.providers.events import cli_identity, parse_events
from proof_eval.providers.spending import (
    codex_budget_settings,
    native_cost_guard,
    native_cost_stop,
)
from proof_eval.verification.api import Evaluator

NAME = "CallElimCorrect.substOldPostSubset"
MODEL, EFFORT = "gpt-6.1-sol", "max"
USAGE = dict(
    input_tokens=100000,
    cached_input_tokens=90000,
    cache_write_input_tokens=0,
    output_tokens=50000,
    reasoning_output_tokens=30000,
)

FAKE_AGENT = """
import json, subprocess, sys
from pathlib import Path
prompt=sys.stdin.read()
payload,_=json.JSONDecoder().raw_decode(prompt.split('Optimize this declaration using the supplied tools.\\n',1)[1])
initial=Path('candidate.lean').read_text()
assert initial==payload['incumbent_declaration']
def tool(*args):
 return json.loads(subprocess.check_output([sys.executable,'tools.py',*args],text=True))
status=tool('status')
assert status['finished'] is None
Path('initial_candidate.json').write_text(json.dumps(dict(proof=initial,finished=status['finished'])))
Path('candidate.lean').write_text(sys.argv[1])
assert tool('check','candidate.lean')['kind']!='tool_error'
tool('finish','--reason','Local search completed')
Path(sys.argv[2]).write_text(sys.argv[1])
events=[dict(type='item.completed',item=dict(type='agent_message',text=sys.argv[1])),dict(type='turn.completed',usage=json.loads(sys.argv[3]))]
for event in events: print(json.dumps(event),flush=True)
"""


@pytest.fixture
def tracking_run(tmp_path, monkeypatch):
    """Use genuine saved certificates and copy cleanup evidence into a new run."""
    packs = load_inputs()
    saved_cell = (
        ROOT
        / "results/harness/06_refactor_regression/cells"
        / fingerprint((NAME, MODEL, EFFORT, "score_edges"))
    )
    saved = read(saved_cell / "result.json")
    cleanup_record = json.loads(
        (saved_cell / "evidence/deterministic.jsonl").read_text().splitlines()[-1]
    )
    identity = {"path": sys.executable, "version": "local-test", "sha256": "local-test"}
    monkeypatch.setattr(codex, "cli_identity", lambda: identity)
    monkeypatch.setattr(agy, "cli_identity", lambda: identity)

    def make(
        *,
        tracking="cost",
        usd=1.0,
        restarts=20,
        timeout=3600.0,
        cleanup=True,
        transport_restarts=2,
        provider="codex",
        incumbents_from=None,
    ):
        output = tmp_path / "run"
        model, effort = (agy.MODEL, "high") if provider == "agy" else (MODEL, EFFORT)
        config = prepare(
            output,
            "score_edges",
            packs,
            conditions=[(model, effort)],
            semantic_search=False,
            web_search=False,
            provider=provider,
            budget_tracking=tracking,
            budget_usd_per_problem=usd,
            max_budget_restarts=restarts,
            max_transport_restarts=transport_restarts,
            incumbents_from=incumbents_from,
            problem_timeout_seconds=timeout,
            paths={
                "dataset_path": str(ROOT / "data/benchmark_data_warmup.jsonl"),
                "environments_path": str(ROOT / "environments.local.json"),
            },
        )
        evaluator = Evaluator(
            ROOT / "data/benchmark_data_warmup.jsonl",
            ROOT / "environments.local.json",
            ROOT / ".proof-eval",
        )
        evaluator.evaluate = lambda *a, **k: deepcopy(saved["selected_evaluation"])
        cleanup_inputs = []
        if cleanup:
            source = Path(cleanup_record["job_path"])
            job_folder = Path(config["deterministic_jobs"]) / source.name
            shutil.copytree(source, job_folder)
            job = {
                **read(job_folder / "result.json"),
                "job_path": str(job_folder),
                "job_result_sha256": digest(job_folder / "result.json"),
                "reused": True,
            }

            def clean(code):
                cleanup_inputs.append(code)
                assert code_identity(packs[NAME]["row"], code) == code_identity(
                    packs[NAME]["row"], job["input_proof"]
                )
                return job

        else:

            def clean(code):
                cleanup_inputs.append(code)
                return None

        monkeypatch.setattr(search, "DeterministicCleanup", lambda *a: clean)
        folder = output / "cells" / fingerprint((NAME, model, effort, "score_edges"))
        return SimpleNamespace(
            output=output,
            config=config,
            pack=packs[NAME],
            evaluator=evaluator,
            saved=saved,
            folder=folder,
            identity=identity,
            cleanup_inputs=cleanup_inputs,
            model=model,
            effort=effort,
        )

    return make


def fake_native(run, *, usage=USAGE, events=None):
    def generator(**kwargs):
        assert kwargs["session"].finished is None
        assert read(kwargs["session"].folder / "state.json")["finished"] is None
        assert not (kwargs["session"].folder / "finished.json").exists()

        def build(workspace, system_file, last_message, folder):
            if events is None:
                argv = [
                    sys.executable,
                    "-c",
                    FAKE_AGENT,
                    run.saved["selected_proof"],
                    str(last_message),
                    json.dumps(usage),
                ]
            else:
                argv = [
                    sys.executable,
                    "-c",
                    FAKE_AGENT.split("events=")[0]
                    + "\nprint(sys.argv[4]); raise SystemExit(int(sys.argv[5]))",
                    run.saved["selected_proof"],
                    str(last_message),
                    json.dumps(usage),
                    "\n".join(json.dumps(event) for event in events),
                    (
                        "0"
                        if run.config["provider"] == "agy"
                        and events[-1].get("result", {}).get("status") == "SUCCESS"
                        else "1"
                    ),
                ]
            return execution.Launch(
                argv=argv,
                environment=dict(os.environ),
                runtime_paths=(),
                cwd=workspace,
                parse=(
                    partial(
                        agy.parse_events, requested_slug=agy.slug(run.model, run.effort)
                    )
                    if run.config["provider"] == "agy"
                    else parse_events
                ),
                stream_usage=(
                    agy.stream_usage if run.config["provider"] == "agy" else None
                ),
            )

        return execution.generate(
            **{key: value for key, value in kwargs.items() if key != "provider"},
            provider=run.config["provider"],
            authentication="local-test-only",
            identity=run.identity,
            tool_service=ProofToolService,
            build=build,
        )

    return generator


def run_worker(run, generator):
    """Policy unit tests run inside an explicit supervisor-owned deadline."""
    run.folder.mkdir(parents=True, exist_ok=True)
    limits.start_budget(run.folder, run.config["problem_timeout_seconds"])
    return search._run_cell(
        run.output,
        run.config,
        run.pack,
        run.model,
        run.effort,
        run.evaluator,
        generator,
    )


def test_agy_host_cost_stop_keeps_verified_proof_and_audits_partial_usage(tracking_run):
    from functools import partial

    run = tracking_run(provider="agy", usd=1.0)
    initial = {
        "event": "init",
        "conversation_id": "conv",
        "init": {"model": "gemini-3.8-flash-high"},
    }

    def update(index, ordinary, output, state):
        return {
            "event": "step_update",
            "step_update": {
                "conversation_id": "conv",
                "step_index": index,
                "state": state,
                "step_type": "agent_response",
                "usage": {
                    "input_tokens": ordinary,
                    "cache_read_tokens": 0,
                    "output_tokens": output,
                    "thinking_tokens": 0,
                },
            },
        }

    events = [
        initial,
        update(0, 750000, 0, "ACTIVE"),
        update(0, 750000, 0, "DONE"),
        update(1, 700000, 100000, "DONE"),
    ]
    code = (
        FAKE_AGENT.split("events=")[0].replace(
            "Path(sys.argv[2]).write_text(sys.argv[1])", ""
        )
        + """
import time
events=json.loads(sys.argv[4])
for event in events[:3]: print(json.dumps(event),flush=True)
time.sleep(0.5)
print(json.dumps(events[-1]),flush=True)
sys.stdout.write('{"event":'); sys.stdout.flush()
time.sleep(1000)
"""
    )

    def generator(**kwargs):
        def build(workspace, system_file, last_message, folder):
            return execution.Launch(
                argv=[
                    sys.executable,
                    "-c",
                    code,
                    run.saved["selected_proof"],
                    str(last_message),
                    "{}",
                    json.dumps(events),
                ],
                environment=dict(os.environ),
                runtime_paths=(),
                cwd=workspace,
                parse=partial(agy.parse_events, requested_slug="gemini-3.8-flash-high"),
                stream_usage=agy.stream_usage,
            )

        return execution.generate(
            **{key: value for key, value in kwargs.items() if key != "provider"},
            provider="agy",
            identity=run.identity,
            authentication="local-test-only",
            tool_service=ProofToolService,
            build=build,
        )

    started = time.monotonic()
    result = run_worker(run, generator)
    assert time.monotonic() - started < 5
    assert result["status"] == "complete" and result["stop"]["kind"] == "cost_limit"
    assert result["selected_proof"] == run.saved["selected_proof"]
    assert len(result["attempts"]) == 1 and result["agent_tool_checks"] == 1
    assert result["budget_outcome"]["cost_enforcement"] == "host_stream_usage"
    assert result["cost"]["status"] == "unknown_usage"
    assert result["cost"]["known_usage_estimate"]["total_usd"] == pytest.approx(1.4625)
    stop_file = run.folder / "attempt_00/cost_stop.json"
    stop = read(stop_file)
    assert stop["event_count"] == 4
    assert stop["estimate"]["total_usd"] == pytest.approx(1.4625)
    assert audit(run.output)["status"] == "passed"
    stop["event_count"] = 3
    write_json(stop_file, stop)
    with pytest.raises(ValueError, match="stop evidence"):
        audit(run.output)


def _agy_carry_events(run, *, success=False, usage=None):
    return [
        {
            "event": "init",
            "conversation_id": "carry-test",
            "init": {"model": "gemini-3.8-flash-high"},
        },
        {
            "event": "result",
            "result": {
                "conversation_id": "carry-test",
                "status": "SUCCESS" if success else "ERROR",
                "response": run.saved["selected_proof"] if success else "",
                "usage": (
                    usage
                    if usage is not None
                    else {
                        "input_tokens": 200000,
                        "cache_read_tokens": 100000,
                        "output_tokens": 80000,
                        "thinking_tokens": 5000,
                    }
                ),
            },
        },
    ]


def _continue_with_carried_budget(run):
    write_json(run.output / "run.json", {"status": "failed"})
    output = run.output.parent / "continued"
    config = prepare(
        output,
        "score_edges",
        load_inputs(),
        provider="agy",
        conditions=[(run.model, run.effort)],
        semantic_search=False,
        web_search=False,
        budget_tracking="cost",
        budget_usd_per_problem=run.config["budget_usd_per_problem"],
        problem_timeout_seconds=run.config["problem_timeout_seconds"],
        max_budget_restarts=0,
        carry_budgets_from=run.output,
        paths={key: run.config[key] for key in ("dataset_path", "environments_path")},
    )
    return SimpleNamespace(
        **{
            **vars(run),
            "output": output,
            "config": config,
            "folder": output / "cells" / run.folder.name,
        }
    )


def test_new_runtime_carries_failed_spend_deadline_and_best_same_condition_proof(
    tracking_run,
):
    run = tracking_run(provider="agy", usd=3, restarts=0)
    first = run_worker(run, fake_native(run, events=_agy_carry_events(run)))
    assert first["status"] == "incomplete"
    assert first["cost"]["total_usd"] == pytest.approx(0.4575)
    prior_hash = digest(run.folder / "result.json")
    original_budget = read(run.folder / "budget_started.json")
    continued = _continue_with_carried_budget(run)
    assert read(continued.folder / "budget_started.json") == original_budget
    second = run_worker(
        continued,
        fake_native(continued, events=_agy_carry_events(continued, success=True)),
    )
    assert second["status"] == "complete" and len(second["generations"]) == 1
    assert second["cost"]["carried_attempts"] == 1
    assert second["cost"]["total_usd"] == pytest.approx(0.915)
    assert second["attempts"][0]["cost_budget"]["remaining_usd"] == pytest.approx(
        2.5425
    )
    assert second["attempts"][0]["cost_before"]["total_usd"] == pytest.approx(0.4575)
    assert second["seed_proof"] == first["selected_proof"]
    assert digest(run.folder / "result.json") == prior_hash
    assert audit(continued.output)["status"] == "passed"
    changed = read(continued.folder / "budget_started.json")
    changed["deadline_epoch"] += 60
    write_json(continued.folder / "budget_started.json", changed)
    with pytest.raises(ValueError, match="deadline was replenished"):
        audit(continued.output)


def test_unknown_prior_usage_blocks_budget_carryover(tracking_run):
    run = tracking_run(provider="agy", usd=3, restarts=0)
    first = run_worker(run, fake_native(run, events=_agy_carry_events(run, usage={})))
    assert first["cost"]["total_usd"] is None
    with pytest.raises(ValueError, match="unknown cumulative spending"):
        _continue_with_carried_budget(run)


def test_spent_prior_budget_cannot_dispatch_another_request(tracking_run):
    run = tracking_run(provider="agy", usd=3, restarts=0)
    events = _agy_carry_events(
        run,
        usage={
            "input_tokens": 4000000,
            "cache_read_tokens": 0,
            "output_tokens": 0,
            "thinking_tokens": 0,
        },
    )
    first = run_worker(run, fake_native(run, events=events))
    assert first["cost"]["total_usd"] == 3
    continued = _continue_with_carried_budget(run)

    def forbidden(**kwargs):
        raise AssertionError("Spent budgets cannot dispatch another request")

    second = run_worker(continued, forbidden)
    assert second["status"] == "complete" and second["stop"]["kind"] == "cost_reserve"
    assert second["cost"]["total_usd"] == 3 and second["cost"]["carried_attempts"] == 1
    assert not second["generations"] and not second["attempts"]
    assert audit(continued.output)["status"] == "passed"


def test_native_restarts_are_audited_and_resume_without_requests(tracking_run):
    run = tracking_run()
    result = search.run_cell(
        run.output, run.config, run.pack, MODEL, EFFORT, run.evaluator, fake_native(run)
    )
    assert result["status"] == "complete" and result["stop"]["kind"] == "cost_limit"
    assert len(result["attempts"]) == 2
    assert result["cost"]["total_usd"] == pytest.approx(1.058)
    assert result["budget_outcome"]["hard_cost_cap"] is False
    first, second = result["attempts"]
    assert (
        first["agent_stop"]["kind"] == second["agent_stop"]["kind"] == "agent_decision"
    )
    assert second["incumbent_proof"] == run.saved["selected_proof"]
    assert second["cost_before"] == first["cost_after"]
    assert second["cost_budget"]["remaining_usd"] == pytest.approx(0.471)
    workspace = run.folder / "attempt_01/workspace"
    assert read(workspace / "initial_candidate.json") == {
        "proof": run.saved["selected_proof"],
        "finished": None,
    }
    assert result["before_final_cleanup"]["proof"] == result["selected_proof"]
    assert result["deterministic_calls"] == 1
    estimates = read(run.output / "cost_estimate.json")
    assert all(
        scenario["summary"]["budget_usd_per_problem"] == 1.0
        for scenario in estimates["scenarios"]
    )
    assert audit(run.output)["requests"] == 2

    def forbidden(**kwargs):
        raise AssertionError("Completed cells cannot dispatch another request")

    assert (
        search.run_cell(
            run.output, run.config, run.pack, MODEL, EFFORT, run.evaluator, forbidden
        )
        == result
    )

    # Updating matching hashes cannot hide an incorrect restarted incumbent.
    attempt = run.folder / "attempt_01"
    request = read(attempt / "request.json")
    prefix = "Optimize this declaration using the supplied tools.\n"
    payload, end = json.JSONDecoder().raw_decode(
        request["messages"][1]["content"][len(prefix) :]
    )
    suffix = request["messages"][1]["content"][len(prefix) + end :]
    payload["incumbent_declaration"] = run.pack["row"]["src"]
    request["messages"][1]["content"] = (
        prefix + json.dumps(payload, ensure_ascii=False, indent=2) + suffix
    )
    write_json(attempt / "request.json", request)
    record = read(attempt / "attempt.json")
    record.update(
        messages=request["messages"], messages_sha256=fingerprint(request["messages"])
    )
    write_json(attempt / "attempt.json", record)
    result["attempts"][1] = record
    write_json(run.folder / "result.json", result)
    with pytest.raises(ValueError, match="verified incumbent"):
        audit(run.output)

    # Reinstating the incumbent cannot make leaked prior conversation valid.
    payload["incumbent_declaration"] = record["incumbent_proof"]
    request["messages"][1]["content"] = (
        prefix
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + suffix
        + "\nPrior assistant transcript"
    )
    record.update(
        messages=request["messages"], messages_sha256=fingerprint(request["messages"])
    )
    write_json(attempt / "request.json", request)
    write_json(attempt / "attempt.json", record)
    result["attempts"][1] = record
    write_json(run.folder / "result.json", result)
    with pytest.raises(ValueError, match="history"):
        audit(run.output)


@pytest.mark.parametrize(
    "tracking,restarts,expected",
    [(None, 20, "agent_decision"), ("cost", 1, "restart_limit")],
)
def test_legacy_completion_and_restart_cap_have_factual_stops(
    tracking_run, tracking, restarts, expected
):
    run = tracking_run(tracking=tracking, restarts=restarts, usd=3.0)
    result = run_worker(run, fake_native(run))
    assert len(result["generations"]) == (1 if tracking is None else 2)
    assert result["stop"]["kind"] == expected
    assert result["cost"]["total_usd"] < 3.0
    assert audit(run.output)["status"] == "passed"
    request = read(run.folder / "attempt_00/request.json")
    assert ("cost_budget" in request) == (tracking == "cost")
    assert ("no fixed total attempt" in request["tool_instructions"]) == (
        tracking is None
    )


@pytest.mark.parametrize(
    "status", ["transport_error", "indeterminate", "model_mismatch"]
)
def test_infrastructure_does_not_restart(tracking_run, status):
    run = tracking_run(cleanup=False)
    calls = []

    def generator(**kwargs):
        calls.append(kwargs)
        return {"status": status, "error": "Unavailable transport"}

    result = run_worker(run, generator)
    assert len(calls) == 1 and result["status"] == "incomplete"
    assert result["stop"]["kind"] == "infrastructure"


TRANSIENT_ERROR = "stream disconnected before completion: Transport error: network error: error decoding response body"


def transient_events(message=TRANSIENT_ERROR):
    return [
        *[
            dict(type="error", message=f"Reconnecting... {number}/5")
            for number in range(1, 6)
        ],
        dict(type="error", message=message),
        dict(type="turn.failed", error=dict(message=message)),
    ]


def test_terminal_transport_recovery_preserves_proof_deadline_and_unknown_usage(
    tracking_run, monkeypatch
):
    monkeypatch.setattr(search, "RECOVERY_BACKOFF_SECONDS", 0)
    run = tracking_run(tracking=None)
    failed, success = fake_native(run, events=transient_events()), fake_native(run)

    def generator(**kwargs):
        return (failed if kwargs["folder"].name == "attempt_00" else success)(**kwargs)

    result = run_worker(run, generator)
    assert result["status"] == "complete"
    assert [g["status"] for g in result["generations"]] == [
        "transport_error",
        "received",
    ]
    first, second = result["attempts"]
    assert second["incumbent_proof"] == run.saved["selected_proof"]
    assert second["deadline_epoch"] == first["deadline_epoch"]
    assert second["generation_timeout_seconds"] < first["generation_timeout_seconds"]
    assert result["cost"]["total_usd"] is None
    assert result["cost"]["unknown_attempt_indices"] == [0]
    assert audit(run.output)["requests"] == 2


def test_terminal_transport_recovery_is_bounded(tracking_run, monkeypatch):
    monkeypatch.setattr(search, "RECOVERY_BACKOFF_SECONDS", 0)
    run = tracking_run(tracking=None, transport_restarts=1)
    result = run_worker(run, fake_native(run, events=transient_events()))
    assert len(result["generations"]) == 2
    assert result["status"] == "incomplete"
    assert result["stop"]["kind"] == "transport_recovery_limit"
    assert audit(run.output)["requests"] == 2


def test_unknown_spending_prevents_transport_recovery_in_cost_mode(tracking_run):
    run = tracking_run()
    result = run_worker(run, fake_native(run, events=transient_events()))
    assert len(result["generations"]) == 1
    assert result["stop"]["kind"] == "unknown_usage"
    assert audit(run.output)["requests"] == 1


def test_permanent_transport_failure_does_not_retry(tracking_run):
    run = tracking_run(tracking=None)
    result = run_worker(
        run,
        fake_native(run, events=transient_events("unexpected status 401 Unauthorized")),
    )
    assert len(result["generations"]) == 1
    assert result["stop"]["kind"] == "infrastructure"
    assert audit(run.output)["requests"] == 1


def test_saved_same_condition_proof_is_used_without_reevaluation(tracking_run):
    run = tracking_run(
        tracking=None, incumbents_from=ROOT / "results/harness/06_refactor_regression"
    )
    result = run_worker(run, fake_native(run))
    inp = read(run.folder / "input.json")
    assert inp["seed_proof"] == run.saved["selected_proof"]
    assert result["attempts"][0]["incumbent_proof"] == run.saved["selected_proof"]
    assert audit(run.output)["status"] == "passed"


def test_missing_usage_stops_with_an_unknown_cost(tracking_run):
    run = tracking_run()
    result = run_worker(run, fake_native(run, usage={}))
    assert len(result["attempts"]) == 1 and result["status"] == "incomplete"
    assert result["cost"]["total_usd"] is None
    assert result["stop"]["kind"] == "unknown_usage"
    assert audit(run.output)["status"] == "passed"


def test_time_tracking_reserves_cleanup_time_after_native_completion(tracking_run):
    run = tracking_run(tracking="time", timeout=20.0)
    result = run_worker(run, fake_native(run))
    assert len(result["generations"]) == 1
    assert result["stop"]["kind"] == "cleanup_reserve"
    assert result["time_budget"]["exhausted"] is False
    assert result["deterministic_calls"] == 1
    assert audit(run.output)["status"] == "passed"


def test_audit_uses_budget_decision_time_when_writing_crosses_cleanup_reserve(
    tracking_run, monkeypatch
):
    run = tracking_run(tracking="time", restarts=0, timeout=120.0)
    finish, stop = search.finish_attempt, search.record_stop

    def finish_before_reserve(*args):
        record = finish(*args)
        monkeypatch.setattr(search.time, "time", lambda: record["deadline_epoch"] - 31)
        return record

    def write_after_reserve(folder, decision, number, **kwargs):
        deadline = read(run.folder / "budget_started.json")["deadline_epoch"]
        monkeypatch.setattr(search.time, "time", lambda: deadline - 29)
        return stop(folder, decision, number, **kwargs)

    monkeypatch.setattr(search, "finish_attempt", finish_before_reserve)
    monkeypatch.setattr(search, "record_stop", write_after_reserve)
    result = run_worker(run, fake_native(run))
    assert result["stop"]["kind"] == "restart_limit"
    assert result["stop"]["at_epoch"] == result["time_budget"]["deadline_epoch"] - 31
    assert audit(run.output)["status"] == "passed"


def test_tiny_cost_budget_does_not_dispatch_a_request(tracking_run):
    run = tracking_run(usd=1e-9, cleanup=False)

    def forbidden(**kwargs):
        raise AssertionError("No money remains for a native response")

    result = run_worker(run, forbidden)
    assert result["generations"] == result["attempts"] == []
    assert result["stop"]["kind"] == "cost_reserve"
    assert result["status"] == "complete"
    assert result["selected_proof"] == result["seed_proof"]


def test_unavailable_verification_prevents_a_successful_response_from_restarting(
    tracking_run,
):
    run = tracking_run(cleanup=False)
    unavailable = deepcopy(run.saved["selected_evaluation"])
    unavailable.update(
        status="incomplete", scores={key: None for key in unavailable["scores"]}
    )
    for outcome in unavailable["per_version"].values():
        outcome.update(status="incomplete", passed=None, error="Compiler unavailable")
    run.evaluator.evaluate = lambda *a, **k: unavailable
    calls = []

    def generator(**kwargs):
        calls.append(kwargs)
        return {
            "status": "received",
            "content": run.saved["selected_proof"],
            "finish_reason": "stop",
            "codex_usage": USAGE,
        }

    result = run_worker(run, generator)
    assert len(calls) == 1 and result["status"] == "incomplete"
    assert result["stop"]["kind"] == "infrastructure"
    assert result["selected_proof"] == result["seed_proof"]


def test_exact_cost_cap_stops_without_marking_an_overspend(tracking_run):
    run = tracking_run(
        usd=estimate_token_cost(CostConfig(MODEL, EFFORT), USAGE)["total_usd"]
    )
    result = run_worker(run, fake_native(run))
    assert len(result["attempts"]) == 1 and result["stop"]["kind"] == "cost_limit"
    assert result["cost"]["over_budget_at_assumed_rates"] is False
    assert audit(run.output)["status"] == "passed"


@pytest.mark.parametrize("budget_failure", [True, False])
def test_only_explicit_native_budget_events_are_controlled(
    tracking_run, budget_failure
):
    run = tracking_run()
    message = (
        "shared rollout token budget exhausted" if budget_failure else "connection lost"
    )
    events = [
        {"type": "error", "message": message},
        {"type": "turn.failed", "error": {"message": message}},
    ]
    result = run_worker(run, fake_native(run, events=events))
    assert len(result["attempts"]) == 1
    assert result["status"] == ("complete" if budget_failure else "incomplete")
    assert result["stop"]["kind"] == (
        "cost_limit" if budget_failure else "infrastructure"
    )
    assert result["cost"]["total_usd"] is None
    assert result["selected_proof"] == run.saved["selected_proof"]
    assert audit(run.output)["status"] == "passed"


def test_public_custom_generator_is_stopped_at_the_whole_problem_deadline(tracking_run):
    run = tracking_run(tracking="time", timeout=1.0, cleanup=False)

    def generator(**kwargs):
        kwargs["session"].check(run.saved["selected_proof"])
        detached = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(1000)"],
            start_new_session=True,
        )
        write_json(kwargs["folder"] / "detached.json", {"pid": detached.pid})
        time.sleep(1000)

    started = time.monotonic()
    result = search.run_cell(
        run.output, run.config, run.pack, MODEL, EFFORT, run.evaluator, generator
    )
    assert time.monotonic() - started < 3.0
    assert result["selected_proof"] == run.saved["selected_proof"]
    assert result["status"] == "complete" and result["stop"]["kind"] == "time_limit"
    assert result["generations"][0]["dispatch_status"] == "not_dispatched"
    pid = read(run.folder / "attempt_00/detached.json")["pid"]
    proc = Path("/proc") / str(pid) / "stat"
    assert not proc.exists() or proc.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    assert audit(run.output)["status"] == "passed"


@pytest.mark.parametrize(
    "fields,match",
    [
        ({"budget_usd_per_problem": float("nan")}, "positive and finite"),
        ({"problem_timeout_seconds": float("inf")}, "positive and finite"),
        ({"budget_usd_per_problem": True}, "positive and finite"),
        ({"max_budget_restarts": -1}, "nonnegative integer"),
        ({"max_budget_restarts": 0.5}, "nonnegative integer"),
        ({"budget_tracking": "invalid"}, "budget_tracking"),
        (
            {
                "provider": "lemex",
                "budget_tracking": "cost",
                "conditions": [("Qwen/Qwen3.8-Flash-Next", "xhigh")],
            },
            "unpriced model",
        ),
    ],
)
def test_prepare_validates_before_creating_output(tmp_path, fields, match):
    output = tmp_path / "invalid"
    with pytest.raises(ValueError, match=match):
        prepare(output, "score_edges", {}, **fields)
    assert not output.exists()


def test_tracking_cli_flags_are_exclusive_and_restart_limit_is_forwarded(
    monkeypatch, tmp_path
):
    for flags in (
        ["--track-cost", "--track-time"],
        ["--budget-tracking", "cost", "--track-cost"],
    ):
        with pytest.raises(SystemExit) as error:
            cli.main(["prepare", *flags])
        assert error.value.code == 2
    captured = []
    monkeypatch.setattr(
        cli, "run", lambda config: captured.append(config) or {"status": "prepared"}
    )
    assert (
        cli.main(
            [
                "prepare",
                "--track-cost",
                "--max-budget-restarts",
                "4",
                "--output",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert captured[0].max_budget_restarts == 4


def test_native_guards_preserve_sampling_and_apply_remaining_dollars(tmp_path):
    guard = native_cost_guard("codex", CostConfig(MODEL, EFFORT), 0.75)
    assert guard["limit_tokens"] == 50000 and guard[
        "prefill_token_weight"
    ] == pytest.approx(1 / 3)
    assert codex_budget_settings(None) == {}
    assert set(codex_budget_settings(guard)) == {
        "features.rollout_budget." + field
        for field in (
            "enabled",
            "limit_tokens",
            "prefill_token_weight",
            "sampling_token_weight",
            "reminder_at_remaining_tokens",
        )
    }
    argv = claude.command(
        binary="claude",
        workspace=tmp_path,
        system_file=tmp_path / "system",
        tool_file=tmp_path / "tools",
        model=claude.MODEL,
        effort="max",
        source_projects=[],
        cost_budget=native_cost_guard("claude", CostConfig(claude.MODEL, "max"), 0.75),
    )
    assert argv[argv.index("--max-budget-usd") + 1] == "0.75"
    assert "--temperature" not in argv
    with pytest.raises(ValueError, match="output token"):
        codex_budget_settings(
            native_cost_guard("codex", CostConfig(MODEL, EFFORT), 1e-9)
        )
    assert not native_cost_stop(
        "codex", [{"type": "error", "message": "connection lost"}], guard
    )
    assert not native_cost_stop(
        "claude", [{"type": "result", "subtype": "error_max_turns"}], guard
    )


@pytest.mark.parametrize(
    "token_limit,expected_requests,stopped", [(150, 2, True), (1000, 3, False)]
)
def test_installed_codex_weighted_guard_stops_multiple_local_responses(
    tmp_path, token_limit, expected_requests, stopped
):
    """Exercise the real native CLI against localhost only, preserving its defaults."""
    if not shutil.which("codex"):
        pytest.skip("Native Codex CLI unavailable")
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(data)
            index = len(requests)
            item = {
                "id": f"call_{index}",
                "type": "function_call",
                "call_id": f"call_{index}",
                "name": "exec_command",
                "arguments": json.dumps(
                    {"cmd": "echo budget-test", "max_output_tokens": 20}
                ),
            }
            if index == 3:
                item = {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "theorem x : True := by trivial",
                            "annotations": [],
                        }
                    ],
                }
            response = {
                "id": f"resp_{index}",
                "object": "response",
                "status": "completed",
                "output": [item],
                "usage": {
                    "input_tokens": 200,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens": 100,
                    "output_tokens_details": {"reasoning_tokens": 10},
                    "total_tokens": 300,
                },
            }
            events = [
                (
                    "response.output_item.added",
                    {
                        "type": "response.output_item.added",
                        "output_index": 0,
                        "item": item,
                    },
                ),
                (
                    "response.output_item.done",
                    {
                        "type": "response.output_item.done",
                        "output_index": 0,
                        "item": item,
                    },
                ),
                (
                    "response.completed",
                    {"type": "response.completed", "response": response},
                ),
            ]
            payload = "".join(
                "event: " + kind + "\ndata: " + json.dumps(value) + "\n\n"
                for kind, value in events
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        system = tmp_path / "system.txt"
        system.write_text("Use shell tools and return a Lean proof.")
        guard = {
            "kind": "native_weighted_tokens",
            "limit_tokens": token_limit,
            "prefill_token_weight": 0.2,
            "sampling_token_weight": 1.0,
            "reminder_at_remaining_tokens": [10],
        }
        settings = {
            "model_provider": "local_test",
            "model_providers.local_test.name": "Local test only",
            "model_providers.local_test.base_url": f"http://127.0.0.1:{server.server_port}/v1",
            "model_providers.local_test.wire_api": "responses",
            "model_providers.local_test.request_max_retries": 0,
            "model_providers.local_test.stream_max_retries": 0,
            "model_providers.local_test.requires_openai_auth": False,
            "features.enable_request_compression": False,
            **codex_budget_settings(guard),
        }
        argv = codex.command(
            binary=cli_identity()["path"],
            workspace=tmp_path,
            system_file=system,
            last_message=tmp_path / "final.txt",
            model=MODEL,
            effort=EFFORT,
            mode="score_edges",
            instructions="Use shell and return proof.",
            settings=settings,
        )
        result = subprocess.run(
            argv,
            input="Optimize theorem x : True := by trivial",
            text=True,
            capture_output=True,
            cwd=tmp_path,
            timeout=20,
        )
        events = [
            json.loads(line) for line in result.stdout.splitlines() if line.strip()
        ]
        assert native_cost_stop("codex", events, guard) is stopped
        assert (
            len(requests) == expected_requests
        )  # 200*.2 + 100 = 140 weighted tokens per response.
        if not stopped:
            parsed = parse_events(
                events, (tmp_path / "final.txt").read_text(), result.returncode
            )
            assert parsed["status"] == "received"
            assert parsed["token_usage"] == {
                "input_tokens": 600,
                "cached_input_tokens": 0,
                "cache_write_input_tokens": 0,
                "output_tokens": 300,
                "reasoning_output_tokens": 30,
            }
            assert estimate_token_cost(
                CostConfig(MODEL, EFFORT), parsed["token_usage"]
            )["total_usd"] == pytest.approx(0.0042)
        assert all(
            "max_output_tokens" not in request and "temperature" not in request
            for request in requests
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
