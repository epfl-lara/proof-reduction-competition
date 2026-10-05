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
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append] at *
  all_goals try solve
    | exact id
    | assumption
    | exact Or.imp (by assumption) (by assumption)
  next ih1 ih2 =>
    split
    · split <;> simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
      · exact fun h => (hx (List.mem_singleton.mp h)).elim
      · exact id
    · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append]
      exact Or.imp ih1 ih2
  next cih tih eih => exact Or.imp (Or.imp cih tih) eih
