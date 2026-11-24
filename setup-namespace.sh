#!/usr/bin/env bash
# Prepare the same explicit protected backend later selected by run-namespace.sh.
set -euo pipefail
submission_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PROOF_EVAL_FILESYSTEM_BACKEND=readonly-mounts
exec bash "$submission_source/setup.sh" "$@"
