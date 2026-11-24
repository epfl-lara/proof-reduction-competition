"""Bounded descriptive line diffs and exact byte-span utilities."""

from __future__ import annotations

from difflib import SequenceMatcher

from .model import fragment_id, integer


def line_ranges(code: str) -> list[tuple[str, int, int]]:
    result, offset = [], 0
    for line in code.splitlines(keepends=True):
        end = offset + len(line.encode("utf-8"))
        result.append((line, offset, end))
        offset = end
    return result


def slice_bytes(code: str, start: int, end: int) -> str:
    data = code.encode("utf-8")
    integer(start, "byte_start", 0, len(data))
    integer(end, "byte_end", start, len(data))
    if any(
        position < len(data) and data[position] & 0xC0 == 0x80
        for position in (start, end)
    ):
        raise ValueError("Byte ranges must lie on UTF-8 character boundaries")
    try:
        return data[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Byte ranges must lie on UTF-8 character boundaries") from exc


def selected_range(code: str, request: dict) -> tuple[int, int]:
    byte_keys = {"byte_start", "byte_end"} & request.keys()
    line_keys = {"line_start", "line_end"} & request.keys()
    if byte_keys and line_keys:
        raise ValueError("Choose byte ranges or line ranges, not both")
    if line_keys:
        lines = line_ranges(code)
        start = integer(request.get("line_start", 1), "line_start", 1, len(lines))
        end = integer(request.get("line_end", start), "line_end", start, len(lines))
        return lines[start - 1][1], lines[end - 1][2]
    size = len(code.encode("utf-8"))
    start = integer(request.get("byte_start", 0), "byte_start", 0, size)
    end = integer(request.get("byte_end", size), "byte_end", start, size)
    slice_bytes(code, start, end)
    return start, end


def describe_span(code: str, start: int, end: int) -> dict:
    data = code.encode("utf-8")
    return {
        "byte_start": start,
        "byte_end": end,
        "line_start": data[:start].count(b"\n") + 1,
        "line_end": data[: max(start, end - 1)].count(b"\n") + 1,
        "boundary": start == end,
    }


def hunks(base: str, result: str) -> list[dict]:
    if base == result:
        return []
    old, new = line_ranges(base), line_ranges(result)
    coarse = len(old) * len(new) > 4_000_000 or len(old) + len(new) > 20000
    if coarse:
        opcodes = [("replace", 0, len(old), 0, len(new))]
    else:
        opcodes = SequenceMatcher(
            None, [x[0] for x in old], [x[0] for x in new], autojunk=True
        ).get_opcodes()
    old_size, new_size = len(base.encode("utf-8")), len(result.encode("utf-8"))
    changes = []
    for tag, a, b, c, d in opcodes:
        if tag == "equal":
            continue
        old_start = old[a][1] if a < len(old) else old_size
        old_end = old[b - 1][2] if b > a else old_start
        new_start = new[c][1] if c < len(new) else new_size
        new_end = new[d - 1][2] if d > c else new_start
        before = slice_bytes(base, old_start, old_end)
        after = slice_bytes(result, new_start, new_end)
        changes.append(
            {
                "hunk": len(changes),
                "kind": tag,
                "base_span": describe_span(base, old_start, old_end),
                "result_span": describe_span(result, new_start, new_end),
                "base_text": before,
                "result_text": after,
                "base_fragment": fragment_id(before) if before else None,
                "result_fragment": fragment_id(after) if after else None,
                "alignment": (
                    "coarse_size_bound" if coarse else "descriptive_line_diff"
                ),
                "lineage": "not_inferred",
            }
        )
    return changes


def touches(code: str, needle: bytes, span: dict) -> bool:
    """Find a full exact occurrence intersecting a changed line/context range."""
    start, end = span["byte_start"], span["byte_end"]
    data = code.encode("utf-8")
    if start == end:
        # Insert/delete anchors remain positional; no empty fragment is made.
        # A query ending or beginning at this boundary is adjacent context.
        position = data.find(
            needle, max(0, start - len(needle)), min(len(data), start + len(needle))
        )
        return position >= 0 and position <= start <= position + len(needle)
    position = data.find(
        needle, max(0, start - len(needle) + 1), min(len(data), end + len(needle) - 1)
    )
    return position >= 0 and position < end and position + len(needle) > start
