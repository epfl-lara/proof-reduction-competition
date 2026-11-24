"""CPU setup owns reference measurements; inference cannot leak into preparation."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from proof_eval import Evaluator
from proof_eval.benchmark import submission
from proof_eval.evidence.io import read, write_json
from proof_eval.verification.metrics import token_count


class Backend:
    def __init__(self):
        self.calls = []
        self.timeout = False

    def fingerprint(self, row, version, path):
        return "fixture-" + version

    def check(self, row, proof, version, path):
        self.calls.append((row["name"], proof, version))
        if self.timeout:
            return {
                "status": "timeout",
                "passed": False,
                "heartbeats": None,
                "heartbeats_raw": None,
            }
        return {
            "status": "passed",
            "passed": True,
            "heartbeats": 100,
            "heartbeats_raw": 100000,
            "details": {"timeout_seconds": 600},
        }


@pytest.fixture
def preparation(tmp_path):
    dataset = tmp_path / "problems.jsonl"
    row = {
        "name": "original",
        "source": "fixture",
        "url": "https://example.org/source",
        "statement": "theorem original : True",
        "src": "theorem original : True := by trivial",
        "proof_length": token_count("by trivial"),
        "version_info": [{"v1": "one"}, {"v2": "two"}],
    }
    dataset.write_text(json.dumps(row) + "\n")
    env = tmp_path / "environments.json"
    write_json(
        env,
        {
            "projects": [
                {"source": "fixture", "version": v, "path": "."} for v in ("v1", "v2")
            ]
        },
    )
    config = submission.SubmissionSetup(
        dataset, env, tmp_path / "work", build_projects=False
    )
    backend = Backend()
    evaluator = Evaluator(
        dataset, env, config.work / "reference_cache", backend=backend
    )
    return config, evaluator, backend


def test_originals_are_measured_once_then_admitted_without_compilation(preparation):
    from proof_eval.benchmark.preparation import load_prepared
    from proof_eval.verification.initial import adopt_prepared_original

    config, evaluator, backend = preparation
    result = submission.setup(config, evaluator=evaluator)
    assert result["status"] == "complete"
    assert result["summary"]["prepared_versions"] == 2
    assert result["request"]["required_version_checks"] == 2
    assert len(backend.calls) == 2
    assert {proof for _, proof, _ in backend.calls} == {
        evaluator.dataset.get("original")["src"]
    }
    for _ in range(2):
        assert submission.setup(config, evaluator=evaluator) == result
        assert submission.verify_setup(config, evaluator=evaluator) == result
    prepared = load_prepared(Path(result["base"]), evaluator)
    adopt_prepared_original(
        evaluator, config.work / "private_cell", prepared.packs["original"]
    )
    assert len(backend.calls) == 2
    assert result["request"]["model_calls"] == 0
    assert result["request"]["measurement_timeout_retries"] == 0


def test_explicit_original_reference_import_builds_and_measures_nothing(
    preparation, monkeypatch
):
    from proof_eval.evidence.io import digest
    from proof_eval.verification.reference_transfer import export_references

    config, evaluator, backend = preparation
    check = backend.check
    monkeypatch.setattr(
        backend,
        "check",
        lambda *args: {
            **check(*args),
            "details": {"timeout_seconds": evaluator.timeout},
        },
    )
    submission.setup(config, evaluator=evaluator)
    source = config.work / "original-reference-bundle.json"
    export_references(evaluator, source)
    imported = replace(
        config,
        work=config.work.parent / "imported-work",
        prepared_reference_bundle=source,
        prepared_reference_sha256=digest(source),
    )
    receiver = Evaluator(
        config.dataset,
        config.environments,
        imported.work / "reference_cache",
        backend=backend,
    )
    monkeypatch.setattr(
        submission, "provision", lambda *a, **k: pytest.fail("no project rebuild")
    )
    monkeypatch.setattr(
        submission,
        "process_benchmark",
        lambda *a, **k: pytest.fail("no repeated original measurement"),
    )
    calls = len(backend.calls)
    result = submission.setup(imported, evaluator=receiver)
    assert len(backend.calls) == calls
    assert result["summary"]["prepared_versions"] == 2
    assert result["summary"]["Lean_calls"] == 0
    receipt = read(imported.work / "reference-import.json")
    assert receipt["source_sha256"] == digest(source)
    assert receipt["producer_machine"] == evaluator.machine
    assert submission.verify_setup(imported, evaluator=receiver) == result
    assert submission.setup(imported, evaluator=receiver) == result
    gpu = Evaluator(
        config.dataset,
        config.environments,
        imported.work / "reference_cache",
        backend=backend,
    )
    gpu.machine = {**receiver.machine, "host": "separate-gpu"}
    admitted = submission.admit_setup(imported, evaluator=gpu)
    assert len(backend.calls) == calls
    assert (
        read(Path(admitted["host_admission"]))["reference_import"]["producer_machine"]
        == evaluator.machine
    )
    assert (
        Path(admitted["references"]).read_bytes()
        == Path(result["references"]).read_bytes()
    )


def test_wrong_import_hash_rejects_before_any_setup(preparation):
    config, evaluator, backend = preparation
    source = config.work.parent / "wrong-reference-bundle.json"
    source.write_text("{}")
    config = replace(
        config, prepared_reference_bundle=source, prepared_reference_sha256="0" * 64
    )
    with pytest.raises(ValueError, match="bundle hash"):
        submission.setup(config, evaluator=evaluator)
    assert not backend.calls and not (config.work / "setup_started.json").exists()


def test_completed_setup_is_admitted_on_another_host_without_measurement(preparation):
    config, producer, backend = preparation
    producer.machine = {"host": "cpu", "system": "Linux", "machine": "x86_64"}
    saved = submission.setup(config, evaluator=producer)
    original_receipt = (config.work / "setup.json").read_bytes()
    reference_bundle = Path(saved["reference_bundle"]["path"]).read_bytes()
    receiver_backend = Backend()
    receiver = Evaluator(
        config.dataset,
        config.environments,
        config.work / "reference_cache",
        backend=receiver_backend,
    )
    receiver.machine = {"host": "gpu", "system": "Linux", "machine": "x86_64"}
    with pytest.raises(ValueError, match="Cached reference unavailable"):
        submission.verify_setup(config, evaluator=receiver)
    admitted = submission.admit_setup(config, evaluator=receiver)
    assert admitted["identity"] == saved["identity"]
    assert admitted["base"] != saved["base"]
    assert admitted["original_preparation"]["base"] == saved["base"]
    assert (
        read(Path(admitted["host_admission"]))["receiver_machine"] == receiver.machine
    )
    assert (
        Path(admitted["references"]).read_bytes()
        == Path(saved["references"]).read_bytes()
    )
    assert (config.work / "setup.json").read_bytes() == original_receipt
    assert Path(saved["reference_bundle"]["path"]).read_bytes() == reference_bundle
    assert len(backend.calls) == 2 and not receiver_backend.calls
    assert submission.admit_setup(config, evaluator=receiver) == admitted
    assert submission.setup(config, evaluator=receiver) == admitted
    assert not receiver_backend.calls


def test_host_transfer_rejects_corrupt_bundle_without_measurement(preparation):
    config, producer, backend = preparation
    saved = submission.setup(config, evaluator=producer)
    receiver = Evaluator(
        config.dataset, config.environments, config.work / "unused", backend=backend
    )
    receiver.machine = {**producer.machine, "host": "different"}
    Path(saved["reference_bundle"]["path"]).write_text("{}")
    with pytest.raises(ValueError, match="Portable reference bundle changed"):
        submission.admit_setup(config, evaluator=receiver)
    assert len(backend.calls) == 2
    assert not (config.work / "host_admissions").exists()


def test_incomplete_setup_cannot_retry_a_timeout(preparation):
    config, evaluator, backend = preparation
    backend.timeout = True
    with pytest.raises(ValueError, match="incomplete"):
        submission.setup(config, evaluator=evaluator)
    before = list(backend.calls)
    failure = (config.work / "setup_failure.json").read_bytes()
    assert len(before) == 2
    with pytest.raises(RuntimeError, match="Prior setup"):
        submission.setup(config, evaluator=evaluator)
    assert backend.calls == before
    assert (config.work / "setup_failure.json").read_bytes() == failure
    assert not (config.work / "setup.json").exists()


def test_setup_measures_original_and_records_a_published_length_difference(preparation):
    from proof_eval.benchmark.preparation import load_prepared

    config, evaluator, backend = preparation
    row = evaluator.dataset.get("original")
    original = row["src"]
    row["proof_length"] += 1
    config.dataset.write_text(json.dumps(row) + "\n")
    evaluator = Evaluator(
        config.dataset,
        config.environments,
        config.work / "reference_cache",
        backend=backend,
    )
    result = submission.setup(config, evaluator=evaluator)
    prepared = load_prepared(Path(result["base"]), evaluator)
    pack = prepared.packs["original"]
    assert result["status"] == "complete"
    assert len(backend.calls) == 2
    assert {proof for _, proof, _ in backend.calls} == {original}
    assert pack["proof"] == pack["row"]["src"] == original
    assert pack["row"]["proof_length"] == row["proof_length"]
    assert pack["incumbent"]["candidate"]["length"] == row["proof_length"] - 1
    assert pack["incumbent"]["original_token_count_comparison"] == {
        "published_denominator": row["proof_length"],
        "local_candidate_tokens": row["proof_length"] - 1,
        "denominator_policy": "unchanged published proof_length",
    }
    assert submission.verify_setup(config, evaluator=evaluator) == result
    assert len(backend.calls) == 2


def test_unknown_setup_and_changed_inputs_do_not_measure(preparation):
    config, evaluator, backend = preparation
    write_json(config.work / "setup_started.json", {"unknown": True})
    with pytest.raises(RuntimeError, match="Prior setup"):
        submission.setup(config, evaluator=evaluator)
    assert not backend.calls
    # A distinct directory is an explicit fresh setup, not a retry.
    config = replace(config, work=config.work.parent / "explicit-new-setup")
    submission.setup(config, evaluator=evaluator)
    before = list(backend.calls)
    with pytest.raises(ValueError, match="changed"):
        submission.verify_setup(replace(config, cpus=4), evaluator=evaluator)
    assert backend.calls == before


def test_bundled_projects_build_before_measurement_without_toolchain_install(
    preparation, monkeypatch
):
    config, evaluator, backend = preparation
    config = replace(config, build_projects=True, workers=2)
    calls = []

    def build(key, rows, logs, cpus, *, project_path, install_toolchains):
        assert backend.calls == []
        assert install_toolchains is False
        assert project_path == config.environments.parent
        calls.append(key)
        return {"status": "built", "source": key[0], "version": key[1]}

    monkeypatch.setattr(submission, "provision", build)
    submission.setup(config, evaluator=evaluator)
    assert set(calls) == {("fixture", "v1"), ("fixture", "v2")}
    assert len(backend.calls) == 2
    assert len(read(config.work / "projects.json")["projects"]) == 2


def test_conflicting_pins_fail_before_setup_intent(preparation):
    config, evaluator, _ = preparation
    row = evaluator.dataset.get("original")
    row.update(name="other", version_info=[{"v1": "different"}])
    with config.dataset.open("a") as stream:
        stream.write(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="Conflicting"):
        submission.setup(config, evaluator=evaluator)
    assert not (config.work / "setup_started.json").exists()
