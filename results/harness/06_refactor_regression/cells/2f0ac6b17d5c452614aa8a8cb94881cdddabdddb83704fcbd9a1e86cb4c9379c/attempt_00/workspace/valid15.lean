open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  refine List.Sublist.subset ?_
  induction h <;> try exact List.nil_sublist _
  case abs ih => exact ih
  case quant ih₁ ih₂ | eq ih₁ ih₂ => exact ih₁.append ih₂
  case ite ih₁ ih₂ ih₃ => exact (ih₁.append ih₂).append ih₃
  case app hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · next hfalse =>
      exfalso
      cases hn .oldPred
      apply hfalse <;> rfl
    · exact ihfn.append ihe
