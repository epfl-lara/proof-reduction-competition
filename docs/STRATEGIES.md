# Strategy bank

Every problem receives the same seven guidance cards from
[`prompts/strategy_bank.json`](../prompts/strategy_bank.json), alongside the
[system policy](../prompts/refactor_system.md):

1. **Reuse an abstraction:** look for an existing theorem or API that captures
   the argument.
2. **Induct on evidence:** choose the induction structure that exposes the facts
   needed by the proof.
3. **Factor a local identity:** isolate a repeated mathematical step in a helper.
4. **Control inference:** make key types or arguments explicit when inference
   adds checking work.
5. **Change representation:** use a formulation that makes the proof simpler.
6. **Reduce kernel work:** compare a computational proof with a structural
   argument, existing theorem or explicit witness.
7. **Scope recursive unfolding:** test focused unfolding and proof-local
   `set_option smartUnfolding false in ...` when reduction is expensive.

The cards suggest transformations, not fixed tactic sequences or stored
solutions. Every candidate follows the same verification and score rules.
Only proof-local `smartUnfolding` with a literal boolean and an `in` scope is
accepted. Kernel bypasses such as `debug.skipKernelTC` remain rejected; the
option's own tokens count toward proof length.

See Lean's [smart-unfolding implementation](https://github.com/leanprover/lean4/blob/v4.34.1/src/Lean/Meta/WHNF.lean)
and [kernel verification documentation](https://lean-lang.org/doc/reference/latest/Elaboration-and-Compilation/).
