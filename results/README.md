# Experiment results

- [October 22 Sol cleanup-placement comparison](summary/20261022_sol_cleanup_placement/README.md):
  the complete original-start, end-only cleanup rerun scored **89.6591%** in
  **3h 17m**, versus **89.3761%** in **3h 59m** with cleanup before and after.
  Both passed all 36 required final checks. Includes 30 final proofs, per-theorem
  scores, saved audits, source hashes and a separate record of the interrupted run.
- [October 21 consolidated results](summary/20261021_deterministic_workflows/manifest.json):
  8 Sol and 5 Qwen conditions, 24 capped and 5 extended deterministic policies,
  with 630 selected proofs/evaluations, source hashes and saved audits. The
  [model table](summary/20261021_deterministic_workflows/model_conditions.csv) and
  [deterministic table](summary/20261021_deterministic_workflows/deterministic_conditions.csv)
  distinguish complete scores, timing, incomplete usage and scheduling estimates.
  The selected default is one sweep before and after a separate model batch,
  history off; the completed combined-workflow comparison is linked above. Full raw
  session traces are preserved in a private external archive, not included in
  the compact publication bundle or represented as locally rerunnable audits.
- [One-shot model/context experiments](one_shot/): fixed incumbents, strategy-card
  and goal/cost-context ablations through RCP, one output per experimental cell.
- [Codex agent baselines](one_shot/09_codex_tools_baselines/README.md): Astra and
  Luna with tools, paired original and deterministic seeds, and validity debugging.
- [Structural context and score-feedback search](harness/README.md): revised
  prompts and source/goal tools, followed by continued optimization with the
  measured competition tuple, deterministic cleanup and model-cost comparisons.
- [Sol package-refactor validation](harness/06_refactor_regression/PROTOCOL.md):
  a fresh Sol 6.1/max replicate through the maintained APIs, with unchanged
  prompts, cached references and scoring.

- [Deterministic optimization](deterministic/): the complete warm-up portfolio,
  repeated sweeps, candidate proofs, rejected trials, audits and findings.
- [Arena result](deterministic/arena/README.md): user-provided leaderboard evidence
  showing **46.34%** combined score on October 2, 2026.
- [Running the harness on a new batch](../docs/DETERMINISTIC_BATCH.md): explicit
  inputs, setup, cached references, resumable execution and submission export.

Future experiment families should use their own subdirectory. Historical
deterministic evidence was moved from this directory without changing proof or
measurement records; the [relocation manifest](deterministic/relocation_manifest.json)
records every preserved non-Markdown file's original path and SHA256.
