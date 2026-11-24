#!/usr/bin/env bash
# CPU/source/model-file preparation, before the model-search allocation.
set -euo pipefail
submission_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
submission_work="${1:?Usage: bash setup.sh /persistent/arena-work}"
for dependency in git taskset rg; do
  command -v "$dependency" >/dev/null || { echo "Missing $dependency; see README.md." >&2; exit 2; }
done
mkdir -p -- "$submission_work"
submission_work="$(cd -- "$submission_work" && pwd -P)"
source "$submission_source/toolchain-env.sh"
submission_toolchain_env prepare "$submission_work"
if [[ ! -x "$submission_work/envs/harness/bin/python" || ! -x "$submission_work/envs/serving/bin/vllm" ]]; then
  bash "$submission_source/install.sh" "$submission_work"
fi
submission_work="$(cd -- "$submission_work" && pwd -P)"
bundle_dir="$(cd -- "$submission_work/bundle" && pwd -P)"
export PYTHONPATH="$bundle_dir/src"

exec "$submission_work/envs/harness/bin/python" -m proof_eval.interfaces.submission setup --bundle "$bundle_dir" --work "$submission_work" "${@:2}"
