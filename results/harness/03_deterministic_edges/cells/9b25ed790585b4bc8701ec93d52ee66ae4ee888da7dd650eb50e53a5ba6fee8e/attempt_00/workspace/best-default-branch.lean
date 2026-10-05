open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  apply List.Sublist.subset
  induction h <;> repeat' first
  | assumption
  | apply List.nil_sublist
  | apply List.Sublist.append
  next ih1 ih2 =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · exact List.nil_sublist _
    · exact ih1.append ih2
