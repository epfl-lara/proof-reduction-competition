"""The compact and complete packages produce the same sealed input bytes."""

import hashlib
import io
from urllib.error import URLError

import pytest

from proof_eval.benchmark import submission_downloads as downloads
from proof_eval.benchmark.submission_workspace import materialize
from proof_eval.evidence.io import digest, write_json

PAYLOAD = b"pinned public dependency fixture\n"
ASSET = "assets/index.tar.xz.000"
REVISION = "b" * 40
URL = f"https://huggingface.co/datasets/example/assets/resolve/{REVISION}/{ASSET}"


class Response(io.BytesIO):
    def geturl(self):
        return URL


@pytest.fixture
def release(tmp_path):
    source, work = tmp_path / "source", tmp_path / "work"
    source.mkdir()
    write_json(source / "recipe.json", {"workers": 10})
    metadata = {
        "schema_version": 1,
        "repository": "example/assets",
        "revision": REVISION,
        "files": {
            ASSET: {
                "url": URL,
                "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
                "bytes": len(PAYLOAD),
            }
        },
    }

    def seal():
        write_json(source / "downloads.json", metadata)
        write_json(
            source / "bundle.json",
            {
                "files_sha256": {
                    "recipe.json": digest(source / "recipe.json"),
                    "downloads.json": digest(source / "downloads.json"),
                    ASSET: hashlib.sha256(PAYLOAD).hexdigest(),
                }
            },
        )

    seal()
    return source, work, metadata, seal


def test_slim_setup_downloads_without_credentials_and_reuses_verified_bytes(
    release, monkeypatch, capsys
):
    source, work, *_ = release
    calls = []

    def open_asset(request, timeout):
        assert request.full_url == URL and timeout == 60
        assert not request.has_header("Authorization")
        calls.append(request.full_url)
        return Response(PAYLOAD)

    monkeypatch.setattr(downloads, "urlopen", open_asset)
    prepared = materialize(source, work)
    assert (prepared / ASSET).read_bytes() == PAYLOAD
    assert not (source / ASSET).exists()
    assert len(calls) == 1
    assert capsys.readouterr().out == ""  # stdout is the shell's bundle path only.
    monkeypatch.setattr(
        downloads, "urlopen", lambda *a, **k: pytest.fail("no repeated download")
    )
    assert materialize(source, work) == prepared
    (prepared / ASSET).write_bytes(b"changed")
    with pytest.raises(ValueError, match="Prepared source changed"):
        materialize(source, work)


def test_full_package_needs_no_asset_network(release, monkeypatch):
    source, work, *_ = release
    (source / ASSET).parent.mkdir()
    (source / ASSET).write_bytes(PAYLOAD)
    monkeypatch.setattr(
        downloads, "urlopen", lambda *a, **k: pytest.fail("full ZIP has its assets")
    )
    assert (materialize(source, work) / ASSET).read_bytes() == PAYLOAD


@pytest.mark.parametrize("payload", [b"short", b"x" * len(PAYLOAD), PAYLOAD + b"extra"])
def test_bad_download_never_becomes_a_prepared_asset(release, monkeypatch, payload):
    source, work, *_ = release
    monkeypatch.setattr(downloads, "urlopen", lambda *a, **k: Response(payload))
    with pytest.raises(ValueError, match="size|checksum"):
        materialize(source, work)
    assert not (work / "bundle" / ASSET).exists()
    assert not list((work / "bundle/assets").glob("*.download-*"))


def test_interrupted_download_is_not_published_and_can_be_retried(release, monkeypatch):
    source, work, *_ = release

    class Interrupted(Response):
        def read(self, size=-1):
            raise URLError("fixture interrupted transfer")

    monkeypatch.setattr(downloads, "urlopen", lambda *a, **k: Interrupted(PAYLOAD))
    with pytest.raises(URLError, match="interrupted"):
        materialize(source, work)
    assert not (work / "bundle" / ASSET).exists()
    monkeypatch.setattr(downloads, "urlopen", lambda *a, **k: Response(PAYLOAD))
    assert (materialize(source, work) / ASSET).read_bytes() == PAYLOAD


@pytest.mark.parametrize(
    "mutation",
    [
        lambda m: m.update(revision="main"),
        lambda m: m["files"][ASSET].update(url=URL.replace("https://", "http://")),
        lambda m: m["files"][ASSET].update(url=URL.replace(REVISION, "main")),
        lambda m: m["files"][ASSET].update(sha256="0" * 64),
        lambda m: m["files"][ASSET].update(bytes=-1),
        lambda m: m["files"].update({"../escape": m["files"][ASSET]}),
    ],
)
def test_invalid_download_manifest_is_rejected_before_network(
    release, monkeypatch, mutation
):
    source, work, metadata, seal = release
    mutation(metadata)
    seal()
    monkeypatch.setattr(
        downloads, "urlopen", lambda *a, **k: pytest.fail("no unpinned downloads")
    )
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        materialize(source, work)


def test_changed_download_manifest_is_rejected(release):
    source, work, *_ = release
    (source / "downloads.json").write_text("{}")
    with pytest.raises(ValueError, match="manifest changed"):
        materialize(source, work)
