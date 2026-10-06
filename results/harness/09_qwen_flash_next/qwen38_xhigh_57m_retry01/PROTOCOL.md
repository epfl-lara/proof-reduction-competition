# User-authorized gateway retries

Retry the five terminal transport failures from [the original run](../qwen38_xhigh_57m/README.md). The original run and all partial proofs are preserved byte-for-byte. The ten completed searches are not dispatched again.

Use the identical frozen runtime, model `Qwen/Qwen3.8-Flash-Next`, `xhigh` reasoning, canonical prompt, score feedback, heartbeat profiling, and deterministic cleanup at the beginning/end. Sampling defaults remain native. Each retry starts with the same original/deterministic seed and a fresh 3420-second wall deadline; no previous conversation or model solution is supplied. Three problems run concurrently. Original references are read from cache without remeasurement.

The user explicitly requested these retries after checking model availability. `launch.json` records the authorization, five original result hashes, original artifact hashes, and prior best scores. Keep those partial proofs available when comparing or selecting eventual submissions. Any later combined report must identify this retry policy and preserve cumulative/unknown usage; do not represent it as an uninterrupted single-attempt cohort.

There is no automatic retry of a new transport failure. An offline completion auditor checks saved evidence when this retry batch terminates. The report retains the original 15-problem denominator, so this five-problem subset has no standalone full-benchmark mean.
