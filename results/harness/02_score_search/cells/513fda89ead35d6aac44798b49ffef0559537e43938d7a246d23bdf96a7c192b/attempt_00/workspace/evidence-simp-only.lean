open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  change extractOldExprVars post ⊆ Lambda.LExpr.LExpr.getVars post
  induction h <;> simp only [extractOldExprVars, Lambda.LExpr.LExpr.getVars, List.nil_subset,
    List.append_subset, List.subset_append_of_subset_left,
    List.subset_append_of_subset_right, *, and_self]
  case app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hfalse =>
      have hv := hn IsOldPred.oldPred
      cases hv
      exfalso
      apply hfalse
      rfl
    · simpa only [List.append_subset] using
        And.intro (List.subset_append_of_subset_left _ ihfn)
          (List.subset_append_of_subset_right _ ihe)
