# Literature and competition plan

Research snapshot: **2026-10-02**. Start with the [implementation proposal](PROPOSAL.md) and [model and training assessment](MODELS.md). The recommendation is to build one verified search harness for both tracks, establish repeated symbolic cleanup and frozen-model baselines, then train a smaller editor before attempting large-model or test-time RL.

| File | Purpose |
| --- | --- |
| [LITERATURE.md](LITERATURE.md) | Annotated papers, useful mechanisms, limitations, and corrections to the supplied research. |
| [PROPOSAL.md](PROPOSAL.md) | Prioritized experiments, shared harness, closed-track accounting, open-track SFT/GRPO, and milestones. |
| [MODELS.md](MODELS.md) | Verified model IDs, weight sizes, A100 feasibility, framework support, and selection gates. |
| [papers.json](papers.json) | Paper metadata, source URLs, versions where available, byte sizes, and SHA-256 checksums. |
| [references.bib](references.bib) | Bibliography for the downloaded reading list. |
| [model_metadata.json](model_metadata.json) | Public model configuration and weight-index metadata at exact Hub revisions; no weights. |
| [framework_sources.json](framework_sources.json) | Exact framework commits inspected for support claims. |
| [inputs](inputs/) | Both supplied research notes, preserved verbatim. They are discovery inputs, not authoritative citations. |

## Downloaded papers

The selected **19-paper** reading list has been downloaded to `related_work/papers/`. PDFs and extracted research caches stay local and are Git-ignored; the summaries, originals, bibliography, downloader, and checksum inventory are committed. This keeps binary literature out of Git history while making the collection reproducible on another checkout:

```bash
python related_work/download_papers.py          # download missing copies; verify checksums
python related_work/download_papers.py --check  # offline inventory check
python related_work/download_papers.py --id leanpolish --id proofoptimizer
```

The downloader rejects HTML/error pages and changed hashes. Three arXiv versioned PDF endpoints returned HTTP 406, so their unversioned PDFs were downloaded and their first-page version stamps checked. Those exceptions are recorded in the manifest. The author-hosted TTT-Discover PDF is a checksum-pinned snapshot; its exact correspondence to the arXiv revision is unconfirmed. A future changed source should be reviewed and explicitly recorded as a new snapshot.

LeanRefiner's code was accessible, but its OpenReview PDF returned HTTP 403. Its entry is therefore based on the repository and is not counted among the downloaded papers. Secondary historical references are linked in the annotated bibliography rather than included in the core download set.

## Reading order

1. **LeanPolish**: strong symbolic baseline and pitfalls in collecting training/ranking data.
2. **ImProver**: proof-state context and verified iterative editing.
3. **Lean Refactor**: retrieval conditioned on objectives and versions.
4. **ProofOptimizer**: expert iteration, GRPO, and iterative sampling.
5. **Growing Mathlib**: reasons short proofs can still elaborate slowly.
6. **ImProver 2**: preference training with replay and stronger context.
7. **TTT-Discover / TTRL**: optional test-time adaptation experiments.

## Evidence boundaries

Paper results are author-reported, not reproduced here; their compression numbers use different input proofs and metrics. Framework documentation establishes a candidate implementation path, not a tested four-A100 configuration. This update downloads literature and adds proposals; harness generation, training, and GPU feasibility experiments remain future work.

Use [RULES.md](../RULES.md) for the saved arena contract. The [workshop page](https://vericodegen.github.io/#challenge-competition-track) currently differs from the saved Space on report minimum length, required budget heading, and OpenReview venue. [PROPOSAL.md](PROPOSAL.md#rule-questions-to-resolve-before-the-final-run) records this and the unresolved treatment of test-time training. The saved rules snapshot has not been silently rewritten.
