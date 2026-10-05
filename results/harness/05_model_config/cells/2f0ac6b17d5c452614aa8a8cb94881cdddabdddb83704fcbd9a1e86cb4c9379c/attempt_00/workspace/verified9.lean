open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  clear h
  apply List.Sublist.subset
  induction post
  all_goals try apply_rules only [List.nil_sublist, List.Sublist.append, *]
  unfold extractOldExprVars
  split <;> first | exact List.Sublist.refl _ | exact List.nil_sublist _ | apply List.Sublist.append <;> assumption
