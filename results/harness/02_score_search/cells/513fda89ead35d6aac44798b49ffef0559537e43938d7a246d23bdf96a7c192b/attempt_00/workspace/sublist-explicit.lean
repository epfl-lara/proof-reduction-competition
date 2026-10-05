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
  | app hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · next hfalse =>
      have hv := hn IsOldPred.oldPred
      cases hv
      exfalso
      apply hfalse
      rfl
    · exact ihfn.append ihe
