open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  by_cases hx : x = h1
  · simp [hx]
  simp only [List.mem_append, List.mem_singleton, hx, or_false]
  induction post <;>
    simp_all [substOld, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars, List.mem_append] <;>
    try solve | apply Or.imp <;> first | assumption | apply Or.imp <;> assumption
  split
  · split <;> simp_all [Lambda.LExpr.LExpr.getVars]
  · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
    exact Or.imp ‹_› ‹_›