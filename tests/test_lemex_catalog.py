"""Run-local catalogs survive unrelated shared configuration updates."""

from pathlib import Path

import pytest

from proof_eval.providers import lemex


@pytest.fixture
def catalogs(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        lemex, "environment", lambda: {"LEMEX_BASE_URL": "https://example.invalid"}
    )
    monkeypatch.setattr(
        lemex, "executable_identity", lambda _: {"path": "/fake/lemex", "sha256": "x"}
    )
    monkeypatch.delenv("PROOF_EVAL_LEMEX_CATALOG", raising=False)
    shared = tmp_path / ".lemex/models.json"
    shared.parent.mkdir()
    shared.write_text('{"models": []}')
    private = tmp_path / "run/models.json"
    private.parent.mkdir()
    private.write_bytes(shared.read_bytes())
    return shared, private


def test_explicit_catalog_survives_shared_changes_but_detects_private_changes(
    catalogs, monkeypatch
):
    shared, private = catalogs
    monkeypatch.setenv("PROOF_EVAL_LEMEX_CATALOG", str(private))
    pinned = lemex.cli_identity()
    assert pinned["catalog_path"] == str(private)
    shared.write_text('{"models": ["new-shared-model"]}')
    assert lemex.cli_identity() == pinned
    private.write_text('{"models": ["changed-private-model"]}')
    assert lemex.cli_identity()["catalog_sha256"] != pinned["catalog_sha256"]


def test_default_catalog_remains_shared(catalogs):
    shared, _ = catalogs
    assert lemex.cli_identity()["catalog_path"] == str(shared)


def test_missing_explicit_catalog_never_falls_back(catalogs, monkeypatch):
    _, private = catalogs
    private.unlink()
    monkeypatch.setenv("PROOF_EVAL_LEMEX_CATALOG", str(private))
    with pytest.raises(FileNotFoundError):
        lemex.cli_identity()
