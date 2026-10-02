"""Backend contract and real Lean checks, using a tiny pinned local project."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from proof_eval.lean_backend import LeanBackend, _masked_comments


def _installed(version):
    if not shutil.which("elan") or not shutil.which("lake"):
        return False
    output = subprocess.run(["elan", "toolchain", "list"], capture_output=True, text=True).stdout
    return any(line.split()[0] == f"leanprover/lean4:{version}" for line in output.splitlines() if line.split())


class BackendScannerTests(unittest.TestCase):
    def test_nested_comments_and_literal_boundaries(self):
        source = 'theorem x : «x/-y-/» = r#"-- /- "/-"# := by rfl /- a /- b -/ c -/ -- z\n'
        masked = _masked_comments(source)
        self.assertEqual(len(source), len(masked))
        self.assertIn('«x/-y-/»', masked)
        self.assertIn('r#"-- /- "/-"#', masked)
        self.assertTrue(masked.rstrip().endswith("rfl"))

    def test_invalid_timeout(self):
        for value in (0, -1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                LeanBackend(timeout=value)


@unittest.skipUnless(_installed("v4.25.0"), "Lean v4.25.0 and Lake are not installed")
class LeanIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="proof-eval-backend-")
        self.project = Path(self.directory.name)
        self.version = "v4.25.0"
        self.source = "theorem tiny (n : Nat) : n = n := by rfl"
        self.prefix = "import Lean\nnamespace Demo\n"
        self.suffix = "\nexample (n : Nat) : n = n := tiny n\nend Demo\n"
        self._write_project()
        self.backend = LeanBackend(timeout=30)

    def tearDown(self):
        self.directory.cleanup()

    def _write_project(self):
        (self.project / "lean-toolchain").write_text(f"leanprover/lean4:{self.version}\n")
        (self.project / "lakefile.toml").write_text('name = "proof_eval_test"\nversion = "0.1.0"\n')
        manifest = {"version": "1.1.0", "name": "proof_eval_test", "lakeDir": ".lake", "packagesDir": ".lake/packages", "packages": []}
        (self.project / "lake-manifest.json").write_text(json.dumps(manifest))
        (self.project / "Example.lean").write_text(self.prefix + self.source + self.suffix)
        self._git("init", "-q")
        self._git("add", "lean-toolchain", "lakefile.toml", "lake-manifest.json", "Example.lean")
        self._git("-c", "user.name=Backend Test", "-c", "user.email=backend@example.invalid", "commit", "-qm", "Fixture")
        commit = self._git("rev-parse", "HEAD")
        self.row = {"name": "Demo.tiny", "statement": self.source.split(" :=")[0], "src": self.source,
                    "file_path": "Example.lean", "version_info": [{self.version: commit}]}

    def _git(self, *args):
        result = subprocess.run(["git", "-C", str(self.project), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def evaluate(self, code):
        return self.backend.check(self.row, code, self.version, self.project)

    def test_valid_candidate_context_and_raw_units(self):
        before = (self.project / "Example.lean").read_bytes()
        fingerprint = self.backend.fingerprint(self.row, self.version, self.project)
        result = self.evaluate(self.source + " /- trailing comment -/")
        self.assertEqual(result["status"], "passed", result["diagnostics"])
        self.assertGreater(result["heartbeats_raw"], 0)
        self.assertEqual(result["heartbeats"], result["heartbeats_raw"] / 1000)
        self.assertEqual(result["environment_fingerprint"], fingerprint)
        self.assertEqual(result["details"]["context_mode"], "full_file_replacement")
        self.assertEqual((self.project / "Example.lean").read_bytes(), before)
        self.assertEqual(list(self.project.glob("_ProofEval_*.lean")), [])

    def test_appended_command_is_rejected_by_lean_parser(self):
        result = self.evaluate(self.source + "\n#check Nat")
        self.assertEqual(result["status"], "failed", result["diagnostics"])
        self.assertTrue(any("exactly one complete declaration" in str(d) for d in result["diagnostics"]))

    def test_unfinished_proof_is_rejected(self):
        result = self.evaluate(self.row["statement"] + " := by sorry")
        self.assertEqual(result["status"], "failed", result["diagnostics"])
        self.assertTrue(any("depends on sorryAx" in str(d) for d in result["diagnostics"]))

    def test_transitive_sorry_rejected_but_unrelated_sorry_allowed(self):
        self.prefix += "theorem helper (n : Nat) : n = n := by sorry\n"
        self._write_project()
        valid = self.evaluate(self.source)
        self.assertEqual(valid["status"], "passed", valid["diagnostics"])
        invalid = self.evaluate(self.row["statement"] + " := by exact helper n")
        self.assertEqual(invalid["status"], "failed", invalid["diagnostics"])
        self.assertTrue(any("depends on sorryAx" in str(d) for d in invalid["diagnostics"]))

    def test_missing_import_is_infrastructure_unavailable(self):
        self.prefix = "import MissingUnbuiltDependency\nnamespace Demo\n"
        self._write_project()
        result = self.evaluate(self.source)
        self.assertEqual(result["status"], "unavailable", result["diagnostics"])

    def test_import_support_precedes_module_documentation(self):
        self.prefix = "/- Copyright -/\nimport Lean\n\n/-! # Module documentation\nMore text. -/\nnamespace Demo\n"
        self._write_project()
        result = self.evaluate(self.source)
        self.assertEqual(result["status"], "passed", result["diagnostics"])

    def test_declaration_doc_comment_and_scoped_option(self):
        self.prefix += "set_option linter.unusedVariables false in\n/-- Target documentation. -/\n"
        self._write_project()
        result = self.evaluate(self.source)
        self.assertEqual(result["status"], "passed", result["diagnostics"])

    def test_quoted_package_name_uses_unquoted_directory(self):
        dependency = self.project / ".lake/packages/a-b"
        subprocess.run(["git", "clone", "-q", str(self.project), str(dependency)], check=True)
        manifest_path = self.project / "lake-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["packages"] = [{"name": "«a-b»", "type": "git", "rev": self._git("rev-parse", "HEAD")}]
        manifest_path.write_text(json.dumps(manifest))
        self._git("add", "lake-manifest.json")
        self._git("-c", "user.name=Backend Test", "-c", "user.email=backend@example.invalid", "commit", "-qm", "Dependency")
        self.row["version_info"] = [{self.version: self._git("rev-parse", "HEAD")}]
        environment = self.backend._environment(self.row, self.version, self.project)
        self.assertIn("a-b", environment["dependencies"])

    def test_optimizer_syntax_observer_in_both_module_modes(self):
        from proof_eval import Evaluator
        from proof_eval.optimizer import analyze
        for version in ("v4.25.0", "v4.32.0"):
            if not _installed(version):
                continue
            self.version = version
            self.prefix = ("import Lean\n" if version == "v4.25.0" else "module\npublic import Lean\npublic section\n") + "namespace Demo\n-- Syntax observer fixture\n"
            self._write_project()
            dataset = self.project / "dataset.jsonl"
            dataset.write_text(json.dumps({**self.row, "source": "fixture", "proof_length": 2}) + "\n")
            config = self.project / "environments.json"
            config.write_text(json.dumps({"projects": [{"source": "fixture", "version": version, "path": str(self.project)}]}))
            evaluator = Evaluator(dataset, config, self.project / ".cache", timeout=30)
            analysis = analyze(evaluator, evaluator.dataset.get(self.row["name"]), self.source)
            self.assertTrue(any(self.source[n["start"]:n["end"]] == "by rfl" for n in analysis["nodes"]))

    def test_candidate_cannot_use_original_target(self):
        result = self.evaluate(self.row["statement"] + " := by exact Demo.tiny n")
        self.assertEqual(result["status"], "failed", result["diagnostics"])

    def test_source_drift_is_unavailable(self):
        (self.project / "Example.lean").write_text("-- changed\n" + self.prefix + self.source + self.suffix)
        self.assertEqual(self.evaluate(self.source)["status"], "unavailable")

    def test_older_version_with_changed_reference_proof_uses_exact_statement(self):
        benchmark_source = self.source
        self.source = self.row["statement"] + " := Eq.refl n"
        self._write_project()
        self.row["src"] = benchmark_source
        result = self.evaluate(benchmark_source)
        self.assertEqual(result["status"], "passed", result["diagnostics"])
        self.assertEqual(result["details"]["context_mode"], "prefix_only")

    def test_wrong_version_is_unavailable(self):
        self.assertEqual(self.backend.check(self.row, self.source, "v4.27.0", self.project)["status"], "unavailable")

    def test_existing_concurrent_temporary_source_does_not_dirty_checkout(self):
        temp = self.project / ("_ProofEval_" + "a" * 32 + ".lean")
        temp.write_text("example : True := by trivial\n")
        self.backend.fingerprint(self.row, self.version, self.project)

    def test_timeout_kills_process_and_cleans_temporary_file(self):
        backend = LeanBackend(timeout=0.001)
        result = backend.check(self.row, self.source, self.version, self.project)
        self.assertEqual(result["status"], "timeout", result["diagnostics"])
        self.assertEqual(list(self.project.glob("_ProofEval_*.lean")), [])

    @unittest.skipUnless(_installed("v4.32.0"), "Lean v4.32.0 is not installed")
    def test_newer_lean_module_mode(self):
        self.version = "v4.32.0"
        self.prefix = "module\npublic import Lean\npublic section\nnamespace Demo\n"
        self._write_project()
        result = self.evaluate(self.source)
        self.assertEqual(result["status"], "passed", result["diagnostics"])


if __name__ == "__main__":
    unittest.main()
