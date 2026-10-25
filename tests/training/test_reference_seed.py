"""Transferred originals retain measured values and fail closed on changed provenance."""

import hashlib
import json
from contextlib import nullcontext
from copy import deepcopy

import pytest

from proof_eval.evidence.immutable import sha
from proof_eval.training import reference_seed
from proof_eval.training.data import task_id


def seed_fixture(tmp_path, monkeypatch):
    source, dataset, output = (
        tmp_path / name for name in ("source", "dataset", "output")
    )
    source.mkdir()
    dataset.mkdir()
    (dataset / "rl-reserved.jsonl").write_text("fixture reserve")
    row = {
        "name": "Task.t",
        "source": "project",
        "src": "theorem t : True := by trivial",
        "proof_length": 3,
        "version_info": [{"v1": "commit"}],
    }
    identity = task_id(row)
    value = {
        "name": row["name"],
        "version": "v1",
        "status": "prepared",
        "heartbeats": 10.0,
        "heartbeats_raw": 10000,
        "reference_code_sha256": hashlib.sha256(row["src"].encode()).hexdigest(),
        "environment_fingerprint": "pinned-context",
        "length": 3,
        "measured_at": "source-time",
        "machine": {"host": "original-pod"},
    }
    raw = source / "raw-reference.json"
    raw.write_text(json.dumps(value))
    pack = source / "pack.json"
    pack.write_text(
        json.dumps(
            {
                "row": row,
                "proof": row["src"],
                "incumbent": {
                    "per_version": {"v1": {"reference": {**value, "cached": False}}}
                },
            }
        )
    )
    record = {
        "task_id": identity,
        "task": [row["source"], row["name"]],
        "status": "prepared",
        "pack_path": pack.name,
        "pack_sha256": sha(pack),
    }
    prepared = source / "prepared.json"
    prepared.write_text(
        json.dumps(
            {"dataset_sha256": sha(dataset / "rl-reserved.jsonl"), "records": [record]}
        )
    )
    manifest = tmp_path / "seed.json"
    manifest.write_text(
        json.dumps(
            {
                "kind": "original_references_only",
                "policy_model_calls": 0,
                "optimizer_steps": 0,
                "prepared_sha256": sha(prepared),
                "entries": {
                    identity: {
                        "pack_sha256": sha(pack),
                        "references": {"v1": {"path": raw.name, "sha256": sha(raw)}},
                    }
                },
            }
        )
    )
    spec = {
        "manifest": str(manifest),
        "manifest_sha256": sha(manifest),
        "preparation": str(source),
        "count": 1,
    }

    class Store:
        data = {}

        def locked(self, *_):
            return nullcontext()

        def read(self, category, key):
            return self.data.get(key)

        def write(self, category, key, record):
            self.data[key] = deepcopy(record)

    store = Store()

    class Evaluator:
        machine = {"host": "receiving-pod"}

        def __init__(self, *_args, **_kwargs):
            self.store = store
            self.dataset = self

        def get(self, name):
            return row

        def _context(self, row, version):
            return tmp_path, "pinned-context", "new-key"

    monkeypatch.setattr(reference_seed, "Evaluator", Evaluator)
    monkeypatch.setattr(reference_seed, "validate_reserve", lambda _: [row])
    return spec, dataset, output, raw, pack, store, value, Evaluator


def test_only_original_denominators_transfer_with_their_original_machine(
    tmp_path, monkeypatch
):
    spec, dataset, output, _, _, store, value, _ = seed_fixture(tmp_path, monkeypatch)
    result = reference_seed.import_original_references(
        spec, dataset, tmp_path / "env.json", output
    )
    assert store.data == {"new-key": value}
    assert store.data["new-key"]["machine"]["host"] == "original-pod"
    assert result["tasks"] == 1 and result["compiler_calls"] == 0
    assert result["candidate_or_analysis_caches_imported"] is False
    provenance = json.loads(
        next((output / "reference-imports").glob("*.json")).read_text()
    )
    assert provenance["receiving_cache_machine"]["host"] == "receiving-pod"
    assert provenance["fresh_episode_measurement_required"] is True


def test_changed_raw_reference_rejects_import_without_writing_cache(
    tmp_path, monkeypatch
):
    spec, dataset, output, raw, _, store, _, _ = seed_fixture(tmp_path, monkeypatch)
    raw.write_text("{}")
    with pytest.raises(ValueError, match="Source original cache changed"):
        reference_seed.import_original_references(
            spec, dataset, tmp_path / "env.json", output
        )
    assert not store.data


def test_changed_original_pack_rejects_import(tmp_path, monkeypatch):
    spec, dataset, output, _, pack, store, _, _ = seed_fixture(tmp_path, monkeypatch)
    pack.write_text("{}")
    with pytest.raises(ValueError, match="Source original pack changed"):
        reference_seed.import_original_references(
            spec, dataset, tmp_path / "env.json", output
        )
    assert not store.data


def test_fresh_environment_must_match_before_rekeying(tmp_path, monkeypatch):
    spec, dataset, output, _, _, store, _, evaluator = seed_fixture(
        tmp_path, monkeypatch
    )
    monkeypatch.setattr(
        evaluator, "_context", lambda *_: (tmp_path, "changed-compiler", "new-key")
    )
    with pytest.raises(ValueError, match="Original denominator/environment differs"):
        reference_seed.import_original_references(
            spec, dataset, tmp_path / "env.json", output
        )
    assert not store.data


def test_existing_different_receiving_reference_is_never_overwritten(
    tmp_path, monkeypatch
):
    spec, dataset, output, _, _, store, _, _ = seed_fixture(tmp_path, monkeypatch)
    store.data["new-key"] = {"status": "different"}
    with pytest.raises(ValueError, match="cache is occupied"):
        reference_seed.import_original_references(
            spec, dataset, tmp_path / "env.json", output
        )
    assert store.data == {"new-key": {"status": "different"}}
