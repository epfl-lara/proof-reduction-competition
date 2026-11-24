"""Explicit module-safe measurement version; the historical backend stays frozen.

The version reuses pinned source selection and process handling. Its measurement
command adds no ordinary-word keywords and imports elaborator support publicly in
Lean modules. Each reference and candidate receives the new wrapper/source hash.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from . import backend as legacy
from .backend import _run

MEASUREMENT_VERSION = "module_safe_v2"
MEASUREMENT_WRAPPER = r"""
open Lean Elab Command in
elab "#proof_eval_measure_v2 " marker:str targetNameText:str expectedEnd:num cmd:command : command => do
  let some tail := cmd.raw.getTailPos? | throwError "Cannot locate candidate command end"
  unless tail.byteIdx == expectedEnd.getNat do
    throwError m!"Candidate must contain exactly one complete declaration (parsed end {tail.byteIdx}, expected {expectedEnd.getNat})"
  let targetName := targetNameText.getString.toName
  let resolveTarget : CommandElabM (Option Name) := do
    try
      let actual ← resolveGlobalConstNoOverloadCore targetName
      return if Lean.privateToUserName actual == targetName then some actual else none
    catch _ => return none
  let before ← getEnv
  if (← resolveTarget).isSome then
    throwError "Target declaration already exists before candidate elaboration"
  let start ← IO.getNumHeartbeats
  elabCommand (← `(command| set_option Elab.async false in set_option maxHeartbeats 0 in $cmd))
  let finish ← IO.getNumHeartbeats
  let some actualTarget ← resolveTarget
    | throwError "Candidate did not introduce the target declaration"
  if before.contains actualTarget then
    throwError "Candidate did not introduce a new target declaration"
  let axioms ← Lean.collectAxioms actualTarget
  if axioms.contains ``sorryAx then
    throwError "Target declaration depends on sorryAx"
  logInfo m!"{marker.getString}:{finish - start}"
"""


def _declaration_comment(trailing: str) -> tuple[str, str]:
    """Keep module notes outside the command, attaching only the final docstring."""
    cursor, doc_start = 0, None
    while cursor < len(trailing):
        if trailing[cursor].isspace():
            cursor += 1
        elif trailing.startswith("--", cursor):
            end = trailing.find("\n", cursor)
            cursor = len(trailing) if end == -1 else end
        elif trailing.startswith("/-", cursor):
            start = cursor
            depth, cursor = 1, cursor + 2
            while depth and cursor < len(trailing):
                if trailing.startswith("/-", cursor):
                    depth, cursor = depth + 1, cursor + 2
                elif trailing.startswith("-/", cursor):
                    depth, cursor = depth - 1, cursor + 2
                else:
                    cursor += 1
            if depth:
                raise ValueError("Unterminated context comment")
            if trailing.startswith("/--", start):
                doc_start = start
            elif trailing.startswith("/-!", start):
                doc_start = None
        else:
            raise ValueError("Unexpected non-comment in the reference prefix")
    return (
        (trailing, "")
        if doc_start is None
        else (trailing[:doc_start], trailing[doc_start:])
    )


def _source(row: dict, candidate: str, project: Path, nonce: str) -> tuple[str, str]:
    """Reuse exact source selection; replace only the identified instrumentation."""
    source, mode = legacy._source(row, candidate, project, nonce)
    marker = "PROOF_EVAL_" + nonce
    pattern = re.compile(
        r"\n#proof_eval_measure "
        + re.escape(json.dumps(marker))
        + " target "
        + re.escape(json.dumps(row["name"], ensure_ascii=False))
        + r" end (\d+) in\n"
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError("Ambiguous historical instrumentation boundary")
    match = matches[0]
    prefix, following = source[: match.start()], source[match.end() :]
    candidate_bytes = int(match.group(1)) - len(source[: match.end()].encode())
    if candidate_bytes <= 0 or candidate_bytes > len(following.encode()):
        raise ValueError("Invalid historical candidate span")
    measured = following.encode()[:candidate_bytes]
    measured.decode("utf-8")
    candidate_position = following.find(candidate)
    candidate_end = len(legacy._masked_comments(candidate).rstrip())
    while (
        candidate_position >= 0
        and len((following[:candidate_position] + candidate[:candidate_end]).encode())
        != candidate_bytes
    ):
        candidate_position = following.find(candidate, candidate_position + 1)
    if candidate_position < 0:
        raise ValueError("Candidate bytes are missing from the historical assembly")
    old_support = "\nimport Lean\n" + legacy.MEASUREMENT_WRAPPER + "\n"
    if prefix.count(old_support) != 1:
        raise ValueError("Ambiguous historical support insertion")
    is_module = (
        re.search(r"(?m)^module\s*$", legacy._masked_comments(prefix)) is not None
    )
    support_import = "public meta import Lean" if is_module else "import Lean"
    new_support = "\n" + support_import + "\n" + MEASUREMENT_WRAPPER + "\n"
    prefix = prefix.replace(old_support, new_support, 1)
    support_end = prefix.index(new_support) + len(new_support)
    context = prefix[support_end:]
    modifiers = re.search(
        r"\b(?:public|private|protected|noncomputable|unsafe|partial)"
        r"(?:\s+(?:public|private|protected|noncomputable|unsafe|partial))*\s*$",
        legacy._masked_comments(context),
    )
    before_candidate = following[:candidate_position]
    if modifiers is not None:
        leading, modifier_text = (
            context[: modifiers.start()],
            context[modifiers.start() :],
        )
        comment_start = len(legacy._masked_comments(leading).rstrip())
        outside, docstring = _declaration_comment(leading[comment_start:])
        prefix = prefix[:support_end] + leading[:comment_start] + outside
        measured_prefix = docstring + modifier_text + before_candidate
    else:
        outside, docstring = _declaration_comment(before_candidate)
        prefix += outside
        measured_prefix = docstring
    following = measured_prefix + following[candidate_position:]
    candidate_bytes = len((measured_prefix + candidate[:candidate_end]).encode())
    end = 0
    for _ in range(10):
        preamble = (
            prefix
            + "\n#proof_eval_measure_v2 "
            + json.dumps(marker)
            + " "
            + json.dumps(row["name"], ensure_ascii=False)
            + f" {end}\n"
        )
        new_end = len(preamble.encode()) + candidate_bytes
        if new_end == end:
            return preamble + following, mode
        end = new_end
    raise ValueError("Could not establish version-2 candidate boundaries")


def _checked_project(path: Path, revision: str) -> None:
    """Bound metadata checks like proof checks; do not retry unknown subprocesses."""
    for arguments, expected in (
        (["rev-parse", "HEAD"], revision),
        (
            [
                "status",
                "--porcelain",
                "--untracked-files=normal",
                "--",
                *legacy._RELEVANT_PATHS,
            ],
            "",
        ),
    ):
        proc = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(path), *arguments],
            capture_output=True,
            text=True,
            timeout=600,
        )
        actual = proc.stdout.strip()
        if arguments[0] == "status":
            actual = "\n".join(
                line
                for line in actual.splitlines()
                if not re.search(r"(?:^|[/ ])_ProofEval_[a-f0-9]+\.lean$", line)
            )
        if proc.returncode or actual != expected:
            raise ValueError(
                f"Pinned project revision or tracked source changed: {path}: {proc.stderr.strip()}"
            )


class LeanBackend(legacy.LeanBackend):
    """New measurements only; version 1 reference fingerprints stay unchanged."""

    measurement_version = MEASUREMENT_VERSION

    def _environment(self, row: dict, version: str, project_dir: Path) -> dict:
        project = Path(project_dir).resolve()
        versions = {
            v: commit for entry in row["version_info"] for v, commit in entry.items()
        }
        if version not in versions:
            raise ValueError(f"Version {version} is not listed for {row['name']}")
        expected = versions[version]
        toolchain = (project / "lean-toolchain").read_text().strip()
        if toolchain != f"leanprover/lean4:{version}":
            raise ValueError(
                f"Wrong lean-toolchain: {toolchain!r}; expected leanprover/lean4:{version}"
            )
        lake = shutil.which(self.lake)
        if not lake:
            raise ValueError(f"Lake executable not found: {self.lake}")
        # An elan shim could otherwise fetch an absent toolchain implicitly.
        elan = shutil.which("elan")
        if elan:
            installed = subprocess.run(
                [elan, "toolchain", "list"], capture_output=True, text=True, timeout=600
            )
            if installed.returncode or not any(
                line.split()[0] == toolchain
                for line in installed.stdout.splitlines()
                if line.split()
            ):
                raise ValueError(f"Lean toolchain {toolchain} is not installed")
            lean_path = subprocess.run(
                [elan, "which", "lean"],
                cwd=project,
                capture_output=True,
                text=True,
                env={**os.environ, "ELAN_TOOLCHAIN": toolchain},
                timeout=600,
            )
            if lean_path.returncode:
                raise ValueError(
                    f"Cannot resolve installed compiler: {lean_path.stderr.strip()}"
                )
            compiler = subprocess.run(
                [lean_path.stdout.strip(), "--version"],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if compiler.returncode:
                raise ValueError(
                    f"Cannot identify installed compiler: {compiler.stderr.strip()}"
                )
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
                raise ValueError(
                    f"Dependency {package.get('name')} is not pinned to a Git revision"
                )
            # Recent Lake manifests serialize non-identifier Name components
            # with Lean quotes, while checkout directory names are unquoted.
            package_name = re.sub(r"«([^»]+)»", r"\1", package["name"])
            dependency_path = packages_dir / package_name
            _checked_project(dependency_path, package["rev"])
            dependencies[package_name] = package["rev"]
        if row.get("file_path"):
            _checked_project(project, expected)
        elif dependencies.get("mathlib") != expected:
            raise ValueError(
                f"Standalone benchmark requires Mathlib revision {expected}"
            )
        # Include the exact lakefile too: options in it affect elaboration.
        config = {}
        for name in ("lakefile.lean", "lakefile.toml", "lake-manifest.json"):
            path = project / name
            if path.exists():
                config[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        environment = {
            "project_dir": str(project),
            "version": version,
            "source_commit": expected,
            "toolchain": toolchain,
            "compiler_version": compiler_version,
            "dependencies": dependencies,
            "configuration_sha256": config,
            "lake": str(Path(lake).absolute()),
            "timeout_seconds": self.timeout,
            "measurement": "synchronous declaration elaboration; IO.getNumHeartbeats delta / 1000",
            "measurement_wrapper_sha256": hashlib.sha256(
                legacy.MEASUREMENT_WRAPPER.encode()
            ).hexdigest(),
            "backend_implementation_sha256": hashlib.sha256(
                Path(legacy.__file__).read_bytes()
            ).hexdigest(),
            "maxHeartbeats": 0,
            "Elab.async": False,
            "build_artifacts": "trusted prebuilt artifacts; source revisions verified",
        }
        environment.update(
            measurement_version=MEASUREMENT_VERSION,
            environment_probe_timeout_seconds=600,
            legacy_backend_implementation_sha256=environment[
                "backend_implementation_sha256"
            ],
            backend_implementation_sha256=hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            measurement_wrapper_sha256=hashlib.sha256(
                MEASUREMENT_WRAPPER.encode()
            ).hexdigest(),
        )
        return environment

    def check(
        self, row: dict, candidate_code: str, version: str, project_dir: Path
    ) -> dict:
        started = time.monotonic()
        result = {
            "status": "unavailable",
            "passed": False,
            "heartbeats": None,
            "heartbeats_raw": None,
            "diagnostics": [],
            "elapsed_seconds": 0.0,
            "environment_fingerprint": "",
            "details": {},
        }
        temporary = None
        evaluating = False
        try:
            project = Path(project_dir).resolve()
            environment = self._environment(row, version, project)
            result["details"] = environment
            result["environment_fingerprint"] = hashlib.sha256(
                json.dumps(environment, sort_keys=True).encode()
            ).hexdigest()
            nonce = uuid.uuid4().hex
            source, context_mode = _source(row, candidate_code, project, nonce)
            result["details"]["context_mode"] = context_mode
            wrapper_line = next(
                i + 1
                for i, line in enumerate(source.splitlines())
                if line.startswith("#proof_eval_measure_v2 ")
            )
            result["details"]["candidate_start_line"] = wrapper_line + 1
            result["details"]["original_file_path"] = row.get("file_path") or None
            temporary = str(project / f"_ProofEval_{nonce}.lean")
            fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            Path(temporary).write_text(source, encoding="utf-8")
            command = [
                environment["lake"],
                "env",
                "lean",
                "--json",
                str(Path(temporary).name),
            ]
            evaluating = True
            proc = _run(command, project, self.timeout)
            diagnostics = []
            for stream, output in (("stdout", proc.stdout), ("stderr", proc.stderr)):
                for line in output.splitlines():
                    try:
                        diagnostic = json.loads(line)
                    except json.JSONDecodeError:
                        diagnostic = {
                            "severity": "output",
                            "message": line,
                            "stream": stream,
                        }
                    if not isinstance(diagnostic, dict):
                        diagnostic = {
                            "severity": "output",
                            "message": line,
                            "stream": stream,
                        }
                    diagnostics.append(diagnostic)
            result["diagnostics"] = diagnostics
            marker = f"PROOF_EVAL_{nonce}:"
            values = []
            for diagnostic in diagnostics:
                message = diagnostic.get("data", diagnostic.get("message", ""))
                if isinstance(message, str) and re.fullmatch(
                    re.escape(marker) + r"\d+", message.strip()
                ):
                    values.append(int(message.strip()[len(marker) :]))
            errors = any(d.get("severity") == "error" for d in diagnostics)
            infrastructure_error = proc.returncode not in (0, 1) or (
                proc.returncode != 0 and not errors
            )
            for diagnostic in diagnostics:
                message = str(
                    diagnostic.get("data", diagnostic.get("message", ""))
                ).lower()
                missing_artifact = any(
                    fragment in message
                    for fragment in (
                        "unknown module prefix",
                        "could not resolve import",
                        "unknown package",
                        "cannot load native shared library",
                        "failed to load shared library",
                    )
                ) or (
                    ".olean" in message
                    and any(
                        fragment in message
                        for fragment in (
                            "does not exist",
                            "no such file",
                            "failed to read",
                            "invalid header",
                        )
                    )
                )
                line = diagnostic.get("pos", {}).get("line")
                prefix_error = (
                    diagnostic.get("severity") == "error"
                    and isinstance(line, int)
                    and line < wrapper_line
                )
                infrastructure_error = (
                    infrastructure_error or missing_artifact or prefix_error
                )
            result["details"]["exit_code"] = proc.returncode
            if proc.returncode == 0 and not errors and len(values) == 1:
                result.update(
                    status="passed",
                    passed=True,
                    heartbeats_raw=values[0],
                    heartbeats=values[0] / 1000,
                )
            else:
                result["status"] = "unavailable" if infrastructure_error else "failed"
                if len(values) != 1:
                    diagnostics.append(
                        {
                            "severity": "error",
                            "message": "Expected exactly one verified target heartbeat marker",
                        }
                    )
        except subprocess.TimeoutExpired as exc:
            result["status"] = "timeout" if evaluating else "unavailable"
            result["diagnostics"].append(
                {
                    "severity": "error",
                    "message": f"Lean evaluation timed out after {exc.timeout} seconds",
                }
            )
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            result["diagnostics"].append({"severity": "error", "message": str(exc)})
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
            result["elapsed_seconds"] = time.monotonic() - started
        return result
