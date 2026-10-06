"""Restarted sessions: budget gating, resume identity and best-proof continuity."""

import json
import shutil
from copy import deepcopy

import pytest

import proof_eval.harness.restarts as restarts
import proof_eval.harness.search as runner
import proof_eval.harness.session as toolmod
from proof_eval.harness.restarts import RestartPolicy, decide

ORIGINAL = "theorem x : True := by trivial"
GOOD = "theorem x : True := by exact True.intro"
BETTER = "theorem x : True := by exact ⟨⟩"


def evaluation(score):
    return {
        "status": "passed",
        "primary_version": "v1",
        "candidate": {"length": 3},
        "scores": {
            "length_reduction_pct": 3 * score - 120,
            "heartbeat_reduction_pct": 20.0,
            "compatibility_pct": 100.0,
            "combined_pct": score,
        },
        "per_version": {
            v: {
                "status": "passed",
                "passed": True,
                "heartbeats": 100,
                "diagnostics": [],
            }
            for v in ("v1", "v2")
        },
    }


class TestDecision:
    POLICY = RestartPolicy(sessions=3, below_pct=90.0, budget_usd=3.0)

    @pytest.mark.parametrize(
        "costs,best,status,expected",
        [
            ([1.0], 80.0, "received", (True, "restart")),
            ([1.0, 1.0, 0.5], 80.0, "received", (False, "session_limit")),
            ([1.0], 80.0, "indeterminate", (False, "previous_session_not_received")),
            ([1.0], 90.0, "received", (False, "score_threshold_reached")),
            ([None], 80.0, "received", (False, "unknown_usage")),
            ([1.6], 80.0, "received", (False, "projected_budget_exceeded")),
            ([0.9, 1.1], 80.0, "received", (False, "projected_budget_exceeded")),
            ([0.9, 0.9], 80.0, "received", (True, "restart")),
        ],
    )
    def test_rules(self, costs, best, status, expected):
        assert decide(self.POLICY, costs, best, status) == expected

    @pytest.mark.parametrize(
        "fields", [{"sessions": 1}, {"below_pct": 0}, {"budget_usd": 0}]
    )
    def test_invalid_policies_are_rejected(self, fields):
        with pytest.raises(ValueError):
            RestartPolicy(**fields)


@pytest.fixture
def cell(tmp_path, monkeypatch):
    seed = evaluation(100 / 3)
    seed["scores"].update(length_reduction_pct=0.0, heartbeat_reduction_pct=0.0)
    monkeypatch.setattr(toolmod, "original_evaluation", lambda _: deepcopy(seed))
    pack = {
        "name": "x",
        "row": {
            "name": "x",
            "source": "test",
            "statement": "theorem x : True",
            "src": ORIGINAL,
            "file_path": "Example.lean",
            "version_info": [{"v1": "a"}, {"v2": "b"}],
        },
    }
    project = tmp_path / "project"
    project.mkdir()

    class Evaluator:
        projects = {("test", "v1"): project, ("test", "v2"): project}
        values = {GOOD: evaluation(70), BETTER: evaluation(80)}

        def evaluate(self, name, code, **kwargs):
            value = deepcopy(self.values[code])
            value["candidate"]["code_sha256"] = toolmod.code_identity(pack["row"], code)
            return value

    def prompt(_, seed=None):
        incumbent = seed[0] if seed else ORIGINAL
        return [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "task " + incumbent},
        ]

    monkeypatch.setattr(runner, "guard", lambda *a: None)
    monkeypatch.setattr(runner, "messages", prompt)
    monkeypatch.setattr(restarts, "messages", prompt)
    monkeypatch.setattr(runner, "historical", lambda *a: (None, None))
    monkeypatch.setattr(runner, "structural_control", lambda *a: (None, None))
    config = {
        "mode": "score",
        "max_outer_correctness_repairs": 0,
        "cli": {},
        "historical_control_sha256": {},
        "structural_control_sha256": {},
        "cost_assumptions": {},
        "budget_usd_per_problem": 3.0,
        "restart": RestartPolicy(sessions=3).record(),
    }
    return pack, Evaluator(), config


def scripted(plan):
    """A durable fake agent: session i checks plan[i], then finishes.

    Like the real executor, a saved generation is returned without running the
    agent again, and a changed request for a saved folder is an error.
    """
    calls = []

    def generate(**kwargs):
        folder, request = kwargs["folder"], kwargs["messages"]
        calls.append((folder.name, deepcopy(request)))
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / "request.json").exists():
            assert json.loads((folder / "request.json").read_text()) == request
            return json.loads((folder / "generation.json").read_text())
        (folder / "request.json").write_text(json.dumps(request))
        session = kwargs["session"]
        index = int(folder.name.split("_")[1])
        code = plan[index % len(plan)]
        if code:
            session.check(code)
        session.dispatch({"op": "finish", "reason": f"idea {index} exhausted"})
        generation = {
            "status": "received",
            "content": session.best_code,
            "finish_reason": "stop",
            "codex_usage": {
                "input_tokens": 1000,
                "cached_input_tokens": 500,
                "cache_write_input_tokens": 0,
                "output_tokens": 100,
                "reasoning_output_tokens": 50,
            },
        }
        (folder / "generation.json").write_text(json.dumps(generation))
        return generation

    generate.calls = calls
    return generate


def run(tmp_path, cell, generate):
    pack, evaluator, config = cell
    return runner.run_cell(
        tmp_path / "out",
        config,
        pack,
        "gpt-6.1-sol",
        "max",
        evaluator,
        generator=generate,
    )


def test_restarts_continue_from_the_best_proof_until_the_session_limit(tmp_path, cell):
    generate = scripted([GOOD, BETTER, None])
    result = run(tmp_path, cell, generate)
    assert result["selected_proof"] == BETTER
    assert [name for name, _ in generate.calls] == [
        "attempt_00",
        "attempt_01",
        "attempt_02",
    ]
    assert [e["decision"] for e in result["restarts"]] == ["restart", "restart", "stop"]
    assert result["restarts"][-1]["reason"] == "session_limit"
    second, third = generate.calls[1][1], generate.calls[2][1]
    assert GOOD in second[1]["content"] and "idea 0 exhausted" in second[1]["content"]
    assert BETTER in third[1]["content"] and "idea 1 exhausted" in third[1]["content"]
    assert second[0] == third[0] == generate.calls[0][1][0]
    assert len(result["generations"]) == 3
    assert result["cost"]["attempts"] == 3 and result["status"] == "complete"


def test_resume_repeats_saved_restart_prompts_exactly(tmp_path, cell):
    first = scripted([GOOD, BETTER, None])
    result = run(tmp_path, cell, first)
    folder = next((tmp_path / "out" / "cells").iterdir())
    (folder / "result.json").unlink()
    again = scripted([GOOD, BETTER, None])
    resumed = run(tmp_path, cell, again)
    # The best proof is now BETTER, yet saved prompts are reused byte for byte.
    assert [m for _, m in again.calls] == [m for _, m in first.calls]
    assert resumed["selected_proof"] == result["selected_proof"]
    assert resumed["restarts"] == json.loads((folder / "restarts.json").read_text())


def test_threshold_stops_after_the_first_session(tmp_path, cell):
    pack, evaluator, config = cell
    config["restart"] = RestartPolicy(sessions=3, below_pct=60.0).record()
    generate = scripted([GOOD])
    result = run(tmp_path, (pack, evaluator, config), generate)
    assert len(generate.calls) == 1
    assert result["restarts"] == [
        {
            **result["restarts"][0],
            "decision": "stop",
            "reason": "score_threshold_reached",
            "messages": None,
        }
    ]


def test_cells_without_restart_config_have_no_restart_record(tmp_path, cell):
    pack, evaluator, config = cell
    config = {k: v for k, v in config.items() if k != "restart"}
    generate = scripted([GOOD])
    result = run(tmp_path, (pack, evaluator, config), generate)
    assert "restarts" not in result and len(generate.calls) == 1
    assert not (next((tmp_path / "out" / "cells").iterdir()) / "restarts.json").exists()
    shutil.rmtree(tmp_path / "out")


def test_frozen_config_gains_keys_only_when_opted_in(tmp_path, monkeypatch):
    from proof_eval.harness import configuration

    class Adapter:
        @staticmethod
        def cli_identity():
            return {"stub": True}

    monkeypatch.setattr(configuration, "adapter", lambda provider: Adapter)
    packs = configuration.load_inputs(configuration.BASE)
    plain = configuration.prepare(tmp_path / "plain", "score_edges", packs)
    assert "restart" not in plain and "final_rewrites" not in plain
    opted = configuration.prepare(
        tmp_path / "opted",
        "score_edges",
        packs,
        restart=RestartPolicy(sessions=2, below_pct=85.0),
        final_rewrites=True,
    )
    assert opted["restart"]["sessions"] == 2 and opted["restart"]["below_pct"] == 85.0
    assert opted["final_rewrites"]["methods"] == ["proof_theory", "golf"]
    assert {
        k: v for k, v in opted.items() if k not in ("restart", "final_rewrites")
    } == {k: v for k, v in plain.items()} | {
        "deterministic_jobs": opted["deterministic_jobs"]
    }
