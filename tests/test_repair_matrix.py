"""Offline arriving-matrix scheduling, exact pilot reuse, and resumability."""
from copy import deepcopy
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from proof_eval.one_shot import fingerprint
from run_deterministic import digest
from run_repair_matrix import prepare, read, run
from run_validity_repair import repair_cell


MODELS = ["Qwen/Qwen3.5-397B-A17B", "Qwen/Qwen3.6-35B-A3B"]
CODE = "theorem p : True := by trivial"
BAD = "theorem p : True := by exact False.elim ?_"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def evaluated(valid=False):
    return {"status": "passed" if valid else "failed", "primary_version": "v",
        "scores": {"combined_pct": 60 if valid else 0},
        "per_version": {"v": {"status": "passed" if valid else "failed", "passed": valid,
            "diagnostics": [] if valid else [{"severity": "error", "data": "unsolved goals\n⊢ True"}]}}}


class FakeEvaluator:
    def __init__(self, pack):
        self.pack = pack
        self.calls = []
        self.changed = False

    def get_reference(self, name):
        reference = deepcopy(self.pack["incumbent"]["per_version"]["v"]["reference"])
        if self.changed:
            reference["heartbeats"] += 1
        return {"versions": {"v": {"status": "prepared", **reference}}}

    def _context(self, row, version):
        return None, None, "context"

    def evaluate(self, name, code, *, versions):
        self.calls.append((name, code, versions))
        return evaluated(True)


class FakeClient:
    api_key = "fixture"

    def __init__(self, block_first_model=False):
        self.requests = []
        self.lock = threading.Lock()
        self.active = {}
        self.maximum = {}
        self.block_first_model = block_first_model
        self.second_model_started = threading.Event()

    def create_chat_completion(self, **request):
        model = request["model"]
        with self.lock:
            self.requests.append(request)
            self.active[model] = self.active.get(model, 0) + 1
            self.maximum[model] = max(self.maximum.get(model, 0), self.active[model])
        if model == MODELS[1]:
            self.second_model_started.set()
        if self.block_first_model and model == MODELS[0]:
            assert self.second_model_started.wait(2), "Another model was blocked behind the first model queue"
        with self.lock:
            self.active[model] -= 1
        return SimpleNamespace(content=CODE, finish_reason="stop", usage={}, model=model, raw={}, reasoning_content="")


@pytest.fixture
def matrix_fixture(tmp_path):
    base = tmp_path / "base"
    dataset, environments = tmp_path / "dataset", tmp_path / "environments"
    dataset.write_text("fixture dataset")
    environments.write_text("fixture environments")
    incumbent = evaluated(True)
    incumbent["per_version"]["v"]["reference"] = {
        "measured_at": "frozen", "heartbeats": 10, "heartbeats_raw": 10000,
        "environment_fingerprint": "environment", "reference_code_sha256": "code"}
    pack = {"name": "p", "row": {"name": "p", "source": "fixture", "statement": "theorem p : True", "version_info": [{"v": "rev"}]},
            "proof": CODE, "incumbent": incumbent, "source_context": ""}
    write(base / "inputs/p.json", pack)
    write(base / "input_hashes.json", {"p": fingerprint(pack)})
    config = {"names": ["p"], "models": MODELS, "arms": ["plain", "goals"], "code_sha256": {},
              "dataset_sha256": digest(dataset), "environment_config_sha256": digest(environments),
              "contexts": {"p": {"v": "context"}}}
    write(base / "config.json", config)
    write(base / "run.json", {"status": "running"})
    index, records = {}, {}
    for arm in config["arms"]:
        for model in MODELS:
            payload = {"model": model, "messages": [{"role": "user", "content": arm}],
                       "temperature": 0.3, "reasoning": True, "reasoning_effort": "high", "max_tokens": 100}
            key = fingerprint(payload)
            request = {"name": "p", "arm": arm, "request_sha256": key, **payload}
            record = {"name": "p", "source": "fixture", "arm": arm, "model": model, "request_sha256": key,
                      "generation": {"status": "received", "content": BAD, "finish_reason": "stop"},
                      "extracted_proof": BAD, "evaluation": evaluated()}
            index[json.dumps(["p", arm, model])] = key
            write(base / "cells" / key / "request.json", request)
            records[key] = record
    write(base / "cell_index.json", index)
    args = SimpleNamespace(input=base, output=tmp_path / "matrix", reuse=[], per_model=1,
                           max_rounds=3, timeout=1800, poll_seconds=0.01, dataset=dataset,
                           environments=environments, cache=tmp_path / "cache")
    return args, pack, records


def arrive(args, records):
    for key, record in records.items():
        write(args.input / "cells" / key / "result.json", record)


def test_full_matrix_has_per_model_slots_and_resume_never_resamples(matrix_fixture):
    args, pack, records = matrix_fixture
    arrive(args, records)
    write(args.input / "run.json", {"status": "finished"})
    evaluator, client = FakeEvaluator(pack), FakeClient(block_first_model=True)
    result = run(args, evaluator=evaluator, client=client)
    assert result["status"] == "complete"
    assert result["recorded_cells"] == result["planned_cells"] == 4
    assert len(client.requests) == 4
    assert client.maximum == {model: 1 for model in MODELS}
    config = read(args.output / "config.json")
    assert len(config["cells"]) == 4
    assert all(set(("result_sha256", "request_sha256", "input_sha256")) <= set(cell) for cell in config["cells"])
    assert "src/run_repair_matrix.py" in config["code_sha256"]
    calls_before = len(evaluator.calls)
    resumed_client = FakeClient()
    resumed = run(args, evaluator=evaluator, client=resumed_client)
    assert resumed["status"] == "complete"
    assert not resumed_client.requests
    assert len(evaluator.calls) == calls_before


def test_waits_for_initial_arrival_without_creating_initial_generations(matrix_fixture):
    args, pack, records = matrix_fixture
    client = FakeClient()
    sleeps = []
    def on_wait(seconds):
        sleeps.append(seconds)
        arrive(args, records)
        write(args.input / "run.json", {"status": "finished"})
    result = run(args, evaluator=FakeEvaluator(pack), client=client, sleep=on_wait)
    assert sleeps == [0.01]
    assert result["status"] == "complete"
    assert not list(args.input.glob("cells/*/generation.json"))
    assert len(client.requests) == 4


def test_terminal_partial_base_stays_incomplete_and_can_resume(matrix_fixture):
    args, pack, records = matrix_fixture
    first = next(iter(records))
    arrive(args, {first: records[first]})
    write(args.input / "run.json", {"status": "paused_at_call_budget"})
    client = FakeClient()
    result = run(args, evaluator=FakeEvaluator(pack), client=client)
    assert result["status"] == "incomplete_base_terminal"
    assert result["recorded_cells"] == 1
    assert result["pending_initial_cells"] == 3
    assert not (args.output / "config.json").exists()
    assert len(read(args.output / "matrix_config.json")["cells"]) == 4
    arrive(args, records)
    write(args.input / "run.json", {"status": "finished"})
    resumed_client = FakeClient()
    resumed = run(args, evaluator=FakeEvaluator(pack), client=resumed_client)
    assert resumed["status"] == "complete"
    assert len(resumed_client.requests) == 3


def test_exact_completed_pilot_is_reused_without_a_call(matrix_fixture, tmp_path):
    args, pack, records = matrix_fixture
    arrive(args, records)
    key = next(iter(records))
    pilot = tmp_path / "pilot"
    repair_cell(base_record=records[key], base_request=read(args.input / "cells" / key / "request.json"),
                pack=pack, folder=pilot / "cells" / key, client=FakeClient(), evaluator=FakeEvaluator(pack))
    args.reuse = [pilot]
    pilot_bytes = (pilot / "cells" / key / "result.json").read_bytes()
    client = FakeClient()
    result = run(args, evaluator=FakeEvaluator(pack), client=client)
    assert result["status"] == "complete"
    assert result["reused_cells"] == 1
    assert len(client.requests) == 3
    assert (args.output / "cells" / key / "result.json").read_bytes() == pilot_bytes
    assert (pilot / "cells" / key / "result.json").read_bytes() == pilot_bytes


def test_mismatched_pilot_and_changed_reference_fail_before_sampling(matrix_fixture, tmp_path):
    args, pack, records = matrix_fixture
    arrive(args, records)
    client, evaluator = FakeClient(), FakeEvaluator(pack)
    evaluator.changed = True
    with pytest.raises(ValueError, match="Cached reference changed"):
        run(args, evaluator=evaluator, client=client)
    assert not client.requests
    args.output = tmp_path / "other"
    key = next(iter(records))
    pilot = tmp_path / "pilot"
    write(pilot / "cells" / key / "result.json", {})
    write(pilot / "cells" / key / "cell_config.json", {"wrong": True})
    args.reuse = [pilot]
    with pytest.raises(ValueError, match="pilot cell configuration mismatch"):
        run(args, evaluator=FakeEvaluator(pack), client=client)
    assert not client.requests


def test_source_index_and_arrival_mutations_are_refused(matrix_fixture):
    args, pack, records = matrix_fixture
    first = next(iter(records))
    arrive(args, {first: records[first]})
    write(args.input / "run.json", {"status": "interrupted"})
    run(args, evaluator=FakeEvaluator(pack), client=FakeClient())
    modified = deepcopy(records[first])
    modified["generation"]["content"] += " "
    arrive(args, {first: modified})
    with pytest.raises(ValueError, match="initial cell snapshot changed"):
        run(args, evaluator=FakeEvaluator(pack), client=FakeClient())
    index = read(args.input / "cell_index.json")
    index.pop(next(iter(index)))
    write(args.input / "cell_index.json", index)
    with pytest.raises(ValueError, match="full declared matrix"):
        prepare(args)
