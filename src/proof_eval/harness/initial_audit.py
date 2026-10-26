"""Read-only evidence checks for original starts and bounded initial transforms."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from proof_eval.evidence.audit import _evaluation, _require
from proof_eval.evidence.io import digest, fingerprint, read
from proof_eval.optimization.bounded import validate_methods
from proof_eval.optimization.limits import audit_discovery_limit
from proof_eval.verification.initial import audit_measurement_attempts


def audit_initial(
    config: dict, result: dict, folder: Path, row: dict, reference: dict
) -> int:
    validate_methods(
        tuple(config["initial_deterministic_methods"]),
        config["initial_deterministic_seconds"],
    )
    prepared = config.get("original_measurement_policy") == "prepared"
    _require(
        config["initial_pipeline_version"] == 1
        and config["seed"]
        == (
            (
                "prepared_original_then_explicit_state"
                if prepared
                else "fresh_original_then_explicit_state"
            )
            if config.get("starting_proofs")
            else ("prepared_original" if prepared else "fresh_measured_original")
        )
        and config["candidate_cache_policy"] == "private_per_cell"
        and config["reference_policy"]
        == (
            "prepared_original_reference_identity"
            if prepared
            else "fresh_original_measurement_fixed_denominators"
        )
        and config["deterministic_placement"] == "initial_only"
        and config["cleanup_reserve_seconds"] == 0
        and not config.get("incumbent_sources"),
        "Original-start pipeline policy changed",
    )
    inp = read(folder / "input.json")
    _require(
        inp["seed_proof"] == row["src"], "Run did not start from the original proof"
    )
    _require(
        result["final_cleanup_status"] == "disabled"
        and result["deterministic_calls"] == 0,
        "Initial-only run performed legacy or final cleanup",
    )
    started = read(folder / "problem_started.json")["started_epoch"]
    if (folder / "budget_started.json").exists():
        _require(
            started == read(folder / "budget_started.json")["started_epoch"],
            "Measurement is outside the problem clock",
        )
    measurement_path = folder / "initial_measurement.json"
    if not measurement_path.exists():
        _require(
            result["status"] == "incomplete"
            and not result["generations"]
            and result.get("time_budget", {}).get("exhausted"),
            "Unmeasured original was treated as a complete run",
        )
        return 0
    measurement = read(measurement_path)
    if prepared:
        from .configuration import load_inputs

        pack = load_inputs(Path(config["base_directory"]))[row["name"]]
        from proof_eval.verification.references import original_evaluation

        _require(
            fingerprint(pack) == config["input_sha256"][row["name"]]
            and pack["row"] == row
            and measurement.get("evaluation") == original_evaluation(pack)
            and measurement.get("reference_policy")
            == "prepared_original_reference_identity"
            and measurement.get("compiler_calls") == 0
            and measurement.get("timeout_retries") == 0
            and config.get("initial_measurement_timeout_retries") == 0
            and measurement.get("prepared_reference_sha256")
            == fingerprint(
                {v: x["reference"] for v, x in pack["incumbent"]["per_version"].items()}
            ),
            "Prepared original admission changed or was remeasured",
        )
    else:
        audit_measurement_attempts(
            folder, row, config.get("initial_measurement_timeout_retries", 0)
        )
    evaluation = measurement["evaluation"]
    _require(
        started <= measurement["started_epoch"] <= measurement["finished_epoch"]
        and inp["seed_evaluation"] == evaluation
        and all(
            check.get("cached") is prepared
            for check in evaluation["per_version"].values()
        ),
        "Original measurement was cached, outside the clock, or differs from the seed",
    )
    count = _evaluation(
        row,
        reference,
        row["src"],
        evaluation,
        "prepared original" if prepared else "fresh original",
    )
    if config.get("model_phase_version"):
        _require(
            config["model_phase_version"] == 1
            and config["budget_scope"] == "model_phase"
            and read(folder / "problem_started.json")["scope"]
            == (
                "model_phase_prepared_original_admission_search"
                if prepared
                else "model_phase_original_and_selected_measurement_admission_search"
            )
            and not config["initial_deterministic_methods"]
            and result["model_phase_elapsed_seconds"]
            == result["pipeline_elapsed_seconds"]
            and result["phase_accounting"] == "model_only_external_cleanup_excluded",
            "Model-phase accounting changed",
        )
        if not config.get("starting_proofs") and not config.get(
            "deterministic_checkpoint"
        ):
            start_score = evaluation["scores"]["combined_pct"]
            _require(
                result["model_start_score"] == start_score
                and abs(
                    result["model_gain_pp"]
                    - (
                        result["selected_evaluation"]["scores"]["combined_pct"]
                        - start_score
                    )
                )
                < 1e-9,
                "Original-start model gain changed",
            )
    phase_path = folder / "initial_optimization/result.json"
    if not phase_path.exists():
        _require(
            not result["generations"]
            and result.get("time_budget", {}).get("exhausted"),
            "Model started before initial optimization ended",
        )
        return count
    phase = read(phase_path)
    phase_folder = phase_path.parent
    audit_discovery_limit(phase_folder, phase)
    marker = read(phase_folder / "started.json")
    certificates = read(phase_folder / "certificates.json")
    _require(
        phase["spec"] == marker["spec"]
        and phase["spec"]["methods"] == config["initial_deterministic_methods"]
        and phase["spec"]["seconds"] == config["initial_deterministic_seconds"]
        and phase["spec"]["proof_sha256"] == fingerprint(row["src"])
        and phase["started_epoch"] == marker["started_epoch"]
        and phase["deadline_epoch"] == marker["deadline_epoch"]
        and phase["started_epoch"] >= measurement["finished_epoch"]
        and phase["deadline_epoch"] - phase["started_epoch"]
        <= config["initial_deterministic_seconds"] + 1e-5
        and phase["certificates_sha256"] == digest(phase_folder / "certificates.json"),
        "Initial optimizer identity or time cap changed",
    )
    _require(
        certificates[0]["proof"] == row["src"]
        and certificates[0]["evaluation"] == evaluation,
        "Initial optimizer used a preprocessed seed",
    )
    prior = evaluation["scores"]["combined_pct"]
    for certificate in certificates[1:]:
        count += _evaluation(
            row,
            reference,
            certificate["proof"],
            certificate["evaluation"],
            "initial certificate",
        )
        value = certificate["evaluation"]["scores"]["combined_pct"]
        _require(
            value > prior + config["selection_margin_pp"]
            and phase["started_epoch"]
            <= datetime.fromisoformat(certificate["at"]).timestamp()
            <= phase["deadline_epoch"],
            "Initial optimizer accepted a regressive or late certificate",
        )
        prior = value
    _require(
        phase["proof"] == certificates[-1]["proof"]
        and phase["evaluation"] == certificates[-1]["evaluation"]
        and abs(phase["gain_pp"] - (prior - evaluation["scores"]["combined_pct"]))
        < 1e-9
        and phase["accepted_improvements"] == len(certificates) - 1,
        "Initial optimizer lost its best verified certificate",
    )
    for relative, expected in phase["stage_result_sha256"].items():
        _require(
            digest(phase_folder / relative) == expected,
            "Initial stage evidence changed",
        )
    if phase["status"] == "time_limit" and (phase_folder / "stopped.json").exists():
        stopped = read(phase_folder / "stopped.json")
        _require(
            stopped["work_stopped_epoch"] == phase["work_stopped_epoch"]
            and stopped["work_stopped_epoch"] >= phase["deadline_epoch"],
            "Missing initial hard-stop evidence",
        )
    if (folder / "initial_phase.json").exists():
        boundary = read(folder / "initial_phase.json")
        _require(
            boundary["measurement_sha256"] == digest(measurement_path)
            and boundary["optimization_sha256"] == digest(phase_path),
            "Initial phase evidence changed",
        )
        checks_path = folder / "evidence/checks.jsonl"
        checks = (
            [json.loads(line) for line in checks_path.read_text().splitlines()]
            if checks_path.exists()
            else []
        )
        checkpoint = bool(config.get("deterministic_checkpoint"))
        starting_proof = bool(config.get("starting_proofs"))
        expected = (
            1 if phase["accepted_improvements"] or checkpoint or starting_proof else 0
        )
        origin = (
            "initial_starting_proof"
            if starting_proof
            else "initial_checkpoint" if checkpoint else "initial_harness"
        )
        _require(
            boundary["check_end"] == expected
            and all(c["origin"] == origin for c in checks[:expected])
            and all(
                c["origin"]
                not in (
                    "initial_harness",
                    "initial_checkpoint",
                    "initial_starting_proof",
                )
                for c in checks[expected:]
            ),
            "Deterministic work occurred after model search",
        )
        if starting_proof:
            from .starting import audit_starting_proof

            _require(
                not config["initial_deterministic_methods"] and not checkpoint,
                "Explicit starting state used in-cell deterministic cleanup",
            )
            audit_starting_proof(config, folder, row, checks, result)
        elif checkpoint:
            from .checkpoint import audit_checkpoint

            audit_checkpoint(config, folder, row, checks)
            saved = read(folder / "checkpoint.json")
            _require(
                result["model_start_score"] == saved["model_start_score"]
                and abs(
                    result["model_gain_pp"]
                    - (
                        result["selected_evaluation"]["scores"]["combined_pct"]
                        - saved["model_start_score"]
                    )
                )
                < 1e-9,
                "Checkpoint model gain changed",
            )
        elif expected:
            _require(
                checks[0]["code"] == phase["proof"]
                and checks[0]["evaluation"] == phase["evaluation"],
                "Initial certificate was not adopted into the ledger",
            )
        for attempt in folder.glob("attempt_*/attempt.json"):
            _require(
                read(attempt)["admitted_epoch"] >= boundary["finished_epoch"],
                "Model started before initial work completed",
            )
    else:
        _require(not result["generations"], "Missing initial phase boundary")
    return count
