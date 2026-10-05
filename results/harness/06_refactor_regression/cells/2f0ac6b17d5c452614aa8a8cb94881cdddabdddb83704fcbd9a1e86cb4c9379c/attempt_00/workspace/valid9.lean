open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  change NormalizedOldExpr post → extractOldExprVars post ⊆ Lambda.LExpr.LExpr.getVars post
  intro h
  induction h <;> simp only [extractOldExprVars, Lambda.LExpr.LExpr.getVars,
    List.nil_subset, List.append_subset, List.subset_append_of_subset_left,
    List.subset_append_of_subset_right, and_self, *]
  case app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hfalse =>
      exfalso
      have hf := hn .oldPred
      cases hf
      apply hfalse <;> rfl
    · exact List.append_subset.mpr ⟨List.subset_append_of_subset_left _ ihfn,
        List.subset_append_of_subset_right _ ihe⟩
