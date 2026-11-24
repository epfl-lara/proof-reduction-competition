"""Model-free, compiler-guided proposals. Scoring remains in Evaluator.

Analysis is separate from measurement: run normal elaboration to obtain linters
and syntax spans, then recompile every edited declaration with the score wrapper.
All offsets stored here are Python character offsets; Lean's UTF-8 byte offsets
and diagnostic line/column positions are converted at the boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import uuid
from dataclasses import asdict, dataclass

from proof_eval.defaults import DEFAULT_SELECTION_MARGIN_PP
from proof_eval.verification.api import EvaluationNotReady
from proof_eval.verification.backend import MEASUREMENT_WRAPPER, _run, _source

SYNTAX_OBSERVER = r"""
open Lean in
private meta partial def proofOptSyntax (s : Syntax) (path : Array Nat := #[]) : Array Json := Id.run do
  let mut result := #[]
  if s.isOfKind ``Lean.Parser.Term.byTactic || s.getArgs.size > 0 then
    if let some start := s.getPos? then
      if let some stop := s.getTailPos? then
        result := result.push <| Json.mkObj [("kind", toJson s.getKind.toString),
          ("path", toJson path), ("start", toJson start.byteIdx), ("end", toJson stop.byteIdx)]
  for i in [:s.getArgs.size] do
    result := result ++ proofOptSyntax s[i] (path.push i)
  return result
open Lean Elab Command in
elab "#proof_opt_sites " "in " cmd:command : command => do
  logInfo m!"PROOF_OPT_SITES:{(Json.arr (proofOptSyntax cmd.raw)).compress}"
  elabCommand cmd
"""


def position_offset(text, position):
    """Lean JSON columns count Unicode code points, lines start at one."""
    lines = text.splitlines(keepends=True)
    line, column = position["line"] - 1, position["column"]
    if line < 0 or line >= len(lines) or column > len(lines[line].rstrip("\r\n")):
        raise ValueError("Diagnostic position outside source")
    return sum(map(len, lines[:line])) + column


def analyze(evaluator, row, code):
    """Parse and elaborate under the primary version; cache by exact context."""
    version = next(iter(row["version_info"][0]))
    project, _, context_key = evaluator._context(row, version)
    assembly = ""
    if getattr(evaluator, "measurement_version", "legacy_v1") == "module_safe_v2":
        from proof_eval.verification.instrumentation import implementation_hash

        assembly = implementation_hash()
    key = hashlib.sha256(
        (context_key + code + SYNTAX_OBSERVER + assembly).encode()
    ).hexdigest()
    cached = evaluator.store.read("analysis", key)
    if cached is not None:
        return cached
    if getattr(evaluator, "measurement_version", "legacy_v1") == "module_safe_v2":
        from proof_eval.verification.instrumentation import module_observation_source

        source, offset, _ = module_observation_source(
            row, code, project, uuid.uuid4().hex, SYNTAX_OBSERVER, "#proof_opt_sites in"
        )
        preamble = source.encode()[:offset].decode()
    else:
        source, _ = _source(row, code, project, uuid.uuid4().hex)
        prefix = source.split("\n#proof_eval_measure ", 1)[0]
        # Define the observer at the import header, before namespace/scoped commands.
        prefix = prefix.replace(
            MEASUREMENT_WRAPPER, MEASUREMENT_WRAPPER + SYNTAX_OBSERVER, 1
        )
        preamble = prefix + "\n#proof_opt_sites in\n"
        source = preamble + code + "\n"
        offset = len(preamble.encode())
    path = project / f"_ProofEval_{uuid.uuid4().hex}.lean"
    path.write_text(source)
    try:
        proc = _run(
            [evaluator.backend.lake, "env", "lean", "--json", path.name],
            project,
            evaluator.timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise EvaluationNotReady("Analysis timed out") from exc
    finally:
        path.unlink(missing_ok=True)
    messages = []
    nodes = None
    raw = code.encode()
    for line in proc.stdout.splitlines():
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        data = msg.get("data", "")
        if data.startswith("PROOF_OPT_SITES:"):
            nodes = json.loads(data.removeprefix("PROOF_OPT_SITES:"))
            inside = []
            for node in nodes:
                if (
                    getattr(evaluator, "measurement_version", "legacy_v1")
                    == "module_safe_v2"
                    and node["start"] < offset
                    and node["end"] <= offset + len(raw)
                ):
                    # Attached source documentation/modifiers belong to the
                    # declaration, but are outside the editable code snapshot.
                    continue
                for bound in ("start", "end"):
                    byte = node[bound] - offset
                    if not 0 <= byte <= len(raw):
                        raise EvaluationNotReady("Syntax position outside candidate")
                    node[bound] = len(raw[:byte].decode())
                inside.append(node)
            nodes = inside
        else:
            if "pos" in msg and "endPos" in msg:
                try:
                    start = position_offset(source, msg["pos"]) - len(preamble)
                    stop = position_offset(source, msg["endPos"]) - len(preamble)
                    if 0 <= start <= stop <= len(code):
                        msg = {**msg, "start": start, "end": stop}
                except ValueError:
                    pass
            messages.append(msg)
    if proc.returncode or nodes is None:
        errors = [m.get("data") for m in messages if m.get("severity") == "error"]
        raise EvaluationNotReady(f"Analysis failed: {errors[:3]} {proc.stderr[:300]}")
    result = {
        "nodes": nodes,
        "messages": messages,
        "version": version,
        "context_key": context_key,
    }
    evaluator.store.write("analysis", key, result)
    return result


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    replacement: str
    reason: str

    def apply(self, code):
        return code[: self.start] + self.replacement + code[self.end :]

    def record(self):
        return asdict(self)


def nonoverlapping(edits):
    """Prefer outermost deletions when a linter marks nested syntax too."""
    out = []
    for edit in sorted(set(edits), key=lambda e: (e.start, -e.end)):
        if not out or edit.start >= out[-1].end:
            out.append(edit)
    return out


def apply_edits(code, edits):
    for edit in reversed(nonoverlapping(edits)):
        code = edit.apply(code)
    return code


def deletion_edits(code, analysis):
    """Delete only spans nominated by unused/unreachable-tactic linters.

    Lift through unary try/parentheses wrappers and remove the adjacent <;>
    when dropping a combinator operand. Keep unrelated punctuation untouched.
    Lean revalidation, not linter trust, determines whether an edit is accepted.
    """
    nodes = analysis["nodes"]
    by_path = {tuple(n["path"]): n for n in nodes}
    edits = []
    for message in analysis["messages"]:
        if (
            message.get("kind")
            not in {"linter.unusedTactic", "linter.unreachableTactic"}
            or "start" not in message
        ):
            continue
        start, stop = message["start"], message["end"]
        matches = [n for n in nodes if n["start"] == start and n["end"] == stop]
        if not matches:
            continue
        node = min(matches, key=lambda n: len(n["path"]))
        while True:
            parent = by_path.get(tuple(node["path"][:-1]))
            if parent is None:
                break
            if parent["kind"] in {
                "Lean.Parser.Tactic.paren",
                "Lean.Parser.Tactic.tacticTry_",
                "Lean.Parser.Tactic.tacticSeq",
                "Lean.Parser.Tactic.tacticSeq1Indented",
                "null",
            }:
                other = (
                    code[parent["start"] : node["start"]]
                    + code[node["end"] : parent["end"]]
                )
                if re.fullmatch(r"[\s()]*|[\s(]*try[\s()]*", other):
                    node = parent
                    continue
            break
        start, stop = node["start"], node["end"]
        parent = by_path.get(tuple(node["path"][:-1]))
        if parent and "tactic_<;>_" in parent["kind"]:
            if stop == parent["end"]:
                operator = code.rfind("<;>", parent["start"], start)
                if operator >= parent["start"]:
                    start = operator
            elif start == parent["start"]:
                operator = code.find("<;>", stop, parent["end"])
                if operator >= stop:
                    stop = operator + 3
        # Deleting the sole tactic in `by`, a bullet, etc. is harmless as a
        # proposal: it will fail verification, never silently introduce sorry.
        edits.append(Edit(start, stop, "", message["kind"]))
    return nonoverlapping(edits)


def simp_probes(code, analysis):
    """Ask simp?/simp_all?/dsimp? for an explicit lemma set at each existing call."""
    edits = []
    for node in analysis["nodes"]:
        if node["kind"] not in {
            "Lean.Parser.Tactic.simp",
            "Lean.Parser.Tactic.simpAll",
            "Lean.Parser.Tactic.dsimp",
        }:
            continue
        start, stop = node["start"], node["end"]
        original = code[start:stop]
        match = re.match(r"(simp_all|dsimp|simp)(?![!?\w])", original)
        if match:
            replacement = original[: match.end()] + "?" + original[match.end() :]
            edits.append(Edit(start, stop, replacement, "simp_suggestion"))
    return nonoverlapping(edits)


def suggestion_edit(probe_code, probe, analysis):
    """Ignore unrelated diagnostics and require one unambiguous suggestion."""
    suggestions = set()
    for msg in analysis["messages"]:
        if msg.get("start") == probe.start and msg.get("data", "").startswith(
            "Try this:"
        ):
            text = msg["data"].removeprefix("Try this:").strip()
            text = text.removeprefix("[apply]").strip()
            if text.startswith(
                (
                    "simp only",
                    "simp_all only",
                    "dsimp only",
                    "simp_all?",
                    "simp?",
                    "dsimp?",
                )
            ):
                # Search tactics themselves are not final optimized candidates.
                if not re.match(r"(?:simp_all|dsimp|simp)\?", text):
                    suggestions.add(text)
    if len(suggestions) != 1:
        return None
    # Apply to the pre-probe source range, whose endpoint lacks the added '?'.
    return Edit(probe.start, probe.end, suggestions.pop(), "explicit_simp_lemmas")


def score_improves(before, after, min_gain=DEFAULT_SELECTION_MARGIN_PP):
    """Require a strict combined-score gain above the declared selection margin."""
    left, right = before["scores"]["combined_pct"], after["scores"]["combined_pct"]
    return (
        left is not None
        and right is not None
        and after["status"] == "passed"
        and right > left + min_gain
    )


def primary_upper_bound(result):
    """Best possible combined score assuming every remaining version passes."""
    scores = result["scores"]
    if (
        scores["length_reduction_pct"] is None
        or scores["heartbeat_reduction_pct"] is None
    ):
        return None
    return (
        scores["length_reduction_pct"] + scores["heartbeat_reduction_pct"] + 100.0
    ) / 3.0


def proposals(evaluator, row, code, method):
    analysis = analyze(evaluator, row, code)
    if method == "lint":
        return deletion_edits(code, analysis), 1
    probes = simp_probes(code, analysis)
    if not probes:
        return [], 1
    instrumented = apply_edits(code, probes)
    suggestions = analyze(evaluator, row, instrumented)
    edits = []
    shift = 0
    for probe in probes:
        shifted = type(probe)(
            probe.start + shift, probe.end + shift, probe.replacement, probe.reason
        )
        edit = suggestion_edit(instrumented, shifted, suggestions)
        if edit is not None:
            edits.append(
                type(edit)(probe.start, probe.end, edit.replacement, edit.reason)
            )
        shift += len(probe.replacement) - (probe.end - probe.start)
    return edits, 2
