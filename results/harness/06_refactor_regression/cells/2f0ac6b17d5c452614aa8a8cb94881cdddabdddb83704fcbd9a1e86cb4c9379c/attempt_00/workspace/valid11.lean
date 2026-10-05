open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have join {a b c d : List Expression.Ident} (h₁ : a ⊆ c) (h₂ : b ⊆ d) :
      a ++ b ⊆ c ++ d :=
    List.append_subset.mpr ⟨List.subset_append_of_subset_left _ h₁,
      List.subset_append_of_subset_right _ h₂⟩
  intro h
  induction h <;> try exact List.nil_subset _
  case abs ih => exact ih
  case quant ih₁ ih₂ | eq ih₁ ih₂ => exact join ih₁ ih₂
  case ite ih₁ ih₂ ih₃ => exact join (join ih₁ ih₂) ih₃
  case app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hfalse =>
      exfalso
      have hf := hn .oldPred
      cases hf
      apply hfalse <;> rfl
    · exact join ihfn ihe
