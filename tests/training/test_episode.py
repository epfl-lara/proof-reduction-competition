"""Real host API wiring with deterministic compiler responses, no model calls."""

import json
from copy import deepcopy

import pytest

from proof_eval import Evaluator
from proof_eval.evidence.immutable import immutable
from proof_eval.training.episode import Episode
from proof_eval.training.prepare import original_pack
from proof_eval.training.reward import UnscorableEpisode
from proof_eval.verification.metrics import token_count, validate_candidate


class Compiler:
    def __init__(self):
        self.calls = []

    def fingerprint(self, row, version, project):
        return {"version": version, "source": "fixed-original"}

    def check(self, row, code, version, project):
        self.calls.append((code, version))
        return {
            "status": "passed",
            "passed": True,
            "heartbeats": 100,
            "heartbeats_raw": 100000,
            "diagnostics": [],
        }


def setup_episode(tmp_path, monkeypatch):
    row = {
        "name": "toy",
        "source": "toy",
        "statement": "theorem toy : True",
        "src": "theorem toy : True := by exact True.intro",
        "version_info": [{"v1": "a" * 40}],
        "header": "import Lean",
    }
    row["proof_length"] = token_count(validate_candidate(row, row["src"])[1])
    dataset = tmp_path / "data.jsonl"
    dataset.write_text(json.dumps(row) + "\n")
    environments = tmp_path / "environments.json"
    environments.write_text(
        json.dumps(
            {"projects": [{"source": "toy", "version": "v1", "path": str(tmp_path)}]}
        )
    )
    prepared = tmp_path / "prepared"
    backend = Compiler()
    evaluator = Evaluator(
        dataset, environments, prepared / "cache", timeout=300, backend=backend
    )
    evaluator.prepare_reference("toy")
    pack = original_pack(row, evaluator)
    pin = immutable(prepared / "packs/toy.json", pack)
    immutable(
        prepared / "prepared.json",
        {
            "environments": str(environments),
            "records": [
                {
                    "task_id": "toy-id",
                    "task": ["toy", "toy"],
                    "status": "prepared",
                    "pack_path": "packs/toy.json",
                    "pack_sha256": pin,
                }
            ],
        },
    )
    prompt = tmp_path / "system.md"
    prompt.write_text("system")
    config = {
        "prepared": str(prepared),
        "dataset": str(dataset),
        "rollout_root": str(tmp_path / "rollouts"),
        "episode_seconds": 1800,
        "max_turns": 32,
        "system_prompt": str(prompt),
        "semantic_config": {"enabled": False},
        "web_config": None,
    }

    def factory(*args, **kwargs):
        return Evaluator(*args, **kwargs, backend=backend)

    monkeypatch.setattr("proof_eval.Evaluator", factory)
    return config, evaluator, backend


def test_rollouts_use_private_candidates_and_fresh_originals(tmp_path, monkeypatch):
    config, source, backend = setup_episode(tmp_path, monkeypatch)
    before = len(backend.calls)
    one = Episode("toy-id", "one", 0, config)
    two = Episode("toy-id", "two", 0, config)
    assert len(backend.calls) == before + 2
    assert (
        len({one.evaluator.store.root, two.evaluator.store.root, source.store.root})
        == 3
    )
    assert not (source.store.root / "candidates").exists()
    assert all(
        v["cached"] is False for v in one.session.original["per_version"].values()
    )
    assert (one.folder / "initial_measurement.json").is_file()
    assert one.session.source_tools.semantic_config == config["semantic_config"]
    result = one.advance(
        '<arena_action>{"op":"finish","reason":"done"}</arena_action>',
        "stop",
        {"task_id": "toy-id"},
    )
    assert result["done"] and result["rollout_infos"]["arena_reward"] == 0
    with pytest.raises(FileExistsError):
        Episode("toy-id", "one", 0, config)


def test_changed_reference_refuses_before_original_or_model_work(tmp_path, monkeypatch):
    config, evaluator, backend = setup_episode(tmp_path, monkeypatch)
    row = evaluator.dataset.get("toy")
    key = evaluator._context(row, "v1")[2]
    value = deepcopy(evaluator.store.read("references", key))
    value["heartbeats"] += 1
    evaluator.store.write("references", key, value)
    before = len(backend.calls)
    with pytest.raises(UnscorableEpisode, match="fingerprint"):
        Episode("toy-id", "changed", 0, config)
    assert len(backend.calls) == before


def test_episode_original_timeout_uses_one_fresh_retry_and_keeps_evidence(
    tmp_path, monkeypatch
):
    config, source, backend = setup_episode(tmp_path, monkeypatch)
    config["original_timeout_retries"] = 1
    original_check = backend.check
    calls = []

    def check(*args):
        calls.append(args)
        if len(calls) == 1:
            return {
                "status": "timeout",
                "passed": False,
                "heartbeats": None,
                "diagnostics": [],
            }
        return original_check(*args)

    monkeypatch.setattr(backend, "check", check)
    episode = Episode("toy-id", "recovered", 0, config)
    assert len(calls) == 2
    saved = json.loads((episode.folder / "initial_measurement.json").read_text())
    assert saved["selected_attempt"] == 1
    assert saved["timeout_retries"] == 1
    assert (episode.folder / "initial_measurements/00.json").exists()
    assert (episode.folder / "initial_measurements/01.json").exists()
    assert all(
        v["cached"] is False for v in episode.session.original["per_version"].values()
    )
    assert source.store.root != episode.evaluator.store.root


def test_semantic_source_is_isolated_but_keeps_the_pinned_project_scope(
    tmp_path, monkeypatch
):
    config, _, _ = setup_episode(tmp_path, monkeypatch)
    episode = Episode("toy-id", "isolated", 0, config)
    calls = []

    def isolated(config, project, request, version, evidence):
        calls.append((config, project, request, version, evidence))
        return {"kind": "semantic_search", "query": request["query"], "count": 0}

    monkeypatch.setattr(
        "proof_eval.training.semantic_process.search_isolated", isolated
    )
    request = {"op": "semantic_search", "query": "natural numbers"}
    result = episode.session.source(request)
    assert result["query"] == "natural numbers"
    assert calls[0][1] == tmp_path and calls[0][3] == "v1"
    assert calls[0][4].is_relative_to(episode.folder)
    with pytest.raises(ValueError, match="Version outside"):
        episode.session.source({**request, "version": "other"})
    with pytest.raises(ValueError, match="Unsupported source fields"):
        episode.session.source({**request, "path": "/outside"})
    assert len(calls) == 1
