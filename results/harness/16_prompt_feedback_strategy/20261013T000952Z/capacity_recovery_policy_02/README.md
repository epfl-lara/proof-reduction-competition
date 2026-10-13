# Delayed capacity recovery

The user questioned why a temporary provider-capacity failure prevented further
recovery. The prior instruction already authorized autonomous failure recovery.
The one-manual-continuation limit was an assistant implementation choice. This
record replaces that choice with a bounded cooldown policy while preserving
the earlier recovery protocol and all historical result/config/request bytes.

The next eligible continuation is no earlier than **2026-10-13 10:03:54
Europe/Zurich**, fifteen minutes after the observed terminal failure, and only
after the current source batch is terminal and audited with no pending request.
AGY reviews the due event and wakes the owning Codex thread. Codex validates the
source, uses the same frozen runtime and model, and carries all prior spending
and failed attempts into a new output. The monitor itself makes no proof calls.

At most two further continuations are planned, `recovery_02` and `recovery_03`.
The latter requires a thirty-minute cooldown after another eligible transient
failure. Every continuation preserves the original $3 per-problem target,
best-effort usage policy, and a total ceiling of 23 admissions across all source
outputs. Unknown reported usage remains unknown. There is no model substitution,
fresh budget, retry of an active/indeterminate request, or change to frozen
proof runtimes. A recovered comparison must disclose the changed recovery policy.

The best `putnam_1964_b2` proof still passes both required versions and scores
99.11788904078371%. Its recorded cumulative estimate is $2.3723508, leaving
$0.6276492 estimated. These are not complete reported usage or an invoice cap.
Other workers finish normally before a new carryover source is admitted.

The live policy and schedule are in
`/localhome/milikic/.codex/monitors/prompt123-20261013/FOLLOWUP.md` and
`capacity_retry_plan.json`. Copies here record this policy revision.
Fifteen offline monitor tests passed, including cooldown timing, source liveness,
audit and pending-request gates, and duplicate notification prevention.
