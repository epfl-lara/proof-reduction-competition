# Stage 02: explicit simplifier lemma sets

**Eight of 15 proofs improved over stage 01. Combined score increased by another
3.442 percentage points, to 37.100%. All 36 version checks pass.**

| Full warm-up mean | After stage 01 | After stage 02 | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 0.978% | -1.716% | -2.694 |
| Heartbeat reduction | -0.006% | 13.015% | +13.020 |
| Compatibility | 100.000% | 100.000% | 0.000 |
| Combined | 33.658% | **37.100%** | **+3.442** |

Across both stages, the gain over the actual unchanged control is **3.770 pp**.
This is an average over all 15 warm-up problems, with no omitted rows. It is a
local score proxy, not an arena worker result.

## The useful tradeoff

| Improved problem | Tokens before → after this stage | Final heartbeat reduction vs reference | Combined gain vs stage 01 (pp) |
| --- | ---: | ---: | ---: |
| `putnam_1964_a4` | 1,665 → 1,776 | 70.205% | +21.304 |
| Electromagnetic potential time derivative | 1,372 → 1,424 | 36.679% | +10.963 |
| `putnam_1964_b2` | 1,623 → 1,848 | 32.874% | +6.688 |
| `putnam_1995_a3` | 4,042 → 4,105 | 18.761% | +5.716 |
| Wick algebra time ordering | 1,217 → 1,361 | 26.307% | +4.868 |
| `CallElimCorrect.substOldPostSubset` | 313 → 318 | 6.052% | +1.486 |
| `Core.InitsUpdatesComm` | 224 → 230 | 3.973% | +0.432 |
| BinaryBasefold fiberwise distance | 1,459 → 1,457 | 0.393% | +0.174 |

The exact benchmark IDs are in the machine-readable records and
[comparison table](../comparison.csv). Final proofs total **17,917 tokens**, versus
17,595 originally and 17,313 after stage 01. The arena's length statistic is the
mean of per-problem reductions, so it differs from a ratio of these totals.

**Do not apply every `simp?` suggestion blindly.** For example, the initial batch
for `substOldPostSubset` increased tokens by 63.898% against the reference while
reducing heartbeats by only 12.854%; its combined score was 16.319%, so it was
rejected. Selecting an individual useful change instead produced 34.818%.

## Method and budget

Starting from stage 01, the harness asks existing `simp`, `simp_all` and `dsimp`
calls for explicit `only` lemma sets. It uses parsed, nonoverlapping spans, matches
suggestions to the originating site, and skips ambiguous suggestions. The proposed
proof contains the resulting ordinary tactics, not the suggestion-producing search.
No extra imports or hand-written mathematical arguments are introduced.

Try the joint edit first; if it does not improve the score, test individual edits
against that incumbent and select the best measured improvement. Reanalyze after
an acceptance. Budgets remain **three rounds, 32 candidates per problem, two
problem workers, and a 0.05 pp minimum improvement**. This is a bounded search,
not a global optimum or a complete-menu training dataset.

There were **99 candidate trials**, with 102 accepted edit operations across the
eight changed proofs. Eleven trials improved their incumbent; some were competing
alternatives at the same point, so not all became selected states. Forty records
stop after primary-version evaluation because even perfect compatibility could
not beat the incumbent. Those records deliberately have no final combined score;
they are not infrastructure failures. All selected outputs are fully checked.

`substOldPostSubset` reached the 32-trial limit. Eight rows stopped because no new
applicable suggestions remained; six stopped with no improving proposal in the
tested set. There were no analysis failures. Recorded per-problem elapsed times
sum to **637.228 s**, including cache hits; this is not a cold-run or end-to-end
competition timing.

- [config.json](config.json), [summary.json](summary.json): exact configuration and aggregates.
- [candidates.jsonl](candidates.jsonl): the current selected model-free proofs for all 15 rows.
- `problem_*.json`, `trials_*.jsonl`: per-version costs, diagnostics, proposed code,
  rejections, accepted transitions and stop reasons.

## Decision and next experiment

Keep score-based explicit simplification in the shared harness for both tracks.
Length-only selection would have discarded most of these improvements.

The next isolated stage should test **local `have` deletion and return-wrapper
contraction**, starting from these proofs. In particular, generate a candidate
that contracts `have h : T := by ...; exact h` when syntax and scope permit it,
and independently test deletion of facts identified as unused by elaborated
dependencies. Retain exactly the same score policy and original denominators;
report the gain over **37.100%**. This directly tests whether we can recover length
without losing the heartbeat savings. It has **not** been run here.

After that, run a bounded goal-closing tactic menu and record complete per-site
outcomes. There is not yet evidence to choose model tool-use training, SFT or GRPO
over improving this deterministic baseline. Those should receive their own later
stage and matched inference/tool budgets.
