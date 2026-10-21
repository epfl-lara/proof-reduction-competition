"""Recovery retains audited successes and starts only incomplete cells afresh."""

import json

import pytest
from test_search_exploration import ROW, SearchPlan, discovery, run

from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.optimization.exploration_reporting import report_exploration
from proof_eval.optimization.exploration_reuse import freeze_completed, reused_records

__all__ = ["discovery"]


def test_recovery_pins_complete_cells_without_copying_or_changing_source(
    tmp_path, discovery
):
    source = tmp_path / "source"
    cell = source / "conditions/test/cells/p"
    plan = SearchPlan(methods=("simp",), strategy="sweep")
    result, _, checked = run(cell, plan)
    write_json(
        cell / "result.json", {**read(cell / "result.json"), "condition": "test"}
    )
    refs = tmp_path / "refs.jsonl"
    refs.write_text(
        json.dumps(
            {
                "name": "p",
                "per_version": {
                    v: {
                        "heartbeats": 1000,
                        "provenance": {"environment_fingerprint": "env_" + v},
                    }
                    for v in ("v1", "v2")
                },
            }
        )
        + "\n"
    )
    config = {
        "names": ["p", "pending"],
        "conditions": {"test": plan.record()},
        "input_sha256": {"p": fingerprint(ROW), "pending": "fixture"},
        "dataset_sha256": "dataset",
        "environments_sha256": "env",
        "references_sha256": digest(refs),
        "references": str(refs),
        "scope": "test recovery",
    }
    write_json(source / "config.json", config)
    write_json(
        source / "conditions/test/cells/pending/result.json",
        {"name": "pending", "status": "incomplete"},
    )
    packs = {"p": {"row": ROW}, "pending": {"row": ROW}}
    before = {str(p): digest(p) for p in source.rglob("*") if p.is_file()}
    reuse = freeze_completed(source, config, packs)
    assert set(reuse["cells"]["test"]) == {"p"}
    assert before == {str(p): digest(p) for p in source.rglob("*") if p.is_file()}
    config["recovery_sources"] = reuse
    output = tmp_path / "recovered"
    write_json(output / "config.json", config)
    partial = report_exploration(output)
    assert partial["conditions"]["test"]["terminal"] == 1
    assert partial["conditions"]["test"]["mean_gain_pp"] is None
    assert not (output / "conditions/test/cells/p").exists()
    write_json(
        output / "conditions/test/cells/pending/result.json",
        {**result, "name": "pending"},
    )
    write_json(output / "conditions/test/cells/pending/audit.json", checked)
    assert report_exploration(output)["status"] == "complete"
    write_json(cell / "result.json", {**read(cell / "result.json"), "gain_pp": 123})
    with pytest.raises(ValueError, match="source evidence changed"):
        reused_records(config, "test")


def test_recovery_rejects_changed_plans_and_active_sources(tmp_path):
    source = tmp_path / "source"
    config = {"names": [], "conditions": {"a": {}}}
    write_json(source / "config.json", config)
    write_json(source / "run.json", {"status": "running"})
    with pytest.raises(ValueError, match="active"):
        freeze_completed(source, config, {})
    write_json(source / "run.json", {"status": "incomplete"})
    with pytest.raises(ValueError, match="contract changed: conditions"):
        freeze_completed(source, {**config, "conditions": {"b": {}}}, {})
