"""Turn Lean parser byte ranges into immutable Arena-style source tasks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from proof_eval.evidence.io import fingerprint, sha
from proof_eval.verification.metrics import (
    strip_comments,
    token_count,
    validate_candidate,
)


@dataclass(frozen=True)
class SourceSnapshot:
    """A source pin and a separately specified, already-built parser environment."""

    source: str
    url: str
    revision: str
    version: str
    project: Path
    roots: tuple[str, ...]
    grammar_project: Path
    grammar_imports: tuple[str, ...]
    file_limit: int | None = None


def signature_key(statement: str) -> str:
    """Conservative textual duplicate key, ignoring theorem names and comments."""
    statement = strip_comments(statement)
    statement = re.sub(
        r"\b(?:lemma|theorem)\s+(?:«[^»]+»|[^\s(:{\[]+)",
        "theorem __TARGET__",
        statement,
        count=1,
    )
    return sha(" ".join(statement.split()))


def split_group(source: str, relative: str) -> str:
    """Keep all files from a pooled project together; other sources use files."""
    parts = Path(relative).parts
    if source == "leanpool" and len(parts) >= 2:
        return f"{source}/{parts[0]}/{Path(parts[1]).stem}"
    return f"{source}/{relative}"


def split_for(group: str, seed: int) -> str:
    """Assign groups deterministically to approximately 90/5/5 splits."""
    bucket = int(sha(f"{seed}:{group}")[:8], 16) % 100
    return "train" if bucket < 90 else "dev" if bucket < 95 else "test"


def task_from_range(
    snapshot: SourceSnapshot,
    path: Path,
    raw: bytes,
    record: dict[str, Any],
    *,
    seed: int,
) -> dict[str, Any]:
    """Preserve original bytes; never find a proof assignment using a regex."""
    if record.get("private") or record.get("has_where"):
        raise ValueError("private_or_where")
    start, assignment, body_start, end = (
        record[field]
        for field in ("start_byte", "assignment_byte", "body_byte", "end_byte")
    )
    if not all(type(x) is int for x in (start, assignment, body_start, end)):
        raise ValueError("invalid_range")
    if not 0 <= start < assignment < body_start < end <= len(raw):
        raise ValueError("invalid_range")
    if raw[assignment : assignment + 2] != b":=":
        raise ValueError("invalid_assignment")
    declaration = raw[start:end].decode("utf-8")
    statement = raw[start:assignment].decode("utf-8").rstrip()
    _, body = validate_candidate({"statement": statement}, declaration)
    relative = str(path.relative_to(snapshot.project))
    group = split_group(snapshot.source, relative)
    return {
        "name": record["name"],
        "source": snapshot.source,
        "statement": statement,
        "src": declaration,
        "proof_length": token_count(body),
        "num_lines": declaration.count("\n") + 1,
        "header": "",
        "file_path": relative,
        "url": snapshot.url,
        "start_line": raw[:start].count(b"\n") + 1,
        "end_line": raw[:end].count(b"\n") + 1,
        "version_info": [{snapshot.version: snapshot.revision}],
        "training_metadata": {
            "id": fingerprint(
                [
                    snapshot.source,
                    snapshot.revision,
                    relative,
                    record["name"],
                    sha(declaration),
                ]
            ),
            "kind": record["kind"],
            "source_sha256": sha(raw.decode("utf-8")),
            "declaration_sha256": sha(declaration),
            "start_byte": start,
            "end_byte": end,
            "proof_nonempty_lines": sum(
                bool(line.strip()) for line in strip_comments(body).splitlines()
            ),
            "signature_key": signature_key(statement),
            "content_key": fingerprint(
                [signature_key(statement), " ".join(strip_comments(body).split())]
            ),
            "split_group": group,
            "split": split_for(group, seed),
            "validation_status": "parsed_not_compiled",
            "heartbeat_baseline_status": "unprepared",
        },
    }


def standalone_task_from_range(
    snapshot: SourceSnapshot,
    path: Path,
    raw: bytes,
    record: dict[str, Any],
    *,
    problem_name: str,
    version: str,
    mathlib_revision: str,
    seed: int,
) -> dict[str, Any]:
    """Export a proof with its preceding context into an explicit Mathlib pin.

    This records the published source pin separately from the compiler pin. It
    does not establish compatibility with the selected compiler. Related proofs
    and supporting lemmas share a problem group across different publishers.
    """
    row = task_from_range(snapshot, path, raw, record, seed=seed)
    metadata = row["training_metadata"]
    metadata.update(
        {
            "origin_url": snapshot.url,
            "origin_revision": snapshot.revision,
            "origin_version": snapshot.version,
            "origin_file_path": row["file_path"],
            "problem_name": problem_name,
            "split_group": f"putnambench/{problem_name}",
        }
    )
    metadata["split"] = split_for(metadata["split_group"], seed)
    row["header"] = raw[: record["start_byte"]].decode("utf-8")
    row["file_path"] = ""
    row["version_info"] = [{version: mathlib_revision}]
    metadata["id"] = fingerprint(
        [metadata["id"], sha(row["header"]), version, mathlib_revision]
    )
    return row


def balanced_select(
    candidates: list[dict[str, Any]], *, limit: int, seed: int, max_per_file: int
) -> list[dict[str, Any]]:
    """Round-robin sources and length tiers, with a per-file diversity cap."""
    from collections import defaultdict, deque

    tiers: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        length = row["proof_length"]
        tier = 0 if length < 500 else 1 if length < 1500 else 2
        tiers[(row["source"], tier)].append(row)
    queues = {
        key: deque(
            sorted(
                rows, key=lambda row: sha(f"{seed}:{row['training_metadata']['id']}")
            )
        )
        for key, rows in sorted(tiers.items())
    }
    selected: list[dict[str, Any]] = []
    counts: dict[tuple[str, str], int] = defaultdict(int)
    names: set[str] = set()
    contents: set[str] = set()
    while queues and len(selected) < limit:
        for key in list(queues):
            queue = queues[key]
            while queue:
                row = queue.popleft()
                file_key = (row["source"], row["file_path"])
                content = row["training_metadata"]["content_key"]
                if (
                    counts[file_key] >= max_per_file
                    or row["name"] in names
                    or content in contents
                ):
                    continue
                selected.append(row)
                counts[file_key] += 1
                names.add(row["name"])
                contents.add(content)
                break
            if not queue:
                del queues[key]
            if len(selected) == limit:
                break
    return selected
