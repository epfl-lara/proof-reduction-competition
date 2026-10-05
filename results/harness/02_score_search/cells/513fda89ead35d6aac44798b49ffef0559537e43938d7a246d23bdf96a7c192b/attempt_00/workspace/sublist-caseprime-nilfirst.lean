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
    repeat first | apply List.nil_sublist | assumption | apply List.Sublist.append
