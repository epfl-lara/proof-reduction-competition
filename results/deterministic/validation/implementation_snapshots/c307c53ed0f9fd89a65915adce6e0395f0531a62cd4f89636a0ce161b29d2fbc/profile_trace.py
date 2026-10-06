"""Bounded views of Lean's structured, inclusive heartbeat profile."""

from __future__ import annotations

from typing import Any


def trace_hotspots(trees: list[dict], limit: int) -> tuple[list[dict], int]:
    """Rank tactic/phase nodes without summing ancestors or merging siblings.

    Sequence containers and consecutive wrappers with identical printed tactics
    are omitted from the view. Their original nodes remain in the saved tree.
    Threshold-pruned trees cannot establish exclusive costs.
    """
    selected: list[dict[str, Any]] = []
    stack = [(node, None, 0) for node in reversed(trees)]
    next_id = 0
    while stack:
        node, parent, depth = stack.pop()
        if not isinstance(node, dict):
            raise ValueError("Invalid profile trace node")
        cls, tag, header, raw, children = (
            node.get(key) for key in ("class", "tag", "header", "raw", "children")
        )
        if (
            not all(isinstance(value, str) for value in (cls, tag, header))
            or type(raw) is not int
            or raw < 0
            or not isinstance(children, list)
        ):
            raise ValueError("Invalid profile trace fields")
        node_id, next_id = next_id, next_id + 1
        tactic = cls == "Elab.step" and not header.startswith("expected type:")
        container = tag in {
            "Lean.Parser.Tactic.tacticSeq",
            "Lean.Parser.Tactic.tacticSeq1Indented",
            "Lean.Parser.Tactic.tacticSeqBracketed",
            "Lean.Parser.Tactic.paren",
            "Lean.Parser.Tactic.withAnnotateState",
        }
        phase = cls in {"Kernel", "Elab.definition.header", "Elab.definition.value"}
        if (tactic and not container) or phase:
            text = " ".join(header.split())
            same_wrapper = (
                parent is not None
                and not node.get("header_truncated", False)
                and not parent["snippet_truncated"]
                and parent["class"] == cls
                and " ".join(parent["snippet"].split()) == text
            )
            if not same_wrapper:
                item = {
                    "node_id": node_id,
                    "parent_id": parent["node_id"] if parent else None,
                    "depth": depth,
                    "kind": "tactic" if tactic else "phase",
                    "class": cls,
                    "syntax_kind": tag,
                    "snippet": header,
                    "snippet_truncated": node.get("header_truncated", False),
                    "heartbeats_raw": raw,
                    "heartbeats": raw / 1000,
                    "inclusive": True,
                }
                selected.append(item)
                parent = item
        stack.extend((child, parent, depth + 1) for child in reversed(children))
    selected.sort(key=lambda item: (-item["heartbeats_raw"], item["node_id"]))
    return selected[:limit], len(selected)


def profile_view(result: dict) -> dict:
    """Keep the full trace in host evidence and return bounded model feedback."""
    view = {key: value for key, value in result.items() if key != "trace"}
    if "marks" in view:
        view["marks"] = view["marks"][: result.get("options", {}).get("limit", 20)]
    return view
