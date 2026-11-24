#!/usr/bin/env bash
# Default ABI query; explicit namespace option writes owned CPU-test receipts.
set -euo pipefail
submission_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PYTHONPATH="$submission_source/src"
exec "${PYTHON:-python3}" -m proof_eval.providers.host_support "$@"
