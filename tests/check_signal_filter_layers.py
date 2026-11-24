"""Exercise the namespace broker's filter composition against an owned peer.

Only the direct seccomp syscall can create a notification listener. It remains
denied. prctl-only filters may restrict a call or cause ENOSYS, never continue
an outside signal past the original broker. Run in a disposable guarded child.
"""

import ctypes
import errno
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from proof_eval.providers.readonly_mounts import deny_namespace_creation


class Instruction(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint),
    ]


class Program(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(Instruction))]


def child(peer):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    deny_namespace_creation()
    checks = {"namespace_filter_installed_inside_signal_guard": True}
    allow = (Instruction * 1)(Instruction(0x06, 0, 0, 0x7FFF0000))
    program = Program(1, allow)
    assert libc.syscall(317, 1, 8, ctypes.byref(program)) == -1
    assert ctypes.get_errno() == errno.EPERM
    checks["replacement_notification_listener_denied"] = True
    assert libc.prctl(22, 2, ctypes.byref(program), 0, 0) == 0
    try:
        os.kill(peer, 0)
    except OSError as error:
        assert error.errno == errno.EPERM
    else:
        raise AssertionError("Additive ALLOW bypassed the original signal broker")
    checks["additive_allow_cannot_relax_outside_signal_denial"] = True
    rows = [(0x20, 0, 0, 0), (0x15, 0, 1, 62),
            (0x06, 0, 0, 0x7FC00000), (0x06, 0, 0, 0x7FFF0000)]
    notify = (Instruction * len(rows))(*(Instruction(*x) for x in rows))
    program = Program(len(rows), notify)
    assert libc.prctl(22, 2, ctypes.byref(program), 0, 0) == 0
    try:
        os.kill(peer, signal.SIGTERM)
    except OSError as error:
        assert error.errno == errno.ENOSYS
    else:
        raise AssertionError("A listenerless filter delivered an outside signal")
    checks["later_listenerless_notify_cannot_deliver_outside_signal"] = True
    assert libc.unshare(0x10000000) == -1 and ctypes.get_errno() == errno.EPERM
    checks["later_filter_cannot_relax_namespace_denial"] = True
    print(json.dumps({"status": "passed", "checks": checks}))


def main(root, binary):
    root.mkdir(parents=True, exist_ok=False)
    peer = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
    try:
        argv = [str(binary), "--audit", str(root / "signals.jsonl"), "--",
                sys.executable, str(Path(__file__).resolve()), "--child", str(peer.pid)]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
        assert peer.poll() is None
        report = json.loads(result.stdout)
        report.update(outside_owned_peer_unharmed=True, model_calls=0, Lean_calls=0)
        (root / "result.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
    finally:
        peer.terminate()
        peer.wait(timeout=5)


if __name__ == "__main__":
    if sys.argv[1] == "--child":
        child(int(sys.argv[2]))
    else:
        main(Path(sys.argv[1]), Path(sys.argv[2]))
