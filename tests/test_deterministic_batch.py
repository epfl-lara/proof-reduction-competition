"""Batch contracts, relocation, and a real non-warm-up Lean end-to-end run."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from proof_eval import Evaluator
from proof_eval.metrics import token_count
from process_benchmark import process_problem
from run_deterministic_batch import BatchConfig, METHODS, REPEAT, REPOSITORY, _validate, run_batch


def test_invalid_batch_budgets_and_methods():
    config = BatchConfig("d", "e", "c", "r", "o")
    for values in ({"workers": 0}, {"max_sweeps": -1}, {"min_gain": float("nan")},
                   {"methods": ()}, {"methods": ("lint", "lint")}, {"methods": ("unknown",)}):
        with pytest.raises(ValueError):
            _validate(replace(config, **values))


@pytest.fixture
def tiny_batch(tmp_path):
    if not shutil.which("elan") or not shutil.which("lake"):
        pytest.skip("Lean/Lake unavailable")
    installed = subprocess.check_output(["elan", "toolchain", "list"], text=True)
    if "leanprover/lean4:v4.25.0" not in installed:
        pytest.skip("Lean v4.25.0 unavailable")
    project = tmp_path / "project"
    project.mkdir()
    (project / "lean-toolchain").write_text("leanprover/lean4:v4.25.0\n")
    (project / "lakefile.toml").write_text('name = "batch_test"\nversion = "0.1.0"\n')
    (project / "lake-manifest.json").write_text(json.dumps({
        "version": "1.1.0", "name": "batch_test", "lakeDir": ".lake", "packagesDir": ".lake/packages", "packages": []}))
    proof = "theorem fresh_α (n : Nat) : n = n := by\n  have h : n = n := by rfl\n  exact h"
    (project / "Example.lean").write_text("import Lean\nnamespace NewBatch\n" + proof + "\nend NewBatch\n")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(project), *args], text=True).strip()
    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Batch Test", "-c", "user.email=batch@example.invalid", "commit", "-qm", "Fixture")
    row = {"name": "NewBatch.fresh_α", "source": "new_batch_fixture", "statement": proof.split(" := by")[0],
           "src": proof, "proof_length": token_count(proof.split(" :=", 1)[1]),
           "file_path": "Example.lean", "version_info": [{"v4.25.0": git("rev-parse", "HEAD")}]}
    dataset = tmp_path / "new.jsonl"
    dataset.write_text(json.dumps(row, ensure_ascii=False) + "\n")
    environments = tmp_path / "environments.json"
    environments.write_text(json.dumps({"projects": [{"source": row["source"], "version": "v4.25.0", "path": str(project)}]}))
    cache = tmp_path / "cache"
    evaluator = Evaluator(dataset, environments, cache)
    exported = process_problem(evaluator, row, versions="all", dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest())
    assert exported["status"] == "prepared", exported
    references = tmp_path / "references.jsonl"
    references.write_text(json.dumps(exported) + "\n")
    config = BatchConfig(dataset, environments, cache, references, tmp_path / "output",
                         workers=1, max_rounds=1, max_trials=2, max_sites=1, max_sweeps=0)
    return config, row


def reference_bytes(config):
    return {p.name: p.read_bytes() for p in Path(config.cache).glob("references/*.json")}


def test_real_new_dataset_full_portfolio_and_resume_outside_repo(tiny_batch, tmp_path):
    config, row = tiny_batch
    config = replace(config, max_sweeps=2)
    before = reference_bytes(config)
    command = [sys.executable, str(REPOSITORY / "src/run_deterministic_batch.py")]
    for key in ("dataset", "environments", "cache", "references", "output", "workers", "max_rounds", "max_trials", "max_sites", "max_sweeps"):
        command.extend(["--" + key.replace("_", "-"), str(getattr(config, key))])
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["status"] == "finished"
    assert [stage["method"] for stage in manifest["stages"]] == list(METHODS) + list(REPEAT) * len(manifest["sweeps"])
    assert 1 <= len(manifest["sweeps"]) <= 2
    assert manifest["stop_reason"] in {"sweep_limit", "no_improvement_in_bounded_portfolio_sweep"}
    assert manifest["problem_count"] == manifest["expected_version_checks"] == manifest["passed_version_checks"] == 1
    submission = Path(manifest["submission"]).read_bytes()
    assert json.loads(submission)["name"] == row["name"]
    assert json.loads(submission)["proof"].startswith(row["statement"])
    assert reference_bytes(config) == before
    trial_hashes = {p: p.read_bytes() for p in Path(config.output).rglob("trials_*.jsonl")}
    resumed = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert Path(manifest["submission"]).read_bytes() == submission
    assert all(path.read_bytes() == data for path, data in trial_hashes.items())
    assert reference_bytes(config) == before
    changed = run_error(command + ["--max-trials", "3"], tmp_path)
    assert "changed" in changed["error"]
    assert Path(manifest["submission"]).read_bytes() == submission


def run_error(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 2, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_missing_or_mismatched_reference_fails_before_stage(tiny_batch, monkeypatch):
    config, _ = tiny_batch
    launched = []
    monkeypatch.setattr("run_deterministic_batch._run_stage", lambda command: launched.append(command))
    before = reference_bytes(config)
    exported = json.loads(Path(config.references).read_text())
    exported["per_version"]["v4.25.0"]["heartbeats"] += 1
    Path(config.references).write_text(json.dumps(exported) + "\n")
    with pytest.raises(ValueError, match="mismatch"):
        run_batch(config)
    assert not launched
    assert reference_bytes(config) == before


def test_unavailable_stage_has_no_submission(tiny_batch, monkeypatch):
    config, _ = tiny_batch
    monkeypatch.setattr("run_deterministic_batch._run_stage", lambda command: 2)
    result = run_batch(config)
    assert result["status"] == "unavailable"
    assert not (Path(config.output) / "submission.jsonl").exists()
    assert json.loads((Path(config.output) / "batch.json").read_text())["status"] == "unavailable"


def test_process_failure_preserves_interrupted_manifest(tiny_batch, monkeypatch):
    config, _ = tiny_batch
    monkeypatch.setattr("run_deterministic_batch._run_stage", lambda command: -15)
    with pytest.raises(RuntimeError, match="code -15"):
        run_batch(config)
    record = json.loads((Path(config.output) / "batch.json").read_text())
    assert record["status"] == "interrupted"
    assert record["active_stage"].endswith("01_linter_deletion")
    assert not (Path(config.output) / "submission.jsonl").exists()


def test_relocated_historical_input_resolves_without_modifying_record(tmp_path, monkeypatch):
    from audit_experiments import _input_proofs
    monkeypatch.chdir(tmp_path)
    code = "theorem x : True := by trivial"
    moved = tmp_path / "results/deterministic/11_repeated_sweeps/sweep_01/10_simp/candidates.jsonl"
    moved.parent.mkdir(parents=True)
    moved.write_text(json.dumps({"name": "x", "proof": code}) + "\n")
    stage = tmp_path / "results/deterministic/11_repeated_sweeps/sweep_02/01_wrappers"
    stage.mkdir(parents=True)
    record = {"input_path": "results/11_repeated_sweeps/sweep_01/10_simp/candidates.jsonl",
              "input_sha256": hashlib.sha256(moved.read_bytes()).hexdigest()}
    assert _input_proofs(stage, record, {"x": {"src": "original"}}, None) == {"x": code}
    assert record["input_path"].startswith("results/11_")
