open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  clear h
  change extractOldExprVars post ⊆ Lambda.LExpr.LExpr.getVars post
  induction post <;> simp [extractOldExprVars, Lambda.LExpr.LExpr.getVars, *]
  case app fn e ihfn ihe =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]
    · exact List.Subset.empty
    · simp [*]
