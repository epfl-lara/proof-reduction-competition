"""Rebuildable SQLite index with an immutable same-cell scope pin."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from proof_eval.evidence.io import fingerprint, read, write_json

from .diffs import hunks, line_ranges
from .model import (
    DIFF_VERSION,
    SCHEMA_VERSION,
    check_base,
    fragment_id,
    integer,
    metadata,
    snapshot_id,
    validate_ledger,
)


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class ProofHistory:
    """Host-owned derived index; ``sync`` accepts the entire committed ledger.

    Construction pins the scope and seed but does not read or write checks.jsonl.
    Call ``sync`` after loading or committing authoritative checks. The optional
    in-memory mode performs no filesystem access and supports offline replay.
    """

    def __init__(
        self,
        folder: str | Path,
        scope: Mapping[str, Any],
        seed_code: str,
        seed_evaluation: dict,
        versions: Sequence[str],
        *,
        memory_only: bool = False,
    ) -> None:
        self.scope = deepcopy(dict(scope))
        self.scope_sha256 = fingerprint(self.scope)
        self.seed_code = seed_code
        self.seed_evaluation = deepcopy(seed_evaluation)
        self.versions = tuple(versions)
        self.folder = Path(folder) / "proof_history"
        self.path = self.folder / "index.sqlite3"
        self.memory_only = memory_only
        self.lock = threading.RLock()
        self._connection: sqlite3.Connection | None = None
        self._events = validate_ledger(
            [],
            scope=self.scope,
            seed_code=seed_code,
            seed_evaluation=seed_evaluation,
            versions=self.versions,
        )
        self._prefixes = [
            fingerprint({"previous": None, "check": self._events[0]["source_sha256"]})
        ]
        self._synced = False
        self._invalidated = False
        self._checks: list[dict] = []
        self._hunks_cache: dict[tuple[str, str], list[dict]] = {}
        self._restored_queries: list[str] = []
        pin = {
            "schema_version": SCHEMA_VERSION,
            "diff_version": DIFF_VERSION,
            "scope": self.scope,
            "scope_sha256": self.scope_sha256,
            "seed_snapshot_id": snapshot_id(seed_code),
            "seed_evaluation_sha256": fingerprint(seed_evaluation),
            "required_versions": list(self.versions),
        }
        if not memory_only:
            self.folder.mkdir(parents=True, exist_ok=True)
            pin_path = self.folder / "scope.json"
            if pin_path.exists():
                if read(pin_path) != pin:
                    raise ValueError("Proof history scope or seed pin mismatch")
            else:
                write_json(pin_path, pin)

    @property
    def indexed_through_check(self) -> int:
        return len(self._events) - 1

    def validate_base(
        self, base_check: int | None, current_count: int | None = None
    ) -> int | None:
        count = self.indexed_through_check if current_count is None else current_count
        integer(count, "current_count", 0, 2**63 - 1)
        return check_base(base_check, count)

    def check_metadata(
        self,
        *,
        code: str,
        base_check: int | None,
        base_provenance: str = "model_declared",
        evaluated_code: str | None = None,
    ) -> dict:
        self.validate_base(base_check)
        return metadata(
            self.scope_sha256, code, base_check, base_provenance, evaluated_code
        )

    def _connect(self) -> sqlite3.Connection:
        if self._connection is None:
            target = ":memory:" if self.memory_only else str(self.path)
            self._connection = sqlite3.connect(target, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        with self.lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def invalidate(self) -> None:
        """Discard trust in derived query state after a failed authority commit.

        The next sync rebuilds from committed checks; restore_queries then adds
        only fragments backed by the committed query journal.
        """
        with self.lock:
            self.close()
            self._invalidated = True
            self._synced = False
            self._restored_queries = []

    def _reset(self) -> sqlite3.Connection:
        self.close()
        self._restored_queries = []
        if not self.memory_only:
            # The disposable index is the only file removed. The scope pin and
            # authoritative checks remain untouched, including on rebuild failure.
            self.path.unlink(missing_ok=True)
            self.path.with_name(self.path.name + "-journal").unlink(missing_ok=True)
        db = self._connect()
        db.executescript("""
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE snapshots (id TEXT PRIMARY KEY, code BLOB NOT NULL);
            CREATE TABLE checks (id INTEGER PRIMARY KEY, snapshot TEXT NOT NULL,
                                 record TEXT NOT NULL);
            CREATE TABLE fragments (id TEXT PRIMARY KEY, code BLOB NOT NULL);
            CREATE TABLE lines (snapshot TEXT NOT NULL, line INTEGER NOT NULL,
                                start INTEGER NOT NULL, end INTEGER NOT NULL,
                                fragment TEXT NOT NULL,
                                PRIMARY KEY(snapshot,line));
            CREATE INDEX line_fragment ON lines(fragment,snapshot,start);
            CREATE TABLE transitions (result_check INTEGER NOT NULL,
                                      hunk INTEGER NOT NULL, body TEXT NOT NULL,
                                      PRIMARY KEY(result_check,hunk));
            """)
        return db

    def _index_consistent(self, db: sqlite3.Connection, events: list[dict]) -> bool:
        if not self.memory_only and not self.path.exists():
            return False
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            return False
        meta = dict(db.execute("SELECT key,value FROM meta"))
        if meta.get("scope") != self.scope_sha256 or meta.get("version") != str(
            (SCHEMA_VERSION, DIFF_VERSION)
        ):
            return False
        records = list(db.execute("SELECT id,record FROM checks ORDER BY id"))
        if len(records) > len(events):
            return False
        if any(
            row["id"] != i or row["record"] != encoded(events[i])
            for i, row in enumerate(records)
        ):
            return False
        prefix = events[: len(records)]
        expected_snapshots = {
            event[key]: event[code_key].encode("utf-8")
            for event in prefix
            for key, code_key in (
                ("snapshot_id", "code"),
                ("evaluated_snapshot_id", "evaluated_code"),
            )
            if key in event
        }
        if dict(db.execute("SELECT id,code FROM snapshots")) != expected_snapshots:
            return False
        expected_lines = sorted(
            (identity, number, start, end, fragment_id(line))
            for identity, data in expected_snapshots.items()
            for number, (line, start, end) in enumerate(
                line_ranges(data.decode("utf-8")), 1
            )
        )
        actual_lines = [
            tuple(row)
            for row in db.execute(
                "SELECT snapshot,line,start,end,fragment FROM lines ORDER BY snapshot,line"
            )
        ]
        if actual_lines != expected_lines:
            return False
        expected_transitions = [
            (event["check_id"], change["hunk"], encoded(change))
            for event in prefix
            if event["base_check"] is not None
            for change in self._changes(events[event["base_check"]], event)
        ]
        if [
            tuple(row)
            for row in db.execute(
                "SELECT result_check,hunk,body FROM transitions ORDER BY result_check,hunk"
            )
        ] != expected_transitions:
            return False
        present_fragments = set()
        for identity, data in db.execute("SELECT id,code FROM fragments"):
            try:
                if fragment_id(bytes(data).decode("utf-8")) != identity:
                    return False
            except (ValueError, UnicodeError, TypeError):
                return False
            present_fragments.add(identity)
        required_fragments = {row[4] for row in expected_lines}
        for _, _, body in expected_transitions:
            change = json.loads(body)
            required_fragments.update(
                identity
                for identity in (change["base_fragment"], change["result_fragment"])
                if identity is not None
            )
        if not required_fragments <= present_fragments:
            return False
        if int(meta.get("checks", "-1")) != len(records):
            return False
        # A transactional row-count checkpoint detects missing derived rows.
        return all(
            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            == int(meta.get(table, "-1"))
            for table in ("snapshots", "lines", "transitions")
        )

    def _changes(self, base: dict, result: dict) -> list[dict]:
        key = (base["snapshot_id"], result["snapshot_id"])
        if key not in self._hunks_cache:
            self._hunks_cache[key] = hunks(base["code"], result["code"])
        return self._hunks_cache[key]

    def _fragment(self, db: sqlite3.Connection, code: str) -> str | None:
        if not code:
            return None
        identity = fragment_id(code)
        db.execute(
            "INSERT OR IGNORE INTO fragments VALUES (?,?)",
            (identity, code.encode("utf-8")),
        )
        return identity

    def _snapshot(self, db: sqlite3.Connection, code: str) -> None:
        identity = snapshot_id(code)
        if db.execute("SELECT 1 FROM snapshots WHERE id=?", (identity,)).fetchone():
            return
        db.execute(
            "INSERT INTO snapshots VALUES (?,?)", (identity, code.encode("utf-8"))
        )
        for number, (line, start, end) in enumerate(line_ranges(code), 1):
            fragment = self._fragment(db, line)
            db.execute(
                "INSERT INTO lines VALUES (?,?,?,?,?)",
                (identity, number, start, end, fragment),
            )

    def sync(self, checks: Sequence[dict]) -> None:
        """Catch up atomically or rebuild; never change authoritative check bytes."""
        with self.lock:
            events = validate_ledger(
                checks,
                scope=self.scope,
                seed_code=self.seed_code,
                seed_evaluation=self.seed_evaluation,
                versions=self.versions,
            )
            db = self._connect()
            try:
                consistent = not self._invalidated and self._index_consistent(
                    db, events
                )
            except (sqlite3.DatabaseError, ValueError):
                consistent = False
            if not consistent:
                db = self._reset()
            with db:
                count = db.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
                for event in events[count:]:
                    self._snapshot(db, event["code"])
                    if "evaluated_code" in event:
                        self._snapshot(db, event["evaluated_code"])
                    db.execute(
                        "INSERT INTO checks VALUES (?,?,?)",
                        (event["check_id"], event["snapshot_id"], encoded(event)),
                    )
                    base = event["base_check"]
                    if base is not None:
                        for change in self._changes(events[base], event):
                            self._fragment(db, change["base_text"])
                            self._fragment(db, change["result_text"])
                            db.execute(
                                "INSERT INTO transitions VALUES (?,?,?)",
                                (event["check_id"], change["hunk"], encoded(change)),
                            )
                meta = {
                    "scope": self.scope_sha256,
                    "version": str((SCHEMA_VERSION, DIFF_VERSION)),
                    "checks": str(len(events)),
                    **{
                        table: str(
                            db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        )
                        for table in ("snapshots", "lines", "transitions")
                    },
                }
                db.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", meta.items())
            self._events = events
            self._checks = deepcopy(list(checks))
            self._prefixes = []
            for event in events:
                self._prefixes.append(
                    fingerprint(
                        {
                            "previous": self._prefixes[-1] if self._prefixes else None,
                            "check": event["source_sha256"],
                        }
                    )
                )
            self._synced = True
            self._invalidated = False

    def restore_queries(self, queries: Sequence[dict]) -> None:
        """Restore query-introduced fragments from the authoritative query journal.

        Arbitrary substrings cannot be inverted from their hashes. The journal
        preserves their text/range requests, so rebuilding a disposable index
        restores those identities without adding a second fragment ledger.
        """
        from .lookup import event_at, resolve_text

        with self.lock:
            identities = [fingerprint(record) for record in queries]
            if identities[: len(self._restored_queries)] != self._restored_queries:
                raise ValueError(
                    "Proof history query journal changed its committed prefix"
                )
            db = self._connect()
            with db:
                for index, record in enumerate(
                    queries[len(self._restored_queries) :],
                    len(self._restored_queries) + 1,
                ):
                    if (
                        type(record.get("number")) is not int
                        or record["number"] != index
                    ):
                        raise ValueError(
                            "History query journal numbers must be contiguous"
                        )
                    if record.get("scope") != self.scope:
                        raise ValueError("History query journal scope mismatch")
                    count = integer(
                        record.get("check_count"),
                        "query check_count",
                        0,
                        self.indexed_through_check,
                    )
                    if record.get("checks_sha256") != fingerprint(self._checks[:count]):
                        raise ValueError("History query journal check prefix mismatch")
                    request, response = record["request"], record["response"]
                    cutoff = integer(response.get("as_of"), "query as_of", 0, count)
                    action = request.get("action")
                    if action in {"find", "expand"} and "transition_id" not in request:
                        text = resolve_text(self, db, request, cutoff)
                        if fragment_id(text) != response.get("fragment_hash"):
                            raise ValueError(
                                "History query journal fragment identity mismatch"
                            )
                        self._fragment(db, text)
                    elif action == "diff" or (
                        action == "expand" and "transition_id" in request
                    ):
                        if action == "diff":
                            base_id = request.get(
                                "base_check_id", request.get("from_check")
                            )
                            result_id = request.get("check_id", request.get("to_check"))
                        else:
                            parts = request["transition_id"].split(":")
                            base_id, result_id = map(int, parts[1:3])
                        base = event_at(self, base_id, cutoff)
                        result = event_at(self, result_id, cutoff)
                        for change in self._changes(base, result):
                            self._fragment(db, change["base_text"])
                            self._fragment(db, change["result_text"])
            self._restored_queries = identities

    def get_snapshot(self, check: int) -> str:
        with self.lock:
            check = integer(check, "check_id", 0, self.indexed_through_check)
            return self._events[check]["code"]

    def query(self, request: dict, *, query_id: int | None = None) -> dict:
        """Execute a bounded, deterministic query against a committed prefix."""
        from .query import query

        with self.lock:
            if not self._synced:
                self.sync(self._checks)
            if not isinstance(request, dict):
                raise ValueError("History request must be an object")
            db = self._connect()
            # One host lock and one read transaction retain a consistent prefix.
            # Fragment registration is derived cache work and is committed with
            # this transaction; it never changes proof evidence.
            try:
                with db:
                    return query(self, db, request, query_id=query_id)
            except sqlite3.DatabaseError as exc:
                raise ValueError(
                    "Proof history index failed; sync committed checks to rebuild"
                ) from exc
