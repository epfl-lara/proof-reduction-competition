# Full-matrix correctness-only repair

**complete**: 225/225 cells complete; 225/225 initial proposals available.

The full model × context × theorem cohort was declared before repair outcomes. Each cell reuses its original proposal and receives at most three correctness-only repair requests. Empty original responses are not regenerated. The first proof passing every required version stops repair, irrespective of score.

Additional repair concurrency is capped at 4 per model. 180 completed pilot cells were reused without new sampling. The original one-shot run remains unchanged.

Cached references and pinned inputs are checked before each repair. Missing initial results remain pending while the base run is running; a terminal partial base run leaves this matrix resumable and incomplete.

Final score comparisons are reported separately in [README.md](README.md). This progress summary is not a full-cohort score. See `matrix_config.json` for the complete declared cohort and `arrivals.json` for received initial-result hashes.
