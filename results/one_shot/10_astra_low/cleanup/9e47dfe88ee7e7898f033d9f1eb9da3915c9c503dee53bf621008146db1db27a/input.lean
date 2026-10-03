open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have join {a b c d : List Expression.Ident}
      (ha : a.Subset (c ++ [h1])) (hb : b.Subset (d ++ [h1])) :
      (a ++ b).Subset ((c ++ d) ++ [h1]) := by
    intro x hx
    apply List.mem_append.mpr
    cases List.mem_append.mp hx with
    | inl hx => cases List.mem_append.mp (ha hx) with
      | inl hx => exact Or.inl (List.mem_append.mpr (Or.inl hx))
      | inr hx => exact Or.inr hx
    | inr hx => cases List.mem_append.mp (hb hx) with
      | inl hx => exact Or.inl (List.mem_append.mpr (Or.inr hx))
      | inr hx => exact Or.inr hx
  induction post <;>
    simp only [substOld, Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
  case fvar => intro x hx; exact List.mem_append.mpr (Or.inl hx)
  case op => exact List.nil_subset _
  case const => exact List.nil_subset _
  case bvar => exact List.nil_subset _
  case abs ih => exact ih
  case ite cih tih eih => exact join (join cih tih) eih
  case quant trih eih => exact join trih eih
  case eq ih1 ih2 => exact join ih1 ih2
  case app ih1 ih2 =>
    split
    · split
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
        intro x hx
        simp_all
      · simpa [Lambda.LExpr.LExpr.getVars] using ih2
    · simpa only [Lambda.LExpr.LExpr.getVars] using join ih1 ih2