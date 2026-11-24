"""Explicitly provision pinned warm-up projects; never invoked by evaluation.

Downloads toolchains/dependencies and builds only the benchmark's source modules.
Existing checkouts must match the requested revision. Logs and a resumable status
record live under the ignored project root. Register only successful builds.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from proof_eval.verification.dataset import Dataset


def checkout(path, url, revision, run):
    if (path / ".git").exists():
        head = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != revision:
            raise ValueError(
                f"Refusing to change existing checkout {path}: {head} != {revision}"
            )
        return
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q", str(path)])
    run(["git", "-C", str(path), "remote", "add", "origin", url])
    run(["git", "-C", str(path), "fetch", "--depth", "1", "origin", revision])
    run(["git", "-C", str(path), "checkout", "--detach", "FETCH_HEAD"])


def provision(
    key, rows, root, cpu_count, *, project_path=None, install_toolchains=True
):
    source, version = key
    revision = next(
        item[version] for item in rows[0]["version_info"] if version in item
    )
    path = (
        Path(project_path) if project_path is not None else root / f"{source}-{version}"
    )
    log_path = root / f"{source}-{version}.log"
    started = time.monotonic()
    result = dict(
        source=source,
        version=version,
        revision=revision,
        path=str(path),
        log=str(log_path),
    )
    print(f"Preparing {source} {version}", flush=True)
    with log_path.open("a") as log:

        def run(args, cwd=None):
            log.write("\n" + json.dumps(args) + "\n")
            log.flush()
            subprocess.run(
                args,
                cwd=cwd,
                env={
                    **os.environ,
                    "ELAN_TOOLCHAIN": f"leanprover/lean4:{version}",
                    "MATHLIB_CACHE_DIR": str(root / f"cache-{source}-{version}"),
                },
                stdout=log,
                stderr=log,
                check=True,
                timeout=3600,
            )

        try:
            installed = subprocess.check_output(
                ["elan", "toolchain", "list"], text=True
            )
            if f"leanprover/lean4:{version}" not in installed.split():
                if not install_toolchains:
                    raise ValueError(
                        f"Required Lean toolchain is not installed: {version}"
                    )
                run(["elan", "toolchain", "install", f"leanprover/lean4:{version}"])
            if source == "putnambench":
                path.mkdir(parents=True, exist_ok=True)
                mathlib = path / ".lake/packages/mathlib"
                checkout(
                    mathlib,
                    "https://github.com/leanprover-community/mathlib4.git",
                    revision,
                    run,
                )
                lakefile = (
                    'name = "arena_warmup"\nversion = "0.1.0"\n\n[[require]]\n'
                    'name = "mathlib"\ngit = "https://github.com/leanprover-community/mathlib4.git"\n'
                    f'rev = "{revision}"\n'
                )
                manifest = json.loads((mathlib / "lake-manifest.json").read_text())
                packages = [{**p, "inherited": True} for p in manifest["packages"]]
                packages.insert(
                    0,
                    dict(
                        name="mathlib",
                        type="git",
                        url="https://github.com/leanprover-community/mathlib4.git",
                        rev=revision,
                        inputRev=revision,
                        inherited=False,
                        scope="",
                        subDir=None,
                        configFile="lakefile.lean",
                        manifestFile="lake-manifest.json",
                    ),
                )
                manifest.update(name="arena_warmup", packages=packages)
                files = {
                    "lakefile.toml": lakefile,
                    "lean-toolchain": f"leanprover/lean4:{version}\n",
                    "lake-manifest.json": json.dumps(manifest, indent=2) + "\n",
                }
                for name, value in files.items():
                    f = path / name
                    if f.exists() and f.read_text() != value:
                        raise ValueError(
                            f"Refusing to overwrite changed configuration: {f}"
                        )
                    f.write_text(value)
            else:
                checkout(path, rows[0]["url"], revision, run)
            if (
                path / "lean-toolchain"
            ).read_text().strip() != f"leanprover/lean4:{version}":
                raise ValueError("Source revision has a different Lean toolchain")
            # Lake honors the committed manifest when fetching missing packages.
            cpus = sorted(os.sched_getaffinity(0))[:cpu_count]
            lake = ["taskset", "-c", ",".join(map(str, cpus)), "lake"]
            run(lake + ["env", "true"], path)
            manifest = json.loads((path / "lake-manifest.json").read_text())
            if any(p["name"] == "mathlib" for p in manifest["packages"]):
                run(lake + ["exe", "cache", "get"], path)
            if source != "putnambench":
                modules = sorted(
                    {
                        str(Path(r["file_path"]).with_suffix("")).replace("/", ".")
                        for r in rows
                    }
                )
                run(lake + ["build", *modules], path)
            result["status"] = "built"
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result.update(status="failed", error=str(exc))
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    (root / f"{source}-{version}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"{source} {version}: {result['status']} ({result['elapsed_seconds']}s)",
        flush=True,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/benchmark_data_warmup.jsonl")
    parser.add_argument("--environments", default="environments.local.json")
    parser.add_argument("--root", default=".proof-eval-projects")
    parser.add_argument("--source", action="append")
    parser.add_argument("--version", action="append")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cpus", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1 or args.cpus < 1:
        parser.error("workers and cpus must be positive")
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    config_path = Path(args.environments)
    config = (
        json.loads(config_path.read_text())
        if config_path.exists()
        else {"projects": []}
    )
    configured = {(p["source"], p["version"]) for p in config["projects"]}
    groups = {}
    dataset = Dataset(args.dataset)
    for name in dataset.names:
        row = dataset.get(name)
        if args.source and row["source"] not in args.source:
            continue
        for entry in row["version_info"]:
            version = next(iter(entry))
            if args.version and version not in args.version:
                continue
            key = row["source"], version
            if key not in configured:
                groups.setdefault(key, []).append(row)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(provision, key, rows, root, args.cpus)
            for key, rows in groups.items()
        ]
        for future in as_completed(futures):
            result = future.result()
            if result["status"] == "built":
                with config_path.with_suffix(config_path.suffix + ".lock").open(
                    "a"
                ) as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    config = (
                        json.loads(config_path.read_text())
                        if config_path.exists()
                        else {"projects": []}
                    )
                    if not any(
                        p["source"] == result["source"]
                        and p["version"] == result["version"]
                        for p in config["projects"]
                    ):
                        config["projects"].append(
                            {k: result[k] for k in ("source", "version", "path")}
                        )
                    temporary = config_path.with_suffix(".tmp")
                    temporary.write_text(json.dumps(config, indent=2) + "\n")
                    temporary.replace(config_path)
    return 0 if all(f.result()["status"] == "built" for f in futures) else 2


if __name__ == "__main__":
    raise SystemExit(main())
