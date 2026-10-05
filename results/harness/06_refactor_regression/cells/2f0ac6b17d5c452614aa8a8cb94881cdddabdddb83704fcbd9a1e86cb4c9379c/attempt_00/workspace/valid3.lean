open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  change NormalizedOldExpr post → extractOldExprVars post ⊆ Lambda.LExpr.LExpr.getVars post
  intro h
  induction h <;> simp_all [extractOldExprVars, Lambda.LExpr.LExpr.getVars]
  case app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]
    · next hfalse =>
      exfalso
      have hf := hn .oldPred
      cases hf
      apply hfalse <;> rfl
    · simp [ihfn, ihe]
