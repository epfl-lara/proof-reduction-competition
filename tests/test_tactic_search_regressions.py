"""Regression cases for discovery-only layout and syntax-category failures."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from proof_eval.optimization.tactics import (
    PROBE_TEMPLATE,
    Site,
    candidate_sites,
    instrument,
)


class SiteCategoryTests(unittest.TestCase):
    def test_concrete_tactic_beats_sequence_container_and_rcases_pattern(self):
        code = "exact h rfl"
        nodes = [
            {"kind": "Lean.Parser.Tactic.tacticSeq", "path": [0], "start": 0, "end": 7},
            {
                "kind": "Lean.Parser.Tactic.tacticSeq1Indented",
                "path": [0, 0],
                "start": 0,
                "end": 7,
            },
            {
                "kind": "Lean.Parser.Tactic.exact",
                "path": [0, 0, 0],
                "start": 0,
                "end": 7,
            },
            {
                "kind": "Lean.Parser.Tactic.rcasesPatLo",
                "path": [1],
                "start": 8,
                "end": 11,
            },
        ]
        sites = candidate_sites(code, {"nodes": nodes})
        self.assertEqual(
            [(s.start, s.end, s.syntax_kind) for s in sites],
            [(0, 7, "Lean.Parser.Tactic.exact")],
        )

    def test_conv_simp_and_normal_simp_nested_under_conv_are_not_tactic_sites(self):
        code = "simp simp simp"
        nodes = [
            {"kind": "Lean.Parser.Tactic.conv", "path": [0], "start": 0, "end": 9},
            {
                "kind": "Lean.Parser.Tactic.Conv.simp",
                "path": [0, 0],
                "start": 0,
                "end": 4,
            },
            {"kind": "Lean.Parser.Tactic.simp", "path": [0, 1], "start": 5, "end": 9},
            {"kind": "Lean.Parser.Tactic.simp", "path": [1], "start": 10, "end": 14},
        ]
        sites = candidate_sites(code, {"nodes": nodes})
        self.assertEqual([(s.start, s.end) for s in sites], [(10, 14)])


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
class NestedLayoutTests(unittest.TestCase):
    def test_nested_inline_by_terms_inside_probed_exact_compile(self):
        code = "example (α : Prop) (h : α) : α := by\n  exact (fun (_ : α) (y : α) => y) (by exact h) (by exact h)"
        leaf = code.index("exact (")
        sites = [Site(leaf, len(code), "tactic", leaf, "Lean.Parser.Tactic.exact")]
        first = code.index("by exact")
        second = code.index("by exact", first + 1)
        for start in (first, second):
            sites.append(
                Site(
                    start,
                    start + len("by exact h"),
                    "by_block",
                    start + 3,
                    "Lean.Parser.Term.byTactic",
                )
            )
        source = "import Lean\n" + PROBE_TEMPLATE.replace(
            "__MENU__", '#["rfl", "assumption"]'
        )
        source = (
            source.replace("__HEARTBEATS__", "1000")
            + "\n"
            + instrument(code, sites)
            + "\n"
        )
        with tempfile.TemporaryDirectory(prefix="proof-search-layout-") as directory:
            project = Path(directory)
            (project / "lean-toolchain").write_text("leanprover/lean4:v4.25.0\n")
            (project / "lakefile.toml").write_text(
                'name = "proof_search_layout"\nversion = "0.1.0"\n'
            )
            (project / "lake-manifest.json").write_text(
                json.dumps(
                    {
                        "version": "1.1.0",
                        "name": "proof_search_layout",
                        "lakeDir": ".lake",
                        "packagesDir": ".lake/packages",
                        "packages": [],
                    }
                )
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
            self.assertEqual(sorted(r["site"] for r in records), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
