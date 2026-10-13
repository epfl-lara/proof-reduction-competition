"""Read experiment evidence, obtain an AGY review, and wake the owning thread.

The observer never repairs or signals experiment processes. Codex owns recovery.
"""

import argparse
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "monitor.json"


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def process(pid, expected_start=None, expected_path=None):
    try:
        base = Path(f"/proc/{int(pid)}")
        fields = (base / "stat").read_text().rsplit(") ", 1)[1].split()
        ticks = int(fields[19])
        matches = expected_start is None or ticks == int(expected_start)
        if expected_path is not None:
            matches = matches and str(expected_path).encode() in (base / "cmdline").read_bytes()
        return {"pid": pid, "state": fields[0], "start_ticks": ticks,
                "identity_matches": matches, "alive": matches and fields[0] not in ("Z", "X")}
    except (OSError, TypeError, ValueError):
        return {"pid": pid, "alive": False, "state": "absent_or_unreadable"}


def capacity_retry_due(snapshot, plan, now):
    """Wake Codex after a cooldown only for a stopped, audited source cohort."""
    return bool(
        plan and plan.get("status") == "waiting"
        and plan.get("source_phase") == snapshot["phase"]
        and now >= plan["not_before_epoch"]
        and not snapshot["ready"]
        and snapshot.get("completion")
        and not snapshot["launcher"]["alive"]
        and not snapshot["live_native_processes"]
        and snapshot["arms"]
        and any(a["output"] == plan["source_output"] for a in snapshot["arms"])
        and all(a["terminal_cells"] == plan["cohort_size"]
                and a["audit_status"] == "passed" and not a["pending_requests"]
                for a in snapshot["arms"])
    )


def collect(config=None):
    config = config or read(CONFIG)
    run = Path(config["run"])
    now = time.time()
    launch = read(Path(config.get("launch_file", run / "launch.json")), {})
    launcher = process(launch.get("pid"), launch.get("pid_start_ticks"))
    completion = read(Path(config.get("completion_file", run / "launch_complete.json")))
    arms, issues, live = [], [], []
    activity = [Path(config.get("launch_file", run / "launch.json"))]
    for target in config["targets"]:
        name, output = target["name"], Path(target["output"])
        report = read(output / "report.json", {})
        status = read(output / "run.json", {})
        audit = read(output / "audit.json", {})
        activity.extend([output / "run.json", output / "audit.json"])
        for pattern in ("*/result.json", "*/evidence/state.json", "*/attempt_*/generation.json",
                        "*/attempt_*/request_started.json", "*/attempt_*/events.jsonl"):
            activity.extend((output / "cells").glob(pattern))
        conditions = report.get("conditions", [])
        complete = (report.get("planned_cells") == config["cohort_size"]
                    and report.get("terminal_cells") == config["cohort_size"]
                    and len(conditions) == 1 and conditions[0].get("complete") is True)
        row = {"name": name, "output": str(output), "run_status": status.get("status", "queued"),
               "terminal_cells": report.get("terminal_cells", 0), "complete": complete,
               "audit_status": audit.get("status"), "conditions": conditions,
               "active": report.get("active", []), "requests_started": 0,
               "terminal_attempts": 0, "pending_requests": []}
        for phase in ("run", "audit"):
            exit_path = run / f"{name}-{phase}.exit"
            if exit_path.exists():
                exit_code = int(exit_path.read_text().strip())
                row[f"{phase}_exit"] = exit_code
                if exit_code:
                    issues.append({"kind": f"{phase}_failed", "arm": name, "exit_code": exit_code,
                                   "evidence": str(exit_path)})
        if status.get("status") == "failed":
            issues.append({"kind": "run_failed", "arm": name, "evidence": str(output / "run.json")})
        if audit and audit.get("status") != "passed":
            issues.append({"kind": "audit_failed", "arm": name, "evidence": str(output / "audit.json")})
        for result_path in sorted((output / "cells").glob("*/result.json")):
            result = read(result_path)
            if result.get("status") != "complete":
                issues.append({"kind": "incomplete_cell", "arm": name, "name": result.get("name"),
                               "status": result.get("status"), "evidence": str(result_path)})
        for started in sorted((output / "cells").glob("*/attempt_*/request_started.json")):
            row["requests_started"] += 1
            attempt = started.parent
            marker = read(attempt / "attempt.json", {})
            if marker.get("status") == "terminal" or (attempt / "generation.json").exists():
                row["terminal_attempts"] += 1
                continue
            proc_record = read(attempt / "process.json", {})
            proc = process(proc_record.get("pid"), expected_path=attempt / "workspace")
            latest = max((p.stat().st_mtime for p in
                          [started, attempt / "events.jsonl", attempt.parent / "evidence/state.json"]
                          if p.exists()), default=started.stat().st_mtime)
            pending = {"path": str(attempt), "process": proc,
                       "quiet_seconds": round(now - latest)}
            row["pending_requests"].append(pending)
            if proc["alive"]:
                live.append({"arm": name, "attempt": str(attempt), **proc})
            elif now - latest > config.get("exit_grace_seconds", 180):
                issues.append({"kind": "request_without_terminal_and_process", "arm": name,
                               "attempt": str(attempt), "resampling_forbidden": True})
            if proc["alive"] and now - latest > config.get("quiet_warning_seconds", 3600):
                issues.append({"kind": "suspected_stall", "arm": name, "attempt": str(attempt),
                               "note": "Quiet evidence requires investigation, not automatic termination."})
        arms.append(row)
    ready = (bool(completion) and bool(arms) and not launcher["alive"]
             and all(a["complete"] and a["audit_status"] == "passed" for a in arms))
    if not launcher["alive"] and not completion:
        issues.append({"kind": "launcher_missing", "evidence": str(run / "launch.json")})
    if completion and not ready:
        issues.append({"kind": "pipeline_terminal_incomplete", "evidence": str(run / "launch_complete.json")})
    if len(live) > 5:
        issues.append({"kind": "worker_cap_exceeded", "workers": len(live)})
    latest = max((p.stat().st_mtime for p in activity if p.exists()), default=now)
    if launcher["alive"] and now - latest > config.get("quiet_warning_seconds", 3600):
        issues.append({"kind": "suspected_host_stall",
                       "note": "No new request, proof, terminal or run-state evidence; inspect before any action."})
    snapshot = {"observed_at": datetime.now(timezone.utc).isoformat(), "run": str(run),
            "phase": config["phase"], "launcher": launcher, "completion": completion,
            "arms": arms, "live_native_processes": live, "ready": ready, "issues": issues,
            "latest_activity_age_seconds": round(now - latest),
            "workflow_complete": read(ROOT / "workflow_complete.json"),
            "scope": "Read-only; invalid proof checks and controlled budget stops are normal."}
    plan = read(ROOT / "capacity_retry_plan.json")
    snapshot["capacity_retry_plan"] = plan
    snapshot["capacity_retry_due"] = capacity_retry_due(snapshot, plan, now)
    return snapshot


def events(snapshot):
    if snapshot.get("workflow_complete"):
        return [{"kind": "workflow_complete", "phase": snapshot["phase"]}]
    result = [{**issue, "phase": snapshot["phase"]} for issue in snapshot["issues"]]
    if snapshot.get("capacity_retry_due"):
        result.insert(0, {"kind": "capacity_retry_due", "phase": snapshot["phase"],
                          "retry_id": snapshot["capacity_retry_plan"]["retry_id"]})
    if snapshot["ready"] and not result:
        result.append({"kind": "cohorts_complete_and_audited", "phase": snapshot["phase"]})
    return result


def agy_review(folder, config, snapshot, detail):
    if (folder / "review.json").exists():
        return read(folder / "review.json")
    if (folder / "started.json").exists():
        return {"status": "indeterminate", "response": "AGY review already started without a terminal record; not resampled. Use the host observations."}
    prompt = (ROOT / "incident_prompt.txt").read_text()
    prompt += "\nEvent: " + json.dumps(detail) + "\nHost observation:\n" + json.dumps(snapshot, indent=2)
    save(folder / "observation.json", snapshot)
    (folder / "prompt.txt").write_text(prompt)
    argv = [config["python"], config["isolation"]]
    for path in config["writable"]:
        argv += ["--writable", path]
    for path in config["protected"]:
        argv += ["--protected", path]
    argv += ["--temporary-directory", str(ROOT / "runtime_tmp"), "--", config["agy"],
             "--agent", "code", "--model", config["model"], "--output-format", "stream-json",
             "--dangerously-skip-permissions", "--disable-slash-commands",
             "--log-file", str(folder / "agy.log"), "--add-dir", str(ROOT),
             "--add-dir", config["run"], "--print-timeout", "180s", "-p=" + prompt]
    conversation = read(ROOT / "conversation.json", {}).get("conversation_id")
    if conversation:
        argv += ["--conversation", conversation]
    env = {k: v for k, v in os.environ.items() if not k.startswith(("RCP_", "LEMEX_"))}
    env["AGY_CLI_DISABLE_AUTO_UPDATE"] = "true"
    save(folder / "started.json", {"at_epoch": time.time(), "model": config["model"]})
    with (folder / "events.jsonl").open("xb") as out, (folder / "stderr.log").open("xb") as err:
        proc = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err, start_new_session=True)
        try:
            code = proc.wait(timeout=240)
        except subprocess.TimeoutExpired:
            # Only this monitor's own isolated AGY process group, never a proof job.
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            code = None
    terminal = None
    for line in (folder / "events.jsonl").read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "result":
            terminal = row.get("result")
    result = terminal or {"status": "indeterminate", "response": "AGY returned no terminal review. Inspect the durable host observation directly."}
    result["cli_returncode"] = code
    save(folder / "review.json", result)
    if result.get("conversation_id"):
        save(ROOT / "conversation.json", {"conversation_id": result["conversation_id"]})
    return result


def notify(folder, config, snapshot, detail):
    if (folder / "queued.json").exists():
        return True
    if (folder / "queue_started.json").exists() and not (folder / "queue_failed.json").exists():
        return False  # Delivery might have happened; never send an unacknowledged duplicate.
    try:
        review = agy_review(folder, config, snapshot, detail)
    except Exception as exc:
        # Monitoring must still wake Codex when AGY itself is unavailable.
        review = {"status": "monitor_review_failed",
                  "response": f"AGY review failed: {type(exc).__name__}: {exc}. Use host evidence."}
        save(folder / "review_error.json", review)
    message = (f'AGY_MONITOR_ALERT [{folder.name}] {detail["kind"]}\n'
               f'AGY status: {review.get("status")}\n{str(review.get("response", ""))[:6000]}\n\n'
               f'Host event: {json.dumps(detail)}\nEvidence: {folder}\n'
               f'Run: {config["run"]}\nAuthorized follow-up: {ROOT / "FOLLOWUP.md"}\n'
               'The user explicitly authorized autonomous completion, safe failure recovery, and one conditional step-4 experiment. '
               'Read FOLLOWUP.md and current evidence, then act within that scope without asking again. '
               'Do not resample active or indeterminate requests or reset spent budgets. '
               'For a handshake event, acknowledge receipt only and leave the jobs running. '
               'If an investigation must defer to active work, persist its disposition in handled.json in this alert directory; '
               'the monitor rechecks actual health and emits later completion/failure events.')
    save(folder / "queue_started.json", {"at_epoch": time.time(), "message": message})
    failed = folder / "queue_failed.json"
    if failed.exists():
        failed.unlink()
    try:
        result = subprocess.run([config["codex"], "queue", "--thread", config["thread_id"],
                                 "--message", message], capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        save(folder / "queue_indeterminate.json", {"reason": "Queue timed out; delivery unknown."})
        return False
    record = {"returncode": result.returncode, "stdout": result.stdout,
              "stderr": result.stderr, "at_epoch": time.time()}
    success = result.returncode == 0 and "Queued message " in result.stdout
    save(folder / ("queued.json" if success else "queue_failed.json"), record)
    return success


def run_once():
    config = read(CONFIG)
    previous = read(ROOT / "state.json", {})
    try:
        snapshot = collect(config)
    except Exception as exc:
        snapshot = {"phase": config["phase"], "ready": False,
                    "issues": [{"kind": "observer_failed", "error": f"{type(exc).__name__}: {exc}"}]}
    save(ROOT / "latest.json", snapshot)
    seen = {}
    dispatched = False
    for detail in events(snapshot):
        key = hashlib.sha256(json.dumps(detail, sort_keys=True).encode()).hexdigest()[:20]
        old = previous.get("events", {}).get(key, {})
        count = old.get("confirmations", 0) + 1
        folder = ROOT / "alerts" / key
        notified = (folder / "queued.json").exists()
        immediate = detail["kind"] in {"run_failed", "audit_failed", "incomplete_cell",
                                        "cohorts_complete_and_audited", "workflow_complete",
                                        "capacity_retry_due"}
        if not notified and not dispatched and (immediate or count >= 2):
            notified = notify(folder, config, snapshot, detail)
            dispatched = True  # One bounded AGY review per service invocation.
        seen[key] = {"detail": detail, "confirmations": count, "notified": notified}
    save(ROOT / "state.json", {"checked_at_epoch": time.time(), "events": seen})
    if snapshot.get("workflow_complete"):
        (ROOT / "STOP").write_text("Authorized workflow completed.\n")
        subprocess.run(["systemctl", "--user", "stop", config["timer"]], check=False, timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe", action="store_true")
    parser.add_argument("--handshake", action="store_true")
    args = parser.parse_args()
    if args.observe:
        print(json.dumps(collect(), indent=2))
        return
    with (ROOT / ".watch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if (ROOT / "STOP").exists():
            return
        if args.handshake:
            config = read(CONFIG)
            delivered = notify(ROOT / "handoff_review", config, collect(config),
                               {"kind": "monitor_handshake", "phase": config["phase"]})
            print(json.dumps({"handshake_queued": delivered}))
        else:
            run_once()


if __name__ == "__main__":
    main()
