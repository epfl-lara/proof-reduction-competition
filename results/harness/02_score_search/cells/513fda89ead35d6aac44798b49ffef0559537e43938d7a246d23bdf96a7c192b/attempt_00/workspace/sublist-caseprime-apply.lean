open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  apply List.Sublist.subset
  induction h
  case' a.app =>
    unfold extractOldExprVars
    split
    apply List.Sublist.refl
  all_goals
    repeat first | assumption | apply List.nil_sublist | apply List.Sublist.append
