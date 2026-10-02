"""Stable Python interface shared by the CLI, HTTP service, and reward functions."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import tempfile
from datetime import datetime, timezone

from .dataset import Dataset
from .lean_backend import LeanBackend
from .metrics import reduction_percent, token_count, validate_candidate


class EvaluationNotReady(RuntimeError):
    """Required projects, measurements, or version checks are unavailable."""


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class _Store:
    """Atomic JSON records and per-key interprocess locks for shared workers."""

    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def locked(self, category, key):
        folder = self.root / category
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / (key + ".lock")).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def read(self, category, key):
        path = self.root / category / (key + ".json")
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise EvaluationNotReady(f"Unreadable cache record {path}: {exc}") from exc

    def write(self, category, key, value):
        folder = self.root / category
        folder.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".record-", suffix=".tmp", dir=folder)
        try:
            with os.fdopen(fd, "w") as out:
                json.dump(value, out, indent=2, ensure_ascii=False, allow_nan=False)
                out.write("\n")
                out.flush()
                os.fsync(out.fileno())
            os.replace(name, folder / (key + ".json"))
        finally:
            if os.path.exists(name):
                os.unlink(name)


class Evaluator:
    """Evaluate code against a dataset row and cached local reference measurements.

    Project paths are supplied explicitly; evaluation never installs dependencies,
    checks out revisions, or measures the reference implicitly. The first version
    in each row is the local primary version for the heartbeat score.
    """

    def __init__(
        self,
        dataset_path="data/benchmark_data_warmup.jsonl",
        environments_path="environments.local.json",
        cache_dir=".proof-eval",
        *,
        heartbeats_path=None,
        timeout=60.0,
        backend=None,
    ):
        self.dataset = Dataset(dataset_path, heartbeats_path=heartbeats_path)
        self.backend = backend or LeanBackend(timeout=timeout)
        self.timeout = float(timeout)
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        self.store = _Store(cache_dir)
        self.projects = {}
        if environments_path is not None:
            config_path = Path(environments_path).expanduser().resolve()
            if config_path.exists():
                config = json.loads(config_path.read_text())
                for item in config.get("projects", []):
                    key = (item["source"], item["version"])
                    if key in self.projects:
                        raise ValueError(f"Duplicate project configuration: {key}")
                    path = Path(item["path"]).expanduser()
                    self.projects[key] = (config_path.parent / path).resolve()
        # Keep local baseline caches isolated across hosts/architectures. The
        # backend additionally fingerprints the actual compiler and dependencies.
        self.machine = {"host": platform.node(), "system": platform.system(), "machine": platform.machine()}

    def _versions(self, row, versions):
        all_versions = [v for entry in row["version_info"] for v in entry]
        if not all_versions or len(set(all_versions)) != len(all_versions):
            raise ValueError("Dataset row must have unique, nonempty version_info")
        if versions == "all":
            selected = all_versions
        elif versions == "primary":
            selected = all_versions[:1]
        elif isinstance(versions, str):
            selected = [versions]
        else:
            selected = list(versions)
        if not selected or len(set(selected)) != len(selected):
            raise ValueError("Select at least one version, without duplicates")
        unknown = set(selected) - set(all_versions)
        if unknown:
            raise ValueError(f"Versions not listed for {row['name']}: {sorted(unknown)}")
        return all_versions, [v for v in all_versions if v in selected]

    def _context(self, row, version):
        path = self.projects.get((row["source"], version))
        if path is None:
            raise EvaluationNotReady(f"No configured project for {row['source']} {version}")
        try:
            fingerprint = self.backend.fingerprint(row, version, path)
        except (ValueError, OSError, RuntimeError) as exc:
            raise EvaluationNotReady(str(exc)) from exc
        identity = {
            "schema": 1,
            "row_hash": _hash(row),
            "version": version,
            "environment": fingerprint,
            "machine": self.machine,
            "timeout_seconds": self.timeout,
        }
        return path, fingerprint, _hash(identity)

    @staticmethod
    def _unavailable(message):
        return {"status": "unavailable", "passed": False, "heartbeats": None,
                "heartbeats_raw": None, "diagnostics": [{"severity": "error", "data": str(message)}]}

    def environments(self):
        """List required environments and whether each is configured."""
        out = {}
        for name in self.dataset.names:
            row = self.dataset.get(name)
            for entry in row["version_info"]:
                for version, commit in entry.items():
                    key = (row["source"], version, commit)
                    path = self.projects.get((row["source"], version))
                    out[key] = {"source": row["source"], "version": version, "commit": commit,
                                "path": str(path) if path else None}
        return list(out.values())

    def get_reference(self, name, *, versions="all"):
        """Read reference values and local cache status without compiling proofs."""
        row = self.dataset.get(name)
        all_versions, selected = self._versions(row, versions)
        out = {"name": name, "length": row["proof_length"],
               "published_heartbeats": row.get("published_heartbeats"),
               "primary_version": all_versions[0], "versions": {}}
        for version in selected:
            try:
                _, _, key = self._context(row, version)
                record = self.store.read("references", key)
                out["versions"][version] = record or {"status": "reference_not_prepared"}
            except EvaluationNotReady as exc:
                out["versions"][version] = self._unavailable(exc)
        return out

    def prepare_reference(self, name, *, versions="all", refresh=False):
        """Measure the reference once per fingerprint; reuse it thereafter.

        Explicit refresh is the only operation that replaces a cached baseline.
        A failed reference run is never recorded as a usable baseline.
        """
        row = self.dataset.get(name)
        _, selected = self._versions(row, versions)
        results = {}
        for version in selected:
            try:
                path, fingerprint, key = self._context(row, version)
                with self.store.locked("references", key):
                    record = self.store.read("references", key)
                    if record is not None and not refresh:
                        results[version] = {**record, "cached": True}
                        continue
                    result = self.backend.check(row, row["src"], version, path)
                    if not result.get("passed") or result.get("heartbeats") is None:
                        results[version] = {**result, "cached": False}
                        continue
                    # Detect an environment changing while compilation ran.
                    _, after_fingerprint, after_key = self._context(row, version)
                    if after_fingerprint != fingerprint or after_key != key:
                        raise EvaluationNotReady("Project changed during reference measurement")
                    record = {"name": name, "version": version, "status": "prepared",
                              "heartbeats": result["heartbeats"], "heartbeats_raw": result.get("heartbeats_raw"),
                              "length": row["proof_length"], "environment_fingerprint": fingerprint,
                              "measured_at": datetime.now(timezone.utc).isoformat(),
                              "reference_code_sha256": hashlib.sha256(row["src"].encode()).hexdigest(),
                              "machine": self.machine, "details": result.get("details", {})}
                    self.store.write("references", key, record)
                    results[version] = {**record, "cached": False}
            except EvaluationNotReady as exc:
                results[version] = self._unavailable(exc)
        return {"name": name, "status": "prepared" if all(r.get("status") == "prepared" for r in results.values()) else "incomplete",
                "versions": results}

    def _candidate(self, row, code, version):
        try:
            path, fingerprint, key = self._context(row, version)
            reference = self.store.read("references", key)
            candidate_key = _hash({"context": key, "code": code})
            with self.store.locked("candidates", candidate_key):
                result = self.store.read("candidates", candidate_key)
                cached = result is not None
                if result is None:
                    result = self.backend.check(row, code, version, path)
                    _, after_fingerprint, after_key = self._context(row, version)
                    if after_fingerprint != fingerprint or after_key != key:
                        raise EvaluationNotReady("Project changed during candidate measurement")
                    if result.get("status") in ("passed", "failed"):
                        self.store.write("candidates", candidate_key, result)
            result = {**result, "cached": cached, "reference": reference}
            result["heartbeat_reduction_pct"] = (
                reduction_percent(reference["heartbeats"], result.get("heartbeats"))
                if reference is not None and result.get("passed") else None
            )
            return result
        except EvaluationNotReady as exc:
            return self._unavailable(exc)

    def evaluate(self, name, code, *, input_kind="declaration", versions="all"):
        """Return component scores and diagnostics; never measure a reference."""
        row = self.dataset.get(name)
        all_versions, selected = self._versions(row, versions)
        out = {"schema_version": 1, "name": name, "status": "incomplete",
               "primary_version": all_versions[0], "requested_versions": selected,
               "all_versions": all_versions, "measurement": "local_cached_reference",
               "reference": {"length": row["proof_length"], "published_heartbeats": row.get("published_heartbeats")},
               "candidate": {}, "per_version": {}, "diagnostics": [],
               "scores": {"length_reduction_pct": None, "heartbeat_reduction_pct": None,
                          "compatibility_pct": None, "combined_pct": None}}
        try:
            full_code, body = validate_candidate(row, code, input_kind=input_kind)
        except ValueError as exc:
            out["status"] = "invalid"
            out["diagnostics"] = [str(exc)]
            out["scores"] = dict.fromkeys(out["scores"], 0.0)
            return out
        length = token_count(body)
        out["candidate"] = {"length": length, "code_sha256": hashlib.sha256(full_code.encode()).hexdigest()}
        results = {v: self._candidate(row, full_code, v) for v in selected}
        out["per_version"] = results
        primary = results.get(all_versions[0])
        if primary is not None and primary.get("status") in ("failed", "timeout"):
            out["status"] = "failed"
            out["scores"] = dict.fromkeys(out["scores"], 0.0)
            return out
        if primary and primary.get("passed"):
            out["scores"]["length_reduction_pct"] = reduction_percent(row["proof_length"], length)
            out["scores"]["heartbeat_reduction_pct"] = primary.get("heartbeat_reduction_pct")
            if primary.get("reference") is None:
                out["diagnostics"].append("Primary local reference is not prepared; run prepare_reference explicitly.")
            elif primary.get("heartbeat_reduction_pct") is None:
                out["diagnostics"].append("Primary reference heartbeat count is zero or unavailable; a relative heartbeat score is undefined.")
        fully_checked = set(selected) == set(all_versions) and all(
            r.get("status") in ("passed", "failed", "timeout") for r in results.values()
        )
        if primary and primary.get("passed") and fully_checked:
            out["scores"]["compatibility_pct"] = 100.0 * sum(bool(r.get("passed")) for r in results.values()) / len(all_versions)
            axes = [out["scores"][key] for key in ("length_reduction_pct", "heartbeat_reduction_pct", "compatibility_pct")]
            if all(x is not None for x in axes):
                out["scores"]["combined_pct"] = sum(axes) / 3.0
                out["status"] = "passed"
        if not fully_checked:
            out["diagnostics"].append("Compatibility and combined score require checks for every listed version.")
        return out

    def reward(self, name, code, *, metric="combined", input_kind="declaration", versions="all", invalid_reward=0.0):
        """Return the chosen percentage divided by 100 for a training loop.

        Missing infrastructure/baselines raise instead of being mislabeled as
        bad model outputs. Negative reductions are preserved without clipping.
        """
        fields = {"combined": "combined_pct", "length": "length_reduction_pct",
                  "heartbeat": "heartbeat_reduction_pct", "compatibility": "compatibility_pct"}
        if metric not in fields:
            raise ValueError(f"metric must be one of {list(fields)}")
        if not math.isfinite(invalid_reward):
            raise ValueError("invalid_reward must be finite")
        result = self.evaluate(name, code, input_kind=input_kind, versions=versions)
        if result["status"] in ("invalid", "failed"):
            return float(invalid_reward)
        value = result["scores"][fields[metric]]
        if value is None:
            raise EvaluationNotReady(f"{name}: {metric} reward unavailable; inspect evaluate() diagnostics")
        return value / 100.0

    def reward_batch(self, names, codes, **kwargs):
        """Trainer-neutral batch adapter; supply problem IDs alongside completions."""
        names, codes = list(names), list(codes)
        if len(names) != len(codes):
            raise ValueError("names and codes must have the same length")
        return [self.reward(name, code, **kwargs) for name, code in zip(names, codes)]
