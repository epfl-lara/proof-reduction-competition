open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  refine List.Sublist.subset ?_
  induction h
  case' app =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
  repeat' apply List.Sublist.append
  all_goals first | assumption | apply List.nil_sublist
