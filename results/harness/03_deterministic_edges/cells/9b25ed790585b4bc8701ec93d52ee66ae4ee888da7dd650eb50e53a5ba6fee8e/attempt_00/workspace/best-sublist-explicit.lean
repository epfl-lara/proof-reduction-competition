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
  | quant _ _ ih1 ih2 | eq _ _ ih1 ih2 => exact ih1.append ih2
  | ite _ _ _ ih1 ih2 ih3 => exact (ih1.append ih2).append ih3
  | app hnfn hne hwf ih1 ih2 =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · next h =>
      cases hwf .oldPred
      exact False.elim (h _ _ _ rfl)
    · exact ih1.append ih2
