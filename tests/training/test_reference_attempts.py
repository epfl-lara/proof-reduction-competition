"""A terminal wall timeout is recoverable; unknown or semantic work is not."""

from copy import deepcopy

import pytest

from proof_eval.evidence.immutable import read
from proof_eval.training.reference_attempts import prepare_reference_attempts


class References:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def prepare_reference(self, name, *, versions):
        self.calls.append((name, list(versions)))
        result = next(self.results)
        if isinstance(result, BaseException):
            raise result
        return {"name": name, "versions": deepcopy(result)}


ROW = {"name": "original", "version_info": [{"v1": "a"}, {"v2": "b"}]}


def test_only_the_finished_timed_out_version_is_retried(tmp_path):
    good = {"status": "prepared", "measured_at": "first", "heartbeats": 100}
    evaluator = References(
        [
            {"v1": good, "v2": {"status": "timeout"}},
            {"v2": {"status": "prepared", "heartbeats": 200}},
        ]
    )
    result = prepare_reference_attempts(evaluator, ROW, tmp_path, 1)
    assert result["status"] == "prepared"
    assert evaluator.calls == [("original", ["v1", "v2"]), ("original", ["v2"])]
    assert result["versions"]["v1"] == good
    assert read(tmp_path / "00.json")["result"]["versions"]["v2"]["status"] == "timeout"
    assert (
        read(tmp_path / "01.json")["result"]["versions"]["v2"]["status"] == "prepared"
    )
    assert (
        read(tmp_path / "00.json")["finished_epoch"]
        <= read(tmp_path / "01.json")["started_epoch"]
    )


@pytest.mark.parametrize("status", ["failed", "unavailable", "interrupted"])
def test_other_failures_cannot_trigger_a_retry(tmp_path, status):
    evaluator = References([{"v1": {"status": "timeout"}, "v2": {"status": status}}])
    assert (
        prepare_reference_attempts(evaluator, ROW, tmp_path, 1)["status"]
        == "incomplete"
    )
    assert len(evaluator.calls) == 1


def test_a_second_timeout_is_terminal_and_preserved(tmp_path):
    result = {"v1": {"status": "timeout"}, "v2": {"status": "timeout"}}
    evaluator = References([result, result])
    assert (
        prepare_reference_attempts(evaluator, ROW, tmp_path, 1)["status"]
        == "incomplete"
    )
    assert len(evaluator.calls) == 2
    assert not (tmp_path / "02-started.json").exists()


def test_unknown_first_attempt_is_never_replayed(tmp_path):
    evaluator = References([RuntimeError("process custody unavailable")])
    with pytest.raises(RuntimeError, match="custody"):
        prepare_reference_attempts(evaluator, ROW, tmp_path, 1)
    with pytest.raises(RuntimeError, match="indeterminate"):
        prepare_reference_attempts(evaluator, ROW, tmp_path, 1)
    assert len(evaluator.calls) == 1
    assert not (tmp_path / "00.json").exists()


def test_default_zero_retries_keeps_first_timeout(tmp_path):
    evaluator = References(
        [{"v1": {"status": "timeout"}, "v2": {"status": "prepared"}}]
    )
    assert (
        prepare_reference_attempts(evaluator, ROW, tmp_path, 0)["status"]
        == "incomplete"
    )
    assert len(evaluator.calls) == 1


@pytest.mark.parametrize("count", [True, -1, 2])
def test_retry_budget_is_checked_before_any_measurement(tmp_path, count):
    evaluator = References([])
    with pytest.raises(ValueError, match="one timeout retry"):
        prepare_reference_attempts(evaluator, ROW, tmp_path, count)
    assert not evaluator.calls
