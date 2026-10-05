open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  rintro -
  refine List.Sublist.subset ?_
  fun_induction extractOldExprVars
  all_goals solve_by_elim only [*, List.Sublist.append, List.nil_sublist, List.sublist_append_right]