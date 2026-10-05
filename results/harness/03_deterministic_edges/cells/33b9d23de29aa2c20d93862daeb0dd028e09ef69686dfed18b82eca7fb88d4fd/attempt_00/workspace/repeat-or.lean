open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append, List.mem_singleton]
  by_cases hx : x = h1
  · simp [hx]
  · simp only [hx, or_false]
    induction post <;>
      simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append] <;> try (solve | exact id | (repeat (first | assumption | apply Or.imp)))
    · rename_i ih1 ih2
      split
      · split <;> simp [Lambda.LExpr.LExpr.getVars, hx]
      · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
        exact Or.imp ih1 ih2
