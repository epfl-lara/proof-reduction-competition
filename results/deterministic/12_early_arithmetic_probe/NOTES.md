# Early arithmetic-hint removal: separate branch

This experiment starts from [stage 03](../03_wrappers/), not from the end of the
main portfolio. It asks whether the arithmetic-hint improvement observed late in
the pipeline is already available immediately after wrapper contraction.

```bash
python src/run_experiments.py --method arith_min \
  --input results/deterministic/03_wrappers/candidates.jsonl \
  --output results/deterministic/12_early_arithmetic_probe --workers 2 \
  --max-rounds 6 --max-trials 64 --max-sites 6 --min-gain 0.05
```

The full 15-problem score improves from **37.847467% to 38.314458%**:
**+0.466991 percentage points**, with all **36 required version checks passing**.
There is one eligible hint list and one tested candidate. Removing its six hints
from `nlinarith [...]` in `fundamental_theorem_of_variational_calculus'` changes
the complete proof to use `nlinarith []` and improves its score to **40.338240%**.
The [stage report](README.md) gives the component scores and exact accepted edit.

This establishes that the cheap arithmetic improvement was already available
before the local-fact, menu, search, and simplifier-list stages. It does **not**
establish the final result of moving this pass earlier in the whole pipeline:
early edits can change later search opportunities. Its gain must not be added
to the main portfolio's cumulative gain; the canonical pipeline already made
the analogous edit in stage 09.

Recorded wall time was **4.165 seconds**, using two workers, 16 analysis requests,
and one uncached candidate check. Existing analysis/candidate caches were reused,
and this branch overlapped the tail of the first repeated library-search pass.
These are observed costs, not a controlled timing comparison with stage 09.

The [independent audit](../validation/audit_early_arithmetic.json) verifies the
stage-03-to-branch proof chain, score arithmetic, implementation hashes, and all
36 unchanged cached reference measurements. No reference was remeasured.
