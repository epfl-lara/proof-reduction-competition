open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have join {a b c d : List Expression.Ident}
      (ha : a ⊆ c ++ [h1]) (hb : b ⊆ d ++ [h1]) :
      a ++ b ⊆ (c ++ d) ++ [h1] := by
    intro x
    have ha := @ha x
    have hb := @hb x
    simp only [List.mem_append] at *
    grind only
  induction post <;>
    simp only [substOld, Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
  all_goals try first
    | exact List.subset_append_left _ _
    | assumption
    | exact join (by assumption) (by assumption)
  case ite cih tih eih => exact join (join cih tih) eih
  case app ih1 ih2 =>
    split
    · split <;> simp only [Lambda.LExpr.LExpr.getVars]
      · exact List.subset_append_right _ _
      · exact List.subset_append_left _ _
    · exact join ih1 ih2
