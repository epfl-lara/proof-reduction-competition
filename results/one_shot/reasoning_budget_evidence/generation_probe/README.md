# Two isolated thinking-budget probes

On 2026-10-03, two calls to `deepseek-ai/DeepSeek-V4.1-Flash` through the configured
RCP route tested top-level `thinking_token_budget` values of 32 and 128. Both
requests used the same arithmetic prompt, temperature 0.3, reasoning enabled,
high effort, `max_tokens=512`, and a 180-second timeout. There were no retries or
additional calls. The frozen Lean experiments were unchanged.

| Requested thinking budget | Provider-reported reasoning tokens | Total completion tokens | Final-channel characters | Finish reason | Requested integer-only answer |
| ---: | ---: | ---: | ---: | --- | --- |
| 32 | 32 | 512 | 1,031 | `length` | Not delivered |
| 128 | 128 | 512 | 750 | `length` | Not delivered |

The two requests consumed **1,024 completion tokens in aggregate**, equal to
their combined configured allowance. The correct answer to the prompt is `353`;
neither response delivered that requested integer-only answer. Both final-channel
contents continued calculation steps and were truncated at the total output cap.
Nonempty final content therefore did **not** mean successful final-answer delivery.

The exact reported counts at two different requested boundaries support the
field affecting **reasoning-channel or budget handling on this tested route**.
These are provider-reported usage counters. We did not obtain token IDs, a server
trace, the backend configuration, or a forced-boundary event. Consequently, the
observations do not prove that the server forced a particular model-level end
sequence, or that semantic reasoning stopped at either boundary. Continued
calculation in the final channel is an important qualification.

This is not a verified mechanism for reserving a useful final answer, producing a
concise answer, or improving Lean proof delivery. It also does not establish
behavior for other models, requests, budgets, or deployments. Each setting has
only one stochastic sample. No further calls were made for this interpretation.

The [summary](probe.json) records the observations and qualification. The executed
[script](run_probe.py) and [configuration](config.json) retain their original
hashes. Per-budget folders preserve the exact client arguments, expected wire
payload, durable start marker, and result:

- [Budget 32 result](budget_32/result.json), [arguments](budget_32/call_args.json).
- [Budget 128 result](budget_128/result.json), [arguments](budget_128/call_args.json).

Results retain final-channel content, returned model, usage, finish reason,
elapsed time, and the character count of the separate reasoning field. The
reasoning field's text, credentials, endpoint address, and full raw provider
response were not saved. The expected wire payload documents client serialization;
it is not a trace of what the proxy forwarded to its backend.
