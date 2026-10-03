"""Saved-log audit tests; no HTTP, Lean, process signalling, or live client."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from audit_rcp_admission import SEMANTICS, audit, audit_events


INV = "a" * 32
MODELS = ["m1", "m2", "m3"]


def at(seconds):
    return (datetime(2020, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat()


def cfg():
    return {"pid": 123, "started_at": at(0), "legacy_models": MODELS}


def ticket(number, start=10, end=20, slot=1, reserved=None, kind="create_chat_completion"):
    identifier = f"{number:032x}"
    common = {"invocation": INV, "ticket": identifier, "pid": 123, "thread": number, "kind": kind}
    result = [{**common, "event": "queued", "at": at(start - 1)},
              {**common, "event": "admitted", "at": at(start), "slot": slot,
               "reserved_legacy_models": ["m1"] if reserved is None else reserved, "queue_seconds": 1}]
    if end is not None:
        result.append({**common, "event": "released", "at": at(end), "slot": slot,
                       "outcome": "returned", "admitted_seconds": end - start})
    return result


def check(events, complete=False):
    return audit_events(events, {INV: cfg()}, unresolved_models={"m1"}, complete=complete)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def bundle(tmp_path):
    root, initial, repair, logs, gate = (tmp_path / value for value in ["repo", "initial", "repair", "logs", "gate"])
    for name in ["run_one_shot.py", "run_with_rcp_limit.py"]:
        path = root / "src" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# frozen fixture source\n")
    sources = {"src/run_one_shot.py": digest(root / "src/run_one_shot.py")}
    initial_config = {"models": MODELS, "names": ["theorem"], "arms": ["plain"], "code_sha256": sources}
    write(initial / "config.json", initial_config)
    write(initial / "run.json", {"status": "finished", "finished_at": at(-1)})
    cells = [{"key": f"key_{model}", "logical": ["theorem", "plain", model]} for model in MODELS]
    matrix = {"base_directory": str(initial), "base_config_sha256": digest(initial / "config.json"),
              "per_model": 1, "models": MODELS, "cells": cells, "code_sha256": sources}
    write(repair / "matrix_config.json", matrix)
    completed = {}
    for model in MODELS[1:]:
        key = f"key_{model}"
        path = repair / "cells" / key / "result.json"
        write(path, {"name": "theorem", "arm": "plain", "model": model,
                     "base_request_sha256": key, "outcome": "no_candidate"})
        completed[model] = {key: digest(path)}
    config = {"schema_version": 1, "capacity": 5, "legacy_initial_directory": str(initial),
              "legacy_repair_directory": str(repair), "legacy_initial_config_sha256": digest(initial / "config.json"),
              "legacy_repair_matrix_sha256": digest(repair / "matrix_config.json"), "legacy_models": MODELS,
              "legacy_per_model_reservation": 1, "legacy_code_sha256": sources,
              "wrapper_sha256": digest(root / "src/run_with_rcp_limit.py"), "poll_seconds": 0.5, "semantics": SEMANTICS}
    write(gate / "config.json", config)
    write(gate / "reservations.json", {"completed_models": completed})
    write(logs / f"{INV}.config.json", {**config, **cfg(), "invocation": INV})
    output = root / "output"
    write(output / "run.json", {"status": "finished"})
    command = {"wrapped_script": str(root / "src/run_one_shot.py"), "wrapped_script_sha256": sources["src/run_one_shot.py"],
               "arguments": ["--output", str(output)], "wrapper_sha256": config["wrapper_sha256"], "invocation": INV}
    write(logs / f"{INV}.command.json", command)
    (logs / f"{INV}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ticket(1, kind="list_models")))
    return {"root": root, "initial": initial, "repair": repair, "logs": logs, "gate": gate, "output": output}


def run(bundle, complete=False):
    return audit([bundle["logs"]], bundle["gate"], complete=complete, root=bundle["root"])


def test_complete_valid_snapshot_checks_source_and_release_evidence(bundle):
    result = run(bundle, complete=True)
    assert result["status"] == "passed"
    assert result["event_counts"] == {"queued": 1, "admitted": 1, "released": 1}
    assert result["max_observed_http_plus_legacy_upper_bound"] == 2
    assert result["pending_tickets"] == []
    assert result["unresolved_legacy_models"] == ["m1"]
    assert any("gate path/inode" in note for note in result["limitations"])


@pytest.mark.parametrize("target", ["source", "invocation", "released_result", "command", "legacy_matrix"])
def test_changed_pins_and_configuration_fail_closed(bundle, target):
    if target == "source":
        (bundle["root"] / "src/run_with_rcp_limit.py").write_text("changed")
    elif target == "invocation":
        path = bundle["logs"] / f"{INV}.config.json"
        value = json.loads(path.read_text()); value["capacity"] = 6; write(path, value)
    elif target == "released_result":
        path = bundle["repair"] / "cells/key_m2/result.json"
        value = json.loads(path.read_text()); value["outcome"] = "changed"; write(path, value)
    elif target == "command":
        path = bundle["logs"] / f"{INV}.command.json"
        value = json.loads(path.read_text()); value["wrapped_script_sha256"] = "0" * 64; write(path, value)
    else:
        path = bundle["repair"] / "matrix_config.json"
        value = json.loads(path.read_text()); value["per_model"] = 2; write(path, value)
    assert run(bundle)["status"] == "failed"


def test_unfinished_wrapped_run_allowed_only_for_partial(bundle):
    write(bundle["output"] / "run.json", {"status": "running"})
    assert run(bundle)["status"] == "passed"
    assert run(bundle, complete=True)["status"] == "failed"


def test_unterminated_ticket_distinct_from_complete_and_blocked():
    partial = check(ticket(1, end=None))
    assert not partial["errors"] and partial["pending_tickets"][0]["state"] == "admitted"
    assert check(ticket(1, end=None), complete=True)["errors"]
    queued = ticket(1)[:1]
    blocked = {**queued[0], "event": "blocked", "at": at(10), "exception_type": "AdmissionEvidenceError"}
    assert check(queued + [blocked], complete=True)["pending_tickets"] == []
    assert not check(queued + [blocked], complete=True)["errors"]


@pytest.mark.parametrize("edit", ["missing_queue", "duplicate_queue", "different_thread", "unknown_kind", "release_slot", "after_release", "blocked_after_admitted", "unresolved_omitted", "reserved_slot"])
def test_trajectory_and_reservations_tampering(edit):
    events = ticket(1)
    if edit == "missing_queue": events.pop(0)
    elif edit == "duplicate_queue": events.insert(1, deepcopy(events[0]))
    elif edit == "different_thread": events[-1]["thread"] = 12
    elif edit == "unknown_kind": events[0]["kind"] = "hidden_probe"
    elif edit == "release_slot": events[-1]["slot"] = 2
    elif edit == "after_release": events.append(deepcopy(events[-1]))
    elif edit == "blocked_after_admitted": events[-1].update(event="blocked", exception_type="Error")
    elif edit == "unresolved_omitted": events[1]["reserved_legacy_models"] = []
    elif edit == "reserved_slot": events[1]["slot"] = 0
    assert check(events)["errors"]


def test_shared_slots_catch_cross_invocation_overlap():
    first, second = ticket(1, slot=2), ticket(2, start=15, end=25, slot=2)
    other = "b" * 32
    for event in second: event["invocation"] = other; event["pid"] = 456
    result = audit_events(first + second, {INV: cfg(), other: {**cfg(), "pid": 456}}, unresolved_models={"m1"})
    assert any("overlapping admissions" in e for e in result["errors"])


def test_equal_endpoints_are_inconclusive_without_assuming_release_first():
    result = check(ticket(1, end=20, slot=2) + ticket(2, start=20, end=30, slot=2), complete=True)
    assert not result["errors"]
    assert result["uncertainties"]
    assert result["max_observed_http_plus_legacy_upper_bound"] == 3


def test_clock_step_does_not_certify_count_or_claim_definite_slot_violation():
    events = ticket(1, end=20, slot=2) + ticket(2, start=15, end=25, slot=2)
    events[2]["admitted_seconds"] = 2
    result = check(events)
    assert not result["errors"]
    assert any("wall-clock" in u for u in result["uncertainties"])


def test_snapshot_missing_release_cannot_infer_kernel_crash_release():
    events = ticket(1, end=None, slot=2) + ticket(2, start=30, end=40, slot=2)
    assert not check(events)["errors"] and check(events)["uncertainties"]
    assert check(events, complete=True)["errors"]


def test_global_count_includes_reserved_model_and_both_http_kinds():
    events = sum((ticket(i, slot=i, kind="list_models" if i == 1 else "create_chat_completion") for i in range(1, 5)), [])
    result = check(events, complete=True)
    assert not result["errors"] and not result["uncertainties"]
    assert result["max_observed_http_interval_upper_bound"] == 4
    assert result["max_observed_http_plus_legacy_upper_bound"] == 5
    result = check(events + ticket(5, slot=4), complete=True)
    assert any("exceeds five" in e for e in result["errors"])


def test_partial_trailing_write_and_orphan_logs(bundle):
    log = bundle["logs"] / f"{INV}.jsonl"
    with log.open("a") as stream: stream.write('{"event":')
    assert run(bundle)["status"] == "inconclusive"
    assert run(bundle, complete=True)["status"] == "failed"
    log.write_text("")
    (bundle["logs"] / (("b" * 32) + ".jsonl")).write_text("")
    assert run(bundle)["status"] == "failed"


def test_initial_drain_timestamp_is_verified(bundle):
    write(bundle["initial"] / "run.json", {"status": "finished", "finished_at": at(30)})
    assert run(bundle)["status"] == "failed"


def test_blocked_timestamp_regression_is_clock_uncertainty():
    queued = ticket(1)[:1]
    blocked = {**queued[0], "event": "blocked", "at": at(8), "exception_type": "EvidenceError"}
    result = check(queued + [blocked], complete=True)
    assert not result["errors"] and result["uncertainties"]


def test_optimized_python_still_rejects_malformed_trajectory():
    events = ticket(1)
    events[1]["slot"] = 0
    events[2]["thread"] = 100
    payload = json.dumps({"events": events, "configurations": {INV: cfg()}})
    source = str(Path(__file__).resolve().parents[1] / "src")
    code = "import json,sys;sys.path.insert(0,sys.argv[1]);from audit_rcp_admission import audit_events; p=json.loads(sys.stdin.read());r=audit_events(p['events'],p['configurations'],unresolved_models={'m1'});print(json.dumps(r));sys.exit(0 if any('slot violates' in e for e in r['errors']) and any('identity changed' in e for e in r['errors']) else 1)"
    result = subprocess.run([sys.executable, "-O", "-c", code, source], input=payload, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("deleted", [False, True])
def test_complete_one_shot_cannot_silently_lose_startup_http_evidence(bundle, deleted):
    log = bundle["logs"] / f"{INV}.jsonl"
    if deleted:
        log.unlink()
    else:
        log.write_text("".join(json.dumps(e) + "\n" for e in ticket(1)))
    assert run(bundle)["status"] == "passed"
    assert run(bundle, complete=True)["status"] == "failed"


def test_log_copied_to_another_directory_is_not_silently_ignored(bundle, tmp_path):
    other = tmp_path / "other_logs"
    other.mkdir()
    (other / f"{INV}.jsonl").write_bytes((bundle["logs"] / f"{INV}.jsonl").read_bytes())
    result = audit([bundle["logs"], other], bundle["gate"], root=bundle["root"])
    assert result["status"] == "failed"
    assert "same directory" in result["errors"][0]
