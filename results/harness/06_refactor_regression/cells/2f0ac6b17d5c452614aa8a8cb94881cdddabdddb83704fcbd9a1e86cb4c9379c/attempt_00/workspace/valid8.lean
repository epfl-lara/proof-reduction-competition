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
  induction h <;> first
    | exact List.nil_subset _
    | assumption
    | exact join ‹_› ‹_›
    | exact join (join ‹_› ‹_›) ‹_›
    | skip
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
