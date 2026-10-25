"""Root runtime threads can cancel owned children while peer signals stay denied."""

import json
import subprocess
import sys

from proof_eval.providers.processes import owned_command


def test_native_root_thread_owned_cancellation_and_peer_denial(
    tmp_path, signal_identity
):
    peer = subprocess.Popen(["sleep", "25"], start_new_session=True)
    script = tmp_path / "thread.py"
    script.write_text(
        "import errno,json,os,signal,subprocess,sys,threading\n"
        "child=subprocess.Popen(['sleep','20'],start_new_session=True)\n"
        "result={'pid':os.getpid()}\n"
        "def run():\n"
        " result['tid']=threading.get_native_id()\n"
        " os.kill(child.pid,0);os.killpg(child.pid,0)\n"
        " try:os.kill(int(sys.argv[1]),0)\n"
        " except OSError as e:assert e.errno==errno.EPERM\n"
        " else:raise AssertionError('peer signal crossed boundary')\n"
        " os.killpg(child.pid,signal.SIGTERM)\n"
        " result['cancelled']=True\n"
        "thread=threading.Thread(target=run);thread.start();thread.join(5)\n"
        "assert not thread.is_alive() and result.get('cancelled')\n"
        "assert child.wait(timeout=3)==-signal.SIGTERM\n"
        "print(json.dumps(result))\n"
    )
    audit = tmp_path / "signals.jsonl"
    ownership = tmp_path / "ownership.json"
    argv = [
        signal_identity["binary"],
        "--audit",
        str(audit),
        "--",
        sys.executable,
        str(script),
        str(peer.pid),
    ]
    try:
        result = subprocess.run(
            owned_command(argv, ownership),
            capture_output=True,
            text=True,
            timeout=12,
            start_new_session=True,
        )
        assert result.returncode == 0, result.stderr
        value = json.loads(result.stdout)
        assert value["pid"] != value["tid"]
        rows = [json.loads(line) for line in audit.read_text().splitlines()]
        calls = [row for row in rows if row["caller"] == value["tid"]]
        assert len(calls) == 4
        assert all(row["caller_tgid"] == value["pid"] for row in calls)
        assert [row["error"] for row in calls] == [0, 0, 1, 0]
        assert json.loads(ownership.read_text())["cleanup"]["complete"]
        assert peer.poll() is None
    finally:
        if peer.poll() is None:
            peer.terminate()
        peer.wait(timeout=3)
