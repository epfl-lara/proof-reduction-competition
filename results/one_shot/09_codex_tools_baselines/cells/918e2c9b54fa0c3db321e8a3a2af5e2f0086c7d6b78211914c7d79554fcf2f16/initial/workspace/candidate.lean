open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  induction post generalizing h <;>
    simp [NormalizedOldExpr, extractOldExprVars,
      Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at h ⊢
  all_goals
    simp_all [extractOldExprVars, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars]
