open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  induction h <;>
    simp_all +contextual [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars, List.Subset, List.mem_append, or_imp]
  rename_i hn ih₁ ih₂
  unfold extractOldExprVars
  split
  · simp [Lambda.LExpr.LExpr.getVars, List.Subset, List.mem_append, or_imp]
  · next hf =>
    cases hn .oldPred
    exact False.elim (hf _ _ _ rfl)
  · simp_all +contextual [or_imp]
