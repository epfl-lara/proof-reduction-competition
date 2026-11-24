"""Restore pinned source environments and native assets before measured setup."""

from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

from proof_eval.evidence.io import digest, read, write_json


def _extract(archive: Path, target: Path) -> None:
    """Extract regular files/directories only, never links or escaping members."""
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    with tarfile.open(archive, "r:*") as stream:
        for member in stream:
            path = (target / member.name).resolve()
            if not path.is_relative_to(root) or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe submission archive member: " + member.name)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            source = stream.extractfile(member)
            if source is None:
                raise ValueError("Unreadable archive member")
            with source, path.open("wb") as output:
                shutil.copyfileobj(source, output)
            path.chmod(0o700 if member.mode & 0o100 else 0o600)


def native(bundle: Path) -> None:
    """Unpack the exact validated Linux native pair; no code is rebuilt."""
    manifest = read(bundle / "native/manifest.json")
    for name, record in manifest["files"].items():
        if name not in {"lemex", "lemex-code-mode-host", "signal-scope"}:
            raise ValueError("Unknown native executable")
        target = bundle / "bin" / name
        if target.exists():
            if digest(target) != record["sha256"]:
                raise ValueError("Existing native executable differs: " + name)
            target.chmod(0o700)
            continue
        with tempfile.TemporaryDirectory(prefix=".native-", dir=bundle) as tmp:
            archive = Path(tmp) / "payload.tar.xz"
            with archive.open("wb") as output:
                for part in record["parts"]:
                    source = bundle / part["file"]
                    if digest(source) != part["sha256"]:
                        raise ValueError("Native archive changed")
                    with source.open("rb") as stream:
                        shutil.copyfileobj(stream, output)
            if digest(archive) != record["archive_sha256"]:
                raise ValueError("Native archive is incomplete")
            unpacked = Path(tmp) / "unpacked"
            _extract(archive, unpacked)
            if (
                set(p.name for p in unpacked.iterdir()) != {name}
                or digest(unpacked / name) != record["sha256"]
            ):
                raise ValueError("Native executable checksum changed")
            target.parent.mkdir(exist_ok=True)
            os.replace(unpacked / name, target)


def _source_file(name: str) -> bool:
    """Source snapshots exclude repository, agent, credential and editor metadata."""
    return all(
        not part.startswith((".git", ".env"))
        and part
        not in {".claude", ".codex", ".aider", ".vscode", ".ssh", ".aws", ".DS_Store"}
        for part in Path(name).parts
    )


def _source_checkout(archive: Path, target: Path, record: dict) -> None:
    """Restore plain sources; obtain genuine public revision metadata at setup."""
    with tarfile.open(archive, "r:*") as stream:
        files = [member for member in stream if member.isfile()]
    paths = [member.name for member in files]
    if not paths or any(not _source_file(name) or "\n" in name for name in paths):
        raise ValueError("Source snapshots must not contain Git metadata")
    _extract(archive, target)

    def git(*arguments: str, input: bytes | None = None) -> bytes:
        try:
            return subprocess.run(
                [
                    "git",
                    "-c",
                    "safe.directory=" + str(target.resolve()),
                    "-C",
                    str(target),
                    *arguments,
                ],
                input=input,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=300,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            ).stdout
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                "Pinned source Git step failed: "
                + error.stderr.decode(errors="replace").strip()
            ) from error

    git("init", "--quiet")
    # Restore source blobs without changing line endings or applying Git filters.
    blobs = (
        git(
            "hash-object",
            "-w",
            "--no-filters",
            "--stdin-paths",
            input=("\n".join(paths) + "\n").encode(),
        )
        .decode()
        .splitlines()
    )
    if len(blobs) != len(paths):
        raise ValueError("Source snapshot blob inventory changed")
    git("remote", "add", "origin", record["upstream"])
    git("config", "remote.origin.promisor", "true")
    git("config", "remote.origin.partialclonefilter", "blob:none")
    git(
        "-c",
        "credential.helper=",
        "fetch",
        "--quiet",
        "--no-tags",
        "--depth=1",
        "--filter=blob:none",
        "origin",
        record["revision"],
    )
    if git("rev-parse", "FETCH_HEAD").decode().strip() != record["revision"]:
        raise ValueError("Upstream returned a different source revision")
    if git("rev-parse", "FETCH_HEAD^{tree}").decode().strip() != record["tree"]:
        raise ValueError("Upstream source tree changed")
    expected = {}
    for entry in git("ls-tree", "-r", "-z", "FETCH_HEAD").split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, sha = metadata.decode().split()
        name = name.decode()
        if kind == "blob" and _source_file(name):
            expected[name] = sha
    if dict(zip(paths, blobs)) != expected:
        raise ValueError("Plain source snapshot differs from its pinned tree")
    # The archive contains no Git objects/configuration. Obtain omitted public
    # metadata during CPU setup, keeping real source identity and normal Lake
    # behavior. No private repository or experiment history is used.
    git("-c", "credential.helper=", "reset", "--hard", record["revision"])
    # Lake's cache tooling uses the genuine public origin to locate releases.
    # The pinned URL contains no private checkout path or credentials.


def _source_metadata(target: Path, record: dict) -> None:
    """Restore the pinned public origin and release labels used by Lake."""
    def git(*arguments: str) -> str:
        return subprocess.run(
            [
                "git",
                "-c",
                "safe.directory=" + str(target.resolve()),
                "-C",
                str(target),
                *arguments,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()

    if "origin" in git("remote").splitlines():
        git("remote", "set-url", "origin", record["upstream"])
    else:
        git("remote", "add", "origin", record["upstream"])
    for tag, revision in record.get("release_tags", {}).items():
        if revision != record["revision"]:
            raise ValueError("Release label must bind the pinned source revision")
        reference = "refs/tags/" + tag
        git("check-ref-format", reference)
        current = git("for-each-ref", "--format=%(objectname)", reference)
        if current and current != revision:
            raise ValueError("Prepared release label changed: " + str(target))
        if not current:
            git("update-ref", reference, revision, "0" * 40)


def _git_trust(manifest: dict, bundle: Path, work: Path) -> None:
    """Limit shared-filesystem ownership exceptions to this work's sealed repos."""
    configured = os.environ.get("PROOF_SUBMISSION_GIT_CONFIG")
    if configured is None:
        return
    config = Path(configured).resolve()
    if config != (work / "git-safe.config").resolve():
        raise ValueError("Git trust configuration must belong to this work directory")
    repos = {(work / "source-cache" / key).resolve() for key in manifest["objects"]}
    for environment in manifest["environments"]:
        project = (bundle / environment["path"]).resolve()
        if not project.is_relative_to(bundle.resolve()):
            raise ValueError("Source project escapes its bundle")
        if "root" in environment:
            repos.add(project)
        for dependency in environment["dependencies"]:
            path = (project / dependency["path"]).resolve()
            if not path.is_relative_to(project):
                raise ValueError("Source dependency escapes its project")
            repos.add(path)
    # Local clone serves the repository through its .git directory, rather
    # than its worktree root. Git checks that exact path in the upload-pack child.
    repos |= {repo / ".git" for repo in repos}
    with tempfile.TemporaryDirectory(prefix=".git-config-", dir=work) as temporary:
        generated = Path(temporary) / "config"
        for repo in sorted(repos):
            subprocess.run(
                [
                    "git",
                    "config",
                    "--file",
                    str(generated),
                    "--add",
                    "safe.directory",
                    str(repo),
                ],
                check=True,
                timeout=30,
            )
        if not generated.exists():
            generated.write_text("")
        os.replace(generated, config)


def projects(bundle: Path, work: Path) -> None:
    """Restore plain source snapshots and verify their public pinned identities."""
    manifest = read(bundle / "project-sources/manifest.json")
    if manifest.get("archive_format") != "plain_source_snapshot":
        raise ValueError("Expected Git-free plain source archives")
    sources = work / "source-cache"
    sources.mkdir(parents=True, exist_ok=True)
    _git_trust(manifest, bundle, work)

    def checkout(reference: dict, target: Path) -> None:
        item = manifest["objects"][reference["object"]]
        revision = reference["revision"]
        if item["revision"] != revision:
            raise ValueError("Project revision mapping changed")
        archive = bundle / item["file"]
        if digest(archive) != item["sha256"]:
            raise ValueError("Pinned project archive changed")
        cached = sources / reference["object"]
        if not cached.exists():
            temporary = Path(tempfile.mkdtemp(prefix=".source-", dir=sources))
            try:
                _source_checkout(archive, temporary, item)
                os.replace(temporary, cached)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        _source_metadata(cached, item)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--quiet", "--no-local", str(cached), str(target)],
                check=True,
            )
        actual = subprocess.check_output(
            ["git", "--no-optional-locks", "-C", str(target), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        if actual != revision:
            raise ValueError("Prepared checkout changed: " + str(target))
        _source_metadata(target, item)

    for env in manifest["environments"]:
        target = bundle / env["path"]
        if "root" in env:
            checkout(env["root"], target)
        else:
            target.mkdir(parents=True, exist_ok=True)
            for name, contents in env["template"].items():
                path = target / name
                if path.exists() and path.read_text() != contents:
                    raise ValueError("Standalone project template changed")
                path.write_text(contents)
        for dependency in env["dependencies"]:
            checkout(dependency, target / dependency["path"])


def search_assets(bundle: Path, work: Path) -> None:
    """Use the supplied offline index and a public pinned embedding snapshot."""
    manifest = read(bundle / "assets/manifest.json")
    index = bundle / "assets/index"
    if not index.exists():
        archive = bundle / "assets/lean-explore-index.tar.xz"
        if not archive.exists() and manifest.get("index_archive_parts"):
            temporary = archive.with_suffix(".partial")
            with temporary.open("xb") as output:
                for part in manifest["index_archive_parts"]:
                    source = bundle / part["file"]
                    if digest(source) != part["sha256"]:
                        raise ValueError("Offline index archive part changed")
                    with source.open("rb") as stream:
                        shutil.copyfileobj(stream, output)
            if digest(temporary) != manifest["index_archive_sha256"]:
                raise ValueError("Offline index archive is incomplete")
            os.replace(temporary, archive)
        if not archive.exists():
            raise ValueError(
                "The offline LeanExplore index is missing. Use the complete submission ZIP, "
                "or place its assets/lean-explore-index.tar.xz here before setup. "
                "Contact lazar.milikic@epfl.ch for the asset archive."
            )
        if digest(archive) != manifest["index_archive_sha256"]:
            raise ValueError("Offline search archive changed")
        _extract(archive, index)
    for name, expected in manifest["index_files_sha256"].items():
        if digest(index / name) != expected:
            raise ValueError("Search index changed: " + name)
    embedding = bundle / "assets/embedding"
    if not embedding.exists():
        from huggingface_hub import snapshot_download

        snapshot_download(
            "Qwen/Qwen3-Embedding-0.6B",
            revision=manifest["embedding_revision"],
            cache_dir=str(work / "models/hub"),
            local_dir=str(embedding),
        )
    for name, expected in manifest["embedding_files_sha256"].items():
        if digest(embedding / name) != expected:
            raise ValueError("Embedding snapshot changed: " + name)


def toolchains(bundle: Path, work: Path) -> dict:
    """Install the exact restored projects' Lean versions during CPU setup."""
    manifest = read(bundle / "project-sources/manifest.json")
    required = set()
    for environment in manifest["environments"]:
        project = (bundle / environment["path"]).resolve()
        if not project.is_relative_to(bundle.resolve()):
            raise ValueError("Toolchain project escapes its bundle")
        version = (project / "lean-toolchain").read_text().strip()
        if not version.startswith("leanprover/lean4:") or any(
            char.isspace() for char in version
        ):
            raise ValueError("Unexpected pinned Lean toolchain: " + version)
        required.add(version)
    installed = set(
        subprocess.check_output(["elan", "toolchain", "list"], text=True).split()
    )
    started, downloaded = time.time(), []
    for version in sorted(required - installed):
        print("Installing pinned CPU-setup toolchain " + version, flush=True)
        subprocess.run(
            ["elan", "toolchain", "install", version], check=True, timeout=1800
        )
        downloaded.append(version)
    record = {
        "required": sorted(required),
        "installed_during_setup": downloaded,
        "elapsed_seconds": time.time() - started,
        "model_calls": 0,
        "proof_measurements": 0,
    }
    write_json(work / "toolchains-ready.json", record)
    return record


def prepare(bundle: Path, work: Path) -> dict:
    """Only asset/source materialization. Measurements remain in setup()."""
    work.mkdir(parents=True, exist_ok=True)
    native(bundle)
    projects(bundle, work)
    toolchains(bundle, work)
    search_assets(bundle, work)
    receipt = {
        "status": "ready",
        "model_calls": 0,
        "Lean_calls": 0,
        "source_manifest_sha256": digest(bundle / "project-sources/manifest.json"),
        "asset_manifest_sha256": digest(bundle / "assets/manifest.json"),
    }
    write_json(work / "assets-ready.json", receipt)
    return receipt
