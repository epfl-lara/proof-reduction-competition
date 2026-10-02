# Lean Refactor Arena rules

Checked on **October 2, 2026**. This is a saved, paraphrased account of the organizer's published rules and intake behavior, not a replacement for the official rules or mandatory report template.

## Sources

- [Competition page](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena), especially Tracks & Rules and Submit.
- [Pinned rules and submission source: app.py](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena/blob/d9e46ee13c822925fb3031b0a0eac53b51631198/app.py), including `_desk_rejection_html`, `_scoring_html`, the Tracks & Rules tab, and `_FORBIDDEN_PATTERNS`.
- [Pinned scoring implementation: leaderboard.py](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena/blob/d9e46ee13c822925fb3031b0a0eac53b51631198/leaderboard.py).
- [Pinned benchmark documentation: benchmark.py](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena/blob/d9e46ee13c822925fb3031b0a0eac53b51631198/benchmark.py).
- [Official report template](https://www.overleaf.com/read/fhmwmtrgwkmc#4d5413). The organizers identify the template itself as the binding text for report requirements; this snapshot summarizes the requirements exposed in the Space.

## Objective and tracks

Refactor the benchmark's Lean 4 proofs without changing what they prove. Optimize three equally weighted dimensions: proof token reduction, elaboration heartbeat reduction, and unchanged compilation across the specified toolchains.

The tracks have separate rankings. A team may enter either or both, using separate submissions.

| Requirement | Closed-source LLM track | Open-source LLM track |
| --- | --- | --- |
| Models | Closed-source frontier models through provider APIs; arbitrary harnesses are permitted. | Only models with publicly available weights; post-training and harnesses are permitted. |
| Budget | At most **US$3 per problem**, priced at the provider's public list prices. | Inference must fit on at most **4 A100 GPUs with 80 GB each**; the complete benchmark run must finish within **48 hours** on that hardware. |
| Code | Complete harness used to generate the proofs. | Inference harness and model-serving setup. Post-training code is not required. |
| Other deliverables | Proof JSONL and technical report. | Proof JSONL and technical report. |

For closed-track accounting, count every API call, including retries and discarded candidates. The maximum spend for any problem must remain within the cap; an average below US$3 is insufficient.

## Scoring

For each accepted, compiling declaration:

- Length reduction compares the token count of the submitted proof body with the reference body. Comments and blank lines do not provide a length advantage. A longer proof can have a negative reduction.
- Heartbeat reduction compares Lean elaboration cost with the reference proof. More expensive elaboration can produce a negative reduction.
- Zero-shot compatibility is the percentage of the row's `version_info` toolchains on which the same proof compiles without modification.

The per-problem score is the arithmetic mean of these three percentages. The overall Combined % is the mean of per-problem scores over **the entire benchmark**, including omitted problems.

A missing submission, compilation failure, changed statement, or invalid proof receives zero on all axes. Submitting only a subset is allowed, but omitted rows remain in the denominator. Heartbeat baselines are maintained separately by the organizer; the benchmark loader notes that rows without a measured baseline do not yet contribute a heartbeat denominator.

## Proof submission contract

Upload a UTF-8 JSONL file. Each nonempty line must be a JSON object containing nonempty `name` and `proof` fields:

```json
{"name": "benchmark_id", "proof": "theorem original_name (n : Nat) : n = n := by rfl"}
```

This is a schema illustration. Replace both fields with an actual benchmark ID and its exact declaration statement.

- `name` must match a benchmark ID. Unmatched IDs are ignored, and an upload with no matching IDs is rejected.
- `proof` contains the **full declaration**, including the original statement and `:=` followed by the replacement proof. Only the body after `:=` contributes to the length metric.
- Preserve the benchmark statement. Submit the statement and proof alone, without extra top-level declarations or syntax extensions.
- The Space handles intake and displays results; a dedicated worker compiles and scores the proofs.
- A successful first upload reserves the username and issues a submission key. Save the key; later uploads under that username require it. Name matching ignores case and spacing.
- Resubmissions are permitted. A scored run replaces the previous leaderboard entry; the latest entry counts rather than an automatic best-of-history result.
- The current intake implementation limits uploads to 8 MiB and each user to five pending unscored jobs. It applies a 256 KiB proof-size guard; the source currently checks the Python string length for that guard.
- Invalid JSON, missing fields, or a forbidden construct rejects the upload before worker evaluation.

## Forbidden constructs

The public rules and current intake filter prohibit:

- Executable commands or unsafe execution: `#eval`, `#reduce`, `IO.*`, `unsafe`, `extern`, `initialize`, `@[implemented_by]`, and `@[extern]`.
- Proof placeholders and kernel bypasses: `sorry`, `sorryAx`, `admit`, `axiom`, `native_decide`, `ofReduceBool`, and `ofReduceNat`.
- Elaboration commands and measurement interference: `run_cmd`, `run_elab`, `#exit`, and `#count_heartbeats`.
- Extra top-level declarations such as `def`, `abbrev`, `instance`, `structure`, `inductive`, `class`, and `opaque`; `attribute` commands and `deriving instance` are also blocked.
- Syntax and elaborator extensions: `macro`, `macro_rules`, `elab`, `elab_rules`, `notation`, and `syntax`.

Comments are stripped before the forbidden-pattern scan. These implementation details describe the saved revision; the organizers may update validation.

## Code and technical report

Every full-benchmark entry needs both reproduction code and a technical report, in addition to proofs.

- Upload proofs and code in the arena under the same username. Code intake is scheduled to open with the full benchmark; it was disabled in the saved source revision.
- Submit the report to the [workshop OpenReview venue](https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/VERICODEGEN), not to the arena.
- Proofs and code may arrive separately, provided both arrive by the deadline.
- Package code as one `.zip` or `.tar.gz` archive with a top-level README containing exact commands to regenerate the submitted JSONL. Pin the environment, Lean toolchains, and dependency revisions.
- Results must be reproducible within the track's budget. Organizers will rerun leading entries.

Use the official template's `neurips_2026_vericode_workshop_competition.tex` and `neurips_2026_vericode_competition.sty`. The report body must be **3–9 pages**, including figures but excluding references and appendices. Omit the `final` and `preprint` style options for submission so review line numbers remain visible.

The main report must contain these sections under these exact headings, in this order; none may be moved to an appendix:

1. **Approach**: explain the full refactoring pipeline.
2. **Models**: disclose every model, including embeddings, rerankers, and judges, with exact name, version, and provider. Link publicly available weights and identify the base checkpoint for fine-tuned models.
3. **Budget accounting**: for closed entries, give total API spend and mean and maximum per-problem spend, with the complete per-problem table in an appendix. For open entries, report hardware and end-to-end full-benchmark runtime.
4. **Reproduction**: describe reproducibility; put the exact execution steps in the code archive's top-level README, as required by the Space.

Review is single-blind. Include real author names, affiliations, and contact information; reports are not anonymized.

An entry can be removed from the ranking regardless of score for a missing report, a missing required report section, exceeding its budget, under-reporting costs, failing to disclose models, or supplying code that cannot reproduce the result. Review checks validity, accounting, budget compliance, and reproducibility rather than novelty.

## Timeline and prizes

| Milestone | Published date |
| --- | --- |
| Warm-up submissions | Open through October 31, 2026; 15 development problems. |
| Full benchmark and leaderboard refresh | November 1, 2026; advertised as 50 problems. |
| Proof, code, and OpenReview report deadline | November 8, 2026. |
| Review and awards date | November 22, 2026. |
| Workshop | December 12, 2026, NeurIPS in Atlanta. |

Each track advertises a US$5,000 winner's prize and a workshop presentation slot. The saved page still includes a disclaimer that prize amounts and benchmark size were provisional and could change before September 1, 2026. No deadline time or timezone is specified in the inspected source. The timeline lists November 22 for review and awards, while the workshop is separately dated December 12.

## Updates and clarification

Follow the live competition page, [arena Discord](https://discord.gg/zg88y8xyC), and [Lean Zulip discussion](https://leanprover.zulipchat.com/#narrow/channel/113488-general/topic/Lean.20Refactor.20Competition.2C/with/621991779) for announcements and rule clarifications.
