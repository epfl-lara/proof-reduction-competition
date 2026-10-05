open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  refine Decidable.not_imp_not.mp ?_
  intro hn
  simp only [List.mem_append, List.mem_singleton, not_or] at hn
  obtain ⟨hp, hh⟩ := hn
  revert hp
  induction post <;> intro hp
  case app =>
    simp only [substOld]
    split
    · split <;> simp_all [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
    · simp_all [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
  all_goals simp_all [substOld, Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
