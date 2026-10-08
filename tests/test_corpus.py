"""Contracts for source fidelity, contamination guards and grouped task splits."""

from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from proof_eval.benchmark.corpus import _parse
from proof_eval.benchmark.harvest import (
    SourceSnapshot,
    balanced_select,
    signature_key,
    split_for,
    split_group,
    standalone_task_from_range,
    task_from_range,
)
from proof_eval.verification.metrics import token_count, validate_candidate

ROOT = Path(__file__).resolve().parents[1]


def snapshot(project: Path) -> SourceSnapshot:
    return SourceSnapshot(
        "example",
        "https://example.invalid/source",
        "abc",
        "v4.32.0",
        project,
        ("Example",),
        project,
        ("Mathlib",),
    )


def test_unicode_source_ranges_preserve_binder_defaults_and_exact_proof(tmp_path):
    text = "namespace Example\n@[simp] theorem α (n : Nat := 1) : n = n := by\n  rfl\nend Example\n"
    raw = text.encode()
    start = raw.index(b"@[simp]")
    assignment = raw.index(b":= by")
    end = raw.index(b"\nend")
    record = {
        "name": "Example.α",
        "kind": "theorem",
        "start_byte": start,
        "assignment_byte": assignment,
        "body_byte": assignment + 3,
        "end_byte": end,
    }
    row = task_from_range(
        snapshot(tmp_path), tmp_path / "Example.lean", raw, record, seed=1
    )
    assert row["src"].encode() == raw[start:end]
    assert "Nat := 1" in row["statement"]
    assert row["proof_length"] == token_count("by\n  rfl")
    assert row["start_line"] == 2 and row["end_line"] == 3
    assert validate_candidate(row, row["src"])[1] == "by\n  rfl"
    assert row["training_metadata"]["validation_status"] == "parsed_not_compiled"


def test_sorry_and_private_declarations_cannot_become_reference_proofs(tmp_path):
    raw = b"theorem bad : True := by sorry"
    record = {
        "name": "bad",
        "kind": "theorem",
        "start_byte": 0,
        "assignment_byte": raw.index(b":="),
        "body_byte": raw.index(b"by"),
        "end_byte": len(raw),
    }
    with pytest.raises(ValueError, match="sorry"):
        task_from_range(
            snapshot(tmp_path), tmp_path / "Example.lean", raw, record, seed=1
        )
    with pytest.raises(ValueError, match="private_or_where"):
        task_from_range(
            snapshot(tmp_path),
            tmp_path / "Example.lean",
            raw,
            {**record, "private": True},
            seed=1,
        )


def test_standalone_context_keeps_dependencies_without_exposing_target_or_suffix(
    tmp_path,
):
    raw = (
        "import Mathlib\nnamespace P\n"
        "lemma earlier : True := by trivial\n"
        "theorem α : True := by exact earlier\n"
        "theorem later : True := by exact α\nend P\n"
    ).encode()
    start = raw.index("theorem α".encode())
    assignment = raw.index(b":=", start)
    record = {
        "name": "P.α",
        "kind": "theorem",
        "start_byte": start,
        "assignment_byte": assignment,
        "body_byte": assignment + 3,
        "end_byte": raw.index(b"\ntheorem later"),
    }
    row = standalone_task_from_range(
        snapshot(tmp_path),
        tmp_path / "Proof.lean",
        raw,
        record,
        problem_name="putnam_2008_a1",
        version="v4.27.0",
        mathlib_revision="mathlib-pin",
        seed=1,
    )
    assert row["header"].encode() + row["src"].encode() == raw[: record["end_byte"]]
    assert "lemma earlier" in row["header"]
    assert "theorem α" not in row["header"] and "later" not in row["header"]
    assert row["file_path"] == ""
    assert row["version_info"] == [{"v4.27.0": "mathlib-pin"}]
    metadata = row["training_metadata"]
    assert metadata["origin_revision"] == "abc"
    assert metadata["origin_version"] == "v4.32.0"
    assert metadata["split_group"] == "putnambench/putnam_2008_a1"
    assert metadata["validation_status"] == "parsed_not_compiled"


def test_duplicate_signatures_and_group_splits_are_name_independent():
    assert signature_key("lemma a (x : Nat) : x = x") == signature_key(
        "theorem b (x : Nat) /- note -/ : x = x"
    )
    a = split_group("leanpool", "LeanPool/Project/One.lean")
    b = split_group("leanpool", "LeanPool/Project/Two.lean")
    assert a == b
    assert split_group("leanpool", "LeanPool/Project.lean") == a
    assert split_for(a, 42) == split_for(b, 42)
    assert split_group("physlib", "Physlib/A.lean") != split_group(
        "physlib", "Physlib/B.lean"
    )


def test_selection_balances_sources_caps_files_and_removes_cross_source_duplicates():
    def row(source, name, content, file):
        return {
            "source": source,
            "name": name,
            "proof_length": 300,
            "file_path": file,
            "training_metadata": {"id": source + name, "content_key": content},
        }

    rows = [row("a", f"a{i}", f"content{i}", "One.lean") for i in range(10)]
    rows += [
        row("b", "b0", "content0", "Two.lean"),
        row("b", "b1", "distinct", "Two.lean"),
        row("b", "a1", "another", "Three.lean"),
    ]
    selected = balanced_select(rows, limit=20, seed=42, max_per_file=2)
    assert len({r["name"] for r in selected}) == len(selected)
    assert len({r["training_metadata"]["content_key"] for r in selected}) == len(
        selected
    )
    assert sum(r["file_path"] == "One.lean" for r in selected) == 2
    assert {r["source"] for r in selected} == {"a", "b"}
    assert selected == balanced_select(
        list(reversed(rows)), limit=20, seed=42, max_per_file=2
    )


def test_real_parser_keeps_ranges_and_resolves_output_before_changing_cwd(
    tmp_path, monkeypatch
):
    project = ROOT / ".proof-eval-projects/physlib-v4.32.0"
    mathlib = project / ".lake/packages/mathlib/.lake/build/lib/lean/Mathlib.olean"
    if not shutil.which("lake") or not mathlib.exists():
        pytest.skip("Pinned local parser environment is unavailable")
    source = tmp_path / "Example.lean"
    source.write_text(
        "import Mathlib\nnamespace A\nsection\n"
        "@[simp] theorem α (x : Nat := 1) : x = x := by rfl\n"
        "end\nnamespace B\ntheorem β : True := by trivial\nend B\nend A\n"
    )
    monkeypatch.chdir(tmp_path)
    parser_snapshot = replace(
        snapshot(tmp_path), grammar_project=project, grammar_imports=("Mathlib",)
    )
    parsed = _parse(parser_snapshot, [source], Path("parser-output"), 60)[0]
    assert parsed["errors"] == 0
    assert [r["name"] for r in parsed["records"]] == ["A.α", "A.B.β"]
    for record in parsed["records"]:
        row = task_from_range(
            snapshot(tmp_path), source, source.read_bytes(), record, seed=1
        )
        validate_candidate(row, row["src"])
