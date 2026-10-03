"""Offline end-to-end checks for sampling identity and durable one-shot resume.

Both compiler evaluation and the RCP client are replaced before the runner is
called. No test imports credentials, opens a network connection, or runs Lean.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

import run_one_shot as runner


class SimulatedInterruption(BaseException):
    """An abrupt interruption must not be mistaken for a transport response."""


def read_json(path):
    return json.loads(path.read_text())


@pytest.fixture
def harness(tmp_path, monkeypatch):
    name = "sample"
    proof = "theorem sample : True := by trivial"
    candidate = "theorem sample : True := by exact True.intro"
    row = {
        "name": name, "source": "fixture", "statement": "theorem sample : True",
        "src": proof, "proof_length": 10,
        "version_info": [{"v1": "commit-one"}, {"v2": "commit-two"}],
    }
    references = {
        version: {
            "status": "prepared", "measured_at": "2026-10-03T00:00:00Z",
            "heartbeats": 100, "heartbeats_raw": 100000,
            "environment_fingerprint": {"version": version},
            "reference_code_sha256": hashlib.sha256(proof.encode()).hexdigest(),
        }
        for version in ("v1", "v2")
    }
    state = SimpleNamespace(
        row=row, references=references, calls=[], evaluations=[], model_list_calls=0,
        client_constructions=0, response_error=None, evaluation_error=None,
    )

    class FakeDataset:
        names = [name]

        def get(self, selected_name):
            assert selected_name == name
            return deepcopy(state.row)

    class FakeEvaluator:
        dataset = FakeDataset()

        def get_reference(self, selected_name):
            assert selected_name == name
            return {"versions": deepcopy(state.references)}

        def _context(self, selected_row, version):
            assert selected_row == state.row
            return tmp_path, {"version": version}, "context-" + version

        def evaluate(self, selected_name, code, *, versions="all"):
            assert selected_name == name
            state.evaluations.append((code, versions))
            if code == candidate and state.evaluation_error is not None:
                error, state.evaluation_error = state.evaluation_error, None
                raise error
            assert versions == "all"
            reduction = 13.0 if code == candidate else 10.0
            scores = {
                "length_reduction_pct": reduction, "heartbeat_reduction_pct": reduction,
                "compatibility_pct": 100.0, "combined_pct": (2 * reduction + 100) / 3,
            }
            return {
                "status": "passed", "primary_version": "v1", "scores": scores,
                "per_version": {
                    version: {"passed": True, "status": "passed", "reference": deepcopy(reference)}
                    for version, reference in state.references.items()
                },
            }

    class FakeClient:
        api_key = "fake-secret-never-loaded-from-environment"

        def __init__(self, **kwargs):
            state.client_constructions += 1

        def list_models(self, **kwargs):
            state.model_list_calls += 1
            return ["fixture/model"]

        def create_chat_completion(self, **kwargs):
            state.calls.append(deepcopy(kwargs))
            if state.response_error is not None:
                error, state.response_error = state.response_error, None
                raise error
            return SimpleNamespace(
                content=candidate, finish_reason="stop",
                usage={"prompt_tokens": 100, "completion_tokens": 30},
                model="fixture/model", raw={"id": "fixture-response"},
                reasoning_content="private mocked reasoning, never candidate code",
            )

    evaluator = FakeEvaluator()
    monkeypatch.setattr(runner, "Evaluator", lambda *args, **kwargs: evaluator)
    monkeypatch.setattr(runner, "RCPClient", FakeClient)
    monkeypatch.setattr(
        runner, "_source",
        lambda *args, **kwargs: ("import Lean\n#proof_eval_measure fixture", "fixture"),
    )

    def unexpected_context(*args, **kwargs):
        raise AssertionError("Plain-arm fixture must not run context extraction")

    monkeypatch.setattr(runner, "build_context", unexpected_context)
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(json.dumps(row) + "\n")
    input_path = tmp_path / "incumbents.jsonl"
    input_path.write_text(json.dumps({"name": name, "proof": proof}) + "\n")
    environments = tmp_path / "environments.json"
    environments.write_text("{}\n")
    bank = tmp_path / "bank.json"
    bank.write_text('{"cards": []}\n')
    system = tmp_path / "system.txt"
    system.write_text("Return a complete declaration.\n")
    args = SimpleNamespace(
        dataset=dataset, input=input_path, environments=environments,
        cache=tmp_path / "cache", bank=bank, system=system, output=tmp_path / "output",
        name=None, models=["fixture/model"], arms=["plain"], per_model=1,
        max_tokens=32768, timeout=1800, max_calls=None, prepare_only=False,
    )
    return SimpleNamespace(
        args=args, state=state, evaluator=evaluator, name=name, proof=proof, candidate=candidate,
        input_pack=args.output / "inputs" / (hashlib.sha256(name.encode()).hexdigest()[:16] + ".json"),
    )


def only_cell(harness):
    paths = list((harness.args.output / "cells").iterdir())
    assert len(paths) == 1
    return paths[0]


def test_interruption_after_request_start_is_indeterminate_and_never_resampled(harness):
    harness.state.response_error = SimulatedInterruption("interrupted during request")
    with pytest.raises(SimulatedInterruption):
        runner.run(harness.args)
    cell = only_cell(harness)
    assert (cell / "request_started.json").exists()
    assert not (cell / "generation.json").exists()
    assert read_json(harness.args.output / "run.json")["status"] == "interrupted"

    report = runner.run(harness.args)
    assert len(harness.state.calls) == 1
    result = read_json(cell / "result.json")
    assert result["generation"]["status"] == "indeterminate"
    assert result["evaluation"]["status"] == "unavailable"
    assert result["selected_proof"] == harness.proof
    assert report["conditions"][0]["raw_mean"]["combined_pct"] is None
    assert report["conditions"][0]["selected_gain_pp"] == 0
    assert harness.state.evaluations == [(harness.proof, "all")]


def test_saved_generation_is_evaluated_on_resume_without_another_model_call(harness):
    harness.state.evaluation_error = SimulatedInterruption("interrupted before evaluation saved")
    with pytest.raises(SimulatedInterruption):
        runner.run(harness.args)
    cell = only_cell(harness)
    assert read_json(cell / "generation.json")["status"] == "received"
    assert not (cell / "result.json").exists()

    report = runner.run(harness.args)
    assert len(harness.state.calls) == 1
    assert report["conditions"][0]["improved_problems"] == 1
    result = read_json(cell / "result.json")
    assert result["accepted"] and result["all_versions_passed"]
    assert result["selected_proof"] == harness.candidate
    assert harness.state.evaluations == [
        (harness.proof, "all"), (harness.candidate, "all"), (harness.candidate, "all"),
    ]
    request = harness.state.calls[0]
    assert request["max_tokens"] == 32768
    assert request["temperature"] == 0.3
    assert request["reasoning"] is True and request["reasoning_effort"] == "high"

    generation_bytes = (cell / "generation.json").read_bytes()
    input_bytes = harness.input_pack.read_bytes()
    previous_evaluations = list(harness.state.evaluations)
    runner.run(harness.args)
    assert len(harness.state.calls) == 1
    assert harness.state.evaluations == previous_evaluations
    assert (cell / "generation.json").read_bytes() == generation_bytes
    assert harness.input_pack.read_bytes() == input_bytes


def test_transport_error_is_recorded_redacted_and_not_retried_on_resume(harness):
    harness.state.response_error = RuntimeError("request failed: fake-secret-never-loaded-from-environment")
    runner.run(harness.args)
    cell = only_cell(harness)
    generation = read_json(cell / "generation.json")
    assert generation["status"] == "transport_error"
    assert "[REDACTED]" in generation["error"]
    assert "fake-secret" not in (cell / "generation.json").read_text()
    runner.run(harness.args)
    assert len(harness.state.calls) == 1
    assert harness.state.evaluations == [(harness.proof, "all")]


@pytest.mark.parametrize("field,new_value", [
    ("measured_at", "2026-10-04T00:00:00Z"),
    ("heartbeats", 101),
    ("heartbeats_raw", 100001),
    ("environment_fingerprint", {"version": "changed"}),
    ("reference_code_sha256", "changed"),
])
def test_reference_drift_fails_before_any_request(harness, field, new_value):
    harness.args.prepare_only = True
    runner.run(harness.args)
    original = harness.input_pack.read_bytes()
    harness.state.references["v2"][field] = new_value
    harness.args.prepare_only = False
    with pytest.raises(ValueError, match="Reference changed since input preparation"):
        runner.run(harness.args)
    assert harness.state.calls == []
    assert harness.state.client_constructions == 0
    assert harness.input_pack.read_bytes() == original


@pytest.mark.parametrize("field", ["row", "proof"])
def test_saved_row_or_proof_drift_fails_before_any_request(harness, field):
    harness.args.prepare_only = True
    runner.run(harness.args)
    pack = read_json(harness.input_pack)
    if field == "row":
        pack["row"]["statement"] = "theorem changed : True"
    else:
        pack["proof"] = harness.candidate
    harness.input_pack.write_text(json.dumps(pack))
    harness.args.prepare_only = False
    with pytest.raises(ValueError, match="Saved input changed"):
        runner.run(harness.args)
    assert harness.state.calls == []
    assert harness.state.client_constructions == 0


def test_saved_context_drift_fails_input_hash_check_before_any_request(harness):
    harness.args.prepare_only = True
    runner.run(harness.args)
    pack = read_json(harness.input_pack)
    pack["source_context"] += "\n-- modified after preparation"
    harness.input_pack.write_text(json.dumps(pack))
    harness.args.prepare_only = False
    with pytest.raises(ValueError, match="Prepared input bytes changed; refusing to resample"):
        runner.run(harness.args)
    assert harness.state.calls == []
    assert harness.state.client_constructions == 0


def test_changed_dataset_file_fails_config_check_before_request(harness):
    harness.args.prepare_only = True
    runner.run(harness.args)
    harness.args.dataset.write_text(harness.args.dataset.read_text() + "\n")
    harness.args.prepare_only = False
    with pytest.raises(ValueError, match="Experiment configuration changed"):
        runner.run(harness.args)
    assert harness.state.calls == []
    assert harness.state.client_constructions == 0


def test_logical_cell_request_drift_never_creates_a_second_sample(harness, monkeypatch):
    runner.run(harness.args)
    original_index = (harness.args.output / "cell_index.json").read_bytes()
    original_builder = runner.build_messages

    def changed_messages(*args, **kwargs):
        messages = original_builder(*args, **kwargs)
        messages[1]["content"] += "\nChanged request content."
        return messages

    monkeypatch.setattr(runner, "build_messages", changed_messages)
    with pytest.raises(ValueError, match="A cell request changed.*refusing to resample"):
        runner.run(harness.args)
    assert len(harness.state.calls) == 1
    assert (harness.args.output / "cell_index.json").read_bytes() == original_index


def test_call_budget_resume_fills_other_cells_without_resampling_completed_cells(harness):
    harness.args.arms = ["plain", "cards"]
    harness.args.max_calls = 1
    report = runner.run(harness.args)
    assert report["recorded_cells"] == 1 and report["planned_cells"] == 2
    assert read_json(harness.args.output / "run.json")["status"] == "paused_at_call_budget"
    runner.run(harness.args)
    assert len(harness.state.calls) == 2
    assert read_json(harness.args.output / "run.json")["status"] == "finished"
    runner.run(harness.args)
    assert len(harness.state.calls) == 2
    results = [read_json(path) for path in (harness.args.output / "cells").glob("*/result.json")]
    assert {result["arm"] for result in results} == {"plain", "cards"}
    assert all(result["selected_proof"] == harness.candidate for result in results)
