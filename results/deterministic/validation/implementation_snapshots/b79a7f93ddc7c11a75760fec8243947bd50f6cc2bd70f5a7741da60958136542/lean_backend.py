"""Fresh-process Lean evaluation in explicitly configured, pinned Lake projects.

Projects and their dependencies must already be built.  This module never runs
``lake update`` or downloads a repository.  Build artifacts are trusted local
inputs: source revision checks cannot establish how an existing .olean was built.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import uuid


# This uses Lean itself, and consequently also works in projects without Mathlib.
# Keep the measurement scope and options in the environment fingerprint.
MEASUREMENT_WRAPPER = r'''
open Lean Elab Command in
elab "#proof_eval_measure " marker:str " target " target:str " end " expectedEnd:num " in " cmd:command : command => do
  let some tail := cmd.raw.getTailPos? | throwError "Cannot locate candidate command end"
  unless tail.byteIdx == expectedEnd.getNat do
    throwError "Candidate must contain exactly one complete declaration"
  let targetName := target.getString.toName
  if (← getEnv).contains targetName then
    throwError "Target declaration already exists before candidate elaboration"
  let start ← IO.getNumHeartbeats
  elabCommand (← `(command| set_option Elab.async false in set_option maxHeartbeats 0 in $cmd))
  let finish ← IO.getNumHeartbeats
  unless (← getEnv).contains targetName do
    throwError "Candidate did not introduce the target declaration"
  let axioms ← Lean.collectAxioms targetName
  if axioms.contains ``sorryAx then
    throwError "Target declaration depends on sorryAx"
  logInfo m!"{marker.getString}:{finish - start}"
'''

_RELEVANT_PATHS = (
    "*.lean", "lean-toolchain", "lakefile.toml", "lakefile.lean", "lake-manifest.json"
)


def _masked_comments(text: str) -> str:
    """Mask nested Lean comments, preserving character offsets and strings."""
    out = list(text)
    i = 0
    depth = 0
    in_string = False
    while i < len(text):
        if depth:
            if text.startswith("/-", i):
                out[i:i + 2] = "  "
                depth += 1
                i += 2
            elif text.startswith("-/", i):
                out[i:i + 2] = "  "
                depth -= 1
                i += 2
            else:
                if text[i] != "\n":
                    out[i] = " "
                i += 1
        elif in_string:
            if text[i] == "\\":
                i += 2
            elif text[i] == '"':
                in_string = False
                i += 1
            else:
                i += 1
        elif text[i] == "r" and (raw := re.match(r'r(#+)?"', text[i:])):
            terminator = '"' + (raw.group(1) or "")
            end = text.find(terminator, i + raw.end())
            if end < 0:
                raise ValueError("Unterminated raw string")
            i = end + len(terminator)
        elif text[i] == "«":
            end = text.find("»", i + 1)
            if end < 0:
                raise ValueError("Unterminated quoted identifier")
            i = end + 1
        elif text[i] == "'" and (char := re.match(r"'(?:\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'", text[i:])):
            i += char.end()
        elif text.startswith("/-", i):
            out[i:i + 2] = "  "
            depth = 1
            i += 2
        elif text.startswith("--", i):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            out[i:end] = " " * (end - i)
            i = end
        elif text[i] == '"':
            in_string = True
            i += 1
        else:
            i += 1
    if depth:
        raise ValueError("Unterminated block comment")
    return "".join(out)


def _inject_support(prefix: str) -> str:
    """Insert the import and command after a Lean module's import header."""
    masked = _masked_comments(prefix)
    pos = 0
    offset = 0
    for line, original in zip(masked.splitlines(keepends=True), prefix.splitlines(keepends=True)):
        stripped = line.strip()
        offset += len(original)
        if not stripped:
            continue
        if stripped in {"module", "prelude"} or re.match(r"(?:(?:public|private|meta)\s+)*import\s", stripped):
            pos = offset
            continue
        break
    # Stop at the last import, not at the first declaration: /-! module docs
    # are commands even though the comment scanner masks their contents.
    return prefix[:pos] + "\nimport Lean\n" + MEASUREMENT_WRAPPER + "\n" + prefix[pos:]


def _source(row: dict, candidate: str, project: Path, nonce: str) -> tuple[str, str]:
    relative = row.get("file_path", "")
    if relative:
        source_path = (project / relative).resolve()
        if not source_path.is_relative_to(project):
            raise ValueError("Benchmark file_path escapes configured project")
        original = source_path.read_text(encoding="utf-8")
        reference = row["src"]
        if original.count(reference) == 1:
            prefix, suffix = original.split(reference, 1)
            context_mode = "full_file_replacement"
        else:
            # Older releases sometimes have the same statement but a different
            # reference proof. Only the context preceding the target is needed
            # to check it: stop after the replacement rather than guessing the
            # old declaration's end. Lean permits open scopes at end of file.
            statement = row.get("statement", "")
            if not statement or original.count(statement) != 1:
                raise ValueError(
                    "Reference statement is not an exact unique match in the pinned source file; "
                    "refusing to substitute using stale line numbers"
                )
            offset = original.index(statement)
            masked = _masked_comments(original)
            if masked[offset:offset + len(statement)] != _masked_comments(statement):
                raise ValueError("Reference statement occurs inside a comment")
            if not masked[offset + len(statement):].lstrip().startswith(":="):
                raise ValueError("Reference statement does not end at a proof assignment")
            prefix, suffix = original[:offset], ""
            context_mode = "prefix_only"
    else:
        prefix, suffix = row.get("header", ""), ""
        context_mode = "standalone_header"
    # A declaration doc comment must remain attached to the declaration inside
    # the measurement command. Leaving it before our custom command makes Lean
    # (and Mathlib's lemma parser) reject the file. Scoped `omit ... in` and
    # `set_option ... in` stay outside and continue to scope the whole command.
    comment_start = len(_masked_comments(prefix).rstrip())
    trailing = prefix[comment_start:]
    if "/--" in trailing:
        prefix = prefix[:comment_start]
        candidate = trailing + candidate
    prefix = _inject_support(prefix)
    marker = f"PROOF_EVAL_{nonce}"
    # Adding a decimal offset changes the offset itself. Find its fixed point.
    end = 0
    candidate_end_chars = len(_masked_comments(candidate).rstrip())
    for _ in range(10):
        preamble = (
            prefix + f'\n#proof_eval_measure "{marker}" target '
            + json.dumps(row["name"], ensure_ascii=False) + f" end {end} in\n"
        )
        new_end = len((preamble + candidate[:candidate_end_chars]).encode("utf-8"))
        if new_end == end:
            return preamble + candidate + "\n" + suffix, context_mode
        end = new_end
    raise ValueError("Could not establish candidate source boundaries")


def _run(args: list[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess:
    """Kill Lake, Lean and any descendants together when evaluation times out."""
    proc = subprocess.Popen(
        args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", start_new_session=True,
        env={**os.environ, "ELAN_TOOLCHAIN": (cwd / "lean-toolchain").read_text().strip()},
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(args, timeout, output=stdout, stderr=stderr) from None
    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)


def _git(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, timeout=15,
    )
    if proc.returncode:
        raise ValueError(f"Cannot verify Git checkout {path}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _checked_git(path: Path, revision: str) -> None:
    if _git(path, "rev-parse", "HEAD") != revision:
        raise ValueError(f"Wrong source revision in {path}; expected {revision}")
    dirty = _git(path, "status", "--porcelain", "--untracked-files=normal", "--", *_RELEVANT_PATHS)
    # Each worker owns one temporary source; concurrent workers never edit originals.
    dirty = "\n".join(line for line in dirty.splitlines() if not re.search(r"(?:^|[/ ])_ProofEval_[a-f0-9]+\.lean$", line))
    if dirty:
        raise ValueError(f"Relevant sources or Lake configuration are dirty in {path}: {dirty[:1000]}")


class LeanBackend:
    """Compile one benchmark candidate in one prebuilt version environment."""

    def __init__(self, lake: str = "lake", timeout: float = 60):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        self.lake = lake
        self.timeout = float(timeout)

    def _environment(self, row: dict, version: str, project_dir: Path) -> dict:
        project = Path(project_dir).resolve()
        versions = {v: commit for entry in row["version_info"] for v, commit in entry.items()}
        if version not in versions:
            raise ValueError(f"Version {version} is not listed for {row['name']}")
        expected = versions[version]
        toolchain = (project / "lean-toolchain").read_text().strip()
        if toolchain != f"leanprover/lean4:{version}":
            raise ValueError(f"Wrong lean-toolchain: {toolchain!r}; expected leanprover/lean4:{version}")
        lake = shutil.which(self.lake)
        if not lake:
            raise ValueError(f"Lake executable not found: {self.lake}")
        # An elan shim could otherwise fetch an absent toolchain implicitly.
        elan = shutil.which("elan")
        if elan:
            installed = subprocess.run([elan, "toolchain", "list"], capture_output=True, text=True, timeout=15)
            if installed.returncode or not any(line.split()[0] == toolchain for line in installed.stdout.splitlines() if line.split()):
                raise ValueError(f"Lean toolchain {toolchain} is not installed")
            lean_path = subprocess.run(
                [elan, "which", "lean"], cwd=project, capture_output=True, text=True,
                env={**os.environ, "ELAN_TOOLCHAIN": toolchain}, timeout=15,
            )
            if lean_path.returncode:
                raise ValueError(f"Cannot resolve installed compiler: {lean_path.stderr.strip()}")
            compiler = subprocess.run([lean_path.stdout.strip(), "--version"], capture_output=True, text=True, timeout=15)
            if compiler.returncode:
                raise ValueError(f"Cannot identify installed compiler: {compiler.stderr.strip()}")
            compiler_version = compiler.stdout.strip()
        else:
            compiler_version = "toolchain pin only (elan unavailable)"
        manifest_path = project / "lake-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        packages_dir = project / manifest.get("packagesDir", ".lake/packages")
        packages = manifest.get("packages", [])
        dependencies = {}
        for package in packages:
            if package.get("type") != "git" or not package.get("rev"):
                raise ValueError(f"Dependency {package.get('name')} is not pinned to a Git revision")
            # Recent Lake manifests serialize non-identifier Name components
            # with Lean quotes, while checkout directory names are unquoted.
            package_name = re.sub(r"«([^»]+)»", r"\1", package["name"])
            dependency_path = packages_dir / package_name
            _checked_git(dependency_path, package["rev"])
            dependencies[package_name] = package["rev"]
        if row.get("file_path"):
            _checked_git(project, expected)
        elif dependencies.get("mathlib") != expected:
            raise ValueError(f"Standalone benchmark requires Mathlib revision {expected}")
        # Include the exact lakefile too: options in it affect elaboration.
        config = {}
        for name in ("lakefile.lean", "lakefile.toml", "lake-manifest.json"):
            path = project / name
            if path.exists():
                config[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return {
            "project_dir": str(project), "version": version,
            "source_commit": expected, "toolchain": toolchain,
            "compiler_version": compiler_version,
            "dependencies": dependencies, "configuration_sha256": config,
            "lake": str(Path(lake).absolute()), "timeout_seconds": self.timeout,
            "measurement": "synchronous declaration elaboration; IO.getNumHeartbeats delta / 1000",
            "measurement_wrapper_sha256": hashlib.sha256(MEASUREMENT_WRAPPER.encode()).hexdigest(),
            "backend_implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "maxHeartbeats": 0, "Elab.async": False,
            "build_artifacts": "trusted prebuilt artifacts; source revisions verified",
        }

    def fingerprint(self, row: dict, version: str, project_dir: Path) -> str:
        try:
            environment = self._environment(row, version, project_dir)
        except (OSError, subprocess.SubprocessError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(str(exc)) from exc
        return hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()

    def check(self, row: dict, candidate_code: str, version: str, project_dir: Path) -> dict:
        started = time.monotonic()
        result = {
            "status": "unavailable", "passed": False, "heartbeats": None,
            "heartbeats_raw": None, "diagnostics": [], "elapsed_seconds": 0.0,
            "environment_fingerprint": "", "details": {},
        }
        temporary = None
        evaluating = False
        try:
            project = Path(project_dir).resolve()
            environment = self._environment(row, version, project)
            result["details"] = environment
            result["environment_fingerprint"] = hashlib.sha256(json.dumps(environment, sort_keys=True).encode()).hexdigest()
            nonce = uuid.uuid4().hex
            source, context_mode = _source(row, candidate_code, project, nonce)
            result["details"]["context_mode"] = context_mode
            wrapper_line = next(i + 1 for i, line in enumerate(source.splitlines()) if line.startswith("#proof_eval_measure "))
            result["details"]["candidate_start_line"] = wrapper_line + 1
            result["details"]["original_file_path"] = row.get("file_path") or None
            temporary = str(project / f"_ProofEval_{nonce}.lean")
            fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            Path(temporary).write_text(source, encoding="utf-8")
            command = [environment["lake"], "env", "lean", "--json", str(Path(temporary).name)]
            evaluating = True
            proc = _run(command, project, self.timeout)
            diagnostics = []
            for stream, output in (("stdout", proc.stdout), ("stderr", proc.stderr)):
                for line in output.splitlines():
                    try:
                        diagnostic = json.loads(line)
                    except json.JSONDecodeError:
                        diagnostic = {"severity": "output", "message": line, "stream": stream}
                    if not isinstance(diagnostic, dict):
                        diagnostic = {"severity": "output", "message": line, "stream": stream}
                    diagnostics.append(diagnostic)
            result["diagnostics"] = diagnostics
            marker = f"PROOF_EVAL_{nonce}:"
            values = []
            for diagnostic in diagnostics:
                message = diagnostic.get("data", diagnostic.get("message", ""))
                if isinstance(message, str) and re.fullmatch(re.escape(marker) + r"\d+", message.strip()):
                    values.append(int(message.strip()[len(marker):]))
            errors = any(d.get("severity") == "error" for d in diagnostics)
            infrastructure_error = proc.returncode not in (0, 1) or (proc.returncode != 0 and not errors)
            for diagnostic in diagnostics:
                message = str(diagnostic.get("data", diagnostic.get("message", ""))).lower()
                missing_artifact = any(fragment in message for fragment in (
                    "unknown module prefix", "could not resolve import", "unknown package",
                    "cannot load native shared library", "failed to load shared library",
                )) or (".olean" in message and any(fragment in message for fragment in (
                    "does not exist", "no such file", "failed to read", "invalid header",
                )))
                line = diagnostic.get("pos", {}).get("line")
                prefix_error = diagnostic.get("severity") == "error" and isinstance(line, int) and line < wrapper_line
                infrastructure_error = infrastructure_error or missing_artifact or prefix_error
            result["details"]["exit_code"] = proc.returncode
            if proc.returncode == 0 and not errors and len(values) == 1:
                result.update(status="passed", passed=True, heartbeats_raw=values[0], heartbeats=values[0] / 1000)
            else:
                result["status"] = "unavailable" if infrastructure_error else "failed"
                if len(values) != 1:
                    diagnostics.append({"severity": "error", "message": "Expected exactly one verified target heartbeat marker"})
        except subprocess.TimeoutExpired as exc:
            result["status"] = "timeout" if evaluating else "unavailable"
            result["diagnostics"].append({"severity": "error", "message": f"Lean evaluation timed out after {exc.timeout} seconds"})
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            result["diagnostics"].append({"severity": "error", "message": str(exc)})
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
            result["elapsed_seconds"] = time.monotonic() - started
        return result


def check(row: dict, candidate_code: str, version: str, project_dir: Path, timeout: float = 60) -> dict:
    return LeanBackend(timeout=timeout).check(row, candidate_code, version, project_dir)
