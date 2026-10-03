# Parallel continuation of the original experiment

This is an operational continuation of the original **225 declared cells**,
not an additional model sample or context experiment. It preserves the initial
proposals, prompts, three-round correctness-only repair limit, temperature,
reasoning settings, 32,768-token cap, toolchains, references, and runtime source.

The original repair scheduler admits one request per model. Once DeepSeek and
Qwen3.6 had completed all their cells, the remaining Qwen3.5 work was serial.
At the planning checkpoint, 37 of its 46 arrived, unfinished cells required
repair; four initial responses were still pending. A separate continuation uses
the already-tested shared admission gate to parallelize the remaining cells.

## Drain and exact reuse

The [one-off controller](launch_continuation.py) waits until the original initial
run is finished, its process has exited, and the original repair's complete
initial-snapshot configuration exists. It then sends **one SIGINT to the repair
Python PID only**. The existing executor's context manager calls
`shutdown(wait=True)`: scheduling stops, while the current cell can finish its
remaining permitted repair rounds and Lean checks. No process-group signal or
second interrupt is sent.

The controller waits for process exit and verifies that every started source
cell has a terminal result and every started repair request has a saved
generation record. An incomplete source cell blocks migration; it must never be
silently skipped and regenerated. The original runtime summary can lag the last
drained worker, so the handoff counts actual terminal files. The controller saves
all copied-cell file hashes and the drain timestamps in `launch.json`.

The original repair and combined folders remain as partial historical evidence.
The new repair runner uses the frozen implementation with `--reuse` pointing to
the drained original repair folder. Its exact per-cell reuse contract excludes
scheduler concurrency but includes the initial request/result, prepared input,
repair budget, timeout, system prompt, and implementation hashes.

## Scheduling and accounting

The new repair scheduler uses `--per-model 4`, behind the unchanged shared gate
also used by the Qwen3.8 extension. The gate conservatively retains one slot for
the now-drained original Qwen3.5 queue because its original folder remains
partial. Consequently **at most four actual new HTTP calls** overlap across
this continuation and the Qwen3.8 generation/repair workers, within the user's
five-request key limit. This deliberately leaves one slot unused and requires no
changes to either frozen scheduler or the gate.

Completed source repair calls are reused without resampling. Reported full-study
repair counts and usage include that historical work once; do not add the old
partial report or pilot totals again. Queue waits prevent interpreting recorded
request elapsed times as model latency rankings.

A read-only health check at approximately 08:59 UTC on 2026-10-03 confirmed
two active continuation HTTP calls, two queued continuation calls, and two
active Qwen3.8 HTTP calls. Intermediate repair responses were still arriving
even though no new cell had yet become terminal. The admission gate is not
FIFO: one queued continuation request had waited about 39 minutes while newer
Qwen3.8 requests acquired released slots. The [admission event log](admission/3e74638ea17d42749d69a83c8ce401fc.jsonl)
records these waits. This is a scheduling limitation, not evidence that the
waiting model was generating slowly or that a worker had died. A future
scheduler should provide fair admission; this run retains its frozen gate.

After the original combined runner drains its registered jobs and reaches
`incomplete_repair_terminal`, its verified completed job trees are copied into
the continuation's combined folder. Job configuration, proof/input/reference
identities, stage hashes and copied bytes must match. Top-level matrix and run
manifests are regenerated from the actual new repair manifest. Selection is
rebuilt from saved evidence. Reused cleanup counters are historical work, not
new continuation compute.

Final full-cohort reports, audits, condition exports, and findings belong in
this continuation's `03_repaired_context_ablation/` and
`04_combined_deterministic/`. The separate Qwen3.8 extension remains a later-added
75-cell cohort. No selection is pooled across models or context arms.

## External interruption and credential resolution

A later parent-turn interruption stopped every worker. The
[recovery receipt](interruption_recovery/README.md) distinguishes four queued,
never-admitted continuation requests from two already-admitted Qwen3.8 calls
with unknown responses. Only the four proven unsent markers were reset. Repair
and cleanup resumed from their existing evidence with unchanged algorithms.
New RCP launches explicitly use repository `.env` credentials; an inherited
different key otherwise takes precedence. Historical worker credentials cannot
be verified after process exit, so latency before/after recovery is not a clean
model comparison.

The additive [report watcher](update_reports.py) refreshes derived repair and
combined reports as terminal cells arrive. Once both matrices complete, it runs
the full saved-evidence audits, repair-budget replay, rejected-proposal cleanup
analysis (with the historical-copy receipt), and figures. It makes no model calls
or Lean measurements. Its commands and exit codes are saved in
`report_history.jsonl`; `reporter_status.json` distinguishes completion from a
reporting failure requiring inspection.
