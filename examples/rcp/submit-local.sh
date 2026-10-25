#!/usr/bin/env bash
# Preview by default. Publish a frozen release to the PVC before explicit submit.
set -euo pipefail

mode=${1:---dry-run}
[[ "$mode" == --dry-run || "$mode" == --submit ]] || {
  echo "Usage: $0 [--dry-run|--submit]" >&2; exit 2;
}
for setting in RCP_PROJECT RCP_IMAGE RCP_JOB RCP_UID RCP_GID RCP_USER RCP_HOME \
  RCP_HARNESS RCP_PROFILE RCP_OUTPUT RCP_PLUGIN RCP_BASE RCP_DATASET \
  RCP_REFERENCES RCP_ENVIRONMENTS RCP_CACHE; do
  [[ -n ${!setting:-} ]] || { echo "Set $setting explicitly" >&2; exit 2; }
done

bootstrap='import sys; sys.path.insert(0, sys.argv.pop(1)); from proof_eval.interfaces.local import main; raise SystemExit(main())'
command=(runai submit --name "$RCP_JOB" --project "$RCP_PROJECT"
  --image "$RCP_IMAGE" --image-pull-policy Always --gpu 4
  --cpu "${RCP_CPU:-64}" --memory "${RCP_MEMORY:-512G}"
  --node-pools "${RCP_GPU_POOL:-a100}" --large-shm
  --run-as-uid "$RCP_UID" --run-as-gid "$RCP_GID"
  --create-home-dir=false --environment "USER=$RCP_USER"
  --environment "HOME=$RCP_HOME" --environment PYTHONNOUSERSITE=1
  --environment "PROOF_SIGNAL_SCOPE_BINARY=${PROOF_SIGNAL_SCOPE_BINARY:?Set the validated broker path}"
  --existing-pvc "claimname=${RCP_SCRATCH_PVC:-lara-scratch},path=/scratch"
  --existing-pvc "claimname=${RCP_HOME_PVC:-home},path=$RCP_HOME"
  --working-dir "$RCP_HOME" --backoff-limit 0 --command --
  "${RCP_ENTRYPOINT:-/opt/rcp/bin/rcp-entrypoint}" python3 -c "$bootstrap"
  "$RCP_HARNESS/src" run --profile "$RCP_PROFILE" --output "$RCP_OUTPUT"
  --plugin "$RCP_PLUGIN" -- --base "$RCP_BASE" --dataset "$RCP_DATASET"
  --references "$RCP_REFERENCES" --environments "$RCP_ENVIRONMENTS" --cache "$RCP_CACHE")

if [[ "$mode" == --dry-run ]]; then
  printf '%q ' "${command[@]}"; printf '\n'
  exit 0
fi

: "${RCP_LOCAL_RECEIPTS:?Set a local receipt directory outside the source release}"
mkdir -p "$RCP_LOCAL_RECEIPTS"
intent="$RCP_LOCAL_RECEIPTS/$RCP_JOB.intent.json"
python3 - "$intent" "${command[@]}" <<'PY'
import json, os, sys, time
with open(sys.argv[1], "x") as stream:
    json.dump({"at_epoch": time.time(), "command": sys.argv[2:],
               "status": "dispatch_once", "unknown_submission_must_be_inspected": True}, stream)
    stream.flush()
    os.fsync(stream.fileno())
PY
python3 - "$RCP_LOCAL_RECEIPTS/$RCP_JOB" "${command[@]}" <<'PY'
import json, subprocess, sys, time
from pathlib import Path
prefix = Path(sys.argv[1])
with Path(str(prefix) + ".response.log").open("xb") as log:
    try:
        result = subprocess.run(sys.argv[2:], stdout=log, stderr=subprocess.STDOUT, timeout=45)
        receipt = {"at_epoch": time.time(), "returncode": result.returncode,
                   "status": "acknowledged_unbound" if result.returncode == 0 else "submission_failed",
                   "workload_pod_identity_verified": False}
        code = result.returncode
    except subprocess.TimeoutExpired:
        receipt = {"at_epoch": time.time(), "status": "submission_unknown",
                   "repeat": False, "instruction": "Inspect this exact job before any further action"}
        code = 124
Path(str(prefix) + ".submission.json").write_text(json.dumps(receipt, indent=2) + "\n")
raise SystemExit(code)
PY
cat "$RCP_LOCAL_RECEIPTS/$RCP_JOB.response.log"
# Resolve actual workload/pod UIDs and inspect logs; an acknowledgment is not a run result.
