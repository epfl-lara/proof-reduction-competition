open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro H
  induction post <;> simp_all [Imperative.HasVarsPure.getVars,
    extractOldExprVars, Lambda.LExpr.LExpr.getVars]
