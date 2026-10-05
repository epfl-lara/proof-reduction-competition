open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  clear h
  apply List.Sublist.subset
  induction post
  all_goals try (solve | assumption | exact List.nil_sublist _ | apply List.Sublist.append <;> first | assumption | apply List.Sublist.append <;> assumption)
  next fn e ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · exact List.nil_sublist _
    · exact List.Sublist.append ihfn ihe
