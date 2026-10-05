# Optimization notes

- Replaced broad progress-case `grind` searches with explicit reduction constructors, canonical-form eliminations, and typing-WF facts: all three versions pass; heartbeats fell from 59,833.58 to about 661.45.
- Used `rcases` to split the recursive progress disjunction and inferred existential reduct witnesses from reduction constructors; score improved while keeping all versions passing.
- Used `sub.wf` once for the type-argument local-closure proof, direct `ih` for the subsumption case, `subst_vars`, inferred derivation aliases, and one final `simp_all`; best measured score 66.1742 with 409 source tokens and 737.326 primary heartbeats.
- Tried focused `grind` in the sum/injection branches (failed or regressed), a helper for wrapping reduction witnesses (regressed), and broader simplification in place of `subst_vars` (failed). Retained the best all-version proof.
