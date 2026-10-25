"""Freeze repository training code with an explicitly selected host runtime.

This is source packaging only. It neither submits jobs nor prepares references.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read, sha

BOOTSTRAP = '''"""Generic frozen-package entrypoint, after container environment activation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from proof_eval.interfaces.training import main
if __name__ == "__main__":
    raise SystemExit(main())
'''


def freeze_release(
    repository: Path,
    host_runtime: Path,
    host_manifest: Path,
    dataset: Path,
    test_wheels: Path,
    destination: Path,
    plan: dict,
    authorization: dict,
    predecessor: dict,
    repository_identity: dict,
    host_extensions: tuple[str, ...] = (),
) -> dict:
    """Create one immutable source bundle; never overwrite an earlier release."""
    destination.mkdir(parents=True, exist_ok=False)
    for relative, pin in read(host_manifest).items():
        source = host_runtime / relative
        if sha(source) != pin:
            raise ValueError("Selected host runtime changed: " + relative)
        if relative.startswith("src/"):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    sources = [
        *sorted((repository / "src/proof_eval/training").glob("*.py")),
        repository / "src/proof_eval/interfaces/training.py",
        repository / "src/proof_eval/evidence/immutable.py",
        *sorted((repository / "tests/training").glob("*.py")),
        *[repository / relative for relative in host_extensions],
    ]
    source_pins = repository_identity["files"]
    for source in sources:
        relative = source.relative_to(repository)
        if sha(source) != source_pins.get(str(relative)):
            raise ValueError(
                "Training source differs from repository identity: " + str(relative)
            )
        target = destination / relative
        if target.exists():
            raise ValueError("Training overlay may not replace an existing host module")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for name in ("rl-reserved.jsonl", "sft.jsonl", "validation.jsonl"):
        target = destination / "dataset" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(dataset / name, target)
    for source in sorted(test_wheels.glob("*.whl")):
        target = destination / "test-wheels" / source.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source, target)
    immutable(destination / "plan.json", plan)
    immutable(destination / "launch-authorization.json", authorization)
    immutable(destination / "startup-failure-predecessor.json", predecessor)
    immutable(destination / "repository.json", repository_identity)
    (destination / "bootstrap.py").write_text(BOOTSTRAP)
    pins = {
        str(p.relative_to(destination)): sha(p)
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    immutable(destination / "source-manifest.json", pins)
    return {
        "status": "frozen_sources_only",
        "files": len(pins),
        "source_manifest_sha256": sha(destination / "source-manifest.json"),
        "repository_revision": repository_identity["revision"],
        "host_manifest_sha256": sha(host_manifest),
        "model_calls": 0,
    }
