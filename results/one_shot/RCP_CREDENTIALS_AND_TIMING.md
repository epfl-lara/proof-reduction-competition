# Credential resolution and timing

The RCP client resolves inherited `RCP_API_KEY`/`RCP_OPENAI_API_KEY` before values
in an explicitly supplied `.env` file. At the 2026-10-03 continuation check, the
parent process had an inherited key different from the repository file. The
endpoint was `https://inference.rcp.epfl.ch/v1` in both cases. No key was printed
or saved. Historical workers had exited; their exact effective key is unverified.

New recovery and medium-probe launches remove inherited `RCP_*` variables and
load the repository file explicitly. This changes credential resolution, without
changing prompts, model names, decoding arguments or evaluation. To ensure a
new shell invocation falls back to the repository file:

```bash
env -u RCP_API_KEY -u RCP_OPENAI_API_KEY \
    -u RCP_BASE_URL -u RCP_OPENAI_BASE_URL \
    python src/run_with_rcp_limit.py [the usual gate and runner arguments]
```

Keep that shared gate for requests on this key. The clarified limit is five
requests total, not five models. The existing continuation conservatively
reserves one slot for its historical repair cohort, leaving four new HTTP slots.
The gate is not FIFO; long waits are possible. Do not interpret its queue time
as model generation latency. Logged admitted intervals include provider queueing
and network time, not just model computation.

The [Qwen3.8 medium request](07_qwen38_reasoning/summary.json) spent **463.72 seconds
waiting locally** and **457.11 seconds admitted to HTTP**. Its approximately
920.83-second elapsed time therefore roughly doubles the actual admitted interval.
It still returned no final proof, with all 32,768 output tokens reported as
reasoning. Changing to the repository credential did not fix that delivery case.

The earlier high cohort includes 47 saved empty capped responses and two
interrupted calls with unknown response/usage. Those two requests are not repeated.
The [stop record](05_qwen38_extension/STOPPED.md) and
[continuation recovery](06_parallel_continuation/interruption_recovery/README.md)
separate admitted calls from four proven never-admitted requests safely resumed.

Codex Astra/Luna use the existing ChatGPT login independently of RCP. Their
elapsed time includes model-side tools and Lean validation, and their CLI does
not enforce the RCP study's fixed output-token cap. Report these as different
inference setups rather than a model-only latency comparison.
