open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  simp only [Imperative.HasVarsPure.getVars]
  intro x
  refine Decidable.not_imp_not.mp ?_
  simp only [List.mem_append, List.mem_singleton, not_or, and_imp]
  intro hp hh
  revert hp
  induction post <;> simp only [substOld] <;> intro hp <;>
    (try split) <;> (try split) <;>
    simp_all only [Lambda.LExpr.LExpr.getVars,
      List.mem_append, List.mem_singleton, List.not_mem_nil, not_or,
      false_or, not_false_eq_true, true_and, and_true, true_implies, implies_true]
