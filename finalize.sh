#!/usr/bin/env bash
# Repair delivery from a finished saved model run; no model or search replay.
set -euo pipefail
submission_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
submission_work="${1:?Usage: bash finalize.sh WORK PARENT_OUTPUT NEW_OUTPUT [--no-cleanup]}"
parent_output="${2:?Usage: bash finalize.sh WORK PARENT_OUTPUT NEW_OUTPUT [--no-cleanup]}"
submission_output="${3:?Usage: bash finalize.sh WORK PARENT_OUTPUT NEW_OUTPUT [--no-cleanup]}"
cleanup_mode="${4:---cleanup}"
[[ "$cleanup_mode" == --cleanup || "$cleanup_mode" == --no-cleanup ]] || { echo 'Use --cleanup or --no-cleanup' >&2; exit 2; }
submission_work="$(cd -- "$submission_work" && pwd -P)"
producer_bundle="$submission_work/bundle"
source "$submission_source/toolchain-env.sh"
submission_toolchain_env prepared "$submission_work"
export PYTHONPATH="$submission_source/src"
"$submission_work/envs/harness/bin/python" -m proof_eval.harness.submission_finalize \
  --producer-bundle "$producer_bundle" --work "$submission_work" \
  --parent "$parent_output" --output "$submission_output"
if [[ "$cleanup_mode" == --cleanup ]]; then
  exec bash "$producer_bundle/cleanup.sh" "$submission_work" "$submission_output"
fi
