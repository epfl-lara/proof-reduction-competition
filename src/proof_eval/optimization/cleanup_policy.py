"""Best-effort cleanup outcomes and recovery from saved proof certificates."""

from __future__ import annotations

import json
import time
from pathlib import Path

from proof_eval.evidence.audit import _evaluation, _require
from proof_eval.evidence.io import digest, fingerprint, read, sha, write_json
from proof_eval.verification.references import original_evaluation, require_valid, score

POLICY = "best_effort_verified"


def lineage(selected: dict) -> dict:
    value = selected["lineage"]
    return {
        **value,
        "origin_kind": value.get("origin_kind", value["kind"]),
        "kind": "deterministic",
    }


def search_skips(search: Path) -> list[dict]:
    """Keep the raw search's failed methods visible without withholding its proof."""
    skips = []
    for key in read(search / "progress.json")["expansions"]:
        folder = search / "expansions" / key
        result = read(folder / "result.json")
        if result["status"] != "incomplete":
            continue
        optimizer = read(folder / "optimizer.json")
        events = [
            json.loads(s) for s in (folder / "trials.jsonl").read_text().splitlines()
        ]
        skips.append(
            {
                "method": result["identity"]["method"],
                "reason": result["stop_reason"],
                "error": optimizer.get("error")
                or next(
                    (
                        e.get("message")
                        for e in reversed(events)
                        if e.get("kind") == "discovery_error"
                    ),
                    None,
                ),
                "expansion": key,
            }
        )
    return skips


def completed_search(result: dict, search: Path) -> dict:
    """A verified output is complete even when optional search methods were skipped."""
    skipped = search_skips(search)
    return {
        **result,
        "status": "complete",
        "search_status": result["status"],
        "cleanup_outcome": "completed_with_skips" if skipped else "complete",
        "skipped_methods": skipped,
    }


def verified_inputs(
    packs: dict, selected: dict, references: dict, records: dict | None
) -> dict:
    """Freeze existing certificates for use only if optional cleanup cannot run."""
    frozen = {}
    for name, pack in packs.items():
        original = {
            "proof": pack["row"]["src"],
            "evaluation": original_evaluation(pack),
            "lineage": {"kind": "original"},
            "basis": "pinned_original_reference",
        }
        choices = [original]
        if records and name in records:
            record = records[name]
            proof = record.get("proof", record.get("selected_proof"))
            evaluation = record.get("evaluation", record.get("selected_evaluation"))
            _require(
                proof == selected["cells"][name]["proof"],
                "Cleanup fallback input changed",
            )
            choices.append(
                {
                    "proof": proof,
                    "evaluation": evaluation,
                    "lineage": selected["cells"][name]["lineage"],
                    "basis": "verified_input",
                }
            )
        for item in choices:
            require_valid(item["evaluation"], pack["row"], item["proof"])
            _evaluation(
                pack["row"],
                references[name],
                item["proof"],
                item["evaluation"],
                "cleanup fallback input",
            )
        frozen[name] = max(choices, key=lambda item: score(item["evaluation"]))
    return frozen


def _fallback_candidates(
    folder: Path, config: dict, row: dict, reference: dict
) -> tuple[list[dict], dict]:
    initial = config["verified_fallbacks"][row["name"]]
    selected = config["starting_proofs"]["cells"][row["name"]]
    if initial["basis"] == "pinned_original_reference":
        _require(
            initial["proof"] == row["src"]
            and initial["lineage"] == {"kind": "original"},
            "Cleanup original fallback changed",
        )
    else:
        _require(
            initial["basis"] == "verified_input"
            and initial["proof"] == selected["proof"]
            and initial["lineage"] == selected["lineage"],
            "Cleanup verified input fallback changed",
        )
    choices, evidence = [initial], {}
    seed_path = folder / "seed.json"
    if seed_path.exists():
        seed = read(seed_path)
        _require(
            seed["proof"] == selected["proof"]
            and seed["state_sha256"] == fingerprint(selected),
            "Cleanup fallback seed changed",
        )
        choices.append(
            {
                "proof": seed["proof"],
                "evaluation": seed["evaluation"],
                "lineage": selected["lineage"],
                "basis": "verified_seed",
            }
        )
        evidence["seed.json"] = digest(seed_path)
        nodes = {p.stem: (p, read(p)) for p in (folder / "search/nodes").glob("*.json")}
        certified = {sha(seed["proof"])}
        pending = dict(nodes)
        while pending:
            added = []
            for key, (path, node) in pending.items():
                if key not in certified and node["parent"] not in certified:
                    continue
                _require(
                    sha(node["proof"]) == key, "Cleanup fallback node identity changed"
                )
                if node["parent"] is None:
                    _require(
                        node["proof"] == seed["proof"]
                        and node["evaluation"] == seed["evaluation"],
                        "Cleanup fallback root changed",
                    )
                else:
                    _require(
                        node["parent"] in nodes
                        and score(node["evaluation"])
                        > score(nodes[node["parent"]][1]["evaluation"])
                        + config["plan"]["budget"]["min_gain"],
                        "Cleanup fallback edge changed",
                    )
                choices.append(
                    {
                        "proof": node["proof"],
                        "evaluation": node["evaluation"],
                        "lineage": selected["lineage"],
                        "basis": "verified_checkpoint",
                    }
                )
                evidence[str(path.relative_to(folder))] = digest(path)
                certified.add(key)
                added.append(key)
            if not added:
                raise ValueError("Unlinked cleanup fallback certificate")
            for key in added:
                del pending[key]
    for item in choices:
        require_valid(item["evaluation"], row, item["proof"])
        _evaluation(
            row, reference, item["proof"], item["evaluation"], "cleanup fallback"
        )
    return choices, evidence


def recover_cell(
    folder: Path, config: dict, row: dict, reference: dict, reason: str
) -> dict:
    """Finalize a failed/abandoned worker without dispatching any search or verifier."""
    choices, evidence = _fallback_candidates(folder, config, row, reference)
    best = max(choices, key=lambda item: score(item["evaluation"]))
    incoming = config["verified_fallbacks"][row["name"]]
    for name in ("failure.json", "worker_termination.json"):
        if (folder / name).exists():
            evidence[name] = digest(folder / name)
    result = {
        "name": row["name"],
        "status": "complete",
        "search_status": "skipped",
        "cleanup_outcome": "skipped",
        "skipped_methods": [],
        "proof": best["proof"],
        "evaluation": best["evaluation"],
        "lineage": lineage(best),
        "input_score": score(incoming["evaluation"]),
        "gain_pp": score(best["evaluation"]) - score(incoming["evaluation"]),
        "elapsed_seconds": time.time() - read(folder / "started.json")["epoch"],
        "fallback": {
            "reason": reason,
            "basis": best["basis"],
            "evidence_sha256": evidence,
        },
    }
    write_json(folder / "result.json", result)
    return result


def audit_fallback(folder: Path, config: dict, row: dict, reference: dict) -> dict:
    result = read(folder / "result.json")
    _require(
        config.get("cleanup_failure_policy") == POLICY, "Unconfigured cleanup fallback"
    )
    choices, evidence = _fallback_candidates(folder, config, row, reference)
    best = max(choices, key=lambda item: score(item["evaluation"]))
    incoming = config["verified_fallbacks"][row["name"]]
    for relative, expected in result["fallback"]["evidence_sha256"].items():
        _require(
            digest(folder / relative) == expected, "Cleanup fallback evidence changed"
        )
    _require(
        all(
            result["fallback"]["evidence_sha256"].get(k) == v
            for k, v in evidence.items()
        ),
        "Cleanup fallback evidence omitted",
    )
    _require(
        result["name"] == row["name"]
        and result["status"] == "complete"
        and result["search_status"] == result["cleanup_outcome"] == "skipped"
        and not result["skipped_methods"]
        and bool(result["fallback"]["reason"])
        and result["fallback"]["basis"] == best["basis"]
        and result["proof"] == best["proof"]
        and result["evaluation"] == best["evaluation"]
        and result["lineage"] == lineage(best)
        and result["input_score"] == score(incoming["evaluation"])
        and abs(
            result["gain_pp"]
            - (score(best["evaluation"]) - score(incoming["evaluation"]))
        )
        < 1e-9,
        "Cleanup fallback output changed",
    )
    return {
        "status": "passed",
        "nodes": len(choices),
        "checked_version_outcomes": sum(
            len(item["evaluation"]["per_version"]) for item in choices
        ),
    }
