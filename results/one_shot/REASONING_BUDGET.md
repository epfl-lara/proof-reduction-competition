# Separate reasoning and final-answer budgets

Updated **2026-10-03**. **Upstream vLLM supports a hard thinking-token limit.
Two subsequent small RCP probes matched the requested reasoning-channel token
counts, but neither delivered its requested final answer.** The original
read-only schema check and these two generation calls are recorded separately.
No server configuration or running benchmark request was changed. The tests do
not establish the server's termination mechanism or behavior on Lean proofs.

The current empty-final responses do not show that Lean proofs need more than
32,768 output tokens. A separate thinking limit could leave generation capacity
for the final declaration while preserving the input context and total output
cap. It would not guarantee a correct or complete proof.

## Upstream capability

The versioned **vLLM 0.21.0** documentation describes the per-request
`thinking_token_budget` sampling parameter. When the reasoning count reaches
the limit, the sampler forces the configured reasoning-end sequence and
generation can continue into the answer. Without this parameter, the ordinary
generation limit is the only explicit bound described there. This establishes
support in that version, not the first version to introduce it.
[Versioned documentation](https://docs.vllm.ai/en/v0.21.0/features/reasoning_outputs/#thinking-budget-control).

The server needs a compatible reasoning parser and correctly identified
reasoning boundaries. `--reasoning-config` can supply
`reasoning_start_str`/`reasoning_end_str`; otherwise vLLM attempts to derive
them from the parser. Its documented Qwen3 example uses
`--reasoning-parser qwen3`. The configured end sequence can include a short
transition phrase followed by the actual closing marker.
[Server configuration example](https://docs.vllm.ai/en/v0.21.0/features/reasoning_outputs/#online-serving).
The configuration source leaves boundary initialization disabled if either
boundary is unavailable. A recognized request field alone is therefore
insufficient evidence of functioning enforcement.
[ReasoningConfig source](https://github.com/vllm-project/vllm/blob/v0.21.0/vllm/config/reasoning.py).

On the vLLM **wire request**, `thinking_token_budget` is a top-level field,
separate from `chat_template_kwargs` and the total `max_tokens` or
`max_completion_tokens`. The request conversion passes it into sampling
parameters. The server's chat template and parser must match the actual model;
the Qwen3 example is not a verified configuration for our three RCP deployments.
[Request schema and sampling conversion](https://github.com/vllm-project/vllm/blob/v0.21.0/vllm/entrypoints/openai/chat_completion/protocol.py).

An illustrative future request fragment is:

```json
{
  "max_tokens": 32768,
  "thinking_token_budget": 8192,
  "reasoning_effort": "high",
  "chat_template_kwargs": {"enable_thinking": true}
}
```

This changes the thinking limit while holding the existing total cap and
requested effort fixed. It is an example to verify, not a measured optimum or
a guarantee of exactly 24,576 answer tokens. Closing-sequence tokens and other
generated tokens share the total allowance; EOS, stop conditions, or the model
context limit can still end the response. The implementation counts reasoning
boundaries and forces end tokens; it does not promise a minimum final-answer
length. [Sampler implementation](https://github.com/vllm-project/vllm/blob/v0.21.0/vllm/v1/sample/thinking_budget_state.py),
[generation parameters](https://github.com/vllm-project/vllm/blob/v0.21.0/vllm/sampling_params.py).

Suppressing returned reasoning is a different operation:
`include_reasoning=false` still generates reasoning tokens and does not solve
the generation-budget problem.
[vLLM documentation](https://docs.vllm.ai/en/stable/features/reasoning_outputs/#suppressing-reasoning-output).

## LiteLLM forwarding and a misleading alternative

LiteLLM documents `hosted_vllm/` routing for a hosted vLLM endpoint and says
nonstandard provider parameters are passed into the request body. That supplies
a possible route for `thinking_token_budget`, but a deployment's routing,
filters, defaults, and backend still need checking.
[Hosted-vLLM integration](https://docs.litellm.ai/docs/providers/vllm#usage---litellm-proxy-server-calling-openai-compatible-endpoint),
[provider-specific input handling](https://docs.litellm.ai/docs/completion/input).

**Do not substitute `thinking: {"type": "enabled", "budget_tokens": B}` and
assume it enforces B on vLLM.** In LiteLLM's tagged `v1.94.0` hosted-vLLM
adapter, that object is removed and, if no explicit effort was supplied, its
numeric budget is converted into a `reasoning_effort` category. That is different
from forwarding vLLM's `thinking_token_budget` sampling field.
[Pinned adapter source](https://github.com/BerriAI/litellm/blob/v1.94.0/litellm/llms/hosted_vllm/chat/transformation.py#L100-L107).

The repository's [RCP client](../../src/proof_eval/rcp.py) currently exposes
thinking enablement, reasoning effort, and total generation tokens; extra keyword
arguments are copied into the top-level payload. The two small probes below used
that path; it does not expose the proxy's forwarded payload or server mechanism. Its DeepSeek
mapping converts `medium` to `high`, so a distinct softer-effort comparison would
use `low`. No existing model request was changed.

## What the RCP read-only probe established

The [sanitized probe record](reasoning_budget_evidence/capability_probe.json)
contains only:

- One authenticated **GET** for the service's OpenAPI schema; **HTTP 200**.
- OpenAPI specification version **3.1.0** and API-declared version **1.94.0**.
- `max_tokens` present in the schema.
- `thinking_token_budget`, `reasoning_effort`, `enable_thinking`,
  `max_completion_tokens`, `reasoning_budget`, and `budget_tokens` absent as
  explicit schema field names.

This API version is not a verified vLLM version or proof of an exact backend
build. Schema absence is inconclusive: it also omits controls the client already
sends, and provider-specific pass-through may be outside the schema. The schema
check alone did not verify parameter forwarding, parser/boundary configuration,
or actual thinking-budget enforcement. Credentials, headers, internal URLs, and the full
schema were not saved in the evidence file.

Version and execution path matter. For example, a historical upstream issue
reported a thinking-budget failure with MTP speculative decoding on vLLM
0.19.0, while its non-MTP example worked. This is a reason to verify the actual
deployment, not a claim that our deployment has that bug.
[Upstream issue #39573](https://github.com/vllm-project/vllm/issues/39573).

## Subsequent two-call generation probe

After the schema-only check, two isolated requests were completed on the
configured RCP route for **DeepSeek-V4.1-Flash**. Both used the same arithmetic
question, temperature 0.3, high reasoning, and `max_tokens=512`. The request
varied only the top-level `thinking_token_budget`, between 32 and 128. It asked
for the final integer only; the expected value was independently computed as
353. The [saved probe](reasoning_budget_evidence/generation_probe/probe.json)
records the exact requests, client/script hashes, responses, usage and limits.

| Requested thinking budget | Reported reasoning tokens | Reported completion tokens | Nonempty final-channel text | Finish reason | Complete requested integer answer |
| ---: | ---: | ---: | --- | --- | --- |
| 32 | 32 | 512 | Yes | `length` | No |
| 128 | 128 | 512 | Yes | `length` | No |

These **two additional calls used 1,024 reported completion tokens**, including
160 reported reasoning tokens. They are separate from the 225-cell benchmark
and its correctness repairs, with no automatic retries. The earlier
`capability_probe.json` continues to describe only its single read-only request;
its zero-generation count does not describe this subsequent probe.

The narrow observation is that reported reasoning-channel usage follows the
two requested boundaries and final-channel content exists afterward. That is
useful evidence about this parameter on this model/route. It is **not proof of
forced reasoning-end-token insertion or semantic reasoning termination**:
there is no server trace, deployed backend revision, tokenizer token-ID stream,
or forced-boundary event in the artifacts. Both final-channel texts continued
calculation steps and were truncated at the total cap. Neither delivered the
requested completed answer, so nonempty `content` is not an adequate success
criterion. One draw per budget also does not establish general reliability.

## Remaining verification

1. **Verify the route without generation if deployment information is
   available.** Record the backend version/revision, model parser and boundary
   configuration, active speculative-decoding path, and whether the proxy
   forwards the top-level field unchanged. A mocked client serialization check
   can verify our payload shape, but cannot verify the server.
2. **Distinguish channel accounting from useful completion.** The two small
   probes above have been run; do not describe them as still pending or repeat
   them silently. A stronger mechanism check would need a server trace or
   token-ID evidence of the boundary event. A delivery check must require the
   requested complete answer, not merely a nonempty final field. Record the
   complete-answer rate, total-cap exhaustion, and output-contract violations
   alongside reasoning usage.
3. **For a separate Lean engineering test**, try one saved input with the
   unchanged full input context, 32,768 total tokens, and a separately declared
   thinking budget. Record final-declaration delivery and all-version validity
   before deciding on a larger paired experiment. Forced termination can hurt
   proof quality; having answer capacity is not the same as having a valid
   optimized answer.

**No Lean reasoning-budget test has been run.** The two arithmetic probes do not
alter the current high-reasoning cohort, establish a useful final-answer reserve,
or show that the same behavior holds for another model, workload, or deployment.
