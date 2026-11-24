#!/usr/bin/env bash
# GPU model search only. CPU setup must already be complete.
set -euo pipefail
submission_work="${1:?Usage: bash search.sh WORK OUTPUT}"
submission_output="${2:?Usage: bash search.sh WORK OUTPUT}"
submission_work="$(cd -- "$submission_work" && pwd -P)"
bundle_dir="$(cd -- "$submission_work/bundle" && pwd -P)"
source "$bundle_dir/toolchain-env.sh"
submission_toolchain_env prepared "$submission_work"
export PYTHONPATH="$bundle_dir/src"
exec "$submission_work/envs/harness/bin/python" -m proof_eval.interfaces.submission search --bundle "$bundle_dir" --work "$submission_work" --output "$submission_output" "${@:3}"
