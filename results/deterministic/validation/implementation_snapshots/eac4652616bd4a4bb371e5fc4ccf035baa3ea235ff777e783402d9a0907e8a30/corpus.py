"""Thin CLI for model-free extraction of RSI/RL refactoring tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from proof_eval.benchmark.corpus import CorpusConfig, build_corpus
from proof_eval.benchmark.harvest import SourceSnapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--exclude-dataset", type=Path, default=Path("data/benchmark_data_warmup.jsonl")
    )
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--minimum-count", type=int, default=1000)
    parser.add_argument("--min-tokens", type=int, default=222)
    parser.add_argument("--min-lines", type=int, default=47)
    parser.add_argument("--unmatched-lengths", action="store_true")
    args = parser.parse_args(argv)
    snapshots = tuple(
        SourceSnapshot(
            source=item["source"],
            url=item["url"],
            revision=item["revision"],
            version=item["version"],
            project=Path(item["project"]).resolve(),
            roots=tuple(item["roots"]),
            grammar_project=Path(item["grammar_project"]).resolve(),
            grammar_imports=tuple(item["grammar_imports"]),
            file_limit=item.get("file_limit"),
        )
        for item in json.loads(args.sources.read_text())
    )
    report = build_corpus(
        CorpusConfig(
            snapshots,
            args.output.resolve(),
            args.exclude_dataset.resolve(),
            limit=args.limit,
            minimum_count=args.minimum_count,
            min_tokens=args.min_tokens,
            min_lines=args.min_lines,
            match_benchmark=not args.unmatched_lengths,
        )
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "count": report["count"],
                "splits": {k: v["count"] for k, v in report["splits"].items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
