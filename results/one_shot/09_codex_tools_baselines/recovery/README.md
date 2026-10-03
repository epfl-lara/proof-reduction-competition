# Luna recovery: isolate scratch files from shared Lean sources

On 2026-10-03 the Luna/max run stopped during deterministic cleanup of
`time_deriv_time_deriv_electricField_of_isExtrema`. Its model response had already
arrived and passed Lean. The saved cleanup diagnostics show the actual cause:

```text
Relevant sources or Lake configuration are dirty in .../physlib-v4.32.0: ?? candidate.lean
```

That untracked scratch file made 25 simplifier trials unavailable, followed by
a failed reference guard. The controller stopped before finishing two combined
Luna/max cells and before expanding high/medium. The file was absent at recovery;
all 36 benchmark reference identities still matched. The diagnostic establishes
the file collision; the saved records do not identify its writer conclusively.

## Fix

The [additive launcher](../../../../src/run_codex_baselines_isolated.py) retains
Codex tools, exact prompts, model/effort settings, existing generation records,
selection, and the frozen evaluator. New tool processes use Linux Landlock to
keep shared Lean source projects read-only. Scratch files stay in the attempt's
workspace. A small host-side service runs the unchanged correctness checks and
returns the same feedback schema through `check_candidate.py`; it never exposes
candidate scores to the model. Relative candidate paths resolve against that
workspace, even when a tool command uses a source project as its working directory.

This is write isolation for tools, not isolation from reading other experiments.
The existing instructions still govern permitted reads. Runtime/authentication
directories remain writable for Codex. Linux Landlock ABI 3 or newer is required;
the launcher checks support before sending a request and refuses an unrestricted
fallback. The [kernel documentation](https://www.kernel.org/doc/html/v6.10/userspace-api/landlock.html)
describes the inherited filesystem restrictions.

Every new attempt records `execution_envelope.json` with launcher/service hashes,
protected projects and the unchanged request hash. Reports audit this envelope
and count `isolated_calls`, making the execution-policy change visible. Completed
Astra and Luna requests are not rerun. The controller also now clears its stopped
status when resuming; failures include underlying reference diagnostics.

## Evidence and restart

The [receipt](receipt.json) pins all 62 completed cells, all 67 saved generations,
and all existing reference-cache files before recovery. The
[interrupted cleanup](interrupted_cleanup/) remains intact. Only the affected
`08_simp_min` stage was reset, retaining methods 01–07 and the same 32-trial stage
budget. Its infrastructure-affected attempts remain additional recorded work;
they are not a second model proposal. Later methods had not started.

The [offline suite](validation/offline_tests.json) passed **471 tests**, with the
three live RCP tests excluded. Tests exercise blocked creation, overwrite,
truncation, deletion and symlink writes; working source reads; host validity RPC;
and the actual installed Codex CLI against a local mock endpoint with tools and
the exact prompt still enabled. A [real Lean integration check](validation/validity_bridge/validation.json)
also passed through the restricted client without changing cached references.

The [resume record](launch.json) starts the remaining Luna/max work, followed by
the previously authorized high/medium cohorts and the report watcher. Qwen3.8
remains on hold. No new Astra run or reference measurement is scheduled.

The [post-recovery audit](validation/recovered_cleanup.json) now passes all ten
cleanup methods, including six accepted transitions. It also confirms that all
62 earlier terminal cells, all 67 earlier generations, all 53 cached reference
files and the 36-file incident archive remain byte-unchanged.

Luna/max subsequently completed all 30 cells. The
[completion audit](validation/luna_max_complete.json) validates the first full
source-protected model call and all ten cleanup methods for its proof, with all
53 reference-cache files still unchanged. High and medium continue in the
original controller; the new Astra/low cohort has its own controller.
