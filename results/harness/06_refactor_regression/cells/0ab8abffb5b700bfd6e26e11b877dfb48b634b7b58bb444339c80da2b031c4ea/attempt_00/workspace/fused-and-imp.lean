open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  simp only [Imperative.HasVarsPure.getVars]
  intro x
  refine Decidable.not_imp_not.mp ?_
  simp only [List.mem_append, List.mem_singleton, not_or, and_imp]
  intro hp hh
  revert hp
  induction post <;> simp only [substOld] <;>
    (try split) <;> (try split) <;>
    simp only [Lambda.LExpr.LExpr.getVars, List.mem_append, not_or, List.mem_singleton] at * <;>
    repeat' (first | exact id | assumption | exact fun _ => hh | refine And.imp ?_ ?_)
