open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [List.mem_append, List.mem_singleton]
  by_cases hx : x = h1
  · simp [hx]
  · simp only [hx, or_false]
    induction post <;>
      simp only [substOld, Imperative.HasVarsPure.getVars,
        Lambda.LExpr.LExpr.getVars, List.mem_append] at * <;> try (solve | exact id | assumption)
    · rename_i ih1 ih2
      exact Or.imp ih1 ih2
    · rename_i ih1 ih2
      split
      · split <;> simp [Lambda.LExpr.LExpr.getVars, hx]
      · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
        exact Or.imp ih1 ih2
    · rename_i ih1 ih2 ih3
      exact Or.imp (Or.imp ih1 ih2) ih3
    · rename_i ih1 ih2
      exact Or.imp ih1 ih2
