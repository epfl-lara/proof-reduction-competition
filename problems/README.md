# Warm-up problems: original, deterministic, and best proofs

Each of the 15 folders contains exactly three Lean files:

- `initial.lean`: the original benchmark declaration and proof, unchanged.
- `deterministic.lean`: the saved model-free D0 cleanup result from `results/deterministic/selected_candidates.jsonl` (the automatic portfolio plus two repeated sweeps).
- `best.lean`: the highest local combined score found in the saved experiment evidence for that problem, requiring successful checks on **every listed Lean version**.

Files include the complete original source-file context at the **primary pinned version**, or the benchmark's imports/header for PutnamBench. Search for `TARGET DECLARATION BEGIN` to jump to the relevant theorem; all other declarations are context. Each variant differs only in the target declaration. Common comments and elaboration options were added for this export. Source copyright notices are preserved.

`best` pools results across methods, models, and intermediate checked attempts. This is a per-problem selection made after the experiments, not a single model or harness run. Selection uses `(length reduction + local heartbeat reduction + compatibility) / 3`, with the original fixed denominators. Saved candidate hashes, token counts, version coverage, environment fingerprints, and score arithmetic were audited. References were not remeasured.

Snapshot: `2026-10-04T22:16:39.036874+00:00`. Ongoing experiments can produce later improvements; these files do not update automatically.

## Problem index

Links open the target declaration. Scores are local combined percentages, not organizer-grader results. Original identity score: 33.3333% for every problem.

| Problem | Initial | Deterministic | Best | D0 score | Best score | Primary Lean |
| --- | --- | --- | --- | ---: | ---: | --- |
| `CallElimCorrect.substOldPostSubset` | [initial](strata_subst_old_post_subset/initial.lean#L3101) | [deterministic](strata_subst_old_post_subset/deterministic.lean#L3101) | [best](strata_subst_old_post_subset/best.lean#L3101) | 37.4070 | 90.0634 | v4.26.0 |
| `CallElimCorrect.extractedOldExprInVars` | [initial](strata_extracted_old_expr_in_vars/initial.lean#L2870) | [deterministic](strata_extracted_old_expr_in_vars/deterministic.lean#L2870) | [best](strata_extracted_old_expr_in_vars/best.lean#L2870) | 37.3956 | 91.1280 | v4.26.0 |
| `Core.InitsUpdatesComm` | [initial](strata_inits_updates_comm/initial.lean#L962) | [deterministic](strata_inits_updates_comm/deterministic.lean#L962) | [best](strata_inits_updates_comm/best.lean#L962) | 50.4434 | 86.2391 | v4.29.1 |
| `fundamental_theorem_of_variational_calculus'` | [initial](physlib_variational_calculus/initial.lean#L111) | [deterministic](physlib_variational_calculus/deterministic.lean#L111) | [best](physlib_variational_calculus/best.lean#L111) | 43.4620 | 90.0256 | v4.32.0 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | [initial](physlib_electric_field_extrema/initial.lean#L388) | [deterministic](physlib_electric_field_extrema/deterministic.lean#L388) | [best](physlib_electric_field_extrema/best.lean#L388) | 47.1427 | 84.9738 | v4.32.0 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | [initial](physlib_wick_time_order/initial.lean#L174) | [deterministic](physlib_wick_time_order/deterministic.lean#L174) | [best](physlib_wick_time_order/best.lean#L174) | 40.5626 | 84.0782 | v4.32.0 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | [initial](cslib_fsub_progress/initial.lean#L88) | [deterministic](cslib_fsub_progress/deterministic.lean#L88) | [best](cslib_fsub_progress/best.lean#L88) | 34.0353 | 87.8260 | v4.33.0-rc2 |
| `Cslib.SKI.parallelReduction_diamond` | [initial](cslib_ski_diamond/initial.lean#L154) | [deterministic](cslib_ski_diamond/deterministic.lean#L154) | [best](cslib_ski_diamond/best.lean#L154) | 33.5138 | 74.9675 | v4.33.0-rc2 |
| `Cslib.CCS.bisimilarity_congr_choice` | [initial](cslib_ccs_choice_congruence/initial.lean#L323) | [deterministic](cslib_ccs_choice_congruence/deterministic.lean#L323) | [best](cslib_ccs_choice_congruence/best.lean#L323) | 33.3331 | 85.7192 | v4.33.0-rc2 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | [initial](arklib_fiberwise_distance/initial.lean#L1277) | [deterministic](arklib_fiberwise_distance/deterministic.lean#L1277) | [best](arklib_fiberwise_distance/best.lean#L1277) | 38.0436 | 87.8988 | v4.31.0 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | [initial](arklib_fold_evaluation/initial.lean#L827) | [deterministic](arklib_fold_evaluation/deterministic.lean#L827) | [best](arklib_fold_evaluation/best.lean#L827) | 39.8992 | 91.5594 | v4.31.0 |
| `interleaved_affine_gaps_imply_tensor_gaps` | [initial](arklib_interleaved_tensor_gaps/initial.lean#L1219) | [deterministic](arklib_interleaved_tensor_gaps/deterministic.lean#L1219) | [best](arklib_interleaved_tensor_gaps/best.lean#L1219) | 42.9492 | 89.0994 | v4.31.0 |
| `putnam_1964_a4` | [initial](putnam_1964_a4/initial.lean#L21) | [deterministic](putnam_1964_a4/deterministic.lean#L21) | [best](putnam_1964_a4/best.lean#L21) | 73.3195 | 95.8001 | v4.25.0 |
| `putnam_1964_b2` | [initial](putnam_1964_b2/initial.lean#L21) | [deterministic](putnam_1964_b2/deterministic.lean#L21) | [best](putnam_1964_b2/best.lean#L21) | 87.0543 | 99.1371 | v4.25.0 |
| `putnam_1995_a3` | [initial](putnam_1995_a3/initial.lean#L21) | [deterministic](putnam_1995_a3/deterministic.lean#L21) | [best](putnam_1995_a3/best.lean#L21) | 55.1606 | 95.6300 | v4.25.0 |

Mean combined scores: **deterministic 46.2481%**, **best across experiments 88.9430%**. Both selections have saved passing evidence for all 36 required theorem/version combinations.

## Compile a file

These files need the corresponding pinned project and its built dependencies. There is no shared Lean/Mathlib version across all 15 problems. Use the prepared projects recorded in [manifest.json](manifest.json); its absolute paths refer to this machine.

From the repository root, this example compiles one exported file:

```bash
python - <<'PYCODE'
import json
import subprocess
from pathlib import Path

root = Path("problems").resolve()
manifest = json.loads((root / "manifest.json").read_text())
problem = next(p for p in manifest["problems"]
               if p["directory"] == "cslib_ski_diamond")
variant = "best"  # or "initial" / "deterministic"
subprocess.run(
    ["lake", "env", "lean", str(root / problem["variants"][variant]["file"])],
    cwd=problem["project_directory"], check=True,
)
PYCODE
```

The exported full files are pinned to the primary environment. Cross-version results refer to the target declaration evaluated in each version's own source context; do not assume the whole primary-version source file works unchanged in older releases.

## Provenance and validation

[manifest.json](manifest.json) records each full theorem name, project/version/commit, source and exported-file hashes, target line positions, proof-token count, component scores, per-version heartbeat measurements, and the exact source artifact/JSON field for the chosen proof. Paths beginning `results/` or `data/` are relative to the repository root.

Fresh export checks: **45/45 full files compiled successfully** with `lake env lean` in their primary pinned environments. Commands, outputs, and durations are saved in the manifest. This validation compiles the files without collecting heartbeats or refreshing reference measurements.
