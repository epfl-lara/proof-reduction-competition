"""Copy only sealed submission files to a writable shared-storage workspace."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from proof_eval.benchmark.submission_downloads import fetch, records
from proof_eval.evidence.io import digest, read


def materialize(source: Path, work: Path) -> Path:
    source, work = source.resolve(), work.resolve()
    target = work / "bundle"
    manifest = read(source / "bundle.json")
    downloads = records(source, manifest["files_sha256"])
    work.mkdir(parents=True, exist_ok=True)
    target.mkdir(exist_ok=True)
    for name, expected in manifest["files_sha256"].items():
        original = (source / name).resolve()
        destination = (target / name).resolve()
        if not original.is_relative_to(source) or not destination.is_relative_to(
            target
        ):
            raise ValueError("Submission file escapes its source/workspace")
        available = original.is_file()
        if available and digest(original) != expected:
            raise ValueError("Submission source changed: " + name)
        if not available and name not in downloads:
            raise ValueError("Missing sealed submission file: " + name)
        if destination.exists():
            if digest(destination) != expected:
                raise ValueError(
                    "Prepared source changed; choose a new work directory: " + name
                )
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if available:
            shutil.copy2(original, destination)
        else:
            fetch(downloads[name], destination)
    destination = target / "bundle.json"
    if (
        destination.exists()
        and destination.read_bytes() != (source / "bundle.json").read_bytes()
    ):
        raise ValueError("Workspace belongs to a different submission release")
    if source != target:
        shutil.copy2(source / "bundle.json", destination)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    print(materialize(args.source, args.work))


if __name__ == "__main__":
    main()
