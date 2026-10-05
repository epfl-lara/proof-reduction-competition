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
      dsimp only [substOld, Lambda.LExpr.LExpr.getVars] <;>
      (try simp only [List.mem_append, imp_self]) <;>
      (try (split <;> (try split) <;> simp [Lambda.LExpr.LExpr.getVars, hx])) <;>
      repeat (first | assumption | apply Or.imp)
