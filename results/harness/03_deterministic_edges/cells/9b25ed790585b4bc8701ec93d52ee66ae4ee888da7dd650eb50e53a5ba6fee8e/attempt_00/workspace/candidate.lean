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
    · apply List.Sublist.refl
  repeat' apply List.Sublist.append
  all_goals first | assumption | apply List.nil_sublist
