open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have join {a b c d : List Expression.Ident} (h₁ : a ⊆ c) (h₂ : b ⊆ d) :
      a ++ b ⊆ c ++ d :=
    List.append_subset.mpr ⟨List.subset_append_of_subset_left _ h₁,
      List.subset_append_of_subset_right _ h₂⟩
  change NormalizedOldExpr post → extractOldExprVars post ⊆ Lambda.LExpr.LExpr.getVars post
  intro h
  induction h with
  | const | op | bvar | fvar => exact List.nil_subset _
  | abs h ih => exact ih
  | quant h₁ h₂ ih₁ ih₂ | eq h₁ h₂ ih₁ ih₂ => exact join ih₁ ih₂
  | ite h₁ h₂ h₃ ih₁ ih₂ ih₃ => exact join (join ih₁ ih₂) ih₃
  | @app fn e m hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hfalse =>
      exfalso
      have hf := hn .oldPred
      cases hf
      apply hfalse <;> rfl
    · exact join ihfn ihe
