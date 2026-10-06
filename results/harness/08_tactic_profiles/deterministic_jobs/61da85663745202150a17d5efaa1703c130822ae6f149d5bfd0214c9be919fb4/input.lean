open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append,
    List.mem_singleton, Classical.or_iff_not_imp_right]
  refine imp.swap.mpr ?_
  intro hx
  induction post <;> unfold substOld
  all_goals repeat split
  all_goals simp only [Lambda.LExpr.LExpr.getVars, List.mem_append,
    List.mem_singleton, hx, false_implies]
  all_goals repeat (first | assumption | apply Or.imp | intro)