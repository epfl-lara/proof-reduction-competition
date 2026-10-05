open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  induction post <;>
    simp only [substOld, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars, List.mem_append] at *
  case app =>
    split
    · split
      · exact Or.inr
      · exact fun h => Or.inl (Or.inr h)
    · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
      grind
  all_goals first | assumption | exact Or.inl | grind only