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
    induction post <;>
      simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append] at * <;>
      try exact id
    case neg.app ih1 ih2 =>
      split <;> (try split) <;>
        simp only [Lambda.LExpr.LExpr.getVars, List.mem_append, List.mem_singleton] <;>
        first | exact fun h => (hh h).elim | exact id | exact Or.imp ih1 ih2
    all_goals repeat' (first | assumption | refine Or.imp ?_ ?_)
