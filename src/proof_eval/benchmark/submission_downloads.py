"""Fetch omitted release assets into the prepared workspace before installation."""

from __future__ import annotations

import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from proof_eval.evidence.io import digest, read


def records(source: Path, sealed: dict[str, str]) -> dict[str, dict]:
    """Read only a sealed manifest with immutable public asset URLs."""
    if "downloads.json" not in sealed:
        return {}
    path = source / "downloads.json"
    if digest(path) != sealed["downloads.json"]:
        raise ValueError("Submission download manifest changed")
    manifest = read(path)
    repository = manifest.get("repository", "")
    revision = manifest.get("revision", "")
    if (
        manifest.get("schema_version") != 1
        or not re.fullmatch(r"[\w.-]+/[\w.-]+", repository)
        or not re.fullmatch(r"[0-9a-f]{40}", revision)
        or not isinstance(manifest.get("files"), dict)
    ):
        raise ValueError("Invalid submission download manifest")
    base = f"https://huggingface.co/datasets/{repository}/resolve/{revision}/"
    for name, record in manifest["files"].items():
        if (
            not name.startswith(("assets/", "native/", "project-sources/"))
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or "\\" in name
            or ":" in name
            or not isinstance(record, dict)
            or record.get("sha256") != sealed.get(name)
            or not re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", ""))
            or type(record.get("bytes")) is not int
            or record["bytes"] <= 0
            or record.get("url") != base + quote(name, safe="/")
        ):
            raise ValueError("Invalid pinned download entry: " + name)
    return manifest["files"]


def fetch(record: dict, target: Path) -> None:
    """Publish an asset only after its complete size and SHA-256 match."""
    target.parent.mkdir(parents=True, exist_ok=True)
    print(
        f"Downloading {target.name} ({record['bytes'] / 1e6:.1f} MB)", file=sys.stderr
    )
    temporary = None
    try:
        request = Request(
            record["url"], headers={"User-Agent": "EPFL-LARA-submission/1"}
        )
        with tempfile.NamedTemporaryFile(
            prefix="." + target.name + ".download-", dir=target.parent, delete=False
        ) as output:
            temporary = Path(output.name)
            checksum = hashlib.sha256()
            size = 0
            with urlopen(request, timeout=60) as response:
                if not response.geturl().startswith("https://"):
                    raise ValueError("Asset download redirected outside HTTPS")
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > record["bytes"]:
                        raise ValueError("Downloaded asset exceeds its pinned size")
                    checksum.update(block)
                    output.write(block)
        if size != record["bytes"] or checksum.hexdigest() != record["sha256"]:
            raise ValueError(
                "Downloaded asset size or checksum differs: " + target.name
            )
        if target.exists() and digest(target) != record["sha256"]:
            raise ValueError("Existing prepared asset changed: " + target.name)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
