"""Deadline finalization preserves proofs without inventing clean process custody."""

from copy import deepcopy

import pytest

from proof_eval.evidence.io import fingerprint, read, sha, write_json, write_jsonl
from proof_eval.harness.audit import _audit_native_ownership
from proof_eval.harness.recovery import _generation, recover_cell
from proof_eval.providers import deadline_cleanup
from proof_eval.verification.metrics import token_count, validate_candidate


@pytest.fixture
def deadline_attempt(tmp_path):
    cell = tmp_path / "cell"
    folder = cell / "attempt_00"
    folder.mkdir(parents=True)
    process = {
        "pid": 123,
        "start_ticks": "10",
        "native_supervisor": True,
        "ownership_schema_version": 2,
    }
    write_json(folder / "request.json", {"cli": {"ownership_schema_version": 2}})
    write_json(folder / "process.json", process)
    write_json(
        folder / "process_ownership_started.json",
        {
            "schema_version": 2,
            "supervisor": {"pid": 123, "start_ticks": "10"},
            "native": {"pid": 124, "start_ticks": "11"},
            "native_exec_gated": True,
        },
    )
    workspace = folder / "workspace"
    workspace.mkdir()
    (workspace / "final.txt").write_text("theorem t : True := by trivial")
    write_jsonl(
        folder / "events.jsonl",
        [
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 100, "output_tokens": 5},
            }
        ],
    )
    outer = {
        "exhausted": True,
        "work_stopped_epoch": 7300,
        "terminated_pids": [99],
        "process_start_ticks": {"99": "9"},
        "cleanup": {"complete": True, "freeze_complete": True, "remaining_pids": []},
    }
    write_json(cell / "budget_end.json", outer)
    native = {
        **deepcopy(outer),
        "terminated_pids": [123, 124],
        "process_start_ticks": {"123": "10", "124": "11"},
    }
    return folder, process, native


def test_outer_worker_cleanup_is_not_native_cleanup(deadline_attempt):
    folder, _, _ = deadline_attempt
    generation = _generation(folder, "lemex-local")
    assert generation["status"] == "transport_error"
    assert "host_deadline_cleanup" not in generation
    refusal = read(folder / "deadline_cleanup_refused.json")
    assert refusal["status"] == "refused"
    assert generation["host_deadline_cleanup_refusal"]["sha256"] == fingerprint(refusal)
    assert "fully reaped" in generation["error"]
    assert read(folder / "generation.json") == generation
    with pytest.raises(ValueError, match="missing complete host cleanup"):
        _audit_native_ownership(folder, generation, [])


def test_completed_native_stop_survives_a_later_outer_deadline(deadline_attempt):
    folder, process, stopped = deadline_attempt
    deadline_cleanup.save_native_stop(folder, process, stopped, returncode=-9)
    generation = _generation(folder, "lemex-local")
    assert generation["status"] == "budget_exhausted"
    receipt = read(folder / "deadline_cleanup.json")
    assert receipt["source"] == "native_timeout"
    assert receipt["stopped"] == stopped
    assert "process_ownership" not in generation
    _audit_native_ownership(folder, generation, [])


@pytest.mark.parametrize("fault", ["pid", "ticks", "hash", "reaped", "returncode"])
def test_changed_native_stop_never_falls_back_or_promotes(deadline_attempt, fault):
    folder, process, stopped = deadline_attempt
    deadline_cleanup.save_native_stop(folder, process, stopped, returncode=-9)
    path = folder / "native_timeout_cleanup.json"
    receipt = read(path)
    if fault == "pid":
        receipt["supervisor"]["pid"] += 1
    elif fault == "ticks":
        receipt["supervisor"]["start_ticks"] = "20"
    elif fault == "hash":
        receipt["stopped"]["work_stopped_epoch"] += 1
    elif fault == "reaped":
        receipt["supervisor_reaped"] = False
    else:
        receipt["supervisor_returncode"] = None
    write_json(path, receipt)
    generation = _generation(folder, "lemex-local")
    assert generation["status"] == "transport_error"
    assert "host_deadline_cleanup_refusal" in generation
    assert not (folder / "deadline_cleanup.json").exists()


@pytest.mark.parametrize("field", ["complete", "freeze_complete", "remaining_pids"])
def test_unfinished_native_cleanup_remains_refused(deadline_attempt, field):
    folder, process, stopped = deadline_attempt
    stopped["cleanup"][field] = [124] if field == "remaining_pids" else False
    deadline_cleanup.save_native_stop(folder, process, stopped, returncode=-9)
    generation = _generation(folder, "lemex-local")
    assert generation["status"] == "transport_error"
    assert "host_deadline_cleanup" not in generation


def test_unreaped_supervisor_cannot_publish_a_native_stop(deadline_attempt):
    folder, process, stopped = deadline_attempt
    with pytest.raises(deadline_cleanup.CleanupEvidenceError, match="not been reaped"):
        deadline_cleanup.save_native_stop(folder, process, stopped, returncode=None)
    assert not (folder / "native_timeout_cleanup.json").exists()


def test_saved_native_stop_remains_hash_bound_during_audit(deadline_attempt):
    folder, process, stopped = deadline_attempt
    deadline_cleanup.save_native_stop(folder, process, stopped, returncode=-9)
    generation = _generation(folder, "lemex-local")
    path = folder / "native_timeout_cleanup.json"
    value = read(path)
    value["supervisor_returncode"] = 0
    write_json(path, value)
    with pytest.raises(ValueError, match="receipt changed"):
        _audit_native_ownership(folder, generation, [])


def test_refused_deadline_still_writes_incomplete_result_with_best_proof(
    deadline_attempt,
):
    folder, _, _ = deadline_attempt
    cell = folder.parent
    original = "theorem t : True := by exact True.intro"
    best = "theorem t : True := by trivial"
    row = {
        "name": "t",
        "source": "fixture",
        "statement": "theorem t : True",
        "src": original,
        "proof_length": token_count("by exact True.intro"),
        "version_info": [{"v1": {}}],
    }
    reference = {
        "status": "prepared",
        "heartbeats": 100,
        "heartbeats_raw": 100000,
        "reference_code_sha256": sha(original),
        "environment_fingerprint": "fixture",
    }
    evaluation = {
        "status": "passed",
        "candidate": {"code_sha256": sha(validate_candidate(row, best)[0])},
        "per_version": {
            "v1": {"passed": True, "status": "passed", "reference": reference}
        },
        "scores": {
            "length_reduction_pct": 90,
            "heartbeat_reduction_pct": 80,
            "compatibility_pct": 100,
            "combined_pct": 90,
        },
    }
    pack = {"name": "t", "row": row, "incumbent": evaluation, "proof": best}
    ledger = {
        "number": 1,
        "code": best,
        "code_sha256": evaluation["candidate"]["code_sha256"],
        "evaluation": evaluation,
        "all_versions_passed": True,
        "accepted": True,
        "duplicate": False,
        "origin": "agent_tool",
    }
    write_jsonl(cell / "evidence/checks.jsonl", [ledger])
    write_json(cell / "input.json", {})
    write_json(
        cell / "budget_started.json",
        {"started_epoch": 100, "deadline_epoch": 7300, "timeout_seconds": 7200},
    )

    class NoExecution:
        def __getattr__(self, name):
            raise AssertionError("Deadline recovery must not execute " + name)

    result = recover_cell(
        cell,
        {
            "mode": "score_edges",
            "pipeline_version": 1,
            "deterministic_cleanup": False,
            "provider": "lemex-local",
        },
        pack,
        "Qwen/Qwen3.8-Flash-Next-FP8",
        "xhigh",
        NoExecution(),
    )
    assert read(cell / "result.json") == result
    assert result["status"] == "incomplete"
    assert result["generation_status"] == "transport_error"
    assert result["selected_proof"] == best
    assert result["selected_evaluation"] == evaluation
    assert result["time_budget"]["deadline_epoch"] == 7300
    assert read(cell / "evidence/checks.jsonl") == ledger
