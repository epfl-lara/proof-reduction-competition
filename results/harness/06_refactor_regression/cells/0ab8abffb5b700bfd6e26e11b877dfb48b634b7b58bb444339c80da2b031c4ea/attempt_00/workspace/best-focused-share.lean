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
  induction post <;>
    simp only [substOld, Lambda.LExpr.LExpr.getVars, List.mem_append, not_or] at * <;>
    try exact id
  case app ih1 ih2 =>
    split <;> (try split) <;>
      simp only [Lambda.LExpr.LExpr.getVars, List.mem_append, not_or, List.mem_singleton] <;>
      first | exact fun _ => hh | exact id | exact And.imp ih1 ih2
  all_goals repeat' (first | assumption | refine And.imp ?_ ?_)
