open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append]
  induction post <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append]
  repeat' split
  all_goals grind only [Lambda.LExpr.LExpr.getVars, List.mem_append]