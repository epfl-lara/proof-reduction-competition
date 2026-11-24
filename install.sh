#!/usr/bin/env bash
# Dependencies only; no model loading, Lean compilation or proof search.
set -euo pipefail
submission_source="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
submission_work="${1:?Usage: bash install.sh /persistent/arena-work}"
bootstrap_python="${SUBMISSION_PYTHON:-python3.12}"
"$bootstrap_python" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Use Python 3.12"'
"$bootstrap_python" -c 'import platform, sys; assert sys.platform == "linux" and platform.machine() == "x86_64", "This release requires Linux x86-64"'
"$bootstrap_python" -c 'import platform; name, version = platform.libc_ver(); assert name == "glibc" and tuple(map(int, version.split(".")[:2])) >= (2, 39), "The supplied native runtime requires glibc 2.39 or newer; use the Ubuntu 24.04 container in docs/IMAGE.md"'
export PYTHONPATH="$submission_source/src${PYTHONPATH:+:$PYTHONPATH}"
bundle_dir="$("$bootstrap_python" -m proof_eval.benchmark.submission_workspace --source "$submission_source" --work "$submission_work")"
mkdir -p -- "$submission_work"
submission_work="$(cd -- "$submission_work" && pwd -P)"
source "$bundle_dir/toolchain-env.sh"
submission_toolchain_env prepare "$submission_work"
export PYTHONPATH="$bundle_dir/src"
"$bootstrap_python" -c 'import sys; from pathlib import Path; from proof_eval.benchmark.submission_assets import native; native(Path(sys.argv[1]))' "$bundle_dir"
PROOF_SIGNAL_SCOPE_BINARY="$bundle_dir/bin/signal-scope" "$bootstrap_python" -c 'from proof_eval.providers.signal_scope import configured_identity; configured_identity()'
for name in harness serving; do
  if [[ ! -x "$submission_work/envs/$name/bin/python" ]]; then
    "$bootstrap_python" -m venv "$submission_work/envs/$name"
  fi
done
harness_python="$submission_work/envs/harness/bin/python"
serving_python="$submission_work/envs/serving/bin/python"
"$harness_python" -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r "$bundle_dir/requirements/harness.txt"
"$harness_python" -m pip install --no-deps -e "$bundle_dir"
"$serving_python" -m pip install --extra-index-url https://download.pytorch.org/whl/cu129 -r "$bundle_dir/requirements/serving.txt"
"$serving_python" -m pip install --no-deps -e "$bundle_dir/integrations/vllm_ampere"
"$serving_python" -c 'from importlib.metadata import version; expected={"vllm":"0.31.0+cu129","torch":"2.13.0+cu129","transformers":"5.17.0"}; assert all(version(k)==v for k,v in expected.items()), "Serving versions differ from the release"'
for name in harness serving; do
  "$submission_work/envs/$name/bin/python" -m pip check
  "$submission_work/envs/$name/bin/python" -m pip freeze --all > "$submission_work/$name-packages.txt"
done
"$bundle_dir/bin/lemex" --version
echo 'Dependencies installed. Next: bash setup.sh WORK. No model or Lean search has run.'
