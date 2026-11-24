#!/usr/bin/env bash
# Model search, server shutdown, then default CPU cleanup; use --no-cleanup to skip.
set -euo pipefail
submission_work="${1:?Usage: bash run.sh WORK OUTPUT [--cleanup|--no-cleanup]}"
submission_output="${2:?Usage: bash run.sh WORK OUTPUT [--cleanup|--no-cleanup]}"
submission_work="$(cd -- "$submission_work" && pwd -P)"
bundle_dir="$(cd -- "$submission_work/bundle" && pwd -P)"
source "$bundle_dir/toolchain-env.sh"
submission_toolchain_env prepared "$submission_work"
export PYTHONPATH="$bundle_dir/src"
exec "$submission_work/envs/harness/bin/python" -m proof_eval.interfaces.submission run --bundle "$bundle_dir" --work "$submission_work" --output "$submission_output" "${@:3}"
