"""Objective, budget, and restart invariants of the staged experiment engine."""

import unittest
from copy import deepcopy
from unittest.mock import patch

from proof_eval.optimization.engine import Budget, discovery, optimize
from proof_eval.optimization.syntax import Edit

ROW = {"name": "example", "source": "fixture"}


def result(length=0, heartbeat=0, compatibility=100, *, status="passed"):
    combined = (
        None if compatibility is None else (length + heartbeat + compatibility) / 3
    )
    return {
        "status": status,
        "scores": {
            "length_reduction_pct": length,
            "heartbeat_reduction_pct": heartbeat,
            "compatibility_pct": compatibility,
            "combined_pct": combined,
        },
        "candidate": {"length": 20},
        "primary_version": "v1",
        "per_version": {
            "v1": {
                "status": "passed",
                "passed": True,
                "cached": False,
                "diagnostics": [],
            },
            "v2": {
                "status": "unavailable" if compatibility is None else "passed",
                "passed": compatibility is not None,
                "cached": True,
                "diagnostics": [],
            },
        },
    }


class Evaluator:
    def __init__(self, results, primaries=None):
        self.results = {"initial": result(), **results}
        self.primaries = primaries or {}
        self.calls = []

    def evaluate(self, name, code, versions=None):
        self.calls.append((name, code, versions))
        if versions == "primary":
            value = deepcopy(self.primaries.get(code, self.results[code]))
            value["scores"]["compatibility_pct"] = None
            value["scores"]["combined_pct"] = None
            value["per_version"] = {"v1": value["per_version"]["v1"]}
            return value
        return deepcopy(self.results[code])


def groups(parent, *candidates):
    return [[Edit(0, len(parent), candidate, "test")] for candidate in candidates]


class EngineTests(unittest.TestCase):
    def run_search(self, evaluator, candidates, *, policy="best_pool", budget=None):
        events, checkpoints = [], []
        with patch(
            "proof_eval.optimization.engine.discovery",
            return_value=(
                groups("initial", *candidates),
                policy,
                {"analysis_requests": 1},
            ),
        ):
            outcome = optimize(
                evaluator,
                ROW,
                "initial",
                "facts",
                budget or Budget(rounds=1),
                events.append,
                lambda state: checkpoints.append(deepcopy(state)),
            )
        return outcome, events, checkpoints

    def test_primary_upper_bound_avoids_useless_full_evaluation(self):
        evaluator = Evaluator({"short": result(30, -60)})
        outcome, events, _ = self.run_search(evaluator, ["short"])
        self.assertEqual(outcome["proof"], "initial")
        self.assertEqual(
            evaluator.calls,
            [("example", "initial", None), ("example", "short", "primary")],
        )
        candidate = next(event for event in events if event["kind"] == "candidate")
        self.assertFalse(candidate["all_versions_requested"])

    def test_full_version_score_can_reverse_a_promising_primary_score(self):
        evaluator = Evaluator(
            {"candidate": result(20, 10, 20)}, {"candidate": result(20, 10)}
        )
        outcome, _, _ = self.run_search(evaluator, ["candidate"])
        self.assertEqual(outcome["proof"], "initial")
        self.assertEqual(evaluator.calls[-1], ("example", "candidate", None))

    def test_incomplete_versions_never_become_an_accepted_state(self):
        evaluator = Evaluator({"candidate": result(70, 70, None, status="incomplete")})
        outcome, _, _ = self.run_search(evaluator, ["candidate"])
        self.assertEqual(outcome["accepted_transitions"], 0)
        self.assertFalse(outcome["changed"])

    def test_arena_objective_can_accept_longer_proof_with_lower_heartbeats(self):
        evaluator = Evaluator({"longer": result(-10, 40)})
        outcome, _, _ = self.run_search(evaluator, ["longer"])
        self.assertEqual(outcome["proof"], "longer")
        self.assertEqual(outcome["final"]["scores"]["combined_pct"], 130 / 3)

    def test_best_pool_selects_best_result_but_first_policy_stops_early(self):
        for policy, expected, attempts in [
            ("best_pool", "best", 2),
            ("first_improvement", "good", 1),
        ]:
            with self.subTest(policy=policy):
                evaluator = Evaluator({"good": result(10), "best": result(20)})
                outcome, _, _ = self.run_search(
                    evaluator, ["good", "best"], policy=policy
                )
                self.assertEqual(outcome["proof"], expected)
                self.assertEqual(outcome["attempts"], attempts)

    def test_trial_limit_keeps_best_completed_candidate(self):
        evaluator = Evaluator(
            {"good": result(10), "best": result(20), "unseen": result(30)}
        )
        outcome, _, _ = self.run_search(
            evaluator, ["good", "best", "unseen"], budget=Budget(rounds=3, trials=2)
        )
        self.assertEqual(outcome["proof"], "best")
        self.assertEqual(outcome["attempts"], 2)
        self.assertEqual(outcome["stop_reason"], "trial_limit")
        self.assertFalse(any(code == "unseen" for _, code, _ in evaluator.calls))

    def test_noop_duplicates_and_previous_round_candidates_do_not_consume_budget(self):
        evaluator = Evaluator({"good": result(10), "bad": result(-30)})

        def discover(_evaluator, _row, code, _method, _budget, **_kwargs):
            names = (
                ["initial", "good", "good", "bad"]
                if code == "initial"
                else ["bad", "good"]
            )
            return groups(code, *names), "best_pool", {}

        with patch("proof_eval.optimization.engine.discovery", side_effect=discover):
            outcome = optimize(
                evaluator,
                ROW,
                "initial",
                "facts",
                Budget(rounds=4),
                lambda _event: None,
                lambda _state: None,
            )
        self.assertEqual(outcome["attempts"], 2)
        self.assertEqual(outcome["proof"], "good")
        self.assertEqual(outcome["stop_reason"], "no_new_proposals")

    def test_resume_first_improvement_accepts_saved_winner_without_next_trial(self):
        for policy in ("first_improvement", "joint_then_first"):
            with self.subTest(policy=policy):
                evaluator = Evaluator({"good": result(10), "best": result(20)})
                checkpoint = {}

                def interrupted_save(state):
                    checkpoint.clear()
                    checkpoint.update(deepcopy(state))
                    if state["plan"] and state["plan"]["winner"]:
                        raise InterruptedError("after durable candidate checkpoint")

                with patch(
                    "proof_eval.optimization.engine.discovery",
                    return_value=(groups("initial", "good", "best"), policy, {}),
                ):
                    with self.assertRaises(InterruptedError):
                        optimize(
                            evaluator,
                            ROW,
                            "initial",
                            "facts",
                            Budget(rounds=1),
                            lambda _event: None,
                            interrupted_save,
                        )
                previous_calls = list(evaluator.calls)
                with patch("proof_eval.optimization.engine.discovery") as discover:
                    outcome = optimize(
                        evaluator,
                        ROW,
                        "initial",
                        "facts",
                        Budget(rounds=1),
                        lambda _event: None,
                        lambda _state: None,
                        state=checkpoint,
                    )
                self.assertEqual(outcome["proof"], "good")
                self.assertEqual(outcome["attempts"], 1)
                self.assertEqual(evaluator.calls, previous_calls)
                discover.assert_not_called()

    def test_resume_best_pool_continues_pending_alternatives_and_does_not_remeasure_initial(
        self,
    ):
        evaluator = Evaluator({"good": result(10), "best": result(20)})
        checkpoint = {}

        def interrupted_save(state):
            checkpoint.clear()
            checkpoint.update(deepcopy(state))
            if state["attempts"] == 1:
                raise InterruptedError("after first candidate")

        with patch(
            "proof_eval.optimization.engine.discovery",
            return_value=(groups("initial", "good", "best"), "best_pool", {}),
        ):
            with self.assertRaises(InterruptedError):
                optimize(
                    evaluator,
                    ROW,
                    "initial",
                    "menu",
                    Budget(rounds=1),
                    lambda _event: None,
                    interrupted_save,
                )
        outcome = optimize(
            evaluator,
            ROW,
            "initial",
            "menu",
            Budget(rounds=1),
            lambda _event: None,
            lambda _state: None,
            state=checkpoint,
        )
        self.assertEqual(outcome["proof"], "best")
        self.assertEqual(outcome["attempts"], 2)
        self.assertEqual(sum(code == "initial" for _, code, _ in evaluator.calls), 1)
        self.assertEqual(
            sum(
                code == "good" and versions == "primary"
                for _, code, versions in evaluator.calls
            ),
            1,
        )

    def test_initial_incomplete_and_zero_budget_never_start_discovery(self):
        for evaluator, budget, expected in [
            (
                Evaluator({"initial": result(0, 0, None, status="incomplete")}),
                Budget(),
                "initial_evaluation_incomplete_or_failed",
            ),
            (Evaluator({}), Budget(trials=0), "trial_limit"),
        ]:
            with (
                self.subTest(expected=expected),
                patch("proof_eval.optimization.engine.discovery") as discover,
            ):
                outcome = optimize(
                    evaluator,
                    ROW,
                    "initial",
                    "facts",
                    budget,
                    lambda _event: None,
                    lambda _state: None,
                )
                self.assertEqual(outcome["stop_reason"], expected)
                discover.assert_not_called()

    def test_wrong_problem_checkpoint_is_rejected(self):
        evaluator = Evaluator({})
        _, _, checkpoints = self.run_search(evaluator, [])
        with self.assertRaisesRegex(ValueError, "different input or method"):
            optimize(
                evaluator,
                {**ROW, "name": "different"},
                "initial",
                "facts",
                Budget(),
                lambda _event: None,
                lambda _state: None,
                state=checkpoints[-1],
            )

    def test_empty_menu_batch_advances_and_accepted_proof_restarts_sites(self):
        evaluator = Evaluator({"good": result(20)})
        offsets = []

        def discover(_evaluator, _row, code, _method, _budget, *, site_offset=0):
            offsets.append((code, site_offset))
            candidates = (
                groups(code, "good") if code == "initial" and site_offset == 2 else []
            )
            total = 4 if code == "initial" else 1
            return (
                candidates,
                "best_pool",
                {
                    "diagnostics": [
                        {
                            "kind": "site_coverage",
                            "available": total,
                            "selected": min(2, total),
                            "site_offset": site_offset,
                        }
                    ]
                },
            )

        with patch("proof_eval.optimization.engine.discovery", side_effect=discover):
            outcome = optimize(
                evaluator,
                ROW,
                "initial",
                "menu",
                Budget(rounds=5, sites=2),
                lambda _event: None,
                lambda _state: None,
            )
        self.assertEqual(offsets, [("initial", 0), ("initial", 2), ("good", 0)])
        self.assertEqual(outcome["proof"], "good")
        self.assertEqual(outcome["attempts"], 1)

    def test_rejected_menu_batch_advances_but_respects_round_limit(self):
        evaluator = Evaluator({"bad": result(-10)})
        offsets = []

        def discover(_evaluator, _row, code, _method, _budget, *, site_offset=0):
            offsets.append(site_offset)
            candidates = groups(code, "bad") if site_offset == 0 else []
            return (
                candidates,
                "best_pool",
                {
                    "diagnostics": [
                        {
                            "kind": "site_coverage",
                            "available": 100,
                            "selected": 2,
                            "site_offset": site_offset,
                        }
                    ]
                },
            )

        with patch("proof_eval.optimization.engine.discovery", side_effect=discover):
            outcome = optimize(
                evaluator,
                ROW,
                "initial",
                "menu",
                Budget(rounds=2, sites=2),
                lambda _event: None,
                lambda _state: None,
            )
        self.assertEqual(offsets, [0, 2])
        self.assertEqual(outcome["attempts"], 1)
        self.assertEqual(outcome["stop_reason"], "round_limit")
        self.assertEqual(outcome["site_offset"], 4)

    def test_site_offset_checkpoint_resumes_after_empty_batch(self):
        evaluator = Evaluator({})
        checkpoint = {}
        offsets = []

        def discover(_evaluator, _row, _code, _method, _budget, *, site_offset=0):
            offsets.append(site_offset)
            return (
                [],
                "best_pool",
                {
                    "diagnostics": [
                        {
                            "kind": "site_coverage",
                            "available": 4,
                            "selected": 2,
                            "site_offset": site_offset,
                        }
                    ]
                },
            )

        def interrupted_save(state):
            checkpoint.clear()
            checkpoint.update(deepcopy(state))
            if state.get("site_offset") == 2:
                raise InterruptedError("after advancing site slice")

        with patch("proof_eval.optimization.engine.discovery", side_effect=discover):
            with self.assertRaises(InterruptedError):
                optimize(
                    evaluator,
                    ROW,
                    "initial",
                    "search",
                    Budget(rounds=5, sites=2),
                    lambda _event: None,
                    interrupted_save,
                )
            outcome = optimize(
                evaluator,
                ROW,
                "initial",
                "search",
                Budget(rounds=5, sites=2),
                lambda _event: None,
                lambda _state: None,
                state=checkpoint,
            )
        self.assertEqual(offsets, [0, 2])
        self.assertEqual(outcome["stop_reason"], "no_new_proposals")

    def test_failed_discovery_preserves_evidence_without_counting_a_negative_trial(
        self,
    ):
        for status in ("discovery_failed", "discovery_timeout"):
            with self.subTest(status=status):
                evaluator = Evaluator({"untrusted_partial": result(80, 80)})
                diagnostics = [
                    {
                        "kind": "site_coverage",
                        "available": 100,
                        "selected": 2,
                        "site_offset": 0,
                    },
                    {
                        "kind": "discovery_process",
                        "returncode": None if status.endswith("timeout") else 1,
                        "timed_out": status.endswith("timeout"),
                        "stderr": "probe failed before all sites completed",
                    },
                ]
                evidence = {
                    "status": status,
                    "analysis_requests": 2,
                    "diagnostics": diagnostics,
                }
                events = []
                # Even any accidentally returned partial proposals must not be
                # evaluated or treated as negative optimization evidence.
                with patch(
                    "proof_eval.optimization.engine.discovery",
                    return_value=(
                        groups("initial", "untrusted_partial"),
                        "best_pool",
                        evidence,
                    ),
                ) as discover:
                    outcome = optimize(
                        evaluator,
                        ROW,
                        "initial",
                        "search",
                        Budget(rounds=5, sites=2),
                        events.append,
                        lambda _state: None,
                    )
                self.assertEqual(outcome["stop_reason"], "discovery_unavailable")
                self.assertEqual(outcome["proof"], "initial")
                self.assertEqual(outcome["attempts"], 0)
                self.assertEqual(outcome["accepted_transitions"], 0)
                self.assertEqual(outcome["site_offset"], 0)
                self.assertEqual(evaluator.calls, [("example", "initial", None)])
                discover.assert_called_once()
                proposal = next(
                    event for event in events if event["kind"] == "proposal_set"
                )
                self.assertEqual(proposal["discovery"]["diagnostics"], diagnostics)
                self.assertEqual(proposal["discovery"]["status"], status)
                self.assertFalse(
                    any(
                        event["kind"] in {"candidate", "site_batch_completed"}
                        for event in events
                    )
                )


class DiscoveryTests(unittest.TestCase):
    def test_menu_names_map_to_probe_api_and_keep_alternatives_separate(self):
        edits = [Edit(0, 1, "one", "test"), Edit(0, 1, "two", "test")]
        for method, target in [("menu", "tactic_menu"), ("search", "library_search")]:
            with (
                self.subTest(method=method),
                patch(
                    "proof_eval.optimization.tactics.discover",
                    return_value={"groups": [edits], "analysis_requests": 2},
                ) as discover,
            ):
                groups_, policy, _ = discovery(
                    None, ROW, "initial", method, Budget(sites=7)
                )
                self.assertEqual(groups_, [[edits[0]], [edits[1]]])
                self.assertEqual(policy, "best_pool")
                self.assertEqual(
                    discover.call_args.kwargs,
                    {"method": target, "max_sites": 7, "site_offset": 0},
                )

    def test_lint_and_simp_do_not_duplicate_owned_analysis(self):
        for method in ("lint", "simp"):
            with (
                self.subTest(method=method),
                patch(
                    "proof_eval.optimization.syntax.proposals", return_value=([], 2)
                ) as proposals,
            ):
                with patch("proof_eval.optimization.engine.analyze") as analyze:
                    _, _, evidence = discovery(None, ROW, "initial", method, Budget())
                    self.assertEqual(evidence["analysis_requests"], 2)
                    proposals.assert_called_once()
                    analyze.assert_not_called()

    def test_unknown_method_fails_before_running_lean(self):
        with patch("proof_eval.optimization.engine.analyze") as analyze:
            with self.assertRaisesRegex(ValueError, "Unknown optimization method"):
                discovery(None, ROW, "initial", "typo", Budget())
            analyze.assert_not_called()


if __name__ == "__main__":
    unittest.main()
