"""Internal, isolated theorem worker used by the batch deadline supervisor."""

from __future__ import annotations

import sys
from pathlib import Path

from proof_eval.evidence.io import read
from proof_eval.harness.search import run_cell
from proof_eval.providers.processes import enable_subreaper
from proof_eval.verification.api import Evaluator


def main(argv: list[str] | None = None) -> int:
    request = read((argv or sys.argv[1:])[0])
    enable_subreaper()
    run_cell(
        Path(request["output"]),
        request["config"],
        request["pack"],
        request["model"],
        request["effort"],
        Evaluator(**request["evaluator"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
