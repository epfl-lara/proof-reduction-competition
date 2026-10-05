open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  dsimp only [Imperative.HasVarsPure.getVars]
  intro x
  induction post <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars,
      List.mem_append, List.mem_singleton, List.not_mem_nil, false_or, or_false] at *
  case app =>
    split
    · split
      · exact fun h => Or.inr (List.mem_singleton.mp h)
      · exact fun h => Or.inl (List.mem_append.mp h)
    · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
      grind only
  all_goals grind only
