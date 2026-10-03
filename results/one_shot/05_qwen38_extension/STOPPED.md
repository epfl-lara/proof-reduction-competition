# High-effort cohort stopped

The user requested stopping Qwen3.8 high effort and testing a lower setting.
The high cohort has **47 saved responses out of 75 planned cells**, all empty
finals ending at the 32,768-token cap. Known completion usage is 1,540,096 tokens.
These are delivery failures: the correctness debugger has no proposed proof to
repair. There are no valid outputs or accepted improvements among those 47 cells.

The original stop coordinator attempted to acquire all admission slots and drain
HTTP calls. A later parent-turn interruption stopped it and every worker before
it completed that procedure. Its [original receipt](stop_high_reasoning.json)
is retained unchanged, including its unfinished status and absence of signals.

[external_interruption_stop.json](external_interruption_stop.json) separately
records process absence, availability of all five local locks, and **two admitted
calls without saved responses or usage**. Their usage is unknown, not zero; they
are not resampled. The remaining planned calls were not made. No full-cohort
score is reported. Initial, repair and combined reports remain explicitly partial.

The separately recorded [medium-effort probe](../07_qwen38_reasoning/README.md)
uses one exact saved prompt. It is an engineering diagnostic, not another 75-cell
context matrix.
