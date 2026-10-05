open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  induction post <;>
    simp_all [substOld, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars] <;> try grind
  split
  · split <;> simp_all [Lambda.LExpr.LExpr.getVars]
  · simp_all [Lambda.LExpr.LExpr.getVars]
    grind
