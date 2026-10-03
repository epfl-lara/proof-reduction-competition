"""Meaningful denominators, repairs, fallbacks, and paired-effect reporting."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import report_repair_matrix as reporter
from report_one_shot import FIELDS, digest, read_json, write_json


ARMS = ["plain", "cards", "goals", "cards_goals", "cards_goals_costs"]
MODEL = "test/model"


def evaluation(score=0, status="passed"):
    valid = status == "passed"
    return {"status": status, "primary_version": "v1",
            "scores": dict.fromkeys(FIELDS, score),
            "per_version": {"v1": {"status": "passed" if valid else status, "passed": valid}}}


def generation(content="proof", *, status="received", truncated=False):
    return {"status": status, "content": content, "finish_reason": "length" if truncated else "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20,
                      "completion_tokens_details": {"reasoning_tokens": 15}},
            "reasoning_characters": 100, "elapsed_seconds": 2.5}


class MatrixFixture:
    def __init__(self, root, arms=ARMS):
        self.base, self.output = root / "base", root / "repair"
        (self.base / "inputs").mkdir(parents=True)
        self.output.mkdir()
        self.names = ["p", "q"]
        self.arms = arms
        self.packs, self.keys = {}, {}
        config = {"names": self.names, "models": [MODEL], "arms": arms,
                  "temperature": .3, "reasoning_effort": "high", "max_tokens": 32768}
        write_json(self.base / "config.json", config)
        for name, score in zip(self.names, (50.0, 60.0)):
            pack = {"name": name, "row": {"source": "fixture", "version_info": [{"v1": "commit"}]},
                    "proof": "incumbent " + name, "incumbent": evaluation(score)}
            self.packs[name] = pack
            write_json(self.base / "inputs" / (name + ".json"), pack)
        cells, index = [], {}
        for arm in arms:
            for name in self.names:
                key = hashlib.sha256((name + arm).encode()).hexdigest()
                self.keys[arm, name] = key
                cells.append({"key": key, "logical": [name, arm, MODEL]})
                index[json.dumps([name, arm, MODEL])] = key
                self.write_initial(arm, name)
        write_json(self.base / "cell_index.json", index)
        write_json(self.output / "matrix_config.json", {
            "base_directory": str(self.base), "base_config_sha256": digest(self.base / "config.json"),
            "base_index_sha256": digest(self.base / "cell_index.json"), "base_names": self.names,
            "models": [MODEL], "arms": arms, "cells": cells, "max_rounds": 3})

    def write_initial(self, arm, name, *, status="failed", score=0):
        key = self.keys[arm, name]
        folder = self.base / "cells" / key
        folder.mkdir(parents=True, exist_ok=True)
        incumbent = self.packs[name]
        record = {"name": name, "arm": arm, "model": MODEL, "source": "fixture", "request_sha256": key,
                  "evaluation": evaluation(score, status), "generation": generation("initial " + name),
                  "selected_proof": incumbent["proof"], "selected_evaluation": incumbent["incumbent"], "accepted": False}
        write_json(folder / "result.json", record)

    def write_final(self, arm, name, *, score, status="passed", incumbent=False, rounds=1, truncated=False):
        key = self.keys[arm, name]
        pack = self.packs[name]
        folder = self.output / "cells" / key
        folder.mkdir(parents=True, exist_ok=True)
        final_evaluation = evaluation(score, status)
        valid = status == "passed"
        proof = pack["proof"] if incumbent else ("" if truncated or status == "unavailable" else "changed " + name)
        accepted = valid and score > pack["incumbent"]["scores"]["combined_pct"] + .05
        initial = read_json(self.base / "cells" / key / "result.json")
        initial_valid = initial["evaluation"]["status"] == "passed"
        record = {"name": name, "arm": arm, "model": MODEL, "source": "fixture", "base_request_sha256": key,
                  "initial_kind": "already_valid" if initial_valid else "compiler_repair", "initial_valid": initial_valid,
                  "round_count": rounds, "max_rounds": 3, "outcome": "already_valid" if initial_valid else "repaired_valid" if valid else "unavailable" if status == "unavailable" else "repair_budget_exhausted",
                  "final_valid": valid, "final_proof": proof, "final_evaluation": final_evaluation,
                  "returned_incumbent": valid and incumbent, "accepted": accepted,
                  "selected_proof": proof if accepted else pack["proof"],
                  "selected_evaluation": final_evaluation if accepted else pack["incumbent"], "rounds": []}
        for number in range(1, rounds + 1):
            path = folder / "rounds" / f"{number:02d}"
            path.mkdir(parents=True, exist_ok=True)
            gen = generation(proof, status="transport_error" if status == "unavailable" else "received", truncated=truncated)
            trial = {"round": number, "request_sha256": "request-" + str(number), "generation": gen,
                     "proof": proof, "evaluation": final_evaluation}
            write_json(path / "generation.json", gen)
            write_json(path / "result.json", trial)
            record["rounds"].append({"round": number, "request_sha256": trial["request_sha256"]})
        write_json(folder / "result.json", record)
        return folder


def test_initial_denominator_completes_before_repairs_and_pending_calls_are_counted(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    data.write_final("plain", "p", score=55)
    pending = data.output / "cells" / data.keys["plain", "q"] / "rounds" / "01"
    pending.mkdir(parents=True)
    write_json(pending / "request_started.json", {"started_at": "now"})
    report = reporter.run(data.output)
    condition = report["conditions"][0]
    assert report["status"] == "incomplete"
    assert condition["initial_raw_mean"]["combined_pct"] == 0
    assert condition["repaired_raw_mean"]["combined_pct"] is None
    assert condition["selected_mean"]["combined_pct"] is None
    assert condition["observed_selected_mean"]["combined_pct"] == 55
    assert condition["additional_repair_generation"]["request_attempts"] == 2
    assert condition["additional_repair_generation"]["pending_generations"] == 1
    assert condition["additional_repair_generation"]["completion_tokens"] == 20


def test_infrastructure_unknown_is_not_failure_zero_and_fallback_remains_known(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    data.write_initial("plain", "q", status="unavailable", score=None)
    data.write_final("plain", "p", score=0, status="failed")
    data.write_final("plain", "q", score=None, status="unavailable")
    report = reporter.run(data.output)
    c = report["conditions"][0]
    assert c["initial_raw_mean"]["combined_pct"] is None
    assert c["repaired_raw_mean"]["combined_pct"] is None
    assert c["repaired_scored"] == c["initial_scored"] == 1
    assert c["observed_repaired_raw_mean"]["combined_pct"] == 0
    assert c["selected_mean"]["combined_pct"] == 55
    assert c["accepted_improvements"] == 0
    assert "portfolio" not in report
    assert not (data.output / "portfolio").exists()


def test_incumbent_returns_are_valid_recovery_but_not_improvement(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    data.write_final("plain", "p", score=50, incumbent=True)
    data.write_final("plain", "q", score=30)
    report = reporter.run(data.output)
    c = report["conditions"][0]
    assert c["final_all_versions_valid"] == c["repaired_valid"] == 2
    assert c["returned_incumbent"] == c["returned_incumbent_after_repair"] == 1
    assert c["valid_changed_proposals"] == 1
    assert c["accepted_improvements"] == 0
    assert c["repaired_raw_mean"]["combined_pct"] == 40
    assert c["selected_mean"]["combined_pct"] == 55


def test_factorial_and_cost_contrasts_pair_corrected_selected_scores(tmp_path):
    data = MatrixFixture(tmp_path)
    values = {"plain": [51, 60], "cards": [53, 61], "goals": [50, 64],
              "cards_goals": [55, 63], "cards_goals_costs": [54, 60]}
    for arm, scores in values.items():
        for name, score in zip(data.names, scores):
            data.write_final(arm, name, score=score)
    report = reporter.run(data.output)
    effects = {e["contrast"]: e for e in report["paired_contrasts"]}
    assert effects["cards_main_effect"]["corrected_selected_mean_delta_pp"] == 1.75
    assert effects["goals_main_effect"]["corrected_selected_mean_delta_pp"] == 1.75
    assert effects["cards_goals_interaction"]["corrected_selected_mean_delta_pp"] == .5
    assert effects["costs_minus_cards_goals"]["corrected_selected_mean_delta_pp"] == -2
    assert effects["cards_minus_plain"]["accepted_rate_delta_pp"] == 50
    assert all(e["expected_pairs"] == e["recorded_pairs"] == 2 for e in effects.values())
    for path in data.output.glob("*.csv"):
        assert b"\r" not in path.read_bytes()
    assert "not one HTTP request" in (data.output / "README.md").read_text()
    assert len(report["sources"]) == 5


def test_reasoning_truncation_counts_extra_calls_without_double_counting_tokens(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    data.write_final("plain", "p", score=0, status="invalid", truncated=True)
    data.write_initial("plain", "q", score=60, status="passed")
    data.write_final("plain", "q", score=60, incumbent=True, rounds=0)
    report = reporter.run(data.output)
    stats = report["totals"]["additional_repair_generation"]
    assert stats["request_attempts"] == 1
    assert stats["truncated"] == stats["truncated_empty_final_with_reasoning"] == 1
    assert stats["reasoning_tokens"] == 15 and stats["completion_tokens"] == 20
    assert stats["request_elapsed_seconds_sum"] == 2.5
    assert report["totals"]["initial_generation"]["request_attempts"] == 2
    assert report["totals"]["returned_incumbent_after_repair"] == 0


def test_missing_final_round_and_false_validity_labels_are_rejected(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    folder = data.write_final("plain", "p", score=55)
    target = folder / "result.json"
    record = read_json(target)
    changed = deepcopy(record)
    changed["final_valid"] = False
    write_json(target, changed)
    with pytest.raises(ValueError, match="all-version validity"):
        reporter.run(data.output)
    write_json(target, record)
    (folder / "rounds" / "01" / "result.json").unlink()
    with pytest.raises(ValueError, match="rounds are incomplete"):
        reporter.run(data.output)


def test_relocated_base_override_and_planned_cohort_preserve_denominator(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    config = read_json(data.output / "matrix_config.json")
    config["base_directory"] = "/unavailable/old/base"
    write_json(data.output / "matrix_config.json", config)
    missing = data.base / "cells" / data.keys["plain", "q"] / "result.json"
    missing.unlink()
    report = reporter.run(data.output, base=data.base)
    assert report["planned_cells"] == 2 and report["initial_recorded_cells"] == 1
    assert report["conditions"][0]["initial_raw_mean"]["combined_pct"] is None
    assert report["conditions"][0]["expected_problems"] == 2


def test_condition_exports_require_the_complete_original_cohort(tmp_path):
    data = MatrixFixture(tmp_path / "full", arms=["plain"])
    data.write_final("plain", "p", score=55)
    partial = reporter.run(data.output)
    assert partial["condition_exports"] == []
    assert not (data.output / "conditions").exists()
    data.write_final("plain", "q", score=60, incumbent=True)
    complete = reporter.run(data.output)
    assert len(complete["condition_exports"]) == 1
    item = complete["condition_exports"][0]
    target = data.output / item["submission"]
    candidates = [json.loads(line) for line in target.read_text().splitlines()]
    assert [row["name"] for row in candidates] == ["p", "q"]
    assert candidates[0]["proof"] == "changed p"
    assert candidates[1]["proof"] == "incumbent q"
    manifest = read_json(data.output / item["manifest"])
    assert manifest["candidates_sha256"] == digest(target)
    assert manifest["selected_mean"]["combined_pct"] == 57.5
    for row in manifest["problems"]:
        result = data.output / "cells" / row["base_request_sha256"] / "result.json"
        assert row["repair_result_sha256"] == digest(result)

    subset = MatrixFixture(tmp_path / "subset", arms=["plain"])
    config = read_json(subset.output / "matrix_config.json")
    config["cells"] = config["cells"][:1]
    write_json(subset.output / "matrix_config.json", config)
    subset.write_final("plain", "p", score=55)
    report = reporter.run(subset.output)
    assert report["status"] == "complete"
    assert report["conditions"][0]["expected_problems"] == 1
    assert report["condition_exports"] == []
    assert not (subset.output / "conditions").exists()
