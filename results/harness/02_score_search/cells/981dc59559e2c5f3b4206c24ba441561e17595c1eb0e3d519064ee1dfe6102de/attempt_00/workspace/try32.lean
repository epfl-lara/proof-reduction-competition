open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append]
  fun_induction substOld <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append, *, ↓reduceIte]
  all_goals grind -ac -lia -ring -linarith -order -ext -etaStruct only
