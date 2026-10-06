"""Tree search: policy rules, check budgets, durable resume and exact replay."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

import proof_eval.harness.search as runner
import proof_eval.harness.session as toolmod
import proof_eval.harness.tree.search as treesearch
from proof_eval.harness.tree import FrontierPolicy, TreeSearch, dream, replay
from proof_eval.harness.tree.expansion import ExpansionSession
from proof_eval.harness.tree.policy import CARDS, Expansion, Node, TreeView
from proof_eval.harness.tree.replay import load_history

ORIGINAL = "theorem x : True := by trivial"
GOOD = "theorem x : True := by exact True.intro"
BETTER = "theorem x : True := by exact ⟨⟩"
BEST = "theorem x : True := ⟨⟩"


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


class TestPolicy:
    def view(self, scores, expansions):
        nodes = [Node(0, None, None, 50.0)]
        exps = []
        for index, (parent, card, children, cost) in enumerate(expansions):
            for child in children:
                nodes.append(Node(child, parent, index, scores[child]))
            exps.append(Expansion(index, parent, card, cost, "received", children))
        return TreeView(tuple(nodes), tuple(exps))

    def test_root_then_best_parent_with_rotating_cards(self):
        policy = FrontierPolicy()
        assert policy.choose(TreeView((Node(0, None, None, 50.0),))).parent == 0
        view = self.view({1: 60.0, 2: None}, [(0, None, (1, 2), 0.1)])
        decision = policy.choose(view)
        assert (decision.action, decision.parent, decision.card) == (
            "expand",
            1,
            CARDS[0],
        )

    @pytest.mark.parametrize(
        "fields,expansions,reason",
        [
            ({"max_expansions": 1}, [(0, None, (1,), 0.1)], "expansion_limit"),
            ({"budget_usd": 0.5}, [(0, None, (1,), 0.3)], "projected_budget_exceeded"),
            ({"budget_usd": 1.0}, [(0, None, (1,), None)], "unknown_usage"),
            (
                {"flat_stop": 1},
                [(0, None, (1,), 0.1), (1, CARDS[0], (2,), 0.1)],
                "plateau",
            ),
        ],
    )
    def test_stopping_rules(self, fields, expansions, reason):
        view = self.view({1: 60.0, 2: 60.0}, expansions)
        assert FrontierPolicy(**fields).choose(view).reason == reason

    def test_unexpanded_parent_and_greedy_card(self):
        view = self.view(
            {1: 60.0, 2: 70.0, 3: 55.0},
            [(0, None, (1,), 0.1), (1, CARDS[0], (2,), 0.1), (1, CARDS[1], (3,), 0.1)],
        )
        unexpanded = FrontierPolicy(parent_rule="unexpanded", cards=CARDS[:2])
        assert unexpanded.choose(view).parent == 2
        greedy = FrontierPolicy(card_rule="greedy", cards=CARDS[:2], flat_stop=5)
        assert greedy.choose(view).card == CARDS[0]

    def test_expansion_refuses_checks_beyond_its_budget(self):
        calls = []

        class Session:
            def dispatch(self, request):
                calls.append(request["op"])
                return {"kind": "ok"}

        view = ExpansionSession(Session(), "parent", max_checks=1)
        assert view.seed_code == "parent"
        assert view.dispatch({"op": "check", "code": "a"}) == {"kind": "ok"}
        assert view.dispatch({"op": "check", "code": "b"})["stop"] is True
        assert view.dispatch({"op": "status"}) == {"kind": "ok"}
        assert calls == ["check", "status"]


SETTINGS = TreeSearch(FrontierPolicy(max_expansions=5, flat_stop=2), max_checks=2)
PLAN = [[GOOD, BETTER, BEST], [BEST], [GOOD], []]


@pytest.fixture
def cell(tmp_path, monkeypatch):
    seed = evaluation(100 / 3)
    seed["scores"].update(length_reduction_pct=0.0, heartbeat_reduction_pct=0.0)
    monkeypatch.setattr(toolmod, "original_evaluation", lambda _: deepcopy(seed))
    row = {
        "name": "x",
        "source": "test",
        "statement": "theorem x : True",
        "src": ORIGINAL,
        "file_path": "Example.lean",
        "version_info": [{"v1": "a"}, {"v2": "b"}],
    }
    project = tmp_path / "project"
    project.mkdir()

    class Evaluator:
        projects = {("test", "v1"): project, ("test", "v2"): project}
        values = {GOOD: evaluation(70), BETTER: evaluation(80), BEST: evaluation(85)}

        def evaluate(self, name, code, **kwargs):
            value = deepcopy(self.values[code])
            value["candidate"]["code_sha256"] = toolmod.code_identity(row, code)
            return value

    def prompt(_, seed=None):
        return [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "task " + (seed[0] if seed else ORIGINAL)},
        ]

    for module in (runner, treesearch):
        monkeypatch.setattr(module, "messages", prompt)
    monkeypatch.setattr(runner, "guard", lambda *a: None)
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
        "tree": SETTINGS.record(),
    }
    return {"name": "x", "row": row}, Evaluator(), config


def agent(plan):
    """Durable fake agent using only the tool protocol, like a real agent."""
    calls = []

    def generate(**kwargs):
        folder, request, tools = kwargs["folder"], kwargs["messages"], kwargs["session"]
        calls.append((folder.name, deepcopy(request), tools.seed_code))
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / "request.json").exists():
            assert json.loads((folder / "request.json").read_text()) == request
            return json.loads((folder / "generation.json").read_text())
        (folder / "request.json").write_text(json.dumps(request))
        for code in plan[int(folder.name.split("_")[1])]:
            tools.dispatch({"op": "check", "code": code})
        best = tools.dispatch({"op": "status"})["best_proof"]
        tools.dispatch({"op": "finish", "reason": "done"})
        generation = {
            "status": "received",
            "content": best,
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
        tmp_path / "out", config, pack, "gpt-6.1-sol", "max", evaluator, generate
    )


def test_tree_search_expands_best_nodes_until_plateau(tmp_path, cell):
    generate = agent(PLAN)
    result = run(tmp_path, cell, generate)
    tree = result["tree"]
    assert [(e["action"], e["parent"], e["card"]) for e in tree] == [
        ("expand", 0, None),
        ("expand", 2, CARDS[0]),
        ("expand", 4, CARDS[1]),
        ("expand", 4, CARDS[2]),
        ("stop", None, None),
    ]
    assert tree[-1]["reason"] == "plateau"
    assert result["selected_proof"] == BEST and len(result["generations"]) == 4
    root_checks = [
        json.loads(line)["code"]
        for line in (next((tmp_path / "out/cells").iterdir()) / "evidence/checks.jsonl")
        .read_text()
        .splitlines()[: tree[0]["last_check"]]
    ]
    assert BEST not in root_checks  # Third root check was refused, not compiled.
    cell_folder = next((tmp_path / "out/cells").iterdir())
    root_request = generate.calls[0][1]
    assert (
        root_request == json.loads((cell_folder / "input.json").read_text())["messages"]
    )
    assert [c[2] for c in generate.calls] == [ORIGINAL, BETTER, BEST, BEST]
    assert CARDS[0] in generate.calls[1][1][1]["content"]
    assert "messages" not in tree[1]


def test_resume_reuses_decisions_and_requests(tmp_path, cell):
    result = run(tmp_path, cell, agent(PLAN))
    folder = next((tmp_path / "out/cells").iterdir())
    (folder / "result.json").unlink()
    again = run(tmp_path, cell, agent(PLAN))  # The fake asserts identical requests.
    assert again["tree"] == result["tree"]
    assert again["selected_proof"] == result["selected_proof"]


def test_replay_reproduces_the_live_run_and_flags_unrecorded_branches(tmp_path, cell):
    result = run(tmp_path, cell, agent(PLAN))
    name, history = load_history(next((tmp_path / "out/cells").iterdir()))
    live = replay(SETTINGS.policy, name, history)
    assert (live.score, live.expansions, live.stop, live.off_history) == (
        85.0,
        4,
        "plateau",
        False,
    )
    assert live.cost_usd == pytest.approx(result["cost"]["total_usd"])
    reordered = replace(SETTINGS.policy, cards=tuple(reversed(CARDS)))
    assert replay(reordered, name, history).off_history is True
    short = replay(replace(SETTINGS.policy, max_expansions=2), name, history)
    assert (short.score, short.expansions, short.stop) == (85.0, 2, "expansion_limit")


def test_dream_ranks_a_cheaper_on_history_policy_first(tmp_path, cell):
    run(tmp_path, cell, agent(PLAN))
    (tmp_path / "out/config.json").write_text(json.dumps(cell[2]))
    report = dream(tmp_path / "out")
    best = report["best_on_history"][0]
    assert report["deployed"]["mean_score"] == best["mean_score"] == 85.0
    assert best["mean_cost_usd"] < report["deployed"]["mean_cost_usd"]
    assert best["policy"]["max_expansions"] == 2 and best["off_history"] == 0


def test_tree_and_restarts_are_mutually_exclusive(tmp_path, monkeypatch):
    from proof_eval.harness import configuration
    from proof_eval.harness.config import RunConfig
    from proof_eval.harness.restarts import RestartPolicy

    class Adapter:
        @staticmethod
        def cli_identity():
            return {"stub": True}

    monkeypatch.setattr(configuration, "adapter", lambda provider: Adapter)
    packs = configuration.load_inputs(configuration.BASE)
    with pytest.raises(ValueError):
        configuration.prepare(
            tmp_path / "both",
            "score_edges",
            packs,
            restart=RestartPolicy(),
            tree=TreeSearch(),
        )
    with pytest.raises(ValueError):
        RunConfig(restart=RestartPolicy(), tree=TreeSearch())
    frozen = configuration.prepare(
        tmp_path / "tree", "score_edges", packs, tree=SETTINGS
    )
    assert TreeSearch.from_record(frozen["tree"]) == SETTINGS
