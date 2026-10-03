# Later-added Qwen3.8 extension

**Stopped at the user's request:** [final partial-cohort status](STOPPED.md).
The historical launch/preparation narrative below is retained as provenance.

**Launch update, 2026-10-03 UTC:** preparation-only statements below describe
the earlier preparation snapshot. After the original initial run finished all
225 cells, the gated extension initial runner started at **05:50:52** (wrapper
PID 425517; root launch session 92492). The authorized gated repair watcher
started at **05:52:58** (wrapper PID 433780; session 78234), after checking the
actual 75-cell index existed and no extension repair process or prior artifacts
existed. It uses exactly the command below with `--per-model 2`, three maximum
repair rounds, timeout 1800, and poll interval 5. Its actual
[matrix manifest](03_repaired_context_ablation/matrix_config.json),
[run state](03_repaired_context_ablation/run.json), and
[execution log](03_repaired_context_ablation/execution.log) are saved. At this
launch snapshot it was waiting for initial results; later progress is recorded
in the linked run states. The [admission evidence](admission/) records both
wrappers. No initial request was duplicated or restarted.

Prepared on 2026-10-03 at the user's request. This is a separate **75-cell**
cohort: `Qwen/Qwen3.8-27B` × the same fifteen warm-up declarations × the same five
context arms (`plain`, `cards`, `goals`, `cards_goals`, `cards_goals_costs`). It is
not part of the original 225-cell, three-model experiment. Its later start and
addition after observing partial earlier results must remain explicit in reports.
No best-of-model or best-of-arm proof pooling is introduced.

## Prepared inputs and generation contract

All fifteen input-pack files were copied byte-for-byte from
[the original one-shot inputs](../01_context_ablation/inputs/). This preserves
the original deterministic incumbents, cached reference identities, preceding
source context, strategy-card inputs, selected goal sites, and measured original
tactic costs. Preparation reused those files; it did not re-extract context or
measure references.

The frozen `run_one_shot.py --prepare-only` command completed successfully. All
75 newly constructed message lists exactly matched the corresponding original
theorem/arm messages. Compared with the original Qwen3.5 request payloads, only
`model` and the model-specific `reasoning_payload` differ. The
[preparation evidence](validation/preparation.json) records input/config hashes,
all 75 request comparisons, and the reuse checks below.

The requested settings remain temperature **0.3**, reasoning enabled, effort
**high**, a **32,768-token total output cap**, and a **1,800-second timeout**.
The existing client maps Qwen3.8's requested `high` to provider payload **`xhigh`**
in both `reasoning_effort` and `chat_template_kwargs.reasoning_effort`. This
mapping already existed in the frozen client. It must not be described as
identical provider effort semantics across models. There is no added
`thinking_token_budget` field or changed total cap in this extension.

At preparation, **zero model calls** had been made. Preparation did not probe
model availability: `--prepare-only` returns before the client's model-list request.
The user clarified a limit of **five requests total across the API key**, not
five distinct models. Generation waited for completion of the original
initial-generation pool; the execution record below records the later launch.

The already-running original initial and repair pools had independent limits
before this clarification. Their frozen runners have no cooperative mechanism
for resizing or globally coordinating already-queued requests. To preserve the
existing run without interrupting or duplicating requests, let the original
initial-generation pool drain before launching this extension. Require its
`run.json` status to be `finished` and confirm the legacy generation process is
gone before starting any extension generation.

After that drain, both new model runners use the separate
[`run_with_rcp_limit.py`](../../../src/run_with_rcp_limit.py) admission wrapper.
They share **five cross-process flock slots**, reserving one slot for each
original repair model with any unresolved declared cell. The original repair
runner remains unchanged and admits at most one request per model. Thus, with
all three original models unfinished, at most two new HTTP calls can run; freed
legacy reservations increase the new allowance while the combined bound remains
five. Reservations decrease only after that model's entire original terminal
cohort is verified. Missing or changed evidence fails closed.

This shared gate supersedes the earlier proposed static allocation of one new
initial and one new repair request. Both new workers may use `--per-model 2`;
the common gate limits their actual overlap. It covers both `list_models` and
`create_chat_completion`, including the startup model-list request. All other
new RCP calls using the key must use the same gate; no untracked probes may run
alongside it. Deterministic cleanup makes no model calls. This bound applies
after the old initial pool drains; the earlier independent pools did not enforce
this newly clarified global limit.

The wrapper changes admission only: it forwards unchanged positional/keyword
arguments, responses, and transport exceptions. It edits no frozen runtime file
and does not inject a new model parameter. Its configuration, source hash, wrapped
CLI, and queue/admission/release events are saved separately under `admission/`.
Event logs contain no credentials or request content. Slot locks release when
the owning process closes them or dies. Bounded polling is at most one second;
randomized slot selection and polling reduce contention but do not promise strict
FIFO fairness. Core request elapsed times include admission waiting and must not
be interpreted as model latency rankings.

## Planned stages

1. `01_context_ablation/`: one independent proposal for each declared cell,
   using the copied original incumbent. No model tool calls or candidate feedback
   are part of this first request.
2. `03_repaired_context_ablation/`: reuse each proposal and allow at most three
   correctness-only repairs, stopping at the first proof passing every required
   Lean version. Empty initial outputs are not regenerated. Scores never trigger
   another repair request.
3. `04_combined_deterministic/`: apply the existing fixed ten-method cleanup to
   each all-version-valid repaired final, including score-rejected proposals.
   Use the same all-version gate and selection policy as the original combined
   experiment. The method budgets remain three rounds, 32 trials and six sites,
   with a 0.05-point improvement margin and no portfolio repeat sweep.

These stages retain separate manifests and results from the original experiment.
Every complete condition contains all fifteen declarations. Partial cohorts must
not receive a full-condition mean or submission export.

## Reusing the completed deterministic controls

All fifteen original stage04 control jobs are complete, unchanged, and have
exactly matching anticipated extension job configurations: theorem, raw proof
hash, required versions, ordered methods, budget, input fingerprint, environment
contexts, reference fingerprints, and runtime code hashes. The job provenance
does not include the experiment directory or model name. The validated copy set
is approximately **21.1 MB**, excluding lock files.

All **fifteen controls were copied and audited** on 2026-10-03, after the extension
repair runner wrote its actual `matrix_config.json`.
[reuse_controls.py](reuse_controls.py) invoked the real combined preparation code
without executing cleanup. It
compares each source job's `job_config.json` with that matrix's
`cleanup_provenance(...)` and full expected job configuration. It audits matching
completed jobs and copies them into `04_combined_deterministic/jobs/<job_key>/`,
preserving file bytes and verifying saved stage/result hashes. It uses ordinary
copies, excludes locks, rejects symlinks, and never overwrites an existing
destination. Source-to-destination hashes and historical counters are saved in
`04_combined_deterministic/validation/control_reuse.json`. The helper requires
the real repair manifest; it does not fabricate one.

This avoids another deterministic control search. Copied trial/check/cache/time
counters describe **historical original-control work**, not new work spent on
this extension. The unchanged reporter counts saved job evidence, so extension
interpretation must separate these reused controls from newly executed proposal
jobs. A returned original incumbent may share one of these copied control jobs.

## Ready commands

Run from the repository root in the `af` environment, after the original initial
generation pool has finished and its process has exited. Use the same gate
directory for both new runners. Do not change prompts, inputs, budgets, or runtime
files when resuming. These commands record the launched configuration; inspect
the saved run state and live processes before any resume to avoid duplicates.

```bash
admission_args=(
  --legacy-initial results/one_shot/01_context_ablation
  --legacy-repair results/one_shot/03_repaired_context_ablation
  --gate .proof-eval/rcp-admission
  --log-directory results/one_shot/05_qwen38_extension/admission
)

python src/run_with_rcp_limit.py "${admission_args[@]}" -- src/run_one_shot.py \
  --output results/one_shot/05_qwen38_extension/01_context_ablation \
  --models Qwen/Qwen3.8-27B \
  --arms plain cards goals cards_goals cards_goals_costs \
  --max-tokens 32768 --timeout 1800 --per-model 2

python src/run_with_rcp_limit.py "${admission_args[@]}" -- src/run_repair_matrix.py \
  --input results/one_shot/05_qwen38_extension/01_context_ablation \
  --output results/one_shot/05_qwen38_extension/03_repaired_context_ablation \
  --per-model 2 --max-rounds 3 --timeout 1800 --poll-seconds 5

# After the actual repair manifest exists; verify and copy historical controls:
python results/one_shot/05_qwen38_extension/reuse_controls.py

# The helper pins the same workers/watch/poll settings used here:
python src/run_combined_matrix.py \
  --input results/one_shot/05_qwen38_extension/03_repaired_context_ablation \
  --output results/one_shot/05_qwen38_extension/04_combined_deterministic \
  --workers 2 --watch --poll-seconds 5
```

The one-shot runner writes `cell_index.json` when generation starts, not during
`--prepare-only`. Start the repair watcher only after that index exists, and the
combined watcher only after the repair matrix manifest exists. Individual
per-model limits are not a shared global semaphore; the admission wrapper and
its conservative legacy reservations enforce the total HTTP request bound.

The separate [offline admission auditor](../../../src/audit_rcp_admission.py)
checks the supplied stage05 and stage06 invocation configs, source pins, released
legacy-model evidence, ticket lifecycles, shared slot intervals and the observed
HTTP count plus legacy reservations. The
[saved snapshot audit](validation/admission_audit_snapshot.json) passed with a
maximum observed conservative bound of five; its pending tickets remain explicit.
[Focused offline test evidence](validation/admission_audit_tests.json) covers
29 tests, including optimized-Python validation and timestamp ambiguities.

```bash
python src/audit_rcp_admission.py \
  --log-directory results/one_shot/05_qwen38_extension/admission \
  --log-directory results/one_shot/06_parallel_continuation/admission \
  --gate .proof-eval/rcp-admission \
  --output results/one_shot/05_qwen38_extension/validation/admission_audit_snapshot.json
```

After every supplied wrapped run is terminal and all tickets are closed, use
the same command with `--complete` and write `admission_audit_complete.json`.
The audit makes no model, Lean, network or process-control calls. Equal-time
endpoints, clock discrepancies and ambiguous live snapshot tails are reported
as inconclusive rather than assuming that releases preceded admissions. This
evidence covers the supplied gated invocations only: it does not retroactively
bound earlier ungated runs or exclude other clients using the key. Invocation
configs record shared semantics, not the lock directory/inode itself; the
recorded launcher commands establish use of the same gate path separately.

## Execution record

The original initial run finished all 225 cells before the gated extension
generation and repair workers started. The frozen control-copy helper completed
successfully with **zero model calls, zero Lean calls, and zero reference
measurements**. Its [reuse receipt](04_combined_deterministic/validation/control_reuse.json)
records all copied file hashes and historical counters.

The combined watcher started at **2026-10-03 05:54:20 UTC** with two workers and
the exact configuration above. It loaded all fifteen completed control jobs and
waited for new repair results. The [launch record](04_combined_deterministic/validation/launch.json)
and [execution log](04_combined_deterministic/execution.log) preserve the command
and runner provenance. Copied controls are historical evidence; their recorded
2,132.508 seconds are not newly spent extension cleanup time.
