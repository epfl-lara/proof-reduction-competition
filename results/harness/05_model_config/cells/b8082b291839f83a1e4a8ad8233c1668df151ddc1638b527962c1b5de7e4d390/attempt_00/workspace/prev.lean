open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  induction post <;>
    simp only [substOld, Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars,
      List.mem_append, List.mem_singleton, List.not_mem_nil, false_or, or_false] at *
  case app =>
    split
    · split <;> simp_all [Lambda.LExpr.LExpr.getVars]
    · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
      grind only
  all_goals grind only
