"""Portable starting-state identity, exact cohort and model lineage contracts."""

import json
from copy import deepcopy

import pytest
from test_search_exploration import ORIGINAL, ROW, A

from proof_eval.evidence.io import read, write_json
from proof_eval.evidence.proof_states import (
    export_proof_states,
    freeze_proof_states,
    guard_proof_states,
    validate_lineage,
)


@pytest.fixture
def states(tmp_path):
    references = tmp_path / "references.jsonl"
    references.write_text(json.dumps({"name": "p", "denominator": 1000}) + "\n")
    return {"p": {"name": "p", "row": ROW}}, references


def test_original_and_portable_states_keep_original_denominators(tmp_path, states):
    packs, references = states
    original = freeze_proof_states(None, packs, references)
    assert original["cells"]["p"]["proof"] == ORIGINAL
    assert original["cells"]["p"]["lineage"]["kind"] == "original"
    path = tmp_path / "state.json"
    export_proof_states(
        path, packs, references, {"p": A}, lineage={"kind": "deterministic"}
    )
    frozen = freeze_proof_states(path.parent, packs, references)
    guard_proof_states(frozen, packs, references)
    assert frozen["references_sha256"] == original["references_sha256"]
    assert frozen["cells"]["p"]["proof"] == A
    assert frozen["cells"]["p"]["source_score"] is None


def test_model_lineage_survives_cleanup_export_and_rejects_other_conditions(
    tmp_path, states
):
    packs, references = states
    path = tmp_path / "state.json"
    export_proof_states(
        path,
        packs,
        references,
        {"p": {"selected_proof": A, "model": "sol", "effort": "max"}},
    )
    frozen = freeze_proof_states(path, packs, references)
    validate_lineage(frozen, ("sol", "max"))
    with pytest.raises(ValueError, match="another model condition"):
        validate_lineage(frozen, ("qwen", "max"))
    cleaned = tmp_path / "cleaned.json"
    export_proof_states(
        cleaned, packs, references, frozen["cells"], lineage={"kind": "deterministic"}
    )
    assert (
        freeze_proof_states(cleaned, packs, references)["cells"]["p"]["lineage"][
            "model"
        ]
        == "sol"
    )
    with pytest.raises(ValueError, match="another model condition"):
        freeze_proof_states(cleaned, packs, references, condition=("sol", "high"))


def test_raw_jsonl_is_explicitly_external_and_scores_are_not_required(tmp_path, states):
    packs, references = states
    path = tmp_path / "submission.jsonl"
    path.write_text(json.dumps({"name": "p", "code": A}) + "\n")
    state = freeze_proof_states(path, packs, references)
    assert state["cells"]["p"]["lineage"] == {"kind": "external"}
    assert state["cells"]["p"]["source_score"] is None
    path.write_text(json.dumps({"name": "p", "code": ORIGINAL}) + "\n")
    with pytest.raises(ValueError, match="state changed"):
        guard_proof_states(state, packs, references)


@pytest.mark.parametrize(
    "records", [[], [{"name": "unknown", "code": A}], [{"name": "p", "code": A}] * 2]
)
def test_import_rejects_missing_unknown_and_duplicate_names(tmp_path, states, records):
    packs, references = states
    path = tmp_path / "submission.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    with pytest.raises(ValueError, match="cohort|Duplicate"):
        freeze_proof_states(path, packs, references)


def test_manifest_rejects_changed_rows_proofs_and_reference_identity(tmp_path, states):
    packs, references = states
    path = tmp_path / "state.json"
    original = export_proof_states(path, packs, references, {"p": A})
    tampered = deepcopy(original)
    tampered["cells"]["p"]["proof"] = ORIGINAL
    write_json(path, tampered)
    with pytest.raises(ValueError, match="identity changed"):
        freeze_proof_states(path, packs, references)
    write_json(path, original)
    altered = deepcopy(packs)
    altered["p"]["row"]["proof_length"] += 1
    with pytest.raises(ValueError, match="identity changed"):
        freeze_proof_states(path, altered, references)
    references.write_text(json.dumps({"name": "p", "denominator": 1}) + "\n")
    with pytest.raises(ValueError, match="denominators changed"):
        freeze_proof_states(path, packs, references)


def test_invalid_declaration_and_conflicting_model_lineage_are_rejected(
    tmp_path, states
):
    packs, references = states
    path = tmp_path / "state.json"
    with pytest.raises(ValueError):
        export_proof_states(
            path, packs, references, {"p": "theorem p : False := by sorry"}
        )
    with pytest.raises(ValueError, match="Conflicting"):
        export_proof_states(
            path,
            packs,
            references,
            {
                "p": {
                    "proof": A,
                    "model": "sol",
                    "effort": "max",
                    "lineage": {"kind": "model", "model": "qwen", "effort": "max"},
                }
            },
        )
    assert not path.exists()


def test_existing_export_cannot_be_replaced_by_different_proofs(tmp_path, states):
    packs, references = states
    path = tmp_path / "state.json"
    export_proof_states(path, packs, references, {"p": A})
    with pytest.raises(ValueError, match="Existing proof state differs"):
        export_proof_states(path, packs, references, {"p": ORIGINAL})
    assert read(path)["cells"]["p"]["proof"] == A
