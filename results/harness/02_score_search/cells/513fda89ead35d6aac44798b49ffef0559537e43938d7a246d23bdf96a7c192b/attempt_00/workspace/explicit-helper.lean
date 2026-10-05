open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident} (h : a.Subset c) (k : b.Subset d) :
      (a ++ b).Subset (c ++ d) :=
    List.append_subset.mpr ⟨List.subset_append_of_subset_left _ h,
      List.subset_append_of_subset_right _ k⟩
  intro h
  induction h with
  | const | op | bvar | fvar => exact List.nil_subset _
  | abs _ ih => exact ih
  | quant _ _ ih₁ ih₂ | eq _ _ ih₁ ih₂ => exact app ih₁ ih₂
  | ite _ _ _ ih₁ ih₂ ih₃ => exact app (app ih₁ ih₂) ih₃
  | app hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hfalse =>
      have hv := hn IsOldPred.oldPred
      cases hv
      exfalso
      apply hfalse
      rfl
    · exact app ihfn ihe
