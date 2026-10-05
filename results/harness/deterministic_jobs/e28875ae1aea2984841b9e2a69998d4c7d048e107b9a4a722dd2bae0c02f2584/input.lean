open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append]
  by_cases hx : x ∈ [h1] <;> simp only [hx, or_true, or_false, implies_true]
  induction post <;> simp only [substOld]
  repeat' split
  all_goals
    simp only [Lambda.LExpr.LExpr.getVars, List.mem_append,
      List.not_mem_nil, hx, false_or, false_implies]
    repeat' first | assumption | exact id | apply Or.imp