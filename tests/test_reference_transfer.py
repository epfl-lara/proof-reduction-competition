"""Prepared references move across hosts without a second compiler pass."""

import json
from copy import deepcopy

import pytest

from proof_eval import Evaluator
from proof_eval.benchmark.preparation import freeze_prepared_inputs, load_prepared
from proof_eval.evidence.io import digest, read, write_json
from proof_eval.verification.initial import adopt_prepared_original
from proof_eval.verification.metrics import token_count
from proof_eval.verification.reference_transfer import (
    export_references,
    import_references,
)


class Backend:
    def __init__(self):
        self.calls = 0

    def fingerprint(self, row, version, path):
        return "pinned-" + version

    def check(self, row, proof, version, path):
        self.calls += 1
        return {
            "status": "passed",
            "passed": True,
            "heartbeats": 100,
            "heartbeats_raw": 100000,
            "details": {"timeout_seconds": 600},
        }


@pytest.fixture
def transfer(tmp_path):
    source = tmp_path / "dataset.jsonl"
    proof = "theorem x : True := by trivial"
    row = {
        "name": "x",
        "source": "fixture",
        "src": proof,
        "statement": "theorem x : True",
        "proof_length": token_count("by trivial"),
        "version_info": [{"v1": "one"}, {"v2": "two"}],
    }
    source.write_text(json.dumps(row) + "\n")

    def evaluator(name):
        backend = Backend()
        ev = Evaluator(source, None, tmp_path / name, backend=backend)
        ev.machine = {"host": name, "system": "Linux", "machine": "x86_64"}
        ev.projects = {("fixture", v): tmp_path for v in ("v1", "v2")}
        return ev

    producer, receiver = evaluator("producer"), evaluator("receiver")
    producer.prepare_reference("x")
    bundle = tmp_path / "prepared.json"
    export_references(producer, bundle)
    return producer, receiver, bundle


def test_receiver_preserves_producer_measurements_and_never_compiles(transfer):
    producer, receiver, bundle = transfer
    before = producer.get_reference("x")["versions"]
    receipt = import_references(receiver, bundle, digest(bundle))
    assert receipt["checks"] == 2 and receipt["Lean_calls"] == 0
    assert receiver.get_reference("x")["versions"] == before
    assert all(r["machine"]["host"] == "producer" for r in before.values())
    assert receipt["receiver_machine"]["host"] == "receiver"
    assert producer.backend.calls == 2 and receiver.backend.calls == 0
    assert import_references(receiver, bundle, digest(bundle)) == receipt
    assert receiver.backend.calls == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "timeout"),
        ("environment_fingerprint", "other"),
        ("reference_code_sha256", "other"),
        ("heartbeats", 0),
        ("heartbeats_raw", 100001),
        ("machine", {"host": "forged"}),
    ],
)
def test_invalid_record_is_rejected_before_any_receiver_cache_write(
    transfer, field, value
):
    _, receiver, bundle = transfer
    data = read(bundle)
    record = json.loads(data["entries"][-1]["record_json"])
    record[field] = value
    raw = json.dumps(record)
    import hashlib

    data["entries"][-1].update(
        record_json=raw, record_sha256=hashlib.sha256(raw.encode()).hexdigest()
    )
    write_json(bundle, data)
    with pytest.raises(ValueError):
        import_references(receiver, bundle, digest(bundle))
    assert not list((receiver.store.root / "references").glob("*.json"))
    assert receiver.backend.calls == 0


@pytest.mark.parametrize("kind", ["partial", "duplicate", "timeout", "hash"])
def test_incomplete_or_changed_bundle_is_not_promoted(transfer, kind):
    _, receiver, bundle = transfer
    data = read(bundle)
    if kind == "partial":
        data["entries"].pop()
    elif kind == "duplicate":
        data["entries"][-1] = deepcopy(data["entries"][0])
    elif kind == "timeout":
        data["verification_timeout_seconds"] = 300
    write_json(bundle, data)
    pin = "incorrect" if kind == "hash" else digest(bundle)
    with pytest.raises(ValueError):
        import_references(receiver, bundle, pin)
    assert not list((receiver.store.root / "references").glob("*.json"))


def test_admission_uses_prepared_original_without_compilation(transfer, tmp_path):
    producer, receiver, bundle = transfer
    import_references(receiver, bundle, digest(bundle))
    row = receiver.dataset.get("x")
    refs = receiver.get_reference("x")["versions"]
    pack = {
        "name": "x",
        "row": row,
        "incumbent": {
            "status": "passed",
            "primary_version": "v1",
            "requested_versions": ["v1", "v2"],
            "all_versions": ["v1", "v2"],
            "per_version": {v: {"reference": r} for v, r in refs.items()},
        },
    }
    folder = tmp_path / "cell"
    proof, evaluation = adopt_prepared_original(receiver, folder, pack)
    assert proof == row["src"] and evaluation["scores"]["combined_pct"] == 100 / 3
    assert all(v["cached"] for v in evaluation["per_version"].values())
    assert adopt_prepared_original(receiver, folder, pack) == (proof, evaluation)
    assert receiver.backend.calls == 0 and producer.backend.calls == 2
    marker = read(folder / "initial_measurement.json")
    assert marker["compiler_calls"] == 0 and marker["timeout_retries"] == 0
    marker["compiler_calls"] = 1
    write_json(folder / "initial_measurement.json", marker)
    with pytest.raises(ValueError, match="admission changed"):
        adopt_prepared_original(receiver, folder, pack)


def test_gpu_input_freeze_reads_imported_references_without_preparing_again(
    transfer, tmp_path, monkeypatch
):
    _, receiver, bundle = transfer
    import_references(receiver, bundle, digest(bundle))

    def forbidden(*args, **kwargs):
        raise AssertionError("GPU input admission must not compile originals again")

    monkeypatch.setattr(receiver, "prepare_reference", forbidden)
    monkeypatch.setattr(receiver, "evaluate", forbidden)
    env = tmp_path / "environments.json"
    write_json(env, {"projects": []})
    prepared = freeze_prepared_inputs(receiver, env, receiver.store.root)
    assert prepared.packs["x"]["proof"] == receiver.dataset.get("x")["src"]
    assert read(prepared.base / "config.json")["compiler_calls"] == 0
    assert load_prepared(prepared.base, receiver) == prepared
    assert receiver.backend.calls == 0
    manifest = next((prepared.base / "inputs").glob("*.json"))
    manifest.write_text("{}")
    with pytest.raises(ValueError, match="artifact changed"):
        load_prepared(prepared.base, receiver)


def test_gpu_input_freeze_refuses_missing_reference_without_compiling(
    transfer, tmp_path
):
    _, receiver, _ = transfer
    env = tmp_path / "environments.json"
    write_json(env, {"projects": []})
    with pytest.raises(ValueError, match="incomplete"):
        freeze_prepared_inputs(receiver, env, receiver.store.root)
    assert receiver.backend.calls == 0
