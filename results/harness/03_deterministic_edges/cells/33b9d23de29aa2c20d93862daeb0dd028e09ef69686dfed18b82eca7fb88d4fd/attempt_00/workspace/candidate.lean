open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append, List.mem_singleton,
    Decidable.or_iff_not_imp_right]
  apply flip
  intro hx
  induction post <;>
    unfold substOld <;>
    (repeat split) <;>
    simp only [Lambda.LExpr.LExpr.getVars, List.mem_append, List.mem_singleton,
      hx, false_implies, imp_self] <;>
    (repeat apply Or.imp) <;> assumption
