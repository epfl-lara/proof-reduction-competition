open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident} (h : a.Subset c) (h' : b.Subset d) :
      (a ++ b).Subset (c ++ d) :=
    List.Subset.app (List.subset_append_of_subset_left _ h)
      (List.subset_append_of_subset_right _ h')
  intro h
  induction h with
  | const | op | bvar | fvar => exact List.nil_subset _
  | abs _ ih => exact ih
  | quant _ _ ih₁ ih₂ | eq _ _ ih₁ ih₂ => exact app ih₁ ih₂
  | ite _ _ _ ih₁ ih₂ ih₃ => exact app (app ih₁ ih₂) ih₃
  | app _ _ h ih₁ ih₂ =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hfalse =>
      cases h .oldPred
      exact False.elim (hfalse _ _ _ rfl)
    · exact app ih₁ ih₂
