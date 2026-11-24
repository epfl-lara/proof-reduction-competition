#!/usr/bin/env bash
# Explicit protected alternative for hosts without Landlock ABI 3.
set -euo pipefail
submission_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROOF_EVAL_FILESYSTEM_BACKEND=readonly-mounts
exec bash "$submission_source/run.sh" "$@"
