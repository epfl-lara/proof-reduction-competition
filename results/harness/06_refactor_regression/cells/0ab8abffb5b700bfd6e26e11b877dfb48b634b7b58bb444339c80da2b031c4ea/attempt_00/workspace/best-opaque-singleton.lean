open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  simp only [Imperative.HasVarsPure.getVars]
  intro x
  induction post <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append] at * <;>
    try exact Or.inl
  all_goals
    try (split <;> (try split) <;>
      simp only [Lambda.LExpr.LExpr.getVars, List.mem_append] <;>
      (try exact Or.inl) <;> (try exact Or.inr))
  all_goals repeat' (first | assumption |
    refine or_or_distrib_right.mpr ∘ Or.imp ?_ ?_)
