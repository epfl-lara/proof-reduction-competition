"""Detect interrupted native work without mistaking budget stops or PID reuse."""

import os

from proof_eval.evidence.io import read, write_json
from proof_eval.evidence.watch import inspect_runs, poll
from proof_eval.providers.processes import process_identity
from proof_eval.providers.termination import record_exit


def test_signal_cluster_and_budget_stop_are_distinct_and_deduplicated(tmp_path):
    runs, output = tmp_path / "runs", tmp_path / "watch"
    for name, status, code, second in [
        ("sol", "transport_error", -15, 1),
        ("qwen", "transport_error", -15, 2),
        ("timed", "budget_exhausted", -9, 2),
    ]:
        write_json(
            runs / name / "generation.json",
            dict(
                status=status,
                returncode=code,
                finished_at=f"2026-10-17T16:47:0{second}+00:00",
            ),
        )
    before = {str(p): p.read_bytes() for p in runs.rglob("*.json")}
    findings = inspect_runs([runs])
    assert [f["kind"] for f in findings].count("native_failure") == 2
    cluster = next(f for f in findings if f["kind"] == "correlated_native_exits")
    assert len(cluster["attempts"]) == 2 and cluster["span_seconds"] == 1
    assert poll(dict(roots=[str(runs)]), output)["new_alerts"] == 3
    assert poll(dict(roots=[str(runs)]), output)["new_alerts"] == 0
    assert before == {str(p): p.read_bytes() for p in runs.rglob("*.json")}


def test_dead_request_requires_grace_and_reused_pid_does_not_look_alive(tmp_path):
    runs, output = tmp_path / "runs", tmp_path / "watch"
    identity = process_identity(os.getpid())
    write_json(runs / "live/request_started.json", {})
    write_json(runs / "dead/request_started.json", {})
    write_json(runs / "live/process.json", dict(pid=os.getpid(), identity=identity))
    write_json(
        runs / "dead/process.json",
        dict(pid=os.getpid(), identity={**identity, "start_ticks": "0"}),
    )
    spec = dict(roots=[str(runs)])
    assert poll(spec, output, timestamp=100)["new_alerts"] == 0
    assert poll(spec, output, timestamp=159)["new_alerts"] == 0
    assert poll(spec, output, timestamp=160)["new_alerts"] == 1
    write_json(runs / "dead/generation.json", dict(status="budget_exhausted"))
    assert poll(spec, output, timestamp=200)["findings"] == 0


def test_deterministic_worker_is_not_mistaken_for_missing_native_terminal(tmp_path):
    write_json(tmp_path / "study/optimization/process.json", dict(pid=99999999))
    write_json(tmp_path / "study/optimization/result.json", dict(status="complete"))
    assert inspect_runs([tmp_path]) == []


def test_cell_failure_is_detected_while_other_cells_are_running(tmp_path):
    write_json(tmp_path / "run.json", dict(status="running"))
    write_json(
        tmp_path / "conditions/facts/cells/one/result.json",
        dict(status="incomplete_discovery", name="one"),
    )
    write_json(
        tmp_path / "conditions/facts/cells/two/result.json",
        dict(status="discovery_limit", name="two"),
    )
    findings = inspect_runs([tmp_path])
    assert len(findings) == 1 and findings[0]["kind"] == "cell_incomplete"
    assert findings[0]["name"] == "one"


def test_native_cost_stop_does_not_emit_unexpected_exit_alert(tmp_path):
    import os
    import sys
    from contextlib import nullcontext
    from types import SimpleNamespace

    from proof_eval.providers.events import parse_events
    from proof_eval.providers.execution import Launch, generate

    source = tmp_path / "source"
    source.mkdir()
    folder = tmp_path / "attempt"
    script = """
import json,sys
sys.stdin.read()
print(json.dumps({'type':'turn.failed','error':{'message':'shared rollout token budget exhausted'}}))
sys.exit(1)
"""

    def build(workspace, *_):
        return Launch(
            argv=[sys.executable, "-c", script],
            environment=dict(os.environ),
            runtime_paths=(),
            cwd=workspace,
            parse=parse_events,
        )

    result = generate(
        folder=folder,
        messages=[
            dict(role="system", content="policy"),
            dict(role="user", content="task"),
        ],
        model="gpt-6.1-sol",
        effort="max",
        mode="score_edges",
        session=SimpleNamespace(best_code="theorem t : True := by trivial"),
        context=dict(source_projects={"test": str(source)}),
        expected_cli={},
        identity={},
        instructions="tools",
        tool_service=lambda *_: nullcontext(),
        provider="codex",
        authentication="offline fixture",
        build=build,
        timeout=10,
        cost_budget={"kind": "native"},
    )
    assert result["status"] == "budget_exhausted" and result["returncode"] == 1
    assert (
        result["process_exit"]["controlled"]
        and result["process_exit"]["reason"] == "cost_limit"
    )
    assert not (folder / "incident.json").exists()
    assert inspect_runs([folder]) == []


def test_exit_evidence_survives_parser_failure_and_labels_signal_inference(tmp_path):
    actual = record_exit(tmp_path / "actual", -15)
    assert (
        actual["signal"] == "SIGTERM" and actual["signal_basis"] == "kernel_wait_status"
    )
    assert (tmp_path / "actual/incident.json").exists()
    inferred = record_exit(tmp_path / "inferred", 143)
    assert inferred["signal_basis"] == "shell_exit_convention_only"
    stopped = record_exit(tmp_path / "stopped", -9, timed_out=True)
    assert stopped["controlled"] and stopped["reason"] == "deadline"
    assert not (tmp_path / "stopped/incident.json").exists()
    assert read(tmp_path / "actual/termination.json") == actual
