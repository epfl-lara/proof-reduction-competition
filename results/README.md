# Experiment results

- [One-shot model/context experiments](one_shot/): fixed incumbents, strategy-card
  and goal/cost-context ablations through RCP, one output per experimental cell.
- [Codex agent baselines](one_shot/09_codex_tools_baselines/README.md): Astra and
  Luna with tools, paired original and deterministic seeds, and validity debugging.

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
