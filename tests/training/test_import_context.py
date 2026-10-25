"""Dependency checks must use actual task contexts, not declaration snippets."""

import pytest

from proof_eval.training.imports import task_context


def test_original_module_header_is_used_instead_of_declaration(tmp_path):
    original = "import Project.Required\n\ntheorem foo : True := by trivial\n"
    (tmp_path / "Foo.lean").write_text(original)
    row = {"src": "theorem foo : True := by trivial", "file_path": "Foo.lean"}
    assert task_context(row, tmp_path) == original
    assert (
        task_context(
            {"header": "import Mathlib", "src": "example : True := by trivial"},
            tmp_path,
        )
        == "import Mathlib"
    )


def test_original_context_path_cannot_escape(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        task_context({"file_path": "../outside.lean"}, tmp_path)
