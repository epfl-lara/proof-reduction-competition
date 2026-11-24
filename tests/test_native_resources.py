"""The native allocation guard fails closed and leaves host limits untouched."""

import json
import resource
import subprocess
import sys

import pytest

from proof_eval.providers import native_resources as guard


def test_changed_guard_is_rejected_before_launch(tmp_path):
    identity = guard.identity()
    identity["data_bytes"] += 1
    with pytest.raises(ValueError, match="policy or launcher changed"):
        guard.wrap([sys.executable, "-c", "pass"], tmp_path / "receipt.json", identity)


@pytest.mark.skipif(
    sys.platform != "linux", reason="requires real Linux resource limits"
)
def test_inherited_hard_limits_reject_runaway_child_but_preserve_parent(tmp_path):
    parent_limits = [
        resource.getrlimit(k) for k in (resource.RLIMIT_DATA, resource.RLIMIT_AS)
    ]
    child = r"""
import json,resource
limits = {name: list(resource.getrlimit(getattr(resource,name))) for name in ("RLIMIT_DATA","RLIMIT_AS")}
assert limits["RLIMIT_DATA"] == [4*1024**3]*2
assert limits["RLIMIT_AS"] == [32*1024**3]*2
assert bytearray(2*1024**2)[-1] == 0
try:
    resource.setrlimit(resource.RLIMIT_DATA,(8*1024**3,8*1024**3))
except (ValueError,OSError):
    pass
else:
    raise AssertionError("child raised hard limit")
try:
    bytearray(5*1024**3)
except MemoryError:
    print(json.dumps({"normal_allocation_passed":True,"over_limit_allocation_rejected":True,"limits":limits}))
else:
    raise AssertionError("oversized allocation escaped guard")
"""
    parent = "import subprocess,sys; subprocess.run([sys.executable,'-c',sys.argv[1]],check=True)"
    receipt = tmp_path / "receipt.json"
    result = subprocess.run(
        guard.wrap([sys.executable, "-c", parent, child], receipt, guard.identity()),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["over_limit_allocation_rejected"] is True
    assert parent_limits == [
        resource.getrlimit(k) for k in (resource.RLIMIT_DATA, resource.RLIMIT_AS)
    ]
    assert guard.evidence(receipt, guard.identity())["status"] == "verified"
    with pytest.raises(ValueError, match="reuse"):
        guard.wrap([sys.executable, "-c", "pass"], receipt, guard.identity())
