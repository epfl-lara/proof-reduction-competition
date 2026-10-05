open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  change extractOldExprVars post ⊆ _
  induction h <;>
    simp_all [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars]
  case app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]
    · next hf =>
      cases hn .oldPred
      exact False.elim (hf _ _ _ rfl)
    · simp_all
