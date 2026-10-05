open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  simp only [Imperative.HasVarsPure.getVars]
  intro x
  by_cases hh : x = h1
  · simp [hh]
  · simp only [List.mem_append, List.mem_singleton, hh, or_false]
    refine Decidable.not_imp_not.mp ?_
    induction post <;> simp only [substOld] <;> intro hp <;>
      (try split) <;> (try split) <;>
      simp_all only [substOld, Lambda.LExpr.LExpr.getVars,
        List.mem_append, List.mem_singleton, List.not_mem_nil, not_or,
        false_or, not_false_eq_true, true_and, and_true, true_implies, implies_true]
