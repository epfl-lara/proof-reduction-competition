#!/usr/bin/env bash
set -euo pipefail
cd /localhome/milikic/proof-reduction-competition/.proof-eval/runtimes/gemini38_flash_high_3usd_20261006T165450Z
export PYTHONPATH=/localhome/milikic/proof-reduction-competition/.proof-eval/runtimes/gemini38_flash_high_3usd_20261006T165450Z/src
export PYTHONDONTWRITEBYTECODE=1
export PATH=/localhome/milikic/proof-reduction-competition/.proof-eval/runtimes/gemini38_flash_high_3usd_20261006T165450Z/bin:/localhome/milikic/miniconda3/envs/af/bin:"$PATH"
exec /localhome/milikic/miniconda3/envs/af/bin/python -m proof_eval.harness.cli run --provider agy --condition gemini-3.8-flash:high --track-cost --budget-usd 3 --problem-timeout-seconds 3420 --workers 3 --pilot --output /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd > /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd/runner.log 2>&1
