"""Verify the sealed inference-only source bundle and its relative paths."""

from pathlib import Path

from proof_eval.evidence.io import digest, read


def bundle_path(root: Path, relative: str) -> Path:
    """Resolve a bundle-owned path, rejecting absolute paths and escaping symlinks."""
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Submission paths must be relative to the bundle")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Submission path escapes the bundle")
    return path


def verify_bundle(root: Path) -> dict:
    """Verify every packaged source/input/binary before invoking setup or inference."""
    manifest = read(root / "bundle.json")
    if manifest.get("schema_version") != 1:
        raise ValueError("Unknown submission bundle schema")
    for relative, expected in manifest["files_sha256"].items():
        path = bundle_path(root, relative)
        if not path.is_file() or digest(path) != expected:
            raise ValueError("Submission artifact changed: " + relative)
    if digest(root / "recipe.json") != manifest["recipe_sha256"]:
        raise ValueError("Submission recipe changed; build a new archive")
    return read(root / "recipe.json")
