"""Explicit tactic diagnostics, independently cached from arena measurements."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, sha
from proof_eval.verification.api import EvaluationNotReady, Evaluator
from proof_eval.verification.backend import (
    MEASUREMENT_WRAPPER,
    _masked_comments,
    _run,
    _source,
)
from proof_eval.verification.metrics import validate_candidate
from proof_eval.verification.profile_trace import trace_hotspots

# Read the structured MessageData tree rather than parsing the pretty-printed
# trace indentation. Keep context wrappers while printing individual headers.
PROFILE_SUPPORT = r"""
open Lean in
private meta partial def proofProfileTrace (msg : MessageData)
    (wrap : MessageData → MessageData := id) : BaseIO (Array Json) := do
  match msg with
  | .withContext ctx d => proofProfileTrace d (fun m => wrap (.withContext ctx m))
  | .withNamingContext ctx d => proofProfileTrace d (fun m => wrap (.withNamingContext ctx m))
  | .ofWidget _ d | .nest _ d | .group d | .tagged _ d => proofProfileTrace d wrap
  | .compose a b => return (← proofProfileTrace a wrap) ++ (← proofProfileTrace b wrap)
  | .trace data header children =>
    let mut nodes := #[]
    for child in children do
      nodes := nodes ++ (← proofProfileTrace child wrap)
    if data.startTime == 0 then return nodes
    let text ← (wrap header).toString
    return #[Json.mkObj [
      ("class", toJson data.cls.toString), ("tag", toJson data.tag),
      ("header", toJson (List.asString (text.toList.take 500))),
      ("header_truncated", toJson (decide (text.toList.length > 500))),
      ("raw", toJson (data.stopTime - data.startTime).toUInt64.toNat),
      ("children", Json.arr nodes)]]
  | _ => return #[]
open Lean Elab Tactic in
elab "profile_tactic " label:str " in " tac:tactic : tactic => do
  let start ← IO.getNumHeartbeats
  let outcome ← tryCatchRuntimeEx
    (do evalTactic tac; pure (Except.ok () : Except Exception Unit))
    (fun e => pure (.error e))
  let finish ← IO.getNumHeartbeats
  let ref ← getRef
  logInfo <| .tagged `trace m!"__MARKER___MARK:{(Json.mkObj [
    ("label", toJson (List.asString (label.getString.toList.take 200))),
    ("label_truncated", toJson (decide (label.getString.toList.length > 200))),
    ("start", toJson (ref.getPos?.map (·.byteIdx))),
    ("end", toJson (ref.getTailPos?.map (·.byteIdx))),
    ("heartbeats_raw", toJson (finish - start)),
    ("succeeded", toJson outcome.isOk)]).compress}"
  match outcome with
  | .ok _ => pure ()
  | .error e => throw e
open Lean Elab Command in
elab "#proof_profile_report " "in " cmd:command : command => do
  let before := (← get).messages.toList.length
  try
    elabCommand (← `(command|
      set_option trace.profiler true in
      set_option trace.profiler.useHeartbeats true in
      set_option trace.profiler.threshold __THRESHOLD__ in $cmd))
  finally
    let mut trees := #[]
    for message in (← get).messages.toList.drop before do
      if message.data.hasTag (· == `trace) then
        trees := trees ++ (← proofProfileTrace message.data)
    logInfo <| .tagged `trace m!"__MARKER___TRACE:{(Json.arr trees).compress}"
"""


@dataclass(frozen=True)
class ProfileConfig:
    """One diagnostic version; the native threshold uses raw counter units."""

    version: str | None = None
    threshold_raw: int = 10_000
    limit: int = 20

    def __post_init__(self) -> None:
        if self.version is not None and (
            not isinstance(self.version, str) or not self.version
        ):
            raise ValueError("Profile version must be a nonempty string")
        if type(self.threshold_raw) is not int or self.threshold_raw < 0:
            raise ValueError("Profile threshold_raw must be a nonnegative integer")
        if type(self.limit) is not int or not 1 <= self.limit <= 100:
            raise ValueError("Profile limit must be an integer from 1 to 100")


def _profile_source(
    row: dict,
    code: str,
    project: Path,
    nonce: str,
    config: ProfileConfig,
    *,
    measurement_version: str = "legacy_v1",
) -> tuple[str, int, str]:
    """Use the pinned source context and unchanged target-verification wrapper.

    Drop the suffix: diagnostics belong to this declaration only. Recompute the
    wrapper's UTF-8 boundary after injecting diagnostic support at the import
    header; never change the canonical measurement implementation.
    """
    if measurement_version == "module_safe_v2":
        from .instrumentation import module_observation_source

        support = PROFILE_SUPPORT.replace(
            "__MARKER__", f"PROOF_PROFILE_{nonce}"
        ).replace("__THRESHOLD__", str(config.threshold_raw))
        return module_observation_source(
            row, code, project, nonce, support, "#proof_profile_report in", measure=True
        )
    source, mode = _source(row, code, project, nonce)
    prefix = source.split("\n#proof_eval_measure ", 1)[0]
    marker = f"PROOF_PROFILE_{nonce}"
    support = PROFILE_SUPPORT.replace("__MARKER__", marker).replace(
        "__THRESHOLD__", str(config.threshold_raw)
    )
    prefix = prefix.replace(MEASUREMENT_WRAPPER, MEASUREMENT_WRAPPER + support, 1)
    # _source attaches a trailing declaration doc comment to the candidate.
    candidate = source.split("\n#proof_eval_measure ", 1)[1].split(" in\n", 1)[1]
    # Its optional suffix starts after the exact supplied code.
    code_start = candidate.index(code)
    stop = code_start + len(code)
    candidate = candidate[:stop]
    candidate_end = len(_masked_comments(candidate).rstrip())
    end = 0
    for _ in range(10):
        preamble = (
            prefix
            + "\n#proof_profile_report in\n#proof_eval_measure "
            + f'"PROOF_EVAL_{nonce}" target '
            + json.dumps(row["name"], ensure_ascii=False)
            + f" end {end} in\n"
        )
        new_end = len((preamble + candidate[:candidate_end]).encode())
        if new_end == end:
            offset = len((preamble + candidate[:code_start]).encode())
            return preamble + candidate + "\n", offset, mode
        end = new_end
    raise ValueError("Could not establish profile source boundaries")


def _parse_output(
    stdout: str, stderr: str, nonce: str, code: str, offset: int
) -> tuple[list[dict], list[dict], list[str], int | None]:
    trees, marks, errors, totals = [], [], [], []
    traces = 0
    marker = f"PROOF_PROFILE_{nonce}"
    for line in stdout.splitlines():
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict):
            continue
        data = message.get("data", "")
        if not isinstance(data, str):
            continue
        if data.startswith(marker + "_TRACE:"):
            trees = json.loads(data.split(":", 1)[1])
            traces += 1
        elif data.startswith(marker + "_MARK:"):
            item = json.loads(data.split(":", 1)[1])
            raw = item.get("heartbeats_raw")
            if type(raw) is not int or raw < 0:
                raise ValueError("Invalid marked tactic heartbeat count")
            for bound in ("start", "end"):
                byte = item.get(bound)
                if type(byte) is not int or not 0 <= byte - offset <= len(
                    code.encode()
                ):
                    raise ValueError("Marked tactic position outside candidate")
                item[bound] = len(code.encode()[: byte - offset].decode())
            item.update(heartbeats=raw / 1000, inclusive=True)
            item["line"] = code.count("\n", 0, item["start"]) + 1
            marks.append(item)
        elif data.startswith(f"PROOF_EVAL_{nonce}:"):
            totals.append(int(data.split(":", 1)[1]))
        elif message.get("severity") == "error" and len(errors) < 5:
            errors.append(data[:1500])
    if stderr.strip():
        errors.append(stderr[:1500])
    if traces != 1 or not isinstance(trees, list):
        detail = "; ".join(errors)
        raise ValueError(
            "Expected exactly one structured profile trace"
            + (f": {detail}" if detail else "")
        )
    return trees, marks, errors, totals[0] if len(totals) == 1 else None


def profile(
    evaluator: Evaluator,
    name: str,
    code: str,
    *,
    config: ProfileConfig | None = None,
) -> dict:
    """Explicitly profile a declaration without reading or writing references.

    A fresh pinned Lean process measures the native trace, plus any explicitly
    labelled ``profile_tactic \"label\" in tac`` calls. All costs include profiling
    overhead and nested work. They never enter candidate scoring or selection.
    Only successful diagnostics are cached, under a separate namespace with the
    exact proof, environment, profiler implementation and configuration identity.
    """
    config = config or ProfileConfig()
    row = evaluator.dataset.get(name)
    validate_candidate(row, code)
    _, versions = evaluator._versions(
        row, [config.version] if config.version is not None else "primary"
    )
    version = versions[0]
    started = time.monotonic()
    result = {
        "schema": 1,
        "kind": "lean_heartbeat_profile",
        "name": name,
        "version": version,
        "proof_sha256": sha(code),
        "implementation_sha256": fingerprint(
            {
                file: digest(Path(__file__).with_name(file))
                for file in ("profiling.py", "profile_trace.py")
            }
        ),
        "options": asdict(config),
        "diagnostic_only": True,
        "cost_semantics": "Inclusive raw IO.getNumHeartbeats deltas; heartbeats = raw / 1000. Instrumented costs include profiler overhead. Nested entries overlap; do not sum them or use them as arena scores. Remove profile_tactic wrappers before check/final output.",
        "cached": False,
        "trace": [],
        "hotspots": [],
        "marks": [],
        "profile_heartbeats_raw": None,
        "profile_heartbeats": None,
    }
    if getattr(evaluator, "measurement_version", "legacy_v1") == "module_safe_v2":
        from .instrumentation import implementation_hash

        result["instrumentation_sha256"] = implementation_hash()
    path = None
    try:
        project, environment, context = evaluator._context(row, version)
        # The display limit never reaches Lean. Keep it out of the compilation
        # identity so a different-sized view can reuse this cell's full trace.
        compile_options = asdict(config)
        compile_options.pop("limit")
        key = fingerprint({"context": context, **result, "options": compile_options})
        result.update(environment_fingerprint=environment, cache_key=key)
        with evaluator.store.locked("profiles", key):
            cached = evaluator.store.read("profiles", key)
            if cached is not None:
                hotspots, available = trace_hotspots(cached["trace"], config.limit)
                return {
                    **cached,
                    "cached": True,
                    "options": asdict(config),
                    "hotspots": hotspots,
                    "available_hotspots": available,
                    "hotspots_truncated": available > config.limit,
                    "marks_truncated": len(cached["marks"]) > config.limit,
                }
            nonce = uuid.uuid4().hex
            options = (
                {"measurement_version": "module_safe_v2"}
                if getattr(evaluator, "measurement_version", "legacy_v1")
                == "module_safe_v2"
                else {}
            )
            source, offset, mode = _profile_source(
                row, code, project, nonce, config, **options
            )
            path = project / f"_ProofEval_{nonce}.lean"
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(source)
            try:
                proc = _run(
                    [evaluator.backend.lake, "env", "lean", "--json", path.name],
                    project,
                    evaluator.timeout,
                )
            finally:
                path.unlink(missing_ok=True)
            _, after_environment, after_context = evaluator._context(row, version)
            if (environment, context) != (after_environment, after_context):
                raise EvaluationNotReady("Project changed during profile observation")
            trees, marks, errors, total = _parse_output(
                proc.stdout, proc.stderr, nonce, code, offset
            )
            hotspots, available = trace_hotspots(trees, config.limit)
            status = (
                "ok"
                if proc.returncode == 0 and not errors and total is not None
                else "failed"
            )
            result.update(
                status=status,
                trace=trees,
                hotspots=hotspots,
                available_hotspots=available,
                hotspots_truncated=available > config.limit,
                marks=marks,
                mark_count=len(marks),
                marks_truncated=len(marks) > config.limit,
                profile_heartbeats_raw=total,
                profile_heartbeats=total / 1000 if total is not None else None,
                partial=status != "ok",
                diagnostics=errors,
                context_mode=mode,
                returncode=proc.returncode,
                elapsed_seconds=time.monotonic() - started,
            )
            if status == "ok":
                evaluator.store.write("profiles", key, result)
            return result
    except (
        EvaluationNotReady,
        OSError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
    ) as exc:
        result.update(
            status=(
                "timeout"
                if isinstance(exc, subprocess.TimeoutExpired)
                else "unavailable"
            ),
            partial=True,
            diagnostics=[str(exc)[:1500]],
            elapsed_seconds=time.monotonic() - started,
        )
        return result
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
