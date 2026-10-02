# Model and training feasibility

Verified **2026-10-02**. All four requested model IDs exist publicly. Recommendation: compare **Qwen3.8-27B** and **Qwen3.6-35B-A3B** with the same frozen harness, then run LoRA SFT on the better candidate. Keep Qwen3.5-397B and DeepSeek-V4-Flash-0731 as larger inference/teacher experiments until deployment and throughput are measured. None has been run or trained in this repository.

## Weight memory and the four-A100 limit

The following are actual **weight-index payload sizes**, not measured VRAM. Exact revisions, configuration, dtype metadata, and index URLs are saved in [model_metadata.json](model_metadata.json). GB means 10^9 bytes; GiB means 2^30 bytes.

| Model | Architecture / checkpoint | Indexed weight payload | Four A100 80 GB assessment |
| --- | --- | --- | --- |
| [Qwen3.5-397B-A17B](https://huggingface.co/Qwen/Qwen3.5-397B-A17B) | 397B advertised language-model parameters, 17B active; full checkpoint mostly BF16, `qwen3_5_moe` | **806.80 GB / 751.39 GiB** | Does **not** fit fully on four GPUs in BF16. Quantization/offloading is necessary. |
| [Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 35B total / 3B active; BF16, `qwen3_5_moe` | **71.90 GB / 66.97 GiB** | Plausible BF16 serving across multiple GPUs, with useful search throughput potential. Training requires its MoE/hybrid kernels to work. |
| [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | Dense 27B language model; BF16, `qwen3_5` | **55.56 GB / 51.75 GiB** | Best first training candidate for engineering simplicity. Still a hybrid attention model; benchmark its actual kernels. |
| [DeepSeek-V4-Flash-0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) | `deepseek_v4`; config specifies FP4 experts and FP8 quantization, with DSpark components | **166.88 GB / 155.42 GiB** | Weight storage is plausible, but exact A100 kernels and serving topology remain unverified. Do not infer BF16 training feasibility from this size. |

MoE active parameters govern much of the computation per token; inactive experts still occupy memory. Using the nominal 397B count, BF16 needs about 794 GB and ideal four-bit storage about 198.5 GB. The full Qwen checkpoint's stored tensor count gives about **201.7 GB** at an ideal four bits per element, before scales, higher-precision layers, buffers, and runtime state. These are arithmetic bounds, not a working quantization recipe.

The DeepSeek Hub safetensors element-count total is **not** a reliable count of logical model parameters: packed low-bit tensors and metadata distort that comparison. Its index's byte total is the more useful storage measure. Loading can unpack weights or create temporary copies, so even that total is not a VRAM guarantee.

A100 is Ampere/SM80. It lacks the native FP8/FP4 Tensor Core paths used by newer NVIDIA architectures; a compatible weight-only/dequantizing kernel can still support some compressed formats. The exact backend matters. [NVIDIA hardware support](https://nvidia.github.io/TransformerEngine/support_matrix.html) and the [DeepSeek vLLM recipe](https://recipes.vllm.ai/deepseek-ai/DeepSeek-V4-Flash) do not establish our desired four-A100 configuration. The latter emphasizes newer hardware; the official model card's example uses GB300.

## Training memory is a separate decision

A rough conventional mixed-precision Adam estimate is **16 bytes per trainable parameter** for weights, gradients, master weights, and optimizer moments, before activations. Implementations vary. At nominal sizes, that is about 432 GB for 27B and 560 GB for 35B, already above 320 GB aggregate. Sharding spreads these states; it does not eliminate their total size. Offloading or alternative optimizers can change the bound at a throughput cost.

Start with **LoRA SFT**, BF16 frozen weights, gradient checkpointing, small microbatches, and bounded sequence lengths. QLoRA is an alternative only after validating quantization/backward support for the exact architecture. For GRPO, budget rollout KV/recurrent state, policy and reference-policy storage where needed, adapter synchronization, and training activations. Four inference GPUs do not automatically imply four-GPU online training capacity. If larger offline training hardware is available, it expands options, but the final harness still needs to meet the arena inference contract.

## Framework support: what the inspected sources establish

| Framework | Verified evidence | Proposed role / remaining check |
| --- | --- | --- |
| **ms-swift / Megatron-SWIFT** | [Pinned Qwen guide](https://github.com/modelscope/ms-swift/blob/47a0a3ad96f8ac268801891ef88863d396b8f58f/docs/source_en/BestPractices/Qwen3_8-Best-Practice.md) explicitly covers Qwen3.5/3.6/3.8 SFT and RL. It recommends Transformers for dense models and Megatron for MoE. | Preferred initial route: dense 27B with Transformers/PEFT, MoE 35B with Megatron if needed. Examples are not measured recipes for these models at our proof lengths. |
| **LlamaFactory** | [v0.9.5 release](https://github.com/hiyouga/LlamaFactory/releases/tag/v0.9.5) adds Qwen3.5/3.6 and Transformers v5 support. The [inspected registry](https://github.com/hiyouga/LlamaFactory/blob/ce9dc9e072f80fa3abe0989d4ab90da25f083438/src/llamafactory/extras/constants.py) has the Qwen3.5 architecture families; no explicit Qwen3.8 entry was found. | Viable Qwen3.6 SFT alternative. “LlamaFactory does not support these models” is too broad. Shared Qwen3.8 architecture alone does not verify its chat template or an end-to-end GRPO path. |
| **verl** | [Pinned Qwen3.5-35B FSDP GRPO example](https://github.com/verl-project/verl/blob/8718ca30a3f002f93b7c4fd99b9b2506718681bc/examples/grpo_trainer/run_qwen3_5_35b_fsdp.sh) exists; defaults use eight devices, with rollout TP=4. | Strong candidate for distributed/asynchronous reward scheduling once the one-batch loop works. It is not evidence that changing a flag makes the recipe fit four A100s. Exact Qwen3.8 adapter/template behavior needs testing. |
| **TRL + PEFT** | [GRPO documentation](https://huggingface.co/docs/trl/main/en/grpo_trainer) supports custom reward functions and configurable advantage scaling. | Simpler dense-model RL prototype if model loading, generation, backward, and serving all align. Generic trainer support is not model-specific validation. |
| **ms-swift DeepSeek-V4** | [Training guide](https://swift.readthedocs.io/en/latest/BestPractices/deepseek-v4.html) has an eight-device BF16 LoRA example and a 64-device full-training example. It documents conversion/merge precision caveats. | Evidence that a training path exists for the family, not that this quantized 0731 checkpoint supports four-A100 SFT/GRPO. Defer behind the smaller models. |

The inspected Qwen ms-swift guide specifies Transformers ≥5.9, flash-linear-attention ≥0.4.2, Python 3.12 guidance for that kernel stack, and serving dependencies. Qwen3.8 uses the dedicated `qwen3_8` template, including reasoning-effort control and preserved historical thinking; Qwen3.6 uses `qwen3_5`. Pin a tested dependency set in a **separate training environment** instead of upgrading `af` in place. The commits above are evidence pins, not a tested lockfile.

## Model selection experiment

1. **Correctness smoke:** exact template → completion → proof extraction → local evaluator, on one real warm-up problem. Test thinking on/off where supported and record truncation. Freeze vision components for text-only tuning.
2. **Frozen comparison:** all 15 warm-up problems, same prompts, search policy, verifier budget, and generation budget. Measure valid fraction, score gain, solved edits/hour, and best score versus elapsed time. Coding leaderboards do not answer which model edits Lean best.
3. **A100 serving test:** begin around 16K context and a 4K output cap, expanding when real inputs require it. Measure peak memory, prefill, decode, and throughput under concurrent requests. Compare TP layouts and replicas within four GPUs rather than assuming the largest TP is fastest.
4. **Training smoke:** 32–64 verified training pairs; check finite loss/gradients, masked prompts, checkpoint save/resume, adapter reload/merge, and fresh Lean validation. For GRPO, run one group of four rollouts and one update through the existing reward API, then verify policy/serving weight synchronization.
5. **Scale gate:** train 5K–20K deduplicated improvements first. Expand to larger data or longer runs only if held-out score improves over the frozen model under the same search budget. These are proposed pilot sizes, not measured optimums.
6. **Large-model comparison:** attempt an A100-compatible Qwen 397B weight-only quantization or the DeepSeek compressed checkpoint only after smaller-model throughput is known. Record conversion provenance and re-evaluate proof validity after quantization. Quantized inference weights are not automatically usable training checkpoints.

For the closed track, choose between two pinned frontier API models through the same Lean pilot and public-price accounting. Use measured improvement per dollar and whole-problem reliability, rather than committing to a provider based on general coding scores. The [proposal](PROPOSAL.md) defines the common harness and cost ledger.
