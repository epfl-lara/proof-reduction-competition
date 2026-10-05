open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  apply List.Sublist.subset
  induction h with
  | const | op | bvar | fvar => exact List.nil_sublist _
  | abs _ ih => exact ih
  | quant _ _ ih₁ ih₂ | eq _ _ ih₁ ih₂ => exact ih₁.append ih₂
  | ite _ _ _ ih₁ ih₂ ih₃ => exact (ih₁.append ih₂).append ih₃
  | app _ _ hn ih₁ ih₂ =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · next hf =>
      cases hn .oldPred
      exact False.elim (hf _ _ _ rfl)
    · exact ih₁.append ih₂