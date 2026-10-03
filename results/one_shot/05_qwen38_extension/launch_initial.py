"""One-off launch record: wait for the original pool, then run the gated extension."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from run_with_rcp_limit import legacy_initial_alive

OUT = ROOT / "results/one_shot/05_qwen38_extension"
LEGACY = ROOT / "results/one_shot/01_context_ablation"
COMMAND = [sys.executable, "src/run_with_rcp_limit.py",
    "--legacy-initial", str(LEGACY),
    "--legacy-repair", str(ROOT / "results/one_shot/03_repaired_context_ablation"),
    "--gate", str(ROOT / ".proof-eval/rcp-admission"),
    "--log-directory", str(OUT / "admission"), "--", "src/run_one_shot.py",
    "--output", str(OUT / "01_context_ablation"),
    "--models", "Qwen/Qwen3.8-27B",
    "--arms", "plain", "cards", "goals", "cards_goals", "cards_goals_costs",
    "--max-tokens", "32768", "--timeout", "1800", "--per-model", "2"]


def main():
    record_path = OUT / "initial_launch.json"
    if record_path.exists():
        raise RuntimeError("Launch already recorded; inspect it before any manual resume")
    record = {"status": "waiting_for_original_initial_pool", "command": COMMAND,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "launcher_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}

    def save():
        temporary = record_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(record_path)

    save()
    while True:
        original = json.loads((LEGACY / "run.json").read_text())
        if original.get("status") == "finished" and not legacy_initial_alive(LEGACY):
            break
        time.sleep(5)
    record.update(status="running", started_at=datetime.now(timezone.utc).isoformat())
    save()
    with (OUT / "01_context_ablation/execution.log").open("a") as log:
        child = subprocess.Popen(COMMAND, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        record["pid"] = child.pid
        save()
        print(json.dumps({"launched_pid": child.pid, "at": record["started_at"]}), flush=True)
        code = child.wait()
    record.update(status="exited", returncode=code, finished_at=datetime.now(timezone.utc).isoformat())
    save()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
