open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have join {a b c d : List Expression.Ident} (h₁ : a ⊆ c) (h₂ : b ⊆ d) :=
    List.append_subset.mpr ⟨List.subset_append_of_subset_left d h₁,
      List.subset_append_of_subset_right c h₂⟩
  intro h
  induction h <;> try exact List.nil_subset _
  case abs ih => exact ih
  case quant ih₁ ih₂ | eq ih₁ ih₂ => exact join ih₁ ih₂
  case ite ih₁ ih₂ ih₃ => exact join (join ih₁ ih₂) ih₃
  case app hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hfalse =>
      exfalso
      cases hn .oldPred
      apply hfalse <;> rfl
    · exact join ihfn ihe
