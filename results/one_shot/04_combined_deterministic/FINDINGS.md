# Combined cleanup: partial historical findings

This original run ended deliberately at **180/225 cells**, after the serial repair worker drained and the remaining work moved to the [parallel continuation](../06_parallel_continuation/PROTOCOL.md). All **15 controls and 51 registered cleanup jobs** completed. This folder is historical evidence; final 225-cell findings belong in [continuation stage04](../06_parallel_continuation/04_combined_deterministic/). The continuation reuses these completed jobs without another model sample or cleanup search.

The saved-evidence [partial audit](validation/combined_evidence_audit.json) passed 180 cells, 15 controls, 51 jobs, all 510 method stages, 36 unchanged cached reference identities, and ten full-condition exports. It made no Lean or model calls. It is not a complete-cohort audit.

DeepSeek and Qwen3.6 each completed all five conditions (15 declarations per condition). Qwen3.5 completed six declarations in each condition; its five full-condition means and exports are withheld. All saved selected proofs pass every required Lean version.

D0 is the original deterministic incumbent; D1 is the same incumbent after one additional fixed cleanup pass; L is the stage03 selected proof; F is the first all-version-valid model/repair final, even when rejected by the stage03 score rule. H selects the highest eligible score among D1, L, D0, F and cleanup(F), with ties preferring D1. New F branches require more than 0.05 points over D0; D1 and L remain eligible. Scores below are local competition-objective percentages with fixed reference denominators, not organizer-grader results.

All fifteen D1 controls remained byte-for-byte unchanged. D0 = D1 = **46.248122184100176%** combined score (12.187241254540428% length reduction, 26.5571252977601% heartbeat reduction, 100% compatibility). Thus extra deterministic control search alone added zero score in this bounded pass.

| Model | Context | D0 | D1 | L | H | H−D1 (pp) | H−L (pp) |
|---|---|---:|---:|---:|---:|---:|---:|
| DeepSeek V4.1 Flash | plain | 46.248122184 | 46.248122184 | 46.248122184 | 46.248122184 | +0.000000000 | +0.000000000 |
| DeepSeek V4.1 Flash | cards | 46.248122184 | 46.248122184 | 48.470100470 | 48.656863762 | +2.408741578 | +0.186763292 |
| DeepSeek V4.1 Flash | goals | 46.248122184 | 46.248122184 | 47.266594455 | 47.379728062 | +1.131605878 | +0.113133607 |
| DeepSeek V4.1 Flash | cards_goals | 46.248122184 | 46.248122184 | 46.433971793 | 46.433971793 | +0.185849609 | +0.000000000 |
| DeepSeek V4.1 Flash | cards_goals_costs | 46.248122184 | 46.248122184 | 48.124185434 | 48.124185434 | +1.876063250 | +0.000000000 |
| Qwen3.6 35B A3B | plain | 46.248122184 | 46.248122184 | 46.396101283 | 46.396101283 | +0.147979099 | +0.000000000 |
| Qwen3.6 35B A3B | cards | 46.248122184 | 46.248122184 | 46.248122184 | 46.248122184 | +0.000000000 | +0.000000000 |
| Qwen3.6 35B A3B | goals | 46.248122184 | 46.248122184 | 46.348342052 | 46.348342052 | +0.100219868 | +0.000000000 |
| Qwen3.6 35B A3B | cards_goals | 46.248122184 | 46.248122184 | 46.248122184 | 46.248122184 | +0.000000000 | +0.000000000 |
| Qwen3.6 35B A3B | cards_goals_costs | 46.248122184 | 46.248122184 | 46.248122184 | 46.248122184 | +0.000000000 | +0.000000000 |

These are paired 15-declaration condition comparisons. DeepSeek/cards has the highest observed complete-condition score here, improving two declarations over D1 and two over L. DeepSeek/goals also improves two over D1 and two over L. Qwen3.6 receives no additional gain from the post-model cleanup in any condition. Full precision and component metrics are in [report.json](report.json); no proof is selected across arms or models.

For a concrete improvement, DeepSeek/cards on `putnam_1995_a3` moves from D0 **55.16063165811742** to L **79.79884454768376** to H **81.91061481965964**. Its cleanup adds **2.11177027197588 points** over the already accepted model proof. The physical job used 84 attempts, 24 analyses, 94 uncached candidate checks, five cache hits and three accepted transitions (474.295 recorded seconds).

Adding context is not uniformly beneficial in these single draws. DeepSeek costs versus cards+goals is +1.690213641 points with one positive and one negative paired declaration; Qwen3.6 costs versus cards+goals is zero on all fifteen. DeepSeek cards+goals versus cards is lower, despite both using the same bank. [Paired contrasts](pairwise.csv) retain the condition denominators and counts; this small development set does not establish a universal prompt ranking.

Across the 180 recorded cells, 69 have an all-version-valid F; 29 return the incumbent unchanged. There are 27 changed, valid, stage03-score-rejected proposal cells. **None was rescued above D0 or D1 by this cleanup.** These are logical cell counts, not unique physical jobs. Seven recorded cells improve over L, including three from the incomplete Qwen3.5 conditions; those partial observations are not presented as full-cohort means.

| Physical cleanup work | Jobs | Attempts | Analyses | Uncached candidate checks | Cache hits | Accepted transitions | Recorded seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Matched controls | 15 | 961 | 305 | 277 | 683 | 0 | 2132.508 |
| Proposal-only jobs | 36 | 2518 | 754 | 2534 | 103 | 25 | 16869.939 |

The 15 control origins plus 69 valid proposal origins total 84 logical cleanup uses, deduplicated to 51 physical jobs. Each control is reused by many cells; those uses are not additional searches. Total saved physical work is 3,479 attempts, 1,059 analyses, 2,811 uncached candidate checks, 786 cache hits and 25 accepted transitions, with 19,002.447 summed job seconds. Initial/final whole-proof validation is excluded from optimizer counters and uses the existing evaluator cache. Summed job durations overlap and are not wall-clock runtime.

Both branches use the fixed ordered portfolio `lint`, `simp`, `wrappers`, `facts`, `reuse`, `menu`, `search`, `simp_min`, `arith_min`, `rw_min`, with three rounds, 32 trials, six sites and a 0.05-point per-step gain threshold; there is one portfolio pass. H can consume control search plus a separate proposal search, so this is not equal total compute against D1. The all-version acceptance gate prevents compatibility regressions. No reference was remeasured and no model request was made by this stage.

The continuation copies all 51 jobs with audited byte hashes. Its historical counters must not be added again to this partial report. Subsequent analyses should use the continuation report once and separate copied historical work from new work. Each arm remains one initial proposal plus at most three correctness-only repairs; there is no performance-directed regeneration.
