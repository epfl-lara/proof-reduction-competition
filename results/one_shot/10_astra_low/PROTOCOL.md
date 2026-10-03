# Astra at low reasoning

The user requested `gpt-6-astra` at **low reasoning** in addition to the completed
max-reasoning baseline. This is a separate **15 problems × 2 seeds = 30 cells**
cohort. The first paired theorem is checked before the remaining cells start;
its outputs are retained. Luna continues independently.

The initial request must be byte-equivalent as parsed JSON to the corresponding
Astra/max request except for `reasoning_effort`. Both arms retain the same
system/user prompts, strategy cards, source context, Codex tools, correctness-only
debugging, three-outer-repair limit, 1,800-second per-call timeout, scoring,
selection threshold, cached references and toolchains. No model output or
measurement from the max arm is supplied to low. The original arm has no
deterministic transformations; the deterministic arm uses D0 and the same
ten-method cleanup of every valid final. There is no pooling between arms.

The [entry point](../../../src/run_astra_low.py) reuses stage-09 proof operations
without modifying that frozen implementation or its 120-cell manifest. A
process-local context adds the low-effort cohort. Source hashes, the parent
manifest, and all 60 max-arm request/result files are pinned. New calls use
the [source-write protection and host checker](../09_codex_tools_baselines/recovery/README.md).
Historical Astra/max calls preceded that operational fix; the low/max comparison
therefore also carries this execution-policy difference. Source reads and
correctness tools remain available in both. Check tool traces separately.

Two Astra/low workers run alongside the two authorized Luna workers, allowing
up to four Codex requests across these cohorts. This does not use RCP credentials
or change the five-request RCP limit. Concurrency and cache effects make wall
times observational, not a controlled model-speed comparison. CLI output-token
and temperature limits remain unavailable; do not claim a 32,768-token cap.

The installed Codex model metadata advertises `low`. A localhost test captures
the actual CLI request and verifies Astra, low effort, exact prompts and enabled
tools before any live request. [Official OpenAI documentation](https://developers.openai.com/api/docs/models/gpt-6-astra)
also lists low reasoning; retrieved 2026-10-03 through OpenAI Docs.

## Run and report

```bash
conda activate af
python src/run_astra_low.py --name CallElimCorrect.substOldPostSubset
python src/run_astra_low.py
python src/run_astra_low.py --report-only
```

The detached [controller](continue_baselines.py) runs the pilot and full cohort,
audits each new terminal snapshot, and stops on infrastructure/audit failure.
It reuses saved outputs and never resamples an interrupted request. Do not launch
a duplicate controller; the run and controller locks also prevent duplicates.

The report saves per-problem scores, validity, usage, tool counts and
`comparison.json` with paired low-minus-max differences. Means and organizer
submission files are produced only when all 15 problems in an arm finish.
The completed max scores are **78.093430% original** and **78.970302% combined**;
the local deterministic baseline is **46.248122%**. All comparisons use the same
fixed original reference measurements.
