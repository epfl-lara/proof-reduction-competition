open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  change extractOldExprVars post ⊆ Lambda.LExpr.LExpr.getVars post
  induction h <;> simp [extractOldExprVars, Lambda.LExpr.LExpr.getVars, *]
  case app fn e m hnfn hne hwf ih1 ih2 =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]
    · next h =>
      cases hwf .oldPred
      exact False.elim (h _ _ _ rfl)
    · simp [*]
