open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  change extractOldExprVars post ⊆ Lambda.LExpr.LExpr.getVars post
  induction h <;> simp_all [extractOldExprVars, Lambda.LExpr.LExpr.getVars]
  case app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]
    · next hfalse =>
      have hv := hn IsOldPred.oldPred
      cases hv
      exfalso
      apply hfalse
      rfl
    · simp_all
