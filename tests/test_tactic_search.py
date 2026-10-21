"""Goal-state restoration, search materialization, and deterministic site bounds."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from proof_eval.optimization.tactics import (
    CHEAP_MENU,
    PROBE_TEMPLATE,
    Site,
    _format_replacement,
    candidate_sites,
    checked_outcome,
    instrument,
    materialized_suggestions,
)


class DiscoveryTextTests(unittest.TestCase):
    def test_menu_can_introduce_simplification_at_new_sites_without_query_tactics(self):
        self.assertTrue({"simp", "simp_all", "dsimp", "aesop"}.issubset(CHEAP_MENU))
        self.assertEqual(len(CHEAP_MENU), len(set(CHEAP_MENU)))
        self.assertFalse(any("?" in tactic for tactic in CHEAP_MENU))

    def test_nested_probes_preserve_existing_indentation_and_unicode(self):
        code = "theorem π : True := by\n  have α : True := by trivial\n  exact α"
        outer = code.index("by")
        inner = code.index("by", outer + 2)
        first = code.index("have")
        leaf = code.index("trivial")
        result = instrument(
            code,
            [
                Site(outer, len(code), "by_block", first, "by"),
                Site(inner, leaf + 7, "by_block", leaf, "by"),
                Site(leaf, leaf + 7, "tactic", leaf, "trivial"),
            ],
        )
        self.assertIn("by\n  proof_search_probe 0\n  have α", result)
        self.assertIn(
            "by proof_search_probe 1\n"
            + " " * 22
            + "first | (proof_search_probe 2; trivial)",
            result,
        )
        self.assertTrue(result.endswith("\n  exact α"))

    def test_only_syntax_nodes_can_nominate_sites(self):
        code = "theorem x : True := by\n  /- omega -/\n  trivial"
        start = code.index("trivial")
        nodes = [
            {
                "kind": "Lean.Parser.Tactic.trivial",
                "start": start,
                "end": len(code),
                "path": [0],
            }
        ]
        sites = candidate_sites(code, {"nodes": nodes})
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0].start, start)

    def test_search_queries_ambiguous_output_and_holes_are_not_materialized(self):
        messages = [
            "Try this:\n  [apply] exact h",
            "Try this:\n  [apply] exact h",
            "Try this: aesop?",
            "Try this: exact?",
            "Try this: exact sorry",
            "Try these:\n [apply] exact h\n [apply] exact h2",
            "unrelated message",
        ]
        self.assertEqual(materialized_suggestions(messages), ["exact h"])

    def test_multiline_suggestion_preserves_case_branch_indentation(self):
        message = "Try this:\n\n  [apply]     intro a\n    cases a with\n    | inl h =>\n      exact Or.inr h\n    | inr h => exact Or.inl h"
        self.assertEqual(
            materialized_suggestions([message]),
            [
                "first |\n  intro a\n  cases a with\n  | inl h =>\n    exact Or.inr h\n  | inr h => exact Or.inl h"
            ],
        )

    def test_optional_function_names_are_not_query_tactics(self):
        self.assertEqual(
            materialized_suggestions(["Try this: exact List.head?_eq_none_iff.mpr h"]),
            ["exact List.head?_eq_none_iff.mpr h"],
        )

    def test_recovery_sorry_in_auxiliary_declaration_is_not_a_success(self):
        result = checked_outcome(
            {
                "status": "solved",
                "detail": "",
                "tactic": "grind?",
                "suggestions": [
                    "declaration uses `sorry`",
                    "Try this:\n  [apply] grind => sorry",
                ],
            }
        )
        self.assertEqual(result["status"], "rejected_sorry")
        self.assertEqual(materialized_suggestions(result["suggestions"]), [])


def _installed(version):
    if not shutil.which("elan") or not shutil.which("lake"):
        return False
    proc = subprocess.run(["elan", "toolchain", "list"], capture_output=True, text=True)
    return any(
        line.split()[0] == f"leanprover/lean4:{version}"
        for line in proc.stdout.splitlines()
        if line.split()
    )


@unittest.skipUnless(_installed("v4.25.0"), "Lean v4.25.0 is not installed")
class LeanProbeTests(unittest.TestCase):
    def test_state_restoration_and_per_attempt_heartbeat_limit(self):
        """A failed expensive tactic cannot consume the next tactic's budget.

        Successful alternatives must not solve the original goal; its original
        `rfl` still executes after the probe. No project dependencies are needed.
        """
        with tempfile.TemporaryDirectory(prefix="proof-search-test-") as directory:
            project = Path(directory)
            (project / "lean-toolchain").write_text("leanprover/lean4:v4.25.0\n")
            (project / "lakefile.toml").write_text(
                'name = "proof_search_test"\nversion = "0.1.0"\n'
            )
            (project / "lake-manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.1.0",
                        "name": "proof_search_test",
                        "lakeDir": ".lake",
                        "packagesDir": ".lake/packages",
                        "packages": [],
                    }
                )
            )
            support = PROBE_TEMPLATE.replace(
                "__MENU__",
                '#["proof_budget_consumer", "rfl", "unknown_tactic", "exact sorry"]',
            )
            support = support.replace("__HEARTBEATS__", "20")
            source = r"""
import Lean
open Lean Elab Tactic in
elab "proof_budget_consumer" : tactic => do
  for _ in [:1000000] do
    checkSystem "proof_search_test"
    let _ ← mkFreshUserName `temporary
"""
            source += support + """
set_option maxHeartbeats 0 in
example (n : Nat) : n = n := by
  proof_search_probe 0
  rfl
"""
            tactic = materialized_suggestions(
                ["Try this:\n [apply] intro h\n exact h"]
            )[0]
            for original, kind, span in [
                (
                    "example (p : Prop) : p → p := by exact fun h => h",
                    "by_block",
                    "by exact fun h => h",
                ),
                (
                    "example (p : Prop) : p → p := by\n  exact fun h => h",
                    "tactic",
                    "exact fun h => h",
                ),
            ]:
                start = original.index(span)
                site = Site(start, len(original), kind, start, "fixture")
                source += (
                    "\n"
                    + original[:start]
                    + _format_replacement(site, tactic, original)
                    + "\n"
                )
            (project / "Probe.lean").write_text(source)
            proc = subprocess.run(
                ["lake", "env", "lean", "--json", "Probe.lean"],
                cwd=project,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            messages = [
                json.loads(line)["data"]
                for line in proc.stdout.splitlines()
                if line.startswith("{")
            ]
            records = [
                json.loads(m.removeprefix("PROOF_SEARCH:"))
                for m in messages
                if m.startswith("PROOF_SEARCH:")
            ]
            self.assertEqual(len(records), 1)
            results = records[0]["results"]
            self.assertIn("maximum number of heartbeats", results[0]["detail"])
            self.assertEqual(results[1]["status"], "solved")
            self.assertEqual(results[2]["status"], "unavailable")
            self.assertEqual(results[3]["status"], "rejected_sorry")


if __name__ == "__main__":
    unittest.main()
