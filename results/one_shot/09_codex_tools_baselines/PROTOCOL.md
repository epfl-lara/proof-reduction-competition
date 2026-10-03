# Codex agent baselines

The user requested Astra at **max reasoning**, with and without deterministic
transforms, then Luna at **max, high, and medium**. A later clarification kept
Codex tools enabled. This is an agent baseline with source inspection and Lean
checks. Differences from RCP cannot be attributed to model weights alone.

The manifest is **15 theorems × 4 model/effort settings × 2 seeds = 120 cells**.
Check the first Astra pair end to end, retain it if the setup works, finish Astra,
then test Luna. One optimization proposal and at most three outer correctness
repair calls per cell; Codex may also debug within a call using tools. Event logs
record that additional inference work. No candidate scores enter debugging.

Use the saved `cards` prompt, chosen from the strongest completed DeepSeek
combined condition on this warm-up, not from a held-out prompt study. Hold cards
fixed per theorem. Only the starting proof and its scores change in the user payload.

| Arm | Starting proof | Tools | Postprocessing |
| --- | --- | --- | --- |
| `original` | Published original | Source inspection and validity checks | None |
| `deterministic` | Saved D0 | Identical tools | Ten-method cleanup of every valid final |

Selection preserves the valid seed unless improved by more than 0.05 percentage
points. The deterministic arm also preserves its verified D1 control and tests
cleanup of valid proposals rejected before cleanup. No cross-condition pooling.
Every selected proof must pass all listed versions.

Both arms use the same cached original references. Original identity starts at
33.333333%; D0 starts at 46.248122%. Compare absolute scores and gains over D0,
as well as gains over each seed. References are never remeasured. The existing
evaluator keeps fixed source-token denominators, synchronous heartbeats, trust
checks and pinned toolchains. Outer repairs stop on the first all-version-valid
proposal regardless of score.

Every call gets an isolated workspace, source paths and `check_candidate.py`.
Instructions prohibit reading experiment outputs, other arms, measurement caches
or credentials, modifying imports, running deterministic scripts, and requesting
performance scores. This is an instruction boundary, not filesystem read isolation.
Tools use the environment's unrestricted mode. Nested sandbox execution failed
in the excluded [stage-08 pilot](../08_codex_baselines/README.md). Review tool traces.

Save CLI identity, exact commands/messages, tools, final text, usage, evaluations
and cleanup. Codex uses the existing ChatGPT login, separately from RCP. The CLI
exposes neither hard output-token nor temperature controls: do not label these
calls 32,768-token or temperature-0.3 matched to RCP. Incomplete conditions have no
full-benchmark mean or submission export. Completed conditions get individual
organizer-format submissions. Started requests without saved responses are never
automatically repeated. Seed order alternates by theorem; two workers run.

```bash
conda activate af
python src/run_codex_baselines.py --model gpt-6-astra --effort max
python src/run_codex_baselines.py --model gpt-6-luna
```

`--name`, `--model` and `--effort` schedule pending cells in the fixed manifest.
A localhost test inspects real CLI requests without model calls: exact model,
effort, benchmark prompt, tool instructions and tools. Further tests cover paired
inputs, reference identity, stopping on valid but worse proofs, and no repeated
empty delivery.

Official sources: [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference).
Little gain alone would not prove evaluator failure. Inspect delivery, validity,
unchanged returns, actual edits and scoring separately; there are only 15 problems.
