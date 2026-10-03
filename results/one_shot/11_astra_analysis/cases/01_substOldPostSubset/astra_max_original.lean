open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have join {a b c d : List Expression.Ident}
      (ha : a.Subset (c ++ [h1])) (hb : b.Subset (d ++ [h1])) :
      (a ++ b).Subset ((c ++ d) ++ [h1]) := by
    simp only [List.Subset, List.mem_append] at *
    intro x hx
    exact hx.elim
      (fun h => (ha h).elim (fun h => Or.inl (Or.inl h)) Or.inr)
      (fun h => (hb h).elim (fun h => Or.inl (Or.inr h)) Or.inr)
  simp only [Imperative.HasVarsPure.getVars]
  induction post <;> simp only [substOld, Lambda.LExpr.LExpr.getVars] at *
  case const => exact List.subset_append_left _ _
  case bvar => exact List.subset_append_left _ _
  case fvar => exact List.subset_append_left _ _
  case op => exact List.subset_append_left _ _
  case abs ih => exact ih
  case quant trih eih => exact join trih eih
  case ite cih tih eih => exact join (join cih tih) eih
  case eq ih1 ih2 => exact join ih1 ih2
  case app ih1 ih2 =>
    split
    · split
      · exact List.subset_append_right _ _
      · exact List.subset_append_left _ _
    · exact join ih1 ih2
