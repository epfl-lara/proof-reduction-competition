# Reused cleanup work in the continuation

The continuation starts with **51 copied completed physical jobs** from the original combined run: fifteen controls and 36 proposal-only jobs. Their full configurations, reference identities, ten-stage evidence and ordinary-file hashes were checked before and after copying. The [reuse receipt](validation/cleanup_reuse.json) lists every copied key and its historical counters. All 51 copied jobs were subsequently registered from the real continuation repair cohort with the same sets of logical origins and the same result hashes; arrival order may differ.

Copying made zero model calls, zero Lean calls and zero reference measurements. Loading those completed jobs into the frozen runner did not repeat their optimizer searches. The runner regenerated top-level manifests and all 180 inherited cell selections from the actual continuation repair directory.

The copied jobs contain **19,002.447 historical summed job seconds**, 3,479 attempts, 1,059 analyses, 2,811 uncached candidate checks, 786 cache hits and 25 accepted transitions. Of this, the fifteen controls contain 2,132.508 seconds; the 36 proposal-only jobs contain 16,869.939 seconds. These values are part of total study work once, not newly executed continuation work. New physical jobs have keys outside the reuse receipt. Multiple cell references to any one job do not multiply its cost.

The [launch record](validation/launch.json) pins the unchanged combined runner and exact two-worker command. [execution.log](execution.log) and `run.json` track the live continuation. Its full 225-cell report replaces the partial historical report for study-wide totals; do not add those two reports together. The separately added Qwen3.8 cohort remains separate.
