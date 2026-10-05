open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  refine Decidable.not_imp_not.mp ?_
  simp only [Imperative.HasVarsPure.getVars, List.mem_append,
    List.mem_singleton, not_or]
  rintro ⟨hp, hx⟩
  revert hp
  induction post <;> intro hp <;>
    simp_all only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append,
      not_or, List.not_mem_nil, true_and, and_self, implies_true, true_implies, not_false_eq_true]
  split
  · split <;> simp_all [Lambda.LExpr.LExpr.getVars]
  · simp_all only [Lambda.LExpr.LExpr.getVars, List.mem_append, not_or, and_self]
