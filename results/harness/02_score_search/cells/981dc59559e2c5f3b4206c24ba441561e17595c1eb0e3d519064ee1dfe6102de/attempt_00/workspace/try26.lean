open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append]
  induction post <;> dsimp only [substOld]
  case' app => split <;> try split
  all_goals try first | assumption | exact Or.inl | exact Or.inr
  all_goals
    simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
    repeat first
      | assumption
      | refine or_or_distrib_right.mpr ∘ Or.imp ?_ ?_
