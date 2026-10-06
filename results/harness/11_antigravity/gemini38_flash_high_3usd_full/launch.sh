#!/usr/bin/env bash
set -euo pipefail
cd /localhome/milikic/proof-reduction-competition/.proof-eval/runtimes/gemini38_flash_high_3usd_full_20261006T172551Z
export PYTHONPATH=/localhome/milikic/proof-reduction-competition/.proof-eval/runtimes/gemini38_flash_high_3usd_full_20261006T172551Z/src
export PYTHONDONTWRITEBYTECODE=1
export PATH=/localhome/milikic/proof-reduction-competition/.proof-eval/runtimes/gemini38_flash_high_3usd_full_20261006T172551Z/bin:/localhome/milikic/miniconda3/envs/af/bin:"$PATH"
run_status=0
/localhome/milikic/miniconda3/envs/af/bin/python -m proof_eval.harness.cli run --provider agy --condition gemini-3.8-flash:high --track-cost --budget-usd 3 --problem-timeout-seconds 3420 --workers 2 --pilot --carry-budgets-from /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd --output /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd_full > /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd_full/runner.log 2>&1 || run_status=$?
audit_status=0
/localhome/milikic/miniconda3/envs/af/bin/python -m proof_eval.harness.cli audit --output /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd_full >> /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd_full/runner.log 2>&1 || audit_status=$?
if (( run_status == 0 )); then run_status=$audit_status; fi
printf '%s\n' "$run_status" > /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd_full/runner.exit
exit "$run_status"
