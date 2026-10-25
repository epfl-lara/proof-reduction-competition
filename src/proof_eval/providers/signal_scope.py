"""Pinned signal ownership for local native clients; no unrestricted fallback.

The trusted host supervisor owns this broker. Its filtered child enters the
existing file boundary before running the native CLI. Historical evidence can
still be read without executing a binary or installing a filter.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

POLICY = "descendant-signals-v1"
SOURCE_SHA256 = "98e2347e2e2f4b06ef34fa5e9871136387c2364ed4a1e504b68b2439d5ee0425"
BINARY_SHA256 = "883664ba991947d52c44217c6f5a2f97ea3aa40ecc24c767ae41d662f0284afa"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _process(pid: int) -> dict:
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return {"pid": pid, "start_ticks": fields[19]}


def _exclusive(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump(value, out, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("Signal scope: " + message)


def configured_identity() -> dict:
    """Require the exact independently validated Linux binary before admission."""
    value = os.environ.get("PROOF_SIGNAL_SCOPE_BINARY")
    _require(bool(value), "set PROOF_SIGNAL_SCOPE_BINARY to the validated guard")
    binary = Path(value).resolve(strict=True)
    source = Path(__file__).with_suffix(".c").resolve(strict=True)
    identity = {
        "policy": POLICY,
        "binary": str(binary),
        "binary_sha256": _sha(binary),
        "source": str(source),
        "source_sha256": _sha(source),
        "launcher": str(Path(__file__).resolve()),
        "launcher_sha256": _sha(Path(__file__)),
    }
    validate_identity(identity)
    return identity


def validate_identity(identity: dict, *, live: bool = True) -> None:
    """Offline pins do not require a live historical binary to remain installed."""
    _require(
        isinstance(identity, dict)
        and identity.get("policy") == POLICY
        and identity.get("binary_sha256") == BINARY_SHA256
        and identity.get("source_sha256") == SOURCE_SHA256
        and all(
            isinstance(identity.get(k), str) and Path(identity[k]).is_absolute()
            for k in ("binary", "source", "launcher")
        )
        and isinstance(identity.get("launcher_sha256"), str)
        and len(identity["launcher_sha256"]) == 64,
        "missing or unvalidated executable/source identity",
    )
    if not live:
        return
    _require(sys.platform == "linux", "Linux signal boundary required")
    for key in ("binary", "source", "launcher"):
        path = Path(identity[key])
        info = path.lstat()
        _require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and not info.st_mode & 0o022
            and _sha(path) == identity[key + "_sha256"],
            "changed or unprotected " + key,
        )
    _require(os.access(identity["binary"], os.X_OK), "guard is not executable")


def wrap(
    argv: list[str],
    folder: Path,
    identity: dict,
    writable: tuple[Path, ...],
) -> list[str]:
    """Enter the signal filter before Landlock, inside owned_command supervision."""
    validate_identity(identity)
    host_paths = [
        folder,
        *(Path(identity[k]) for k in ("binary", "source", "launcher")),
    ]
    for path in host_paths:
        _require(
            not any(path.resolve().is_relative_to(p.resolve()) for p in writable),
            "guard and host evidence must be outside model-writable paths",
        )
    for name in ("signal_scope_ready.json", "signals.jsonl"):
        _require(not (folder / name).exists(), "refusing to reuse signal evidence")
    return [
        identity["binary"],
        "--audit",
        str(folder / "signals.jsonl"),
        "--",
        sys.executable,
        identity["launcher"],
        "--enter",
        str(folder / "signal_scope_ready.json"),
        "--",
        *argv,
    ]


def _enter(ready: Path, command: list[str]) -> None:
    """Trusted pre-Landlock entry: prove a live peer denial, then exec once."""
    broker = os.getppid()
    parent = Path(f"/proc/{broker}/stat").read_text().rsplit(")", 1)[1].split()
    supervisor = int(parent[1])
    try:
        os.kill(broker, 0)  # A harmless probe of this launch's own broker only.
    except OSError as error:
        if error.errno != errno.EPERM:
            raise
    else:
        raise RuntimeError("Signal scope did not deny a signal to its broker")
    status = Path("/proc/self/status").read_text().splitlines()
    _require("Seccomp:\t2" in status, "entry is not filtered")
    _exclusive(
        ready,
        {
            "policy": POLICY,
            "root": _process(os.getpid()),
            "broker": _process(broker),
            "supervisor": _process(supervisor),
            "parent_signal_denied": True,
            "command": command,
        },
    )
    os.execvp(command[0], command)


def preflight(
    argv: list[str], folder: Path, identity: dict, writable: tuple[Path, ...], env: dict
) -> dict:
    """Check the real kernel/file boundary with no model before a start marker."""
    from proof_eval.evidence.io import write_json

    from .processes import owned_command, stop_tree
    from .processes import owned_identity as process_identity

    folder.mkdir(mode=0o700, exist_ok=False)
    guarded = wrap(argv, folder, identity, writable)
    child = subprocess.Popen(
        owned_command(guarded, folder / "process_ownership.json"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    process = process_identity(child.pid)
    try:
        stdout, stderr = child.communicate(timeout=10)
    except subprocess.TimeoutExpired as error:
        write_json(folder / "timeout_cleanup.json", stop_tree(child.pid))
        child.wait(timeout=5)
        raise ValueError(
            "Signal scope: kernel setup probe exceeded its bound"
        ) from error
    (folder / "stdout.log").write_bytes(stdout)
    (folder / "stderr.log").write_bytes(stderr)
    _require(
        child.returncode == 0,
        "kernel/file setup probe failed: " + stderr.decode(errors="replace")[-800:],
    )
    ownership = json.loads((folder / "process_ownership.json").read_text())
    _require(
        ownership.get("supervisor") == process
        and ownership.get("cleanup", {}).get("complete") is True,
        "setup probe was not fully reaped",
    )
    _require(
        ownership.get("native_returncode") == 0,
        "file-boundary probe exited "
        + str(ownership.get("native_returncode"))
        + ": "
        + stderr.decode(errors="replace")[-800:],
    )
    result = {
        "status": "verified",
        **evidence(folder, identity, argv, process, ownership),
        "ownership_sha256": _sha(folder / "process_ownership.json"),
    }
    _exclusive(folder / "result.json", result)
    return result


def evidence(
    folder: Path,
    identity: dict,
    command: list[str],
    supervisor: dict,
    ownership: dict | None,
    *,
    allow_partial: bool = False,
) -> dict:
    """Bind readiness and the durable kernel decisions to this exact host owner."""
    validate_identity(identity, live=False)
    ready_path, audit = folder / "signal_scope_ready.json", folder / "signals.jsonl"
    _require(ready_path.is_file() and audit.is_file(), "missing setup/audit evidence")
    ready = json.loads(ready_path.read_text())
    _require(
        ready.get("policy") == POLICY
        and ready.get("parent_signal_denied") is True
        and ready.get("supervisor")
        == {k: supervisor.get(k) for k in ("pid", "start_ticks")}
        and ready.get("command") == command,
        "readiness does not match the command and host owner",
    )
    for key in ("root", "broker", "supervisor"):
        proc = ready.get(key, {})
        _require(
            type(proc.get("pid")) is int
            and proc["pid"] > 0
            and isinstance(proc.get("start_ticks"), str)
            and proc["start_ticks"].isdigit(),
            "invalid setup process identity",
        )
    _require(
        len({ready[k]["pid"] for k in ("root", "broker", "supervisor")}) == 3,
        "setup process identities overlap",
    )
    if ownership is not None:
        _require(ready["broker"] == ownership.get("native"), "broker ownership changed")
    raw = audit.read_bytes()
    decisions = []
    partial = False
    for n, line in enumerate(raw.splitlines()):
        try:
            decision = json.loads(line)
        except (ValueError, UnicodeError):
            _require(
                allow_partial
                and n == len(raw.splitlines()) - 1
                and not raw.endswith(b"\n"),
                "malformed kernel decision log",
            )
            partial = True
            break
        _require(
            isinstance(decision, dict)
            and all(
                type(decision.get(k)) is int
                for k in ("id", "caller", "syscall", "target_arg", "error")
            )
            and type(decision.get("continued")) is bool,
            "malformed kernel decision",
        )
        decisions.append(decision)
    _require(
        any(
            row["caller"] == ready["root"]["pid"]
            and row["syscall"] == 62
            and row["target_arg"] == ready["broker"]["pid"]
            and row["error"] == errno.EPERM
            and row["continued"] is False
            for row in decisions
        ),
        "missing persisted peer-denial setup probe",
    )
    return {
        "policy": POLICY,
        "identity": identity,
        "ready": ready,
        "ready_sha256": _sha(ready_path),
        "audit_sha256": hashlib.sha256(raw).hexdigest(),
        "audit_bytes": len(raw),
        "decisions": len(decisions),
        "denials": sum(row["error"] != 0 for row in decisions),
        "partial_final_decision": partial,
    }


def audit_generation(folder: Path, generation: dict) -> None:
    """Validate new saved signal evidence without changing historical contracts."""
    request_path = folder / "request.json"
    request = json.loads(request_path.read_text()) if request_path.exists() else {}
    command_path = folder / "command.json"
    command = json.loads(command_path.read_text()) if command_path.exists() else {}
    identity = request.get("cli", {}).get("signal_scope")
    saved = generation.get("signal_scope")
    if identity is None and saved is None and "signal_scope" not in command:
        return
    _require(request.get("provider") == "lemex-local", "unexpected provider")
    validate_identity(identity, live=False)
    _require(command.get("signal_scope") == identity, "command identity changed")
    _require(
        command.get("policy") == "host_ledger_readonly_sources_signal_scope_v1"
        and isinstance(command.get("isolated_argv"), list),
        "missing guarded command contract",
    )
    inner = command["isolated_argv"]
    argv = command.get("argv", [])
    _require(
        len(argv) >= 10
        and argv[:4]
        == [identity["binary"], "--audit", str(folder / "signals.jsonl"), "--"]
        and argv[5:9]
        == [
            identity["launcher"],
            "--enter",
            str(folder / "signal_scope_ready.json"),
            "--",
        ]
        and argv[9:] == inner,
        "command bypasses the pinned signal boundary",
    )
    probe = folder / "signal_scope_preflight"
    probe_result = json.loads((probe / "result.json").read_text())
    probe_owner = json.loads((probe / "process_ownership.json").read_text())
    _require(
        command.get("signal_scope_preflight") == probe_result
        and probe_result
        == {
            "status": "verified",
            **evidence(
                probe,
                identity,
                probe_result["ready"]["command"],
                probe_owner["supervisor"],
                probe_owner,
            ),
            "ownership_sha256": _sha(probe / "process_ownership.json"),
        }
        and probe_owner.get("native_returncode") == 0
        and probe_owner.get("cleanup", {}).get("complete") is True,
        "preflight evidence changed",
    )
    process = json.loads((folder / "process.json").read_text())
    _require(process.get("signal_scope") == identity, "process identity changed")
    if not saved or saved.get("status") != "verified":
        _require(
            generation.get("status") not in ("received", "budget_exhausted")
            and generation.get("owned_client_eof") is None,
            "unverified signal boundary cannot authorize completion or recovery",
        )
        return
    actual = evidence(
        folder,
        identity,
        inner,
        process,
        generation.get("process_ownership"),
        allow_partial=generation.get("status") == "budget_exhausted",
    )
    _require(saved == {"status": "verified", **actual}, "saved signal evidence changed")
    _require(
        json.loads((folder / "signal_scope.json").read_text()) == saved,
        "signal receipt differs from generation",
    )


if __name__ == "__main__":
    if len(sys.argv) < 5 or sys.argv[1] != "--enter" or sys.argv[3] != "--":
        raise SystemExit("Expected --enter NEW_READY_FILE -- ISOLATED_COMMAND")
    _enter(Path(sys.argv[2]), sys.argv[4:])
