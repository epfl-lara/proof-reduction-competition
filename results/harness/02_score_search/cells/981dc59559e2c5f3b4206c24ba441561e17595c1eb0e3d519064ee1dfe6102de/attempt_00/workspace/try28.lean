open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append]
  fun_induction substOld h2 (Lambda.LExpr.fvar m h1 ty) post <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append, *, ↓reduceIte]
  all_goals
    repeat first
      | assumption
      | exact Or.inl
      | exact Or.inr
      | refine or_or_distrib_right.mpr ∘ Or.imp ?_ ?_
