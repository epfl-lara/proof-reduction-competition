"""Correctness-only repair stopping, request isolation, budgets, and resume."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from run_validity_repair import repair_cell


MODEL = "Qwen/Qwen3.5-397B-A17B"
INCUMBENT = "theorem p : True := by trivial"
BAD = "theorem p : True := by exact False.elim ?_"
REPAIRED = "theorem p : True := by exact True.intro"


def evaluation(*, valid=False, score=0, secondary_valid=None, status=None):
    if secondary_valid is None:
        secondary_valid = valid
    return {
        "status": status or ("passed" if valid else "failed"),
        "primary_version": "v1", "scores": {"combined_pct": score},
        "performance_sentinel": "EVALUATION_PERFORMANCE_SENTINEL",
        "per_version": {
            version: {"status": "passed" if passed else "failed", "passed": passed,
                "heartbeats": 987654321, "reference": {"heartbeats": 123456789},
                "diagnostics": [] if passed else [
                    {"severity": "error", "data": "unsolved goals\n⊢ True"},
                    {"severity": "information", "data": "PERFORMANCE_DIAGNOSTIC_SENTINEL"},
                    {"severity": "error", "message": "Expected exactly one verified target heartbeat marker"}]}
            for version, passed in (("v1", valid), ("v2", secondary_valid))},
        "diagnostics": [],
    }


def fixture_data():
    pack = {"name": "p", "row": {"name": "p", "source": "fixture", "statement": "theorem p : True",
                                  "version_info": [{"v1": "one"}, {"v2": "two"}]},
            "proof": INCUMBENT, "incumbent": evaluation(valid=True, score=60),
            "source_context": "SAFE_SOURCE_CONTEXT", "context": {"costs": "COST_CONTEXT_SENTINEL"}}
    request = {"model": MODEL, "temperature": 0.3, "reasoning": True, "reasoning_effort": "high",
               "max_tokens": 32768, "messages": [{"role": "user", "content": "INITIAL_OPTIMIZATION_PROMPT_SENTINEL"}]}
    base = {"name": "p", "source": "fixture", "model": MODEL, "arm": "cards_goals_costs", "request_sha256": "base",
            "extracted_proof": BAD, "generation": {"status": "received", "finish_reason": "stop", "content": BAD},
            "evaluation": evaluation()}
    return base, request, pack


class FakeClient:
    api_key = "TEST_SECRET"

    def __init__(self, contents):
        self.contents = iter(contents)
        self.requests = []

    def create_chat_completion(self, **request):
        self.requests.append(deepcopy(request))
        content = next(self.contents)
        if isinstance(content, Exception):
            raise content
        if isinstance(content, tuple):
            content, finish = content
        else:
            finish = "stop"
        return SimpleNamespace(content=content, finish_reason=finish, usage={"completion_tokens": 10},
                               model=MODEL, raw={"id": "response"}, reasoning_content="PRIVATE_REASONING_MUST_NOT_BE_SAVED")


class FakeEvaluator:
    def __init__(self, evaluations):
        self.evaluations = iter(evaluations)
        self.calls = []

    def evaluate(self, name, code, *, versions):
        self.calls.append((name, code, versions))
        return next(self.evaluations)


def run_cell(tmp_path, base=None, request=None, pack=None, client=None, evaluator=None, **kwargs):
    defaults = fixture_data()
    return repair_cell(base_record=base or defaults[0], base_request=request or defaults[1],
                       pack=pack or defaults[2], folder=tmp_path,
                       client=client or FakeClient([]), evaluator=evaluator or FakeEvaluator([]), **kwargs)


def test_lower_scoring_valid_repair_stops_without_any_optimization_feedback(tmp_path):
    base, request, pack = fixture_data()
    originals = deepcopy((base, request, pack))
    client = FakeClient([REPAIRED])
    evaluator = FakeEvaluator([evaluation(valid=True, score=-100)])
    result = run_cell(tmp_path, base, request, pack, client, evaluator)
    assert result["final_valid"]
    assert result["outcome"] == "repaired_valid"
    assert result["round_count"] == len(client.requests) == 1
    assert not result["accepted"]
    assert result["final_proof"] == REPAIRED
    assert result["selected_proof"] == INCUMBENT
    assert evaluator.calls == [("p", REPAIRED, "all")]
    prompt = json.dumps(client.requests[0]["messages"])
    for forbidden in ("EVALUATION_PERFORMANCE_SENTINEL", "PERFORMANCE_DIAGNOSTIC_SENTINEL",
                      "COST_CONTEXT_SENTINEL", "INITIAL_OPTIMIZATION_PROMPT_SENTINEL", "987654321", "123456789"):
        assert forbidden not in prompt
    assert "unsolved goals" in prompt
    assert (base, request, pack) == originals
    assert all("PRIVATE_REASONING_MUST_NOT_BE_SAVED" not in path.read_text() for path in tmp_path.rglob("*.json"))
    resumed = run_cell(tmp_path, base, request, pack, FakeClient([]), FakeEvaluator([]))
    assert resumed == result


def test_passed_primary_does_not_stop_until_all_required_versions_pass(tmp_path):
    base, request, pack = fixture_data()
    base["evaluation"] = evaluation(valid=True, secondary_valid=False, score=99)
    client = FakeClient([REPAIRED, INCUMBENT])
    evaluator = FakeEvaluator([evaluation(valid=True, secondary_valid=False, score=99), evaluation(valid=True, score=60)])
    result = run_cell(tmp_path, base, request, pack, client, evaluator)
    assert result["initial_valid"] is False
    assert result["round_count"] == 2
    assert result["final_valid"] and result["returned_incumbent"]
    assert not result["accepted"]
    for request in client.requests:
        payload = json.loads(request["messages"][1]["content"])
        assert payload["required_versions"] == ["v1", "v2"]
        feedback = payload["validity_feedback"]
        assert feedback["versions"][0]["passed"] is True
        assert feedback["versions"][1]["passed"] is False


def test_already_valid_or_empty_output_consumes_no_repair_calls(tmp_path):
    base, request, pack = fixture_data()
    base["evaluation"] = evaluation(valid=True, score=50)
    result = run_cell(tmp_path / "valid", base, request, pack)
    assert result["initial_kind"] == result["outcome"] == "already_valid"
    assert result["round_count"] == 0
    base.pop("extracted_proof")
    base["generation"] = {"status": "received", "content": "", "finish_reason": "length"}
    base["evaluation"] = {"status": "invalid", "per_version": {}, "diagnostics": ["generation_truncated"]}
    result = run_cell(tmp_path / "empty", base, request, pack)
    assert result["initial_kind"] == result["outcome"] == "no_candidate"
    assert result["round_count"] == 0


def test_nonempty_truncation_is_output_recovery_not_compiler_repair(tmp_path):
    base, request, pack = fixture_data()
    base.pop("extracted_proof")
    base["generation"] = {"status": "received", "content": "theorem p : True := by", "finish_reason": "length"}
    base["evaluation"] = {"status": "invalid", "per_version": {}, "diagnostics": ["generation_truncated"]}
    client = FakeClient([REPAIRED])
    result = run_cell(tmp_path, base, request, pack, client, FakeEvaluator([evaluation(valid=True, score=20)]))
    assert result["initial_kind"] == "output_recovery"
    assert result["final_valid"]
    prompt = json.loads(client.requests[0]["messages"][1]["content"])
    assert prompt["current_proposal"] == base["generation"]["content"]
    assert "complete declaration" in prompt["validity_feedback"]["errors"][0]


def test_three_failed_rounds_exhaust_budget_and_each_uses_previous_proposal(tmp_path):
    codes = [BAD + "\n-- attempt " + str(i) for i in range(3)]
    client = FakeClient(codes)
    evaluator = FakeEvaluator([evaluation(), evaluation(), evaluation()])
    result = run_cell(tmp_path, client=client, evaluator=evaluator)
    assert result["round_count"] == 3
    assert result["outcome"] == "repair_budget_exhausted"
    assert not result["final_valid"]
    for index, request in enumerate(client.requests):
        payload = json.loads(request["messages"][1]["content"])
        assert payload["current_proposal"] == (BAD if index == 0 else codes[index - 1])


def test_interrupted_started_request_and_saved_round_are_never_resampled(tmp_path):
    folder = tmp_path / "marker"
    first = folder / "rounds" / "01"
    first.mkdir(parents=True)
    (first / "request_started.json").write_text("{}")
    result = run_cell(folder)
    assert result["outcome"] == "unavailable"
    assert result["round_count"] == 1
    assert result["rounds"][0]["generation_status"] == "indeterminate"
    completed = tmp_path / "saved_round"
    result = run_cell(completed, client=FakeClient([REPAIRED]), evaluator=FakeEvaluator([evaluation(valid=True, score=40)]))
    (completed / "result.json").unlink()
    resumed = run_cell(completed)
    assert resumed == result


def test_transport_failures_stop_and_redact_credentials(tmp_path):
    result = run_cell(tmp_path, client=FakeClient([RuntimeError("provider said TEST_SECRET")]))
    assert result["outcome"] == "unavailable"
    assert result["round_count"] == 1
    assert "TEST_SECRET" not in (tmp_path / "rounds/01/generation.json").read_text()


@pytest.mark.parametrize("kwargs", [{"max_rounds": 4}, {"max_rounds": -1}, {"max_rounds": True},
                                   {"max_rounds": 1.5}, {"timeout": 0}, {"timeout": float("nan")}])
def test_python_api_enforces_authorized_budget(tmp_path, kwargs):
    with pytest.raises(ValueError):
        run_cell(tmp_path, **kwargs)
