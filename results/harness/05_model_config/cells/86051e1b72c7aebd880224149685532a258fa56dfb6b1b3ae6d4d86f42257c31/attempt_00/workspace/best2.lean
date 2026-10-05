open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  change extractOldExprVars post ⊆ _
  induction h <;>
    simp_all only [List.nil_subset, List.append_subset,
      List.subset_append_of_subset_left, List.subset_append_of_subset_right, and_self,
      Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars]
  case app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]
    · next hf =>
      cases hn .oldPred
      exact False.elim (hf _ _ _ rfl)
    · exact List.append_subset.mpr
        ⟨List.subset_append_of_subset_left _ ihfn,
         List.subset_append_of_subset_right _ ihe⟩
