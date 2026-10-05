open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  by_cases hx : x = h1
  · intro _
    exact List.mem_append_right _ (List.mem_singleton.mpr hx)
  simp only [Imperative.HasVarsPure.getVars, List.mem_append,
    List.mem_singleton, hx, or_false]
  induction post <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append] at * <;>
    try solve_by_elim [id, Or.imp]
  split
  · split <;> simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
    · exact fun h => (hx (List.mem_singleton.mp h)).elim
    · exact id
  · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
    solve_by_elim [Or.imp]
