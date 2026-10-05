open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  induction post <;>
    simp [substOld, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars, List.Subset] at *
  all_goals
    repeat first | split | simp_all [Lambda.LExpr.LExpr.getVars, List.Subset]
    all_goals grind