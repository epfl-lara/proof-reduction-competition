open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  apply List.Sublist.subset
  induction h <;> unfold extractOldExprVars <;> (try split) <;>
    solve_by_elim only [*, List.nil_sublist, List.Sublist.append, List.Sublist.refl]
