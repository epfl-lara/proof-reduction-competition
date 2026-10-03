"""Offline tamper and completeness checks for the saved one-shot audit."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

import audit_one_shot as audit
from proof_eval.metrics import token_count, validate_candidate
from proof_eval.one_shot import build_messages, fingerprint, FIELDS
from proof_eval.rcp import map_rcp_reasoning


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def read(path):
    return json.loads(path.read_text())


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    repo, root = tmp_path / "repo", tmp_path / "experiment"
    row = {
        "name": "sample", "source": "fixture", "statement": "theorem sample : True",
        "version_info": [{"v1": "commit1"}, {"v2": "commit2"}],
    }
    proof = row["statement"] + " := by\n  have h : True := by trivial\n  exact h"
    candidate = row["statement"] + " := by trivial"
    row["src"] = proof
    row["proof_length"] = token_count(validate_candidate(row, proof)[1])
    dataset_path = repo / "data/benchmark_data_warmup.jsonl"
    jsonl(dataset_path, [row])
    initial_path = repo / "results/deterministic/selected_candidates.jsonl"
    jsonl(initial_path, [{"name": row["name"], "proof": proof}])
    environment_path = repo / "environments.local.json"
    write(environment_path, {"projects": []})
    source_path = repo / "src/proof_eval/lean_backend.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("frozen source fixture\n")
    references = {}
    exported = {
        "name": row["name"], "status": "prepared", "dataset_sha256": audit.digest(dataset_path),
        "reference_length_tokens": row["proof_length"], "reference_code_sha256": sha(proof), "per_version": {},
    }
    for version, heartbeats in (("v1", 100), ("v2", 200)):
        provenance = {
            "measured_at": "fixed", "environment_fingerprint": "env-" + version,
            "reference_code_sha256": sha(proof), "machine": {"host": "fixture"},
            "details": {"backend_implementation_sha256": audit.digest(source_path)},
        }
        exported["per_version"][version] = {
            "status": "prepared", "heartbeats": heartbeats,
            "heartbeats_raw": heartbeats * 1000, "provenance": provenance,
        }
        references[version] = {
            "status": "prepared", "heartbeats": heartbeats,
            "heartbeats_raw": heartbeats * 1000, **provenance,
        }
    reference_path = repo / "results/deterministic/00_reference_baseline/reference_values.jsonl"
    jsonl(reference_path, [exported])

    def evaluation(code, hb1, hb2):
        normalized, body = validate_candidate(row, code)
        length = token_count(body)
        scores = {
            "length_reduction_pct": 100 * (1 - length / row["proof_length"]),
            "heartbeat_reduction_pct": 100 * (1 - hb1 / 100), "compatibility_pct": 100.0,
        }
        scores["combined_pct"] = sum(scores.values()) / 3
        return {
            "status": "passed", "primary_version": "v1", "scores": scores,
            "candidate": {"length": length, "code_sha256": sha(normalized)},
            "per_version": {
                version: {
                    "status": "passed", "passed": True, "heartbeats": hb,
                    "heartbeat_reduction_pct": 100 * (1 - hb / ref),
                    "environment_fingerprint": "env-" + version,
                    "reference": deepcopy(references[version]),
                }
                for version, hb, ref in (("v1", hb1, 100), ("v2", hb2, 200))
            },
        }

    incumbent, improved = evaluation(proof, 100, 200), evaluation(candidate, 50, 100)
    pack = {
        "name": row["name"], "row": {**row, "published_heartbeats": None}, "proof": proof, "incumbent": incumbent,
        "source_context": "import Lean", "source_excerpt_characters": 11,
    }
    input_path = root / "inputs/sample.json"
    write(input_path, pack)
    write(root / "input_hashes.json", {row["name"]: fingerprint(pack)})
    system_path = repo / "prompts/one_shot_system.md"
    system_path.parent.mkdir(parents=True)
    system_path.write_text("Return one complete proof declaration.")
    bank = {"cards": []}
    bank_path = repo / "prompts/strategy_bank.json"
    write(bank_path, bank)
    config = {
        "names": [row["name"]], "arms": ["plain"], "models": ["fixture/model"],
        "code_sha256": {str(source_path.relative_to(repo)): audit.digest(source_path)},
        "system_sha256": audit.digest(system_path), "bank_sha256": audit.digest(bank_path),
        "dataset_sha256": audit.digest(dataset_path), "input_sha256": audit.digest(initial_path),
        "environment_config_sha256": audit.digest(environment_path),
        "contexts": {row["name"]: {"v1": "context-v1", "v2": "context-v2"}},
        "temperature": 0.3, "reasoning": True, "reasoning_effort": "high",
        "max_tokens": 32768, "request_timeout_seconds": 1800, "min_gain_pp": 0.05,
    }
    write(root / "config.json", config)
    messages = build_messages(system_path.read_text(), row, proof, incumbent, pack["source_context"], "plain", bank)
    payload = {
        "model": "fixture/model", "messages": messages, "temperature": 0.3,
        "reasoning": True, "reasoning_effort": "high", "max_tokens": 32768,
        "reasoning_payload": map_rcp_reasoning("fixture/model", True, "high")[1],
    }
    key = fingerprint(payload)
    cell = root / "cells" / key
    write(root / "cell_index.json", {json.dumps([row["name"], "plain", "fixture/model"]): key})
    write(cell / "request.json", {"name": row["name"], "arm": "plain", "request_sha256": key, **payload})
    generation = {
        "status": "received", "content": candidate, "finish_reason": "stop",
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }
    write(cell / "generation.json", generation)
    write(cell / "request_started.json", {"started_at": "fixed"})
    record = {
        "name": row["name"], "source": row["source"], "model": "fixture/model", "arm": "plain",
        "request_sha256": key, "generation": generation, "evaluation": improved,
        "extracted_proof": candidate, "accepted": True, "all_versions_passed": True,
        "selected_proof": candidate, "selected_evaluation": improved,
    }
    write(cell / "result.json", record)
    state = SimpleNamespace(reference_reads=0)

    class ReadOnlyEvaluator:
        def __init__(self, *args, **kwargs):
            pass

        def get_reference(self, name):
            assert name == row["name"]
            state.reference_reads += 1
            return {"versions": deepcopy(references)}

        def _context(self, selected_row, version):
            assert selected_row["name"] == row["name"]
            return repo, "env-" + version, "context-" + version

        def evaluate(self, *args, **kwargs):
            raise AssertionError("Saved-evidence audit must not evaluate candidates")

        def prepare_reference(self, *args, **kwargs):
            raise AssertionError("Saved-evidence audit must not remeasure references")

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline audit test must not launch subprocesses or network requests")

    monkeypatch.setattr(audit, "ROOT", repo)
    monkeypatch.setattr(audit, "Evaluator", ReadOnlyEvaluator)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    return SimpleNamespace(
        root=root, repo=repo, row=row, pack=pack, config=config, cell=cell, input_path=input_path,
        record=record, generation=generation, references=references, payload=payload,
        source_path=source_path, dataset_path=dataset_path, initial_path=initial_path,
        environment_path=environment_path, reference_path=reference_path, state=state,
    )


def test_complete_audit_checks_saved_arithmetic_without_model_or_lean_execution(evidence):
    before = {path: path.read_bytes() for path in evidence.root.rglob("*.json")}
    report = audit.audit_one_shot(evidence.root, complete=True)
    assert report["status"] == "passed"
    assert report["checked_cells"] == report["expected_cells"] == 1
    assert report["accepted_candidates"] == 1
    assert report["unchanged_cached_references_checked"] == 2
    assert evidence.state.reference_reads == 1
    assert {path: path.read_bytes() for path in evidence.root.rglob("*.json")} == before


def test_partial_audit_never_claims_a_missing_cell_is_complete(evidence):
    (evidence.cell / "result.json").unlink()
    report = audit.audit_one_shot(evidence.root)
    assert report["checked_cells"] == 0 and report["expected_cells"] == 1
    assert report["complete_required"] is False
    with pytest.raises(ValueError, match="Missing completed cell"):
        audit.audit_one_shot(evidence.root, complete=True)


def test_changed_source_bytes_are_rejected(evidence):
    evidence.source_path.write_text("different source")
    with pytest.raises(ValueError, match="implementation changed"):
        audit.audit_one_shot(evidence.root)


def test_changed_request_payload_without_rehash_is_rejected(evidence):
    request = read(evidence.cell / "request.json")
    request["temperature"] = 0.7
    write(evidence.cell / "request.json", request)
    with pytest.raises(ValueError, match="Request hash mismatch"):
        audit.audit_one_shot(evidence.root)


def test_changed_prepared_input_hash_is_rejected(evidence):
    evidence.pack["source_context"] += "\n-- changed"
    write(evidence.input_path, evidence.pack)
    with pytest.raises(ValueError, match="Input changed"):
        audit.audit_one_shot(evidence.root)


@pytest.mark.parametrize("field,new_value", [
    ("measured_at", "remeasured"), ("heartbeats", 101), ("heartbeats_raw", 100001),
    ("environment_fingerprint", "different"), ("reference_code_sha256", "different"),
])
def test_each_frozen_reference_field_is_checked(evidence, field, new_value):
    evidence.references["v2"][field] = new_value
    with pytest.raises(ValueError, match="Cached reference changed"):
        audit.audit_one_shot(evidence.root)


@pytest.mark.parametrize("mutation,match", [
    ("score", "combined_pct"), ("heartbeats", "heartbeat reduction"),
    ("missing_version", "version keys differ"), ("proof_hash", "proof hash mismatch"),
])
def test_selected_evaluation_arithmetic_and_proof_integrity(evidence, mutation, match):
    record = deepcopy(evidence.record)
    result = record["selected_evaluation"]
    if mutation == "score":
        result["scores"]["combined_pct"] += 1
    elif mutation == "heartbeats":
        result["per_version"]["v1"]["heartbeats"] += 1
    elif mutation == "missing_version":
        del result["per_version"]["v2"]
    else:
        result["candidate"]["code_sha256"] = "wrong"
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match=match):
        audit.audit_one_shot(evidence.root)


def test_acceptance_flag_cannot_hide_an_improving_candidate(evidence):
    record = deepcopy(evidence.record)
    record["accepted"] = False
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="Acceptance decision differs"):
        audit.audit_one_shot(evidence.root)


def test_candidate_must_be_extracted_from_the_recorded_generation(evidence):
    generation = deepcopy(evidence.generation)
    generation["content"] = evidence.pack["proof"]
    record = deepcopy(evidence.record)
    record["generation"] = generation
    write(evidence.cell / "generation.json", generation)
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="Extracted proof differs"):
        audit.audit_one_shot(evidence.root)


def test_failed_primary_requires_zero_scores_and_preserves_fallback(evidence):
    record = deepcopy(evidence.record)
    failed = deepcopy(record['evaluation'])
    failed.update(status='failed', scores=dict.fromkeys(FIELDS, 0.0))
    failed['per_version']['v1'].update(status='failed', passed=False, heartbeats=None,
                                       heartbeat_reduction_pct=None)
    record.update(
        accepted=False, all_versions_passed=False, selected_proof=evidence.pack["proof"],
        selected_evaluation=deepcopy(evidence.pack["incumbent"]),
        evaluation=failed,
    )
    write(evidence.cell / "result.json", record)
    assert audit.audit_one_shot(evidence.root, complete=True)["accepted_candidates"] == 0
    record["evaluation"]["scores"]["combined_pct"] = 1
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="Failed candidate does not score zero"):
        audit.audit_one_shot(evidence.root)


def test_transport_unavailable_has_unknown_raw_scores_and_unchanged_fallback(evidence):
    generation = {"status": "transport_error", "error": "mocked transport failure"}
    record = deepcopy(evidence.record)
    record.update(
        generation=generation, accepted=False, all_versions_passed=False,
        selected_proof=evidence.pack["proof"], selected_evaluation=deepcopy(evidence.pack["incumbent"]),
        evaluation={"status": "unavailable", "scores": dict.fromkeys(FIELDS, None), "per_version": {}},
    )
    record.pop("extracted_proof")
    write(evidence.cell / "generation.json", generation)
    write(evidence.cell / "result.json", record)
    assert audit.audit_one_shot(evidence.root, complete=True)["checked_cells"] == 1
    record["evaluation"]["scores"]["combined_pct"] = 0.0
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="Unavailable output has invented scores"):
        audit.audit_one_shot(evidence.root)


@pytest.mark.parametrize("field,new_value", [
    ("temperature", 0.9), ("reasoning", False), ("reasoning_effort", "low"),
    ("max_tokens", 1), ("reasoning_payload", {}),
])
def test_rehashed_request_still_must_match_frozen_generation_settings(evidence, field, new_value):
    request = read(evidence.cell / "request.json")
    payload = {key: value for key, value in request.items() if key not in ("name", "arm", "request_sha256")}
    payload[field] = new_value
    key = fingerprint(payload)
    new_cell = evidence.cell.with_name(key)
    evidence.cell.rename(new_cell)
    write(new_cell / "request.json", {"name": "sample", "arm": "plain", "request_sha256": key, **payload})
    record = read(new_cell / "result.json")
    record["request_sha256"] = key
    write(new_cell / "result.json", record)
    write(evidence.root / "cell_index.json", {json.dumps(["sample", "plain", "fixture/model"]): key})
    with pytest.raises(ValueError, match="generation settings differ"):
        audit.audit_one_shot(evidence.root)


@pytest.mark.parametrize("field", ["name", "arm", "model", "source"])
def test_result_logical_identity_must_match_index(evidence, field):
    record = deepcopy(evidence.record)
    record[field] = "wrong"
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="Result logical identity mismatch"):
        audit.audit_one_shot(evidence.root)


@pytest.mark.parametrize("field", ["name", "arm"])
def test_unhashed_request_metadata_must_match_index(evidence, field):
    request = read(evidence.cell / "request.json")
    request[field] = "wrong"
    write(evidence.cell / "request.json", request)
    with pytest.raises(ValueError, match="Request identity mismatch"):
        audit.audit_one_shot(evidence.root)


@pytest.mark.parametrize("path_field", ["dataset_path", "initial_path", "environment_path"])
def test_frozen_input_artifacts_are_checked_byte_for_byte(evidence, path_field):
    path = getattr(evidence, path_field)
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="Frozen artifact changed"):
        audit.audit_one_shot(evidence.root)


def test_all_versions_passing_count_cannot_be_forged(evidence):
    record = deepcopy(evidence.record)
    record["all_versions_passed"] = False
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="All-version passing flag differs"):
        audit.audit_one_shot(evidence.root)


def test_unknown_evaluation_status_is_rejected(evidence):
    record = deepcopy(evidence.record)
    record["evaluation"] = deepcopy(record["evaluation"])
    record["evaluation"]["status"] = "unknown-status"
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="Unknown evaluation status"):
        audit.audit_one_shot(evidence.root)


def test_duplicate_prepared_input_cannot_be_silently_overwritten(evidence):
    write(evidence.input_path.with_name("duplicate.json"), evidence.pack)
    with pytest.raises(ValueError, match="Prepared inputs: expected exactly 1 rows"):
        audit.audit_one_shot(evidence.root)


def test_unindexed_completed_result_is_rejected(evidence):
    write(evidence.root / "cells/orphan/result.json", evidence.record)
    with pytest.raises(ValueError, match="Unindexed result artifact"):
        audit.audit_one_shot(evidence.root)


def test_incomplete_version_check_has_partial_metrics_and_falls_back(evidence):
    record = deepcopy(evidence.record)
    incomplete = deepcopy(record["evaluation"])
    incomplete["status"] = "incomplete"
    incomplete["scores"].update(combined_pct=None, compatibility_pct=None)
    incomplete["per_version"]["v2"].update(status="unavailable", passed=False,
                                             heartbeats=None, heartbeat_reduction_pct=None)
    record.update(evaluation=incomplete, accepted=False, all_versions_passed=False,
                  selected_proof=evidence.pack["proof"], selected_evaluation=deepcopy(evidence.pack["incumbent"]))
    write(evidence.cell / "result.json", record)
    assert audit.audit_one_shot(evidence.root, complete=True)["accepted_candidates"] == 0
    record["evaluation"]["scores"]["length_reduction_pct"] += 1
    write(evidence.cell / "result.json", record)
    with pytest.raises(ValueError, match="Incomplete length score"):
        audit.audit_one_shot(evidence.root)


def test_reference_export_metadata_is_tied_to_frozen_dataset(evidence):
    exported = json.loads(evidence.reference_path.read_text().splitlines()[0])
    exported["reference_code_sha256"] = "different"
    jsonl(evidence.reference_path, [exported])
    with pytest.raises(ValueError, match="Reference source changed"):
        audit.audit_one_shot(evidence.root)
