open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append, List.mem_singleton]
  induction post <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append] <;>
    (try (split <;> (try split) <;> simp [Lambda.LExpr.LExpr.getVars])) <;>
    repeat (first | assumption | exact Or.inl | exact Or.inr |
      refine fun h => or_or_distrib_right.mpr (Or.imp ?_ ?_ h))
