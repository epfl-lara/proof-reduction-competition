# First live combined test

Completed on 2026-10-03 for `CallElimCorrect.substOldPostSubset`, using the first
accepted model proposal: Qwen3.5-397B-A17B with `cards_goals`, followed by one
correctness-only repair. This case was selected to check the engineering and
interaction between stages; it is not a full-benchmark estimate.

| Branch | Tokens | Length reduction | Heartbeat reduction | Compatibility | Combined score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original deterministic incumbent D0 | 303 | 3.194888% | 9.026097% | 100% | 37.406995% |
| Extra deterministic control D1 | 303 | 3.194888% | 9.026097% | 100% | 37.406995% |
| Model + validity repair L | 259 | 17.252396% | 8.074610% | 100% | 41.775669% |
| Model + repair + deterministic cleanup H | 259 | 17.252396% | 8.398811% | 100% | 41.883736% |

The combined result gains **4.476741 percentage points** over the matched control,
including **0.108067 points** from deterministic cleanup after the model. These
are per-problem local scores against unchanged cached references.

The model shortened several case branches. The fixed tactic menu then replaced
one `simp_all` in its `bvar` branch with `contradiction`, keeping the token count
unchanged while reducing heartbeats. All ten cleanup methods finished; this was
the only accepted deterministic transition. The identical cleanup applied to D0
made no accepted change. This demonstrates one concrete opportunity created by
the model's rewrite that the deterministic methods could subsequently improve.

The control used 73 candidate trials and the proposal used 56. Their optimizer
records contain 10 and 56 uncached candidate checks, respectively, plus 63 and
6 cache hits. Discovery work and initial/final validation are distinct from
those candidate counters. Different inputs and cache histories mean that equal
method budgets do not imply equal realized compute.

No additional model requests were made for this pilot. Both physical cleanup
jobs are stored in the full experiment's job directory and reused there.
The [engineering manifest](validation/engineering_pilot.json) records exact
inputs, scores, work counters and result hashes; the
[saved script](validation/run_engineering_pilot.py) describes the execution.
The [configuration serialization note](validation/configuration_serialization.json)
preserves the pilot's exact configuration hash and records the later CLI rewrite
of the same five-second polling interval from JSON `5.0` to `5`.

The full 225-cell comparison with fifteen controls is reported separately in
[README.md](README.md). Its condition-level means require the complete
corresponding cohort and must not be inferred from this one example.
