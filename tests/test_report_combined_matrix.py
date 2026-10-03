"""Offline combined-report invariants: controls, selection, work and provenance."""
from copy import deepcopy
import hashlib
import json

import pytest

import report_combined_matrix as reporter
from proof_eval.one_shot import fingerprint
from report_one_shot import FIELDS, digest, read_json, write_json


MODEL = "fixture/model"
ARMS = ["plain", "cards", "goals", "cards_goals", "cards_goals_costs"]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def evaluation(value):
    return {"status": "passed", "scores": dict.fromkeys(FIELDS, value),
            "per_version": {v: {"status": "passed", "passed": True} for v in ("v1", "v2")}}


def branch(proof, value):
    return {"proof": proof, "evaluation": evaluation(value)}


class MatrixFixture:
    def __init__(self, root, arms=("plain",)):
        self.base, self.repair, self.output = (root / part for part in ("base", "repair", "combined"))
        for folder in (self.base / "inputs", self.repair, self.output):
            folder.mkdir(parents=True)
        self.names, self.arms = ["p", "q"], list(arms)
        self.packs, self.keys, self.controls, self.manifest = {}, {}, {}, {}
        write_json(self.base / "config.json", {"names": self.names, "models": [MODEL], "arms": self.arms})
        write_json(self.repair / "matrix_config.json", {"stage": "repair"})
        for name, value in zip(self.names, (40.0, 60.0)):
            pack = {"name": name, "proof": "incumbent " + name, "incumbent": evaluation(value),
                    "row": {"name": name, "source": "source_" + name, "version_info": [{"v1": "rev"}, {"v2": "rev"}]}}
            self.packs[name] = pack
            write_json(self.base / "inputs" / (name + ".json"), pack)
        cells, index = [], {}
        for arm in self.arms:
            for name in self.names:
                key = fingerprint([name, arm, MODEL])
                self.keys[arm, name] = key
                cells.append({"key": key, "logical": [name, arm, MODEL]})
                index[json.dumps([name, arm, MODEL])] = key
        write_json(self.base / "cell_index.json", index)
        file_hashes = {"inputs/" + name + ".json": digest(self.base / "inputs" / (name + ".json")) for name in self.names}
        write_json(self.base / "input_hashes.json", file_hashes)
        config = {"base_directory": str(self.base), "repair_directory": str(self.repair),
                  "base_config_sha256": digest(self.base / "config.json"),
                  "repair_matrix_config_sha256": digest(self.repair / "matrix_config.json"),
                  "base_index_sha256": digest(self.base / "cell_index.json"),
                  "base_input_hashes_sha256": digest(self.base / "input_hashes.json"),
                  "input_sha256": {name: fingerprint(pack) for name, pack in self.packs.items()},
                  "input_files_sha256": file_hashes,
                  "names": self.names, "models": [MODEL], "arms": self.arms, "cells": cells,
                  "controls": {name: self.job_key(name, pack["proof"]) for name, pack in self.packs.items()},
                  "methods": ["lint", "simp"], "budget": {"rounds": 3, "trials": 32, "sites": 6, "min_gain": .05}}
        write_json(self.output / "matrix_config.json", config)

    @staticmethod
    def job_key(name, proof):
        return fingerprint({"name": name, "proof_sha256": sha(proof)})

    def job(self, name, seed, initial, result_proof, result_score, origin, status="complete"):
        key = self.job_key(name, seed)
        folder = self.output / "jobs" / key
        folder.mkdir(parents=True, exist_ok=True)
        record = {"name": name, "source": "source_" + name, "input_proof": seed,
                  "input_proof_sha256": sha(seed), "proof": result_proof,
                  "initial_evaluation": evaluation(initial), "evaluation": evaluation(result_score),
                  "all_versions_valid": True, "status": status, "stages": [],
                  "counters": {"attempts": 3, "analysis_requests": 2, "lean_candidate_checks": 2,
                               "cache_hits": 1, "accepted_transitions": int(result_score > initial), "elapsed_seconds": 1.5},
                  "verification_accounting": "Excludes initial and final whole-proof verification."}
        if (folder / "result.json").exists():
            assert read_json(folder / "result.json") == record
        else:
            write_json(folder / "result.json", record)
        self.manifest.setdefault(key, {"name": name, "proof_sha256": sha(seed), "status": status, "origins": []})["origins"].append(origin)
        write_json(self.output / "jobs.json", {"jobs": self.manifest})
        return key, record

    def control(self, name, value=None, *, status="complete"):
        pack = self.packs[name]
        initial = pack["incumbent"]["scores"]["combined_pct"]
        value = initial + 2 if value is None else value
        key, job = self.job(name, pack["proof"], initial, "control " + name, value,
                            {"kind": "control", "name": name}, status)
        self.controls[name] = {"job_key": key, "proof": job["proof"], "evaluation": job["evaluation"],
                               "cleanup_status": status, "result_sha256": digest(self.output / "jobs" / key / "result.json")}
        write_json(self.output / "controls.json", self.controls)

    def cell(self, arm, name, *, final_score=None, cleaned_score=None, proof=None, selected="d1", status="complete"):
        key, pack = self.keys[arm, name], self.packs[name]
        d0 = {"proof": pack["proof"], "evaluation": pack["incumbent"]}
        control = self.controls[name]
        d1 = {field: control[field] for field in ("proof", "evaluation", "job_key")}
        f = branch(proof or ("proposal " + name + arm), final_score) if final_score is not None else None
        accepted = final_score is not None and final_score > pack["incumbent"]["scores"]["combined_pct"] + .05
        previous = f if accepted else d0
        cleaned, proposal_key = None, None
        if f:
            cleaned_score = final_score if cleaned_score is None else cleaned_score
            if f["proof"] == pack["proof"]:
                cleaned_proof, cleaned_score = d1["proof"], d1["evaluation"]["scores"]["combined_pct"]
            else:
                cleaned_proof = "cleaned " + f["proof"]
            proposal_key, job = self.job(name, f["proof"], final_score, cleaned_proof, cleaned_score,
                                         {"kind": "proposal", "cell_key": key}, status)
            cleaned = {"proof": job["proof"], "evaluation": job["evaluation"], "job_key": proposal_key}
        returned = f is not None and f["proof"].strip() == pack["proof"].strip()
        repair = {"name": name, "arm": arm, "model": MODEL, "accepted": accepted, "returned_incumbent": returned,
                  "selected_proof": previous["proof"], "selected_evaluation": previous["evaluation"],
                  "final_valid": f is not None, "final_proof": f["proof"] if f else "bad proof",
                  "final_evaluation": f["evaluation"] if f else {"status": "failed"}}
        repair_folder = self.repair / "cells" / key
        repair_folder.mkdir(parents=True, exist_ok=True)
        write_json(repair_folder / "result.json", repair)
        write_json(repair_folder / "cell_config.json", {"input_sha256": fingerprint(pack)})
        branches = {"d0": d0, "d1": d1, "l": previous, "f": f, "cleaned_f": cleaned}
        h = branches[selected]
        rescued = bool(f and not accepted and not returned and cleaned_score > pack["incumbent"]["scores"]["combined_pct"] + .05)
        record = {"name": name, "source": pack["row"]["source"], "arm": arm, "model": MODEL, "key": key,
                  "repair_result_sha256": digest(repair_folder / "result.json"),
                  "repair_cell_config_sha256": digest(repair_folder / "cell_config.json"), "input_sha256": fingerprint(pack),
                  **branches, "h": h, "selected_from": selected, "selected_proof": h["proof"], "selected_evaluation": h["evaluation"],
                  "all_versions_valid": True, "control_job_key": control["job_key"], "proposal_job_key": proposal_key,
                  "stage03_accepted": accepted, "returned_incumbent": returned,
                  "complete_cleanup": status == control["cleanup_status"] == "complete",
                  "rescued_vs_d0": rescued, "rescued_vs_d1": rescued and cleaned_score > d1["evaluation"]["scores"]["combined_pct"]}
        folder = self.output / "cells" / key
        folder.mkdir(parents=True, exist_ok=True)
        write_json(folder / "result.json", record)
        return folder / "result.json"


def test_partial_controls_and_cells_withhold_full_means_and_exports(tmp_path):
    data = MatrixFixture(tmp_path)
    data.control("p")
    data.cell("plain", "p", final_score=45, cleaned_score=46, selected="cleaned_f")
    report = reporter.run(data.output)
    assert report["status"] == "incomplete"
    assert report["baseline_d0_mean"]["combined_pct"] == 50
    assert report["control_d1_mean"]["combined_pct"] is None
    assert report["conditions"][0]["means"]["h"]["combined_pct"] is None
    assert not report["condition_exports"]
    data.control("q")
    report = reporter.run(data.output)
    assert report["control_d1_mean"]["combined_pct"] == 52
    assert report["conditions"][0]["means"]["h"]["combined_pct"] is None
    assert all(source["means"]["h"]["combined_pct"] is None for source in report["sources"])


def test_full_independent_condition_exports_with_exact_control_and_stage03_gains(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain", "cards"])
    for name in data.names:
        data.control(name)
    data.cell("plain", "p", final_score=45, cleaned_score=46, selected="cleaned_f")
    data.cell("plain", "q")
    report = reporter.run(data.output)
    condition = report["conditions"][0]
    assert condition["complete"] and report["status"] == "incomplete"
    assert condition["means"]["l"]["combined_pct"] == 52.5
    assert condition["means"]["h"]["combined_pct"] == 54
    assert condition["gain_h_minus_d1_pp"] == 2
    assert condition["gain_h_minus_l_pp"] == 1.5
    assert condition["selected_version_checks"] == 4
    assert len(report["condition_exports"]) == 1
    export = data.output / report["condition_exports"][0]["submission"]
    assert [json.loads(line)["name"] for line in export.read_text().splitlines()] == data.names
    manifest = read_json(export.with_name("manifest.json"))
    assert manifest["candidates_sha256"] == digest(export)
    assert all(item["job_result_sha256"] for item in manifest["problems"])
    assert not (data.output / "portfolio").exists()
    assert not (data.output / "conditions" / "model__cards").exists()
    assert all(b"\r" not in path.read_bytes() for path in data.output.glob("*.csv"))


def test_shared_control_and_proposal_jobs_count_physical_work_once(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain", "cards"])
    for name in data.names:
        data.control(name)
        for arm in data.arms:
            data.cell(arm, name, final_score=data.packs[name]["incumbent"]["scores"]["combined_pct"], proof=data.packs[name]["proof"])
    report = reporter.run(data.output)
    work = report["work_accounting"]
    assert work["terminal_physical_jobs"] == work["distinct_jobs_in_recorded_references"] == 2
    assert work["total_recorded_cleanup_references"] == work["registered_logical_cleanup_origins"] == 6
    assert work["deduplicated_recorded_references"] == work["deduplicated_registered_origins"] == 4
    assert work["unique_terminal_job_counters"]["attempts"] == 6
    assert work["unique_terminal_job_counters"]["elapsed_seconds"] == 3
    assert all(c["rescued_vs_d0"] == c["rescued_vs_d1"] == 0 for c in report["conditions"])


def test_rejected_proposals_can_rescue_above_d0_without_beating_control(tmp_path):
    data = MatrixFixture(tmp_path)
    data.control("p", 42)
    data.control("q", 62)
    data.cell("plain", "p", final_score=38, cleaned_score=41)
    data.cell("plain", "q", final_score=59, cleaned_score=63, selected="cleaned_f")
    report = reporter.run(data.output)
    condition = report["conditions"][0]
    assert condition["rescued_vs_d0"] == 2
    assert condition["rescued_vs_d1"] == condition["improved_over_control"] == 1
    assert condition["means"]["l"]["combined_pct"] == 50
    assert condition["means"]["h"]["combined_pct"] == 52.5


def test_gain_below_original_margin_is_not_a_rescue_even_above_control(tmp_path):
    data = MatrixFixture(tmp_path)
    data.control("p", 40)
    data.control("q", 60)
    path = data.cell("plain", "p", final_score=39, cleaned_score=40.03)
    data.cell("plain", "q")
    report = reporter.run(data.output)
    assert report["conditions"][0]["rescued_vs_d1"] == 0
    record = read_json(path)
    record["rescued_vs_d1"] = True
    write_json(path, record)
    with pytest.raises(ValueError, match="Rescue flag"):
        reporter.run(data.output)


def test_exact_selection_preserves_l_and_prefers_control_on_ties(tmp_path):
    data = MatrixFixture(tmp_path)
    data.control("p", 45)
    data.control("q", 62)
    tied = data.cell("plain", "p", final_score=45, cleaned_score=45)
    # A .01 improvement between already-eligible alternatives must be retained.
    data.cell("plain", "q", final_score=62.01, cleaned_score=62.01, selected="l")
    report = reporter.run(data.output)
    assert report["conditions"][0]["means"]["h"]["combined_pct"] == pytest.approx(53.505)
    record = read_json(tied)
    record.update(selected_from="l", h=record["l"], selected_proof=record["l"]["proof"], selected_evaluation=record["l"]["evaluation"])
    write_json(tied, record)
    with pytest.raises(ValueError, match="exact eligible maximum"):
        reporter.run(data.output)


def test_incomplete_discovery_keeps_costs_but_blocks_full_means(tmp_path):
    data = MatrixFixture(tmp_path)
    data.control("p")
    data.control("q", status="incomplete_discovery")
    data.cell("plain", "p")
    data.cell("plain", "q")
    report = reporter.run(data.output)
    assert report["recorded_cells"] == 2 and report["complete_cleanup_cells"] == 1
    assert report["work_accounting"]["incomplete_discovery_jobs"] == 1
    assert report["work_accounting"]["unique_terminal_job_counters"]["attempts"] == 6
    assert report["conditions"][0]["means"]["h"]["combined_pct"] is None
    assert not report["condition_exports"]


def test_factorial_and_cost_effects_use_paired_h_scores(tmp_path):
    data = MatrixFixture(tmp_path, arms=ARMS)
    data.control("p", 40)
    data.control("q", 60)
    values = {"plain": [41, 61], "cards": [43, 62], "goals": [42, 65],
              "cards_goals": [46, 64], "cards_goals_costs": [45, 61]}
    for arm, values in values.items():
        for name, value in zip(data.names, values):
            data.cell(arm, name, final_score=value, cleaned_score=value, selected="l")
    report = reporter.run(data.output)
    effects = {row["contrast"]: row["combined_selected_mean_delta_pp"] for row in report["paired_contrasts"]}
    assert effects["cards_main_effect"] == 1.5
    assert effects["goals_main_effect"] == 2.5
    assert effects["cards_goals_interaction"] == 0
    assert effects["costs_minus_cards_goals"] == -2


@pytest.mark.parametrize("mutation,match", [("repair_hash", "Consumed repair result hash"),
                                         ("missing_version", "all-version valid"),
                                         ("input_fingerprint", "input fingerprint")])
def test_tampered_provenance_and_incomplete_version_evidence_are_rejected(tmp_path, mutation, match):
    data = MatrixFixture(tmp_path)
    data.control("p")
    data.control("q")
    path = data.cell("plain", "p")
    data.cell("plain", "q")
    record = read_json(path)
    if mutation == "repair_hash":
        record["repair_result_sha256"] = "changed"
    elif mutation == "missing_version":
        del record["l"]["evaluation"]["per_version"]["v2"]
    else:
        record["input_sha256"] = "changed"
    write_json(path, record)
    with pytest.raises(ValueError, match=match):
        reporter.run(data.output)


def test_partial_theorem_cohort_cannot_export_a_full_submission(tmp_path):
    data = MatrixFixture(tmp_path)
    config = read_json(data.output / "matrix_config.json")
    config["names"] = ["p"]
    config["cells"] = [cell for cell in config["cells"] if cell["logical"][0] == "p"]
    write_json(data.output / "matrix_config.json", config)
    with pytest.raises(ValueError, match="complete original theorem cohort"):
        reporter.run(data.output)
