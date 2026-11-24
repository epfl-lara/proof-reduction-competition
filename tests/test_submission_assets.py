"""Offline archive restoration, source identities and shared-workspace copying."""

import io
import subprocess
import tarfile

import pytest

from proof_eval.benchmark import submission_assets as assets
from proof_eval.benchmark.submission_workspace import materialize
from proof_eval.evidence.io import digest, write_json
from proof_eval.evidence.submission import verify_bundle


def test_read_only_bundle_materializes_only_sealed_inputs(tmp_path):
    source, work = tmp_path / "source", tmp_path / "shared work"
    source.mkdir()
    write_json(source / "recipe.json", {"workers": 10})
    (source / "private-unsealed.txt").write_text("excluded")
    write_json(
        source / "bundle.json",
        {
            "schema_version": 1,
            "files_sha256": {"recipe.json": digest(source / "recipe.json")},
            "recipe_sha256": digest(source / "recipe.json"),
        },
    )
    target = materialize(source, work)
    assert verify_bundle(target) == {"workers": 10}
    assert not (target / "private-unsealed.txt").exists()
    assert materialize(source, work) == target
    (target / "recipe.json").write_text("changed")
    with pytest.raises(ValueError, match="Prepared source changed"):
        materialize(source, work)


@pytest.mark.parametrize("name,kind", [("../escape", "file"), ("link", "link")])
def test_archive_rejects_escaping_or_link_members(tmp_path, name, kind):
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        item = tarfile.TarInfo(name)
        if kind == "link":
            item.type = tarfile.SYMTYPE
            item.linkname = "/outside"
            stream.addfile(item)
        else:
            item.size = 1
            stream.addfile(item, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe"):
        assets._extract(archive, tmp_path / "out")
    assert not (tmp_path / "escape").exists()


def test_plain_snapshot_and_public_identity_restore_preserve_source_and_symlinks(
    tmp_path,
    monkeypatch,
):
    original = tmp_path / "original"
    original.mkdir()
    subprocess.run(["git", "init", "-q", str(original)], check=True)
    (original / "lean-toolchain").write_text("leanprover/lean4:v4.31.0\n")
    (original / ".gitignore").write_text(".lake/\n")
    (original / "source with spaces.lean").write_text("-- fixture source\n")
    (original / "source-link.lean").symlink_to("source with spaces.lean")
    subprocess.run(["git", "-C", str(original), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(original),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    first = subprocess.check_output(
        ["git", "-C", str(original), "rev-parse", "HEAD"], text=True
    ).strip()
    subprocess.run(
        [
            "git",
            "-C",
            str(original),
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{first},vendor/submodule",
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(original),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "pinned submodule",
        ],
        check=True,
    )
    revision = subprocess.check_output(
        ["git", "-C", str(original), "rev-parse", "HEAD"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(original), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    bundle, work = tmp_path / "bundle", tmp_path / "work"
    (bundle / "project-sources").mkdir(parents=True)
    archive = bundle / "project-sources/project.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        for name in ("lean-toolchain", "source with spaces.lean", "source-link.lean"):
            path = original / name
            payload = (
                "source with spaces.lean".encode()
                if path.is_symlink()
                else path.read_bytes()
            )
            member = tarfile.TarInfo(name)
            member.mode = 0o644
            member.size = len(payload)
            stream.addfile(member, io.BytesIO(payload))
    with tarfile.open(archive) as stream:
        assert all(
            member.isfile() and ".git" not in member.name.split("/")
            for member in stream
        )
    write_json(
        bundle / "project-sources/manifest.json",
        {
            "archive_format": "plain_source_snapshot",
            "objects": {
                "fixture": {
                    "file": "project-sources/project.tar.gz",
                    "sha256": digest(archive),
                    "revision": revision,
                    "tree": tree,
                    "upstream": str(original),
                }
            },
            "environments": [
                {
                    "path": "projects/original",
                    "root": {"object": "fixture", "revision": revision},
                    "dependencies": [
                        {
                            "object": "fixture",
                            "revision": revision,
                            "path": ".lake/packages/dependency",
                        }
                    ],
                }
            ],
        },
    )
    monkeypatch.setenv("PROOF_SUBMISSION_GIT_CONFIG", str(work / "git-safe.config"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(work / "git-safe.config"))
    assets.projects(bundle, work)
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")
    # Exercise upload-pack's bare .git ownership check during an actual clone,
    # in addition to the usual worktree HEAD/status checks.
    (bundle / "projects/original").rename(work / "prior_fixture_checkout")
    assets.projects(bundle, work)
    for path in [
        bundle / "projects/original",
        bundle / "projects/original/.lake/packages/dependency",
    ]:
        assert (path / "lean-toolchain").read_text() == "leanprover/lean4:v4.31.0\n"
        assert (path / ".gitignore").read_bytes() == (
            original / ".gitignore"
        ).read_bytes()
        assert (path / "source-link.lean").is_symlink()
        assert (path / "source-link.lean").read_bytes() == (
            original / "source with spaces.lean"
        ).read_bytes()
        assert (
            subprocess.check_output(
                ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
            ).strip()
            == revision
        )
        # Lake uses the pinned public origin to locate release caches.
        assert subprocess.check_output(
            ["git", "-C", str(path), "remote", "get-url", "origin"], text=True
        ).strip() == str(original)
    assets.projects(bundle, work)
    unrelated = tmp_path / "unrelated repository"
    subprocess.run(["git", "init", "-q", str(unrelated)], check=True)
    rejected = subprocess.run(
        ["git", "-C", str(unrelated), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 128
    assert "dubious ownership" in rejected.stderr


def test_plain_snapshot_rejects_repository_metadata_before_git_or_network(
    tmp_path, monkeypatch
):
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        payload = b"must not be shipped"
        member = tarfile.TarInfo(".git/config")
        member.size = len(payload)
        stream.addfile(member, io.BytesIO(payload))
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: pytest.fail("No Git/network call")
    )
    with pytest.raises(ValueError, match="must not contain Git metadata"):
        assets._source_checkout(archive, tmp_path / "target", {})


def test_cpu_asset_setup_installs_each_missing_pinned_toolchain_once(
    tmp_path, monkeypatch
):
    bundle, work = tmp_path / "bundle", tmp_path / "work"
    work.mkdir()
    rows = []
    for name, version in (("a", "v4.30.0"), ("b", "v4.31.0"), ("c", "v4.31.0")):
        path = bundle / name
        path.mkdir(parents=True)
        (path / "lean-toolchain").write_text("leanprover/lean4:" + version + "\n")
        rows.append({"path": name})
    write_json(bundle / "project-sources/manifest.json", {"environments": rows})
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda args, **kw: "leanprover/lean4:v4.30.0 (default)\n",
    )
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: calls.append(args))
    result = assets.toolchains(bundle, work)
    assert calls == [["elan", "toolchain", "install", "leanprover/lean4:v4.31.0"]]
    assert result["installed_during_setup"] == ["leanprover/lean4:v4.31.0"]
    assert result["model_calls"] == result["proof_measurements"] == 0
    assert (work / "toolchains-ready.json").is_file()
