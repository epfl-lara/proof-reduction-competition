open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append]
  fun_induction substOld
  case case1 | case2 | case3 | case4 | case8 => exact Or.inl
  case case7 => exact Or.inr
  all_goals
    simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
    repeat first | assumption | apply or_or_distrib_right.mpr ∘ Or.imp ?_ ?_