#!/usr/bin/env bash
# Sourced by the entry points. Keep toolchains on the shared work volume.
submission_toolchain_env() {
  local mode="${1:?}" work="${2:?}" selected saved pin
  work="$(cd -- "$work" && pwd -P)" || return
  pin="$work/elan-home.txt"
  if [[ -f "$pin" ]]; then
    IFS= read -r saved < "$pin"
    [[ -n "$saved" && -d "$saved" ]] || { echo "Prepared Elan directory is missing; rerun setup.sh." >&2; return 2; }
    if [[ -n "${ELAN_HOME:-}" ]]; then
      selected="$(cd -- "$ELAN_HOME" && pwd -P)" || return
      [[ "$selected" == "$saved" ]] || { echo "ELAN_HOME differs from setup ($saved). Use the same shared toolchains." >&2; return 2; }
    fi
    selected="$saved"
  elif [[ "$mode" == prepare ]]; then
    selected="${ELAN_HOME:-$work/elan}"
    mkdir -p -- "$selected" || return
    selected="$(cd -- "$selected" && pwd -P)" || return
    printf '%s\n' "$selected" > "$pin" || return
  else
    echo "Missing prepared toolchain selection; run setup.sh WORK first." >&2
    return 2
  fi
  export ELAN_HOME="$selected"
  export PATH="$work/elan-cli/bin:$ELAN_HOME/bin:$PATH"
  if ! command -v elan >/dev/null || ! command -v lake >/dev/null || ! command -v lean >/dev/null; then
    if [[ "$mode" != prepare ]]; then
      echo "Missing Elan/Lake launcher; rerun setup.sh WORK before the GPU allocation." >&2
      return 2
    fi
    submission_install_elan "$work" || return
  fi
  # Some shared filesystems expose a different numeric owner in a container.
  # Trust only this setup's enumerated source repositories, not a global wildcard.
  export PROOF_SUBMISSION_GIT_CONFIG="$work/git-safe.config"
  export GIT_CONFIG_GLOBAL="$PROOF_SUBMISSION_GIT_CONFIG"
  if [[ "$mode" == prepare && ! -e "$GIT_CONFIG_GLOBAL" ]]; then
    : > "$GIT_CONFIG_GLOBAL"
  fi
}

submission_install_elan() (
  set -euo pipefail
  local work="${1:?}" temporary
  [[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || { echo "Elan bootstrap requires Linux x86-64." >&2; exit 2; }
  command -v curl >/dev/null || { echo "Install curl before setup.sh." >&2; exit 2; }
  temporary="$(mktemp -d "$work/.elan-bootstrap.XXXXXX")"
  trap 'rm -rf -- "$temporary"' EXIT
  curl --fail --location --retry 3 \
    https://github.com/leanprover/elan/releases/download/v4.2.4/elan-x86_64-unknown-linux-gnu.tar.gz \
    --output "$temporary/elan.tar.gz"
  printf '%s  %s\n' 42b94d4244e8353142c456ec0e4ca6528fd898a6c604d4059f494e706e431f63 "$temporary/elan.tar.gz" | sha256sum --check --status
  tar -xzf "$temporary/elan.tar.gz" -C "$temporary"
  ELAN_HOME="$work/elan-cli" "$temporary/elan-init" -y --no-modify-path --default-toolchain none
)
