open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident} (h : a ⊆ b) (k : c ⊆ d) :
      a ++ c ⊆ b ++ d :=
    List.append_subset.mpr ⟨List.subset_append_of_subset_left _ h,
      List.subset_append_of_subset_right _ k⟩
  intro h
  induction h with
  | const | op | bvar | fvar => exact List.nil_subset _
  | abs _ ih => exact ih
  | quant _ _ ih1 ih2 | eq _ _ ih1 ih2 => exact app ih1 ih2
  | ite _ _ _ ih1 ih2 ih3 => exact app (app ih1 ih2) ih3
  | app hnfn hne hwf ih1 ih2 =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next h =>
      cases hwf .oldPred
      exact False.elim (h _ _ _ rfl)
    · exact app ih1 ih2
