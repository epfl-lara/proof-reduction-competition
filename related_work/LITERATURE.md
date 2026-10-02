# Annotated literature

Checked **2026-10-02**, using the supplied notes as leads and primary papers/repositories as evidence. “Use here” is our proposed adaptation. Reported results below belong to the authors' experiments; they are not arena scores or reproduced measurements. Local PDF filenames and hashes are in [papers.json](papers.json).

## Direct proof optimization

### 1. LeanPolish — first baseline and first data source

Pauline Bourigault, *LeanPolish: Verified Supervision for Lean Proof Compression*, September 2026 preprint. [Paper](https://arxiv.org/abs/2609.38384v1), [code](https://github.com/paulinebourigault/leanpolish), [dataset](https://huggingface.co/datasets/leanpolish-anon/lean-proof-compression).

A symbolic editor records verified local replacements, proof states, and failed alternatives. The release reports 33,402 accepted edits and 65,596 linked failures. Repeating symbolic passes increased miniF2F token savings from 19.7% to 27.5% in its experiments, exceeding its tested neural hybrids. A particularly useful result concerns selection bias: stopping at the first successful action exposes menu order through the recorded negatives; complete candidate menus reveal a harder ranking problem.

**Use here:** reproduce iterative cleanup, then collect complete or explicitly sampled action outcomes for a learned selector. **Limit:** released code pins Lean/Mathlib 4.21; arena project versions need ports and fresh verification. Inspect the supplied pair-audit script before training. Read §§3–5 and the complete-menu appendix.

### 2. ImProver — verified contextual editing

Riyaz Ahuja, Jeremy Avigad, Prasad Tetali, Sean Welleck, *ImProver: Agent-Based Automated Proof Optimization*, ICLR 2025; downloaded arXiv v2, May 2026. [Paper](https://arxiv.org/abs/2410.04753v2), [code](https://github.com/riyazahuja/ImProver).

Optimizes already valid proofs for user-defined criteria. Chain-of-States context exposes intermediate Lean goals; iterative proposals and compiler feedback support correction. It treats optimization as a broader task than shortening alone.

**Use here:** show the original proof, relevant local goals, exact statement, and current metric vector; retain a verified incumbent. **Limit:** its length/declarativity experiments do not establish gains under the arena's token counter, three-axis score, or API budget. Read §3. Ablate state context against a plain original-proof prompt before adding more agent roles.

### 3. Lean Refactor — objective-aware strategy retrieval

Jialin Lu et al., *Lean Refactor: Multi-Objective Controllable Proof Optimization via Agentic Strategy Search*, 2026, arXiv v2. [Paper](https://arxiv.org/abs/2605.20244v2).

A planner/refactorer/debugger pipeline uses a strategy bank annotated with version and compilation-cost information. The generator is frozen, but the retrieval model is trained. The paper describes 9,237 strategies from 200K long–short pairs and a Qwen3-Embedding-8B retriever. Table 1 reports 88.40%/70.38% token compression on its miniF2F/Putnam inputs; these are not arena Combined percentages.

**Use here:** begin with a small, version-tagged bank of verified transformations and cheap lexical retrieval; learn retrieval only after demonstrating value. **Limit:** do not assume strategy/checkpoint availability or cross-version success transfers to our pinned projects. The expensive bank construction is a separate resource from inference. Read §§3.1–3.3 and Appendix B.

### 4. ProofOptimizer — expert iteration and GRPO

Alex Gu, Bartosz Piotrowski, Fabian Gloeckle, Kaiyu Yang, Aram H. Markosyan, *ProofOptimizer: Training Language Models to Simplify Proofs without Human Demonstrations*, 2025 preprint. [Paper](https://arxiv.org/abs/2510.15700v1), [project](https://proof-optimizer.github.io/).

Combines a symbolic linter, a Lean-specialized Qwen2.5-based 7B model, verified expert iteration or asynchronous GRPO, and iterative sampling. The shortening corpus contains generated proofs for 145K theorems. Reported reductions reach 87% on miniF2F and 57% on PutnamBench. In the studied repair setup, resampling performs better than repairing invalid candidates; repairs often become verbose. §5.2.1 changes inference selection to heartbeats using the length-trained model.

**Use here:** compare SFT on accepted improvements with GRPO, and compare best-of-k resampling with a tightly bounded repair allowance. **Limit:** length-only rewards and large sampling budgets do not reproduce the arena objective/budget. Do not assume published weights or heartbeat outputs are available. Read §3, §4.2, §5.2.1, and Appendix A.

### 5. ImProver 2 — preference training and replay

Riyaz Ahuja, Tate Rowney, Jeremy Avigad, Sean Welleck, *ImProver 2: Iteratively Self-Improving LMs for Neurosymbolic Proof Optimization*, May 2026 preprint. [Paper](https://arxiv.org/abs/2605.22885v1).

Trains DeepSeek-R1-Distill-Qwen-7B with iterative preference optimization, mixing new and previous examples through replay. Its IRPO objective combines preference loss and likelihood on the preferred output. Context includes reachable declarations, goal traces, and informal descriptions; objectives include tactic count, dependencies, and modularity.

**Use here:** retain verified candidate pairs and a replay pool, making an offline preference-training alternative available if online Lean rewards are too expensive. **Limit:** these structural metrics differ from arena scoring. Compare against the same base model with identical context before crediting training. The inspected paper includes redacted release information; checkpoint availability was not established. Read §4 and the context ablations.

### 6. Proof-Refactor — structural rewrites

Yiming Fu et al., *Proof-Refactor: Refactoring Generated Formal Proofs into Modular Artifacts*, June 2026 preprint. [Paper](https://arxiv.org/abs/2606.03743v1), [code](https://github.com/pelicanhere/proof-refactor).

Extracts proof fragments, designs helpers, proves them, and repairs the main proof to use the helpers. This expands the search space beyond deleting tactics.

**Use here:** try local `have`/`let` structure or existing imported lemmas when deletion plateaus. **Limit:** the arena disallows adding auxiliary top-level declarations and changing the statement. Transfer the transformation idea, not the whole artifact format. Automated quality rubrics are not evidence of human readability, and readability is not a scored arena axis.

### 7. LeanRefiner — global-to-local search, repository evidence only

*LeanRefiner: Agentic Global-to-Local Optimization of Lean Proofs*. [OpenReview lead](https://openreview.net/forum?id=60bd3O67QA), [verified repository](https://github.com/Tristan-sdu/LeanRefiner).

The repository exposes global and local editing stages, verified acceptance, two worked examples, and Lean 4.26.0 setup. Its default verification backend invokes Lake.

**Use here:** compare occasional global rewrites followed by local reduction against exclusively local editing. **Limit:** the PDF returned HTTP 403, so no paper-specific performance or venue claim is treated as verified. The CLI-based artifact's generous timeouts also need replacement with explicit arena accounting.

## Lean performance and infrastructure

| Reference | Verified contribution | Use here and boundary |
| --- | --- | --- |
| Baanen et al., [Growing Mathlib](https://arxiv.org/abs/2508.21593v2), 2025 | Library maintenance, deprecation, linters, and compilation performance; §5 discusses typeclasses, coercions, and definitional equality. | Profile expensive proof regions. Explicit arguments or intermediate facts may reduce elaboration work even when longer. Measure transformations; avoid universal rules such as “always use `simp only`.” |
| Aniva et al., [Pantograph](https://arxiv.org/abs/2410.16429v2), [PyPantograph](https://github.com/stanford-centaur/PyPantograph) | Programmatic interaction with Lean states and proof search. | Optional local proposal/goal extraction backend. Metavariable state matters; printed goal equality does not justify composing independently verified edits. Keep fresh full-declaration verification. |
| Yang et al., [LeanDojo](https://arxiv.org/abs/2306.15626v2), NeurIPS 2023 | Accessible-premise extraction and retrieval-augmented proving. | Borrow declaration/context indexing. Filter retrieval to declarations actually available before the target in each project. Tool version support is a separate engineering check. |
| Xin et al., [AXLE](https://arxiv.org/abs/2606.26442v1), [official announcement](https://axiommath.ai/research/releasing-axle/) | Hosted verification and semantic proof utilities, including simplification, repair, and extraction across versions. | Useful API/design comparison. Its hosted environments and heartbeat counts are not our project-specific local denominator. Avoid making final reproduction depend on an unbudgeted cloud prover. |
| Xu and Odersky, [Agentic Proof Automation: A Case Study](https://arxiv.org/abs/2601.03768v1), 2026 | Human-guided agents with lightweight compiler feedback built the System Capless mechanization; the paper reports 189 tasks and 87% success. | Evidence for a simple edit/check loop and preserving useful diagnostics. It is a development case study, not a proof-compression benchmark. |

Our existing [evaluator](../src/proof_eval/) already uses fresh `lake env lean` processes and cached local reference measurements. This literature update does not change it to LeanInteract, Pantograph, LSP, or AXLE. Interactive tools can later supply contexts and cheap intermediate feedback while the current evaluator remains the final local scoring path.

## Adjacent optimization and training ideas

| Reference | Mechanism worth borrowing | Important difference |
| --- | --- | --- |
| Zeller and Hildebrandt, [Simplifying and Isolating Failure-Inducing Input](https://doi.org/10.1109/32.988498), TSE 2002; [PDF](https://www.cs.purdue.edu/homes/xyzhang/fall07/Papers/delta-debugging.pdf) | Test subsets to minimize an input under a predicate; adapt the predicate to “still proves this statement.” | Use Lean syntax boundaries. Local minimality is not global optimality; compiler failure and infrastructure failure must differ. |
| Schkufza, Sharma, Aiken, [Stochastic Superoptimization](https://arxiv.org/abs/1211.0557v1), ASPLOS 2013 | Search equivalent programs using cost and correctness feedback. | Keep a small beam/Pareto archive to allow useful intermediate rewrites. Lean equivalence is enforced by the fixed theorem statement and kernel. |
| Xin et al., [Automated Discovery of Tactic Libraries for Interactive Theorem Proving](https://arxiv.org/abs/2503.24036v2), OOPSLA 2025 | TacMiner uses tactic dependence graphs to identify reusable structure. | Its implemented evaluation targets **Rocq**. This verifies a related idea, not the supplied claim of a Lean tool named Tacflow. New tactic definitions are also outside the arena submission format. |
| Gladshtein, Pîrlea, Sergey, [Small Scale Reflection for the Working Lean User](https://arxiv.org/abs/2403.12733v1), 2024 | LeanSSR combines concise tactic structure and reflection. | Only available tactics/imports may be used. Adding LeanSSR to the project would change the evaluation environment. Low implementation priority. |
| Ringer et al., [Proof Repair across Type Equivalences](https://arxiv.org/abs/2010.00774v4), PLDI 2021 | Structured transformations for repairing proofs after representation changes. | Inspiration for dependency-sensitive edits; the competition instead requires unchanged submission text across versions. |
| Shao et al., [DeepSeekMath](https://arxiv.org/abs/2402.03300v3), 2024 | GRPO estimates advantages from groups of sampled outputs without a separate critic. | Adapt the reward to verified arena metrics. Critic savings do not remove policy, optimizer, rollout, and activation memory. |
| Zuo et al., [TTRL](https://arxiv.org/abs/2504.16084v3), 2025 | RL adaptation at test time using estimated rewards from unlabeled reasoning tasks. | Lean gives a stronger correctness oracle than majority vote. Use compilation, statement preservation, and measured improvement as reward evidence. |
| Yuksekgonul et al., [Learning to Discover at Test Time](https://arxiv.org/abs/2601.16175v2), 2026; [author PDF](https://test-time-training.github.io/discover.pdf) | TTT-Discover combines test-problem-specific training and search to obtain a particularly good solution. | Closely matches optimization of one proof, but reported API-backed training is not evidence of a four-A100/48-hour implementation. Compare against frozen search under equal total resources. |

## Additional leads from the supplied notes

These are useful background or tools, not prerequisites for the first harness. They are linked rather than downloaded in the selected collection.

| Lead | Evidence and decision |
| --- | --- |
| [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp) | Verified repository provides goals, diagnostics, and search tools. Useful for contextual editing; latency depends on project/build state. |
| [mathlib-quality](https://github.com/CBirkbeck/mathlib-quality) | Verified Claude Code plugin with cleanup/profiling workflows. Its style, declaration, and whole-repository edits need adaptation to the fixed-statement arena. Its one-second guideline is not the arena metric. |
| [Lean Pool](https://github.com/Vilin97/lean-pool) | Verified project repository, created by Vasily Ilin and Justin Asher. Potential corpus/environment source; the supplied “3.2M+ lines” claim was not independently established here. |
| [Designing Proof Deautomation for Rocq](https://jwshii.github.io/) | Author page lists the PLATEAU 2025 paper by Shi et al. Relevant for revealing automation steps; lower priority than direct Lean compression. |
| [Hammering towards QED](https://jfr.unibo.it/article/view/4593), [Sledgehammer manual](https://isabelle.in.tum.de/doc/sledgehammer.pdf) | Historical premise minimization and proof reconstruction leads from note 1; no competitive result is inferred from them. |
| [LEGO-Prover](https://proceedings.iclr.cc/paper_files/paper/2024/hash/85dca46374dc0f27b4bb5f265b3d17f0-Abstract-Conference.html), [Apply2Isar](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ITP.2026.18), [Refactoring Proofs with Tactician](https://proof-technologies.com/papers/tactician_hofm2015.html) | Secondary historical leads retained from note 1; not independently reviewed in this pass. They should not be cited for specific findings without reading their primary sources. |

## Corrections and limits of the supplied research

- **Tacflow:** exact claimed Lean artifact/paper could not be verified through the searches and repository lookup. TacMiner is a verified related paper, with a Rocq implementation. Keep these distinct.
- **Frozen versus trained:** Lean Refactor freezes its generator but trains its retriever. ImProver 2 uses IRPO, which is not interchangeable with online GRPO.
- **Training data is not automatically clean:** complete candidate menus avoid one ordering shortcut, but still require theorem-family splits, outcome provenance, and full-proof checks after edit composition.
- **Metrics differ:** character count, model tokens, Lean source tokens, tactic counts, wall time, and heartbeats are different quantities. Re-evaluate methods with our fixed counter and cached local heartbeat denominator.
- **Results do not transfer numerically:** compression depends strongly on how verbose the initial proofs are. Paper leaderboard percentages are not forecasts for our warm-up problems.
- **Public availability is specific:** verified papers and repository links do not establish that every reported checkpoint, strategy bank, or training dataset is released.
