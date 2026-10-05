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
  case abs ih => exact ih
  case quant ih1 ih2 => exact And.imp ih1 ih2
  case ite ih1 ih2 ih3 => exact And.imp (And.imp ih1 ih2) ih3
  case eq ih1 ih2 => exact And.imp ih1 ih2
  case app ih1 ih2 =>
    split
    · split
      · simp only [Lambda.LExpr.LExpr.getVars, List.mem_singleton]
        intro hp
        exact hh
      · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append, not_or]
        exact id
    · simp only [Lambda.LExpr.LExpr.getVars, List.mem_append, not_or]
      exact And.imp ih1 ih2
