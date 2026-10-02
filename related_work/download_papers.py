#!/usr/bin/env python3
"""Fetch the pinned reading list, or check its local SHA-256 inventory."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "papers.json"
MAX_BYTES = 100 * 1024 * 1024


def fetch(paper, *, check, record):
    target = ROOT / paper["file"]
    if target.parent.resolve() != (ROOT / "papers").resolve():
        raise ValueError("paper path must be directly under papers/")
    if target.exists():
        data = target.read_bytes()
    elif check:
        raise FileNotFoundError(target.name)
    else:
        request = Request(paper["pdf_url"], headers={"User-Agent": "proof-reduction-literature/1.0"})
        with urlopen(request, timeout=45) as response:
            data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data.startswith(b"%PDF-"):
        raise ValueError("response is not a PDF within the 100 MiB limit")
    digest = hashlib.sha256(data).hexdigest()
    expected = paper.get("sha256")
    if expected and expected != digest:
        raise ValueError("SHA-256 mismatch; inspect the source rather than silently replacing it")
    if not expected and not record:
        raise ValueError("missing checksum; initial inventory requires --record-hashes")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            tmp = Path(stream.name)
            try:
                stream.write(data)
                stream.close()
                tmp.replace(target)
            finally:
                tmp.unlink(missing_ok=True)
    result = {**paper, "sha256": digest, "bytes": len(data)}
    result.setdefault("downloaded_at", datetime.now(timezone.utc).isoformat())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="offline integrity check; no downloads")
    parser.add_argument("--id", action="append", help="paper ID from papers.json; repeatable")
    parser.add_argument("--record-hashes", action="store_true", help="record missing initial checksums")
    args = parser.parse_args()
    if args.check and args.record_hashes:
        parser.error("--check and --record-hashes are mutually exclusive")
    manifest = json.loads(MANIFEST.read_text())
    known = {p["id"] for p in manifest["papers"]}
    if args.id and set(args.id) - known:
        parser.error("unknown paper IDs: " + ", ".join(sorted(set(args.id) - known)))
    selected = [p for p in manifest["papers"] if not args.id or p["id"] in args.id]
    updates, failures = {}, []
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [(p, pool.submit(fetch, p, check=args.check, record=args.record_hashes)) for p in selected]
        for paper, future in jobs:
            try:
                result = future.result()
                updates[paper["id"]] = result
                print(f"OK {paper['id']} ({result['bytes']:,} bytes)")
            except Exception as error:
                failures.append(paper["id"])
                print(f"FAIL {paper['id']}: {error}")
    if args.record_hashes:
        manifest["papers"] = [updates.get(p["id"], p) for p in manifest["papers"]]
        with tempfile.NamedTemporaryFile(mode="w", dir=ROOT, delete=False, encoding="utf-8") as stream:
            tmp = Path(stream.name)
            try:
                json.dump(manifest, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.close()
                tmp.replace(MANIFEST)
            finally:
                tmp.unlink(missing_ok=True)
    print(f"{len(updates)}/{len(selected)} papers ready")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
