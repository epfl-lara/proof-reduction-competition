open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  refine List.Sublist.subset ?_
  simp only [Imperative.HasVarsPure.getVars]
  induction h <;> simp only [extractOldExprVars, Lambda.LExpr.LExpr.getVars,
    List.nil_sublist, List.Sublist.append, *]
  case app hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · next hfalse =>
      exfalso
      cases hn .oldPred
      apply hfalse <;> rfl
    · exact ihfn.append ihe
