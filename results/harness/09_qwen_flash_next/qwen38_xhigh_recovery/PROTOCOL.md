# Qwen transport recovery

Run only the five interrupted `Qwen/Qwen3.8-Flash-Next/xhigh` problems, with three parallel workers and the existing revised prompt, proof tools, score feedback, and deterministic cleanup at the beginning/end.

Start from each problem’s strongest saved same-condition proof. Read cached reference measurements; do not remeasure original proofs. The original cohort and first retry are preserved byte for byte. Their results are not relabeled as completed model requests.

Enable four native HTTP retries and five stream retries with native backoff/history preservation. If the native process reaches a terminal transient failure, admit at most two fresh host sessions with backoff, passing the best verified proof. All these attempts share one 57-minute deadline per problem. Unresolved requests and permanent failures are never automatically resampled.

These are fresh recovery runs after the earlier budgets expired. They are not a new independent single-attempt benchmark, and they do not establish a new full-cohort mean. Interrupted upstream token usage and unpriced gateway charges remain unknown.

The host records recovered reconnect notices without rejecting a successful final response. `validation.json` records the offline checks; `launch.json` pins the sources, previous evidence, and starting proofs. An independent completion auditor checks saved evidence after the host exits.
