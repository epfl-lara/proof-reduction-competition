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
    simp_all +contextual only [substOld, Lambda.LExpr.LExpr.getVars,
      List.mem_append, or_imp, imp_self, true_or, or_true, and_self]
  split
  · split <;> simp_all only [Lambda.LExpr.LExpr.getVars, List.mem_singleton,
      hx, false_implies, imp_self]
  · simp_all +contextual only [Lambda.LExpr.LExpr.getVars, List.mem_append,
      or_imp, imp_self, true_or, or_true, and_self]
