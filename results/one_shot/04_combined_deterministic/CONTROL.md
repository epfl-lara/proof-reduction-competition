# Completed additional deterministic control

All fifteen controls completed the fixed ten-method pass on 2026-10-03. Every
selected proof is byte-for-byte unchanged from the archived deterministic
incumbent. All **36 required version checks pass** in the saved evaluations.

| Measure | Original deterministic incumbent D0 | Additional cleanup D1 | Change |
| --- | ---: | ---: | ---: |
| Mean length reduction | 12.187241% | 12.187241% | 0 pp |
| Mean heartbeat reduction | 26.557125% | 26.557125% | 0 pp |
| Compatibility | 100% | 100% | 0 pp |
| Combined score | 46.248122% | 46.248122% | 0 pp |

The controls performed **961 candidate trials**, with 305 recorded discovery
requests, 277 uncached candidate version checks and 683 cache hits. These counters
describe different operations and should not be added together as a single trial
count. Initial/final validation is separate from the optimizer's candidate-check
counters. Summed optimizer elapsed time is 2,132.508 seconds; work overlapped, so
this is not wall-clock duration. Previously cached deterministic evaluations were
reused, and no reference values were remeasured.

This establishes the complete additional-cleanup baseline for the model
comparison. The [first combined pilot](PILOT.md) improved a model rewrite while
its control remained unchanged. Model-branch comparisons are reported separately
in [README.md](README.md); their full-condition scores require complete cohorts.

No gain in this bounded pass does not establish a global optimum. Each method
had three rounds, 32 trials and six discovery sites per site batch, with no
repeat sweep. The [protocol](PROTOCOL.md) fixes those limits and the all-version
eligibility gate.

[controls.json](controls.json) maps each theorem to its physical cleanup job and
result hash. The jobs retain every method result, candidate trial, checkpoint
and evaluator evidence. [report.json](report.json) gives the full D1 baseline and
keeps incomplete model-condition means separate.
