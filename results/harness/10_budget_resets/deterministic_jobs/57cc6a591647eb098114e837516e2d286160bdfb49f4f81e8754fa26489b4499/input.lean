open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  rintro -
  apply List.Sublist.subset
  fun_induction extractOldExprVars
  case' a.case7 => apply List.Sublist.refl
  all_goals
    try apply List.nil_sublist
    repeat apply List.Sublist.append
  all_goals assumption