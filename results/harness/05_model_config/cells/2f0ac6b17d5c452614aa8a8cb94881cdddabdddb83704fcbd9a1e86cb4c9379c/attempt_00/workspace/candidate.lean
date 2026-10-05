open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  rintro -
  apply List.Sublist.subset
  change List.Sublist _ (Lambda.LExpr.LExpr.getVars post)
  induction post
  all_goals try apply_rules only [List.Sublist.append, List.nil_sublist, *]
  unfold extractOldExprVars
  split <;> apply_rules only [List.Sublist.append, List.nil_sublist, List.Sublist.refl, *]
