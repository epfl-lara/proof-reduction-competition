open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  intro x
  simp only [Imperative.HasVarsPure.getVars, List.mem_append,
    List.mem_singleton, Classical.or_iff_not_imp_right]
  intro Hin Hx
  revert Hin
  induction post <;> dsimp only [substOld]
  case' app => split <;> try split
  all_goals
    simp only [Lambda.LExpr.LExpr.getVars, List.nil_append, List.mem_append,
      List.mem_singleton, false_implies, Hx, imp_self]
    repeat first | assumption | apply Or.imp