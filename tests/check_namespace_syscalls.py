"""Real Linux regression: deny namespace escapes and retain fork/threads/exec.

Run in a disposable child, never in the model server or a production controller.
The test is also valid when a container mounts /proc/sys read-only.
"""

import ctypes
import errno
import json
import os
import platform
import signal
import subprocess
import sys
import threading

from proof_eval.providers.readonly_mounts import deny_namespace_creation


def main():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise SystemExit("This check requires Linux x86-64")
    deny_namespace_creation()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    checks = {}
    for flag in (0x10000000, 0x00020000, 0x40000000):
        assert libc.unshare(flag) == -1 and ctypes.get_errno() == errno.EPERM
    checks["unshare_namespace_creation_denied"] = True
    assert libc.setns(-1, 0) == -1 and ctypes.get_errno() == errno.EPERM
    checks["setns_denied_before_fd_lookup"] = True
    for flag in (0x10000000, 0x00020000, 0x40000000):
        child = libc.syscall(56, flag | signal.SIGCHLD, 0, 0, 0, 0)
        if child == 0:
            os._exit(97)
        if child > 0:
            os.waitpid(child, 0)
        assert child == -1 and ctypes.get_errno() == errno.EPERM
    checks["clone_namespace_creation_denied"] = True
    assert libc.syscall(435, 0, 0) == -1 and ctypes.get_errno() == errno.ENOSYS
    assert libc.syscall(0x40000000 | 56, 0, 0, 0, 0, 0) == -1
    assert ctypes.get_errno() == errno.ENOSYS
    checks["clone3_and_x32_cannot_bypass_filter"] = True
    ran = []
    thread = threading.Thread(target=lambda: ran.append(True))
    thread.start()
    thread.join(timeout=5)
    assert ran == [True]
    checks["ordinary_threads_work"] = True
    child = os.fork()
    if child == 0:
        os._exit(0)
    assert os.waitpid(child, 0)[1] == 0
    checks["ordinary_fork_works"] = True
    result = subprocess.run(
        [sys.executable, "-c", "import threading; t=threading.Thread(target=lambda:None);t.start();t.join();print('inherited-ok')"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0 and result.stdout.strip() == "inherited-ok"
    checks["exec_and_inherited_threads_work"] = True
    print(json.dumps({"status": "passed", "checks": checks, "model_calls": 0, "Lean_calls": 0}))


if __name__ == "__main__":
    main()
